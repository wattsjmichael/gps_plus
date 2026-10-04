from __future__ import annotations
import argparse, ctypes, platform, re, subprocess, threading, time
from pathlib import Path

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
from pynput.keyboard import Controller, Key, Listener

SYSTEM = platform.system()
SAMPLE_RATE = 16000

KEYS = {
    "INSERT": Key.insert,
    "PAGEUP": Key.page_up,
    "PAGEDOWN": Key.page_down,
    "HOME": Key.home,
    "END": Key.end,
    "DELETE": Key.delete,
}

CHANNEL_KEYS = {
    Key.page_up: ("general", "/1 "),
    Key.delete: ("trade", "/2 "),
    Key.end: ("party", "/p "),
    Key.page_down: ("guild", "/g "),
    Key.home: ("say", "/s "),
}

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

    def toggle(self):
        with self.lock:
            now = time.monotonic()
            if now - self.last_toggle < 0.25:
                return
            self.last_toggle = now
            if self.state == "idle":
                try:
                    self.recorder.start()
                except Exception as e:
                    log(f"Mic failed: {e}")
                    return
                self.active_channel = self.channel
                self.active_prefix = self.prefix
                self.state = "recording"
                log(f"Recording... channel={self.active_channel} destination={self.active_prefix.strip()}")
            elif self.state == "recording":
                audio = self.recorder.stop()
                self.state = "transcribing"
                log("Stopped. Transcribing...")
                threading.Thread(target=self.finish, args=(audio,), daemon=True).start()

    def select_channel(self, name, prefix):
        self.channel, self.prefix = name, prefix
        if self.state in ("recording", "transcribing"):
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

    def deliver(self, text):
        self.keyboard.press(Key.enter); self.keyboard.release(Key.enter)
        time.sleep(0.10)
        for ch in text:
            self.keyboard.press(ch); self.keyboard.release(ch)
            time.sleep(0.002)
        self.keyboard.press(Key.enter); self.keyboard.release(Key.enter)

    def run(self):
        record_key = KEYS[self.args.record_key.upper()]
        log("ForeverVoice ready")
        log(f"Mic: {sd.query_devices(self.args.input_device, 'input')['name'] if self.args.input_device is not None else sd.query_devices(kind='input')['name']}")
        log(f"Record key: {self.args.record_key}")
        log("Channels: PageUp=General, Delete=Trade, End=Party, PageDown=Guild, Home=Say")

        def on_press(key):
            if key == record_key:
                self.toggle()
                return
            if key in CHANNEL_KEYS:
                self.select_channel(*CHANNEL_KEYS[key])

        with Listener(on_press=on_press) as listener:
            listener.join()

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--record-key", default="INSERT")
    p.add_argument("--input-device", type=int)
    p.add_argument("--model", default="base")
    p.add_argument("--any-app", action="store_true")
    args = p.parse_args()
    if args.record_key.upper() not in KEYS:
        raise SystemExit("record key must be INSERT, PAGEUP, PAGEDOWN, HOME, END, or DELETE")
    App(args).run()

if __name__ == "__main__":
    main()
