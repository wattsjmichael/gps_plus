from __future__ import annotations
import argparse
import ctypes
import platform
import re
import threading
import time
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

CHANNEL_PREFIXES = {
    "general": "/1 ",
    "trade": "/2 ",
    "party": "/p ",
    "guild": "/g ",
    "say": "/s ",
}

DEFAULT_CONTROLLER = {
    "toggle": "PADDUP",
    "modifier": "PADLTRIGGER",
    "up_button": "PADDUP",
    "right_button": "PADDRIGHT",
    "down_button": "PADDDOWN",
    "left_button": "PADDLEFT",
    "up_channel": "general",
    "right_channel": "trade",
    "down_channel": "guild",
    "left_channel": "party",
}

def log(s: str):
    print(f"[{time.strftime('%H:%M:%S')}] {s}", flush=True)

def parse_key(name: str):
    name = name.upper()
    if name in SPECIAL_KEYS:
        return SPECIAL_KEYS[name]
    if len(name) == 1:
        return name.lower()
    raise ValueError(f"Unsupported key: {name}")

def default_wow_dir() -> Path:
    candidates = [
        Path(r"D:\World of Warcraft\_classic_beta_"),
        Path(r"C:\Program Files (x86)\World of Warcraft\_classic_beta_"),
        Path(r"C:\Program Files\World of Warcraft\_classic_beta_"),
    ]
    for p in candidates:
        if p.exists():
            return p
    return candidates[0]

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

class ForeverVoiceSettings:
    def __init__(self, wow_dir: Path):
        self.wow_dir = wow_dir
        self.path = None
        self.mtime = None
        self.controller = dict(DEFAULT_CONTROLLER)

    def locate(self):
        root = self.wow_dir / "WTF" / "Account"
        if not root.exists():
            return None
        found = list(root.glob("*/SavedVariables/ForeverVoice.lua"))
        if not found:
            return None
        return max(found, key=lambda p: p.stat().st_mtime)

    @staticmethod
    def value(text: str, key: str):
        m = re.search(r'\["%s"\]\s*=\s*"([^"]*)"' % re.escape(key), text)
        return m.group(1) if m else None

    def refresh(self):
        p = self.locate()
        if p is None:
            return False
        mtime = p.stat().st_mtime
        if self.path == p and self.mtime == mtime:
            return False
        self.path, self.mtime = p, mtime
        text = p.read_text(encoding="utf-8", errors="replace")
        new = dict(DEFAULT_CONTROLLER)
        mapping = {
            "toggle": "controllerToggle",
            "modifier": "controllerModifier",
            "up_button": "controllerUpButton",
            "right_button": "controllerRightButton",
            "down_button": "controllerDownButton",
            "left_button": "controllerLeftButton",
            "up_channel": "controllerUpChannel",
            "right_channel": "controllerRightChannel",
            "down_channel": "controllerDownChannel",
            "left_channel": "controllerLeftChannel",
        }
        for dst, src in mapping.items():
            v = self.value(text, src)
            if v:
                new[dst] = v
        changed = new != self.controller
        self.controller = new
        return changed

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
            self.chunks.append(data[:, 0].copy())

    def start(self):
        self.chunks = []
        self.stream = sd.InputStream(
            samplerate=SAMPLE_RATE, channels=1, dtype="float32",
            blocksize=1024, device=self.device, callback=self._cb
        )
        self.stream.start()

    def stop(self):
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        with self.lock:
            out = np.concatenate(self.chunks) if self.chunks else np.zeros(0, dtype="float32")
            self.chunks = []
        return out

# Standard Windows XInput controls. This deliberately avoids Elite paddle magic:
# paddles can still be used through the keyboard bridge if desired.
XINPUT_BITS = {
    "PADDUP": 0x0001,
    "PADDDOWN": 0x0002,
    "PADDLEFT": 0x0004,
    "PADDRIGHT": 0x0008,
    "PADFORWARD": 0x0010,
    "PADSOCIAL": 0x0020,
    "PADLSTICK": 0x0040,
    "PADRSTICK": 0x0080,
    "PADLSHOULDER": 0x0100,
    "PADRSHOULDER": 0x0200,
    "PAD1": 0x1000,
    "PAD2": 0x2000,
    "PAD3": 0x4000,
    "PAD4": 0x8000,
}

