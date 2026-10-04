from __future__ import annotations
import argparse, ctypes, platform, re, subprocess, threading, time
from pathlib import Path

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
from pynput.keyboard import Controller, Key, Listener

SYSTEM = platform.system()
SAMPLE_RATE = 16000

SPECIAL_KEYS = {
    "INSERT": Key.insert,
    "DELETE": Key.delete,
    "HOME": Key.home,
    "END": Key.end,
    "PAGEUP": Key.page_up,
    "PAGEDOWN": Key.page_down,
    "PAUSE": Key.pause,
    "SCROLLLOCK": Key.scroll_lock,
    **{f"F{i}": getattr(Key, f"f{i}") for i in range(1, 21) if hasattr(Key, f"f{i}")},
}

def parse_key(name: str):
    name = name.upper()
    if name in SPECIAL_KEYS:
        return SPECIAL_KEYS[name]
    if len(name) == 1:
        return name.lower()
    raise ValueError(f"Unsupported key: {name}")

def log(s: str):
    print(f"[{time.strftime('%H:%M:%S')}] {s}", flush=True)

def frontmost_app_name():
    if SYSTEM == "Windows":
        try:
            u = ctypes.windll.user32
            hwnd = u.GetForegroundWindow()
            n = u.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(n + 1)
            u.GetWindowTextW(hwnd, buf, n + 1)
            return buf.value or None
        except Exception:
            return None
    return None

def wow_frontmost():
    n = (frontmost_app_name() or "").lower()
    return "warcraft" in n or n.startswith("wow")

class Recorder:
    def __init__(self, device=None):
        self.device = device
        self.chunks = []
        self.stream = None
        self.lock = threading.Lock()

    def _cb(self, data, frames, info, status):
        if status:
            log(f"Audio: {status}")
        with self.lock:
            self.chunks.append(data[:,0].copy())

    def start(self):
        self.chunks = []
        self.stream = sd.InputStream(
            samplerate=SAMPLE_RATE, channels=1, dtype="float32",
            blocksize=1024, device=self.device, callback=self._cb
        )
        self.stream.start()

    def stop(self):
        if self.stream:
            self.stream.stop(); self.stream.close(); self.stream = None
        with self.lock:
            out = np.concatenate(self.chunks) if self.chunks else np.zeros(0, dtype="float32")
            self.chunks = []
        return out

