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
        c = self.settings.controller
        log("ForeverVoice ready")
        log(f"Mic: {sd.query_devices(self.args.input_device, 'input')['name'] if self.args.input_device is not None else sd.query_devices(kind='input')['name']}")
        log(f"Controller: voice={c['toggle']} modifier={c['modifier']}")

        watcher = XInputWatcher(self)
        threading.Thread(target=watcher.run, daemon=True).start()

        # Keep the process alive; controller input is handled by XInputWatcher.
        while True:
            time.sleep(1.0)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--wow-dir", default=str(default_wow_dir()))
    p.add_argument("--input-device", type=int)
    p.add_argument("--model", default="base")
    p.add_argument("--any-app", action="store_true")
    args = p.parse_args()
    App(args).run()

if __name__ == "__main__":
    main()