class XINPUT_GAMEPAD(ctypes.Structure):
    _fields_ = [
        ("wButtons", ctypes.c_ushort),
        ("bLeftTrigger", ctypes.c_ubyte),
        ("bRightTrigger", ctypes.c_ubyte),
        ("sThumbLX", ctypes.c_short),
        ("sThumbLY", ctypes.c_short),
        ("sThumbRX", ctypes.c_short),
        ("sThumbRY", ctypes.c_short),
    ]

class XINPUT_STATE(ctypes.Structure):
    _fields_ = [("dwPacketNumber", ctypes.c_ulong), ("Gamepad", XINPUT_GAMEPAD)]

class XInputWatcher:
    def __init__(self, app):
        self.app = app
        self.xinput = None
        self.previous = set()
        if SYSTEM == "Windows":
            for dll in ("xinput1_4.dll", "xinput1_3.dll", "xinput9_1_0.dll"):
                try:
                    self.xinput = ctypes.WinDLL(dll)
                    break
                except OSError:
                    pass

    def controls(self):
        if self.xinput is None:
            return set()
        state = XINPUT_STATE()
        if self.xinput.XInputGetState(0, ctypes.byref(state)) != 0:
            return set()
        gp = state.Gamepad
        pressed = {name for name, bit in XINPUT_BITS.items() if gp.wButtons & bit}
        if gp.bLeftTrigger >= 80:
            pressed.add("PADLTRIGGER")
        if gp.bRightTrigger >= 80:
            pressed.add("PADRTRIGGER")
        return pressed

    def run(self):
        if self.xinput is None:
            log("Direct controller: XInput unavailable; keyboard bridge still works")
            return
        log("Direct controller: XInput enabled")
        while True:
            current = self.controls()
            downs = current - self.previous
            self.previous = current
            modifier = self.app.settings.controller["modifier"]
            modifier_held = modifier in current

            for button in downs:
                self.app.on_controller_press(button, modifier_held)

            if self.app.settings.refresh():
                c = self.app.settings.controller
                log(f"Controller mapping updated: voice={c['toggle']} modifier={c['modifier']}")
            time.sleep(0.01)

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
        self.settings = ForeverVoiceSettings(Path(args.wow_dir))
        self.settings.refresh()

    def bridge_signal(self, state, channel=None):
        # Hidden helper -> addon status bridge. F20 is never used as a user
        # binding; modifier combinations encode state/channel.
        combos = {
            ("recording", "general"): (Key.ctrl, Key.f20),
            ("recording", "trade"): (Key.shift, Key.f20),
            ("recording", "party"): (Key.alt, Key.f20),
            ("recording", "guild"): (Key.ctrl, Key.shift, Key.f20),
            ("recording", "say"): (Key.ctrl, Key.alt, Key.f20),
            ("transcribing", None): (Key.shift, Key.alt, Key.f20),
            ("idle", None): (Key.ctrl, Key.shift, Key.alt, Key.f20),
        }
        keys = combos.get((state, channel)) or combos.get((state, None))
        if not keys:
            return
        modifiers, final = keys[:-1], keys[-1]
        try:
            for key in modifiers:
                self.keyboard.press(key)
            self.keyboard.press(final)
            self.keyboard.release(final)
            for key in reversed(modifiers):
                self.keyboard.release(key)
        except Exception as e:
            log(f"HUD bridge failed: {e}")

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
            self.bridge_signal("recording", self.active_channel)

    def send_recording(self):
        with self.lock:
            now = time.monotonic()
            if now - self.last_toggle < 0.25 or self.state != "recording":
                return
            self.last_toggle = now
            audio = self.recorder.stop()
            self.state = "transcribing"
            log(f"Send pressed. destination={self.active_prefix.strip()} Transcribing...")
            self.bridge_signal("transcribing")
            threading.Thread(target=self.finish, args=(audio,), daemon=True).start()

    def toggle_voice(self):
        if self.state == "idle":
            self.start_recording()
        elif self.state == "recording":
            self.send_recording()

    def select_channel(self, name, prefix=None):
        prefix = prefix or CHANNEL_PREFIXES.get(name)
        if not prefix:
            return
        self.channel, self.prefix = name, prefix
        if self.state == "recording":
            self.active_channel = name
            self.active_prefix = prefix
            log(f"Recording destination changed: {name} ({prefix.strip()})")
            self.bridge_signal("recording", name)
        elif self.state == "transcribing":
            log(f"Channel queued for next message: {name}")
        else:
            log(f"Channel: {name}")

    def on_controller_press(self, button, modifier_held):
        c = self.settings.controller

        # The controller is intentionally inert for channel switching until
        # recording starts. Outside recording only the voice toggle matters.
        if self.state == "idle":
            if button == c["toggle"] and not modifier_held:
                self.start_recording()
            return

        if self.state != "recording":
            return

        if modifier_held:
            channel_buttons = {
                c["up_button"]: c["up_channel"],
                c["right_button"]: c["right_channel"],
                c["down_button"]: c["down_channel"],
                c["left_button"]: c["left_channel"],
            }
            channel = channel_buttons.get(button)
            if channel:
                self.select_channel(channel)
            return

        if button == c["toggle"]:
            self.send_recording()

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
            self.bridge_signal("idle")

    def type_text(self, text):
        for ch in text:
            self.keyboard.press(ch)
            self.keyboard.release(ch)
            time.sleep(0.002)

    def deliver(self, text):
        self.keyboard.press(Key.enter)
        self.keyboard.release(Key.enter)
        time.sleep(0.12)
        self.type_text(text)
        time.sleep(0.04)
        self.keyboard.press(Key.enter)
        self.keyboard.release(Key.enter)

        time.sleep(0.15)
        close_command = "/click InputFunctionBindingButton_PAD2 LeftButton 1"
        self.type_text(close_command)
        time.sleep(0.03)
        self.keyboard.press(Key.enter)
        self.keyboard.release(Key.enter)

    def run(self):
        keyboard_bindings = {
            "toggle": parse_key(self.args.toggle_key),
            "general": parse_key(self.args.general_key),
            "trade": parse_key(self.args.trade_key),
            "party": parse_key(self.args.party_key),
            "guild": parse_key(self.args.guild_key),
            "say": parse_key(self.args.say_key),
        }
        keyboard_channels = {
            keyboard_bindings["general"]: ("general", "/1 "),
            keyboard_bindings["trade"]: ("trade", "/2 "),
            keyboard_bindings["party"]: ("party", "/p "),
            keyboard_bindings["guild"]: ("guild", "/g "),
            keyboard_bindings["say"]: ("say", "/s "),
        }

        c = self.settings.controller
        log("ForeverVoice ready")
        log(f"Mic: {sd.query_devices(self.args.input_device, 'input')['name'] if self.args.input_device is not None else sd.query_devices(kind='input')['name']}")
        log(f"Controller: voice={c['toggle']} modifier={c['modifier']}")
        log(f"Keyboard fallback: voice={self.args.toggle_key}")

        watcher = XInputWatcher(self)
        threading.Thread(target=watcher.run, daemon=True).start()

        def on_press(key):
            if key == keyboard_bindings["toggle"]:
                self.toggle_voice()
                return
            # Keyboard channel shortcuts are also recording-only now.
            if self.state == "recording" and key in keyboard_channels:
                self.select_channel(*keyboard_channels[key])

        with Listener(on_press=on_press) as listener:
            listener.join()

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--wow-dir", default=str(default_wow_dir()))
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

    for name in (
        args.toggle_key, args.general_key, args.trade_key,
        args.party_key, args.guild_key, args.say_key
    ):
        parse_key(name)

    App(args).run()

if __name__ == "__main__":
    main()