class App:
    def __init__(self, args):
        self.args = args
        self.state = "idle"
        self.channel = "general"
        self.prefix = "/1 "
        self.active_channel = None
        self.active_prefix = None
        self.recorder = Recorder(args.input_device)
        self.keyboard = Controller()
        self.model = WhisperModel(args.model, device="cpu", compute_type="int8")
        self.lock = threading.Lock()
        self.last_toggle = 0.0

    def start_recording(self):
        with self.lock:
            now = time.monotonic()
            if now - self.last_toggle < 0.25 or self.state != "idle":
                return
            self.last_toggle = now
            try:
                self.recorder.start()
            except Exception as e:
                log(f"Mic failed: {e}")
                return
            self.active_channel = self.channel
            self.active_prefix = self.prefix
            self.state = "recording"
            log(f"Recording... channel={self.active_channel} destination={self.active_prefix.strip()}")

    def send_recording(self):
        with self.lock:
            now = time.monotonic()
            if now - self.last_toggle < 0.25 or self.state != "recording":
                return
            self.last_toggle = now
            audio = self.recorder.stop()
            self.state = "transcribing"
            log(f"Send pressed. destination={self.active_prefix.strip()} Transcribing...")
            threading.Thread(target=self.finish, args=(audio,), daemon=True).start()

    def select_channel(self, name, prefix):
        self.channel, self.prefix = name, prefix
        if self.state == "recording":
            self.active_channel = name
            self.active_prefix = prefix
            log(f"Recording destination changed: {name} ({prefix.strip()})")
        elif self.state == "transcribing":
            log(f"Channel queued for next message: {name}")
        else:
            log(f"Channel: {name}")

    def finish(self, audio):
        try:
            segs, _ = self.model.transcribe(
                audio, beam_size=1, best_of=1, vad_filter=True,
                condition_on_previous_text=False, without_timestamps=True
            )
            text = re.sub(r"\s+", " ", " ".join(s.text.strip() for s in segs)).strip()
            if not text:
                log("Nothing transcribed")
                return
            log(f"Transcript: {text}")
            if not wow_frontmost() and not self.args.any_app:
                log(f"WoW is not frontmost ({frontmost_app_name()}); not typing")
                return
            outgoing = (self.active_prefix or self.prefix) + text
            log(f"Sending: {outgoing}")
            self.deliver(outgoing)
            log(f"Sent to {self.active_channel or self.channel}")
        except Exception as e:
            log(f"Transcription/send failed: {e}")
        finally:
            self.state = "idle"
            self.active_channel = None
            self.active_prefix = None

    def type_text(self, text):
        for ch in text:
            self.keyboard.press(ch); self.keyboard.release(ch)
            time.sleep(0.002)

    def deliver(self, text):
        # Open chat, type and send the dictated message.
        self.keyboard.press(Key.enter); self.keyboard.release(Key.enter)
        time.sleep(0.12)
        self.type_text(text)
        time.sleep(0.04)
        self.keyboard.press(Key.enter); self.keyboard.release(Key.enter)

        # WoW Forever's gamepad chat style can leave the edit box focused after
        # sending. Use the same secure Blizzard click path proven by the original
        # GamepadSpeak helper to deactivate it without addon taint.
        time.sleep(0.15)
        close_command = "/click InputFunctionBindingButton_PAD2 LeftButton 1"
        self.type_text(close_command)
        time.sleep(0.03)
        self.keyboard.press(Key.enter); self.keyboard.release(Key.enter)

    def run(self):
        bindings = {
            "toggle": parse_key(self.args.toggle_key),
            "general": parse_key(self.args.general_key),
            "trade": parse_key(self.args.trade_key),
            "party": parse_key(self.args.party_key),
            "guild": parse_key(self.args.guild_key),
            "say": parse_key(self.args.say_key),
        }
        channels = {
            bindings["general"]: ("general", "/1 "),
            bindings["trade"]: ("trade", "/2 "),
            bindings["party"]: ("party", "/p "),
            bindings["guild"]: ("guild", "/g "),
            bindings["say"]: ("say", "/s "),
        }

        log("ForeverVoice ready")
        log(f"Mic: {sd.query_devices(self.args.input_device, 'input')['name'] if self.args.input_device is not None else sd.query_devices(kind='input')['name']}")
        log(f"Voice toggle={self.args.toggle_key}")
        log(
            f"Channels: General={self.args.general_key}, Trade={self.args.trade_key}, "
            f"Party={self.args.party_key}, Guild={self.args.guild_key}, Say={self.args.say_key}"
        )

        def on_press(key):
            if key == bindings["toggle"]:
                if self.state == "idle":
                    self.start_recording()
                elif self.state == "recording":
                    self.send_recording()
                return
            if key in channels:
                self.select_channel(*channels[key])

        with Listener(on_press=on_press) as listener:
            listener.join()

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--toggle-key", default="F13")
    p.add_argument("--general-key", default="F15")
    p.add_argument("--trade-key", default="F16")
    p.add_argument("--party-key", default="F17")
    p.add_argument("--guild-key", default="F18")
    p.add_argument("--say-key", default="F19")
    p.add_argument("--input-device", type=int)
    p.add_argument("--model", default="base")
    p.add_argument("--any-app", action="store_true")
    args = p.parse_args()

    try:
        for name in (
            args.toggle_key, args.general_key, args.trade_key,
            args.party_key, args.guild_key, args.say_key
        ):
            parse_key(name)
    except ValueError as e:
        raise SystemExit(str(e))

    App(args).run()

if __name__ == "__main__":
    main()
