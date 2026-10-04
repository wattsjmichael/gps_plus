from __future__ import annotations
import argparse
import ctypes
import json
import platform
import re
import threading
import time
from pathlib import Path

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
from pynput.keyboard import Controller, Key

SYSTEM = platform.system()
SAMPLE_RATE = 16000

KNOWN_PREFIXES = {
    "general": "/1 ",
    "trade": "/2 ",
    "party": "/p ",
    "guild": "/g ",
    "say": "/s ",
    "reply": "/r ",
    "raid": "/raid ",
    "instance": "/i ",
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
    "down_channel": "reply",
    "left_channel": "party",
}

def log(s: str):
    print(f"[{time.strftime('%H:%M:%S')}] {s}", flush=True)

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

def appdata_dir() -> Path:
    if SYSTEM == "Windows":
        base = Path.home() / "AppData" / "Roaming"
    else:
        base = Path.home() / ".config"
    p = base / "ForeverVoice"
    p.mkdir(parents=True, exist_ok=True)
    return p

def load_local_config() -> dict:
    p = appdata_dir() / "config.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}

def save_local_config(data: dict):
    (appdata_dir() / "config.json").write_text(
        json.dumps(data, indent=2), encoding="utf-8"
    )

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

def channel_prefix(name: str | None):
    if not name or name == "off":
        return None
    if name in KNOWN_PREFIXES:
        return KNOWN_PREFIXES[name]
    m = re.fullmatch(r"channel:(\d+)", name)
    if m:
        return f"/{m.group(1)} "
    return None

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
            blocksize=1024, device=self.device, callback=self._cb,
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

XINPUT_BITS = {
    "PADDUP": 0x0001, "PADDDOWN": 0x0002, "PADDLEFT": 0x0004, "PADDRIGHT": 0x0008,
    "PADFORWARD": 0x0010, "PADSOCIAL": 0x0020, "PADLSTICK": 0x0040, "PADRSTICK": 0x0080,
    "PADLSHOULDER": 0x0100, "PADRSHOULDER": 0x0200,
    "PAD1": 0x1000, "PAD2": 0x2000, "PAD3": 0x4000, "PAD4": 0x8000,
}

class XINPUT_GAMEPAD(ctypes.Structure):
    _fields_ = [
        ("wButtons", ctypes.c_ushort), ("bLeftTrigger", ctypes.c_ubyte),
        ("bRightTrigger", ctypes.c_ubyte), ("sThumbLX", ctypes.c_short),
        ("sThumbLY", ctypes.c_short), ("sThumbRX", ctypes.c_short), ("sThumbRY", ctypes.c_short),
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
            log("Direct controller: XInput unavailable")
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
                log(
                    "Controller mapping updated: "
                    f"voice={c['toggle']} modifier={c['modifier']} "
                    f"slots=[{c['up_channel']}, {c['right_channel']}, "
                    f"{c['down_channel']}, {c['left_channel']}]"
                )
            time.sleep(0.01)

class App:
    def __init__(self, args):
        self.args = args
        self.state = "idle"
        self.channel = "general"
        self.prefix = "/1 "
        self.active_channel = None
        self.active_prefix = None

        local = load_local_config()
        device = args.input_device
        if device is None and isinstance(local.get("input_device"), int):
            device = local["input_device"]

        self.recorder = Recorder(device)
        self.keyboard = Controller()
        log("Starting ForeverVoice Helper...")
        log(f"Loading Whisper model '{args.model}' on CPU...")
        self.model = WhisperModel(args.model, device="cpu", compute_type="int8")
        log("Whisper model loaded")
        self.lock = threading.Lock()
        self.last_toggle = 0.0
        self.settings = ForeverVoiceSettings(Path(args.wow_dir))
        self.settings.refresh()

    def bridge_signal(self, state, channel=None):
        # Ctrl+Alt+Shift + ordinary keys are consumed by the addon.
        signals = {
            ("recording", "general"): Key.f5,
            ("recording", "trade"): Key.f6,
            ("recording", "party"): Key.f7,
            ("recording", "guild"): Key.f8,
            ("recording", "say"): Key.f9,
            ("recording", "reply"): Key.f10,
            ("recording", "raid"): Key.f11,
            ("recording", "instance"): Key.f12,
            ("recording", "custom"): Key.home,
            ("transcribing", None): Key.end,
            ("idle", None): Key.page_down,
        }
        bridge_channel = channel
        if channel and channel.startswith("channel:"):
            bridge_channel = "custom"
        final = signals.get((state, bridge_channel)) or signals.get((state, None))
        if final is None:
            return
        try:
            for mod in (Key.ctrl, Key.alt, Key.shift):
                self.keyboard.press(mod)
            time.sleep(0.01)
            self.keyboard.press(final)
            time.sleep(0.02)
            self.keyboard.release(final)
            for mod in (Key.shift, Key.alt, Key.ctrl):
                self.keyboard.release(mod)
            log(f"HUD: {state}{'/' + channel if channel else ''}")
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

    def select_channel(self, name):
        prefix = channel_prefix(name)
        if prefix is None:
            if name != "off":
                log(f"Unsupported channel slot: {name}")
            return
        self.channel, self.prefix = name, prefix
        if self.state == "recording":
            self.active_channel, self.active_prefix = name, prefix
            log(f"Recording destination changed: {name} ({prefix.strip()})")
            self.bridge_signal("recording", name)

    def on_controller_press(self, button, modifier_held):
        c = self.settings.controller
        if self.state == "idle":
            if button == c["toggle"] and not modifier_held:
                self.start_recording()
            return
        if self.state != "recording":
            return
        if modifier_held:
            slots = {
                c["up_button"]: c["up_channel"],
                c["right_button"]: c["right_channel"],
                c["down_button"]: c["down_channel"],
                c["left_button"]: c["left_channel"],
            }
            choice = slots.get(button)
            if choice and choice != "off":
                self.select_channel(choice)
            return
        if button == c["toggle"]:
            self.send_recording()

    def finish(self, audio):
        try:
            segs, _ = self.model.transcribe(
                audio, beam_size=1, best_of=1, vad_filter=True,
                condition_on_previous_text=False, without_timestamps=True,
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
        self.keyboard.press(Key.enter); self.keyboard.release(Key.enter)
        time.sleep(0.12)
        self.type_text(text)
        time.sleep(0.04)
        self.keyboard.press(Key.enter); self.keyboard.release(Key.enter)
        time.sleep(0.15)
        self.type_text("/click InputFunctionBindingButton_PAD2 LeftButton 1")
        time.sleep(0.03)
        self.keyboard.press(Key.enter); self.keyboard.release(Key.enter)

    def run(self):
        c = self.settings.controller
        log("ForeverVoice ready")
        mic = sd.query_devices(self.recorder.device, "input")["name"] if self.recorder.device is not None else sd.query_devices(kind="input")["name"]
        log(f"Mic: {mic}")
        log(
            f"Controller: voice={c['toggle']} modifier={c['modifier']} "
            f"slots=[{c['up_channel']}, {c['right_channel']}, "
            f"{c['down_channel']}, {c['left_channel']}]"
        )
        watcher = XInputWatcher(self)
        threading.Thread(target=watcher.run, daemon=True).start()
        while True:
            time.sleep(1.0)

def setup_mic():
    import tkinter as tk
    from tkinter import ttk, messagebox

    devices = []
    for i, dev in enumerate(sd.query_devices()):
        if int(dev.get("max_input_channels", 0)) > 0:
            devices.append((i, dev["name"]))

    root = tk.Tk()
    root.title("ForeverVoice Setup")
    root.geometry("540x210")
    root.resizable(False, False)

    ttk.Label(root, text="ForeverVoice", font=("Segoe UI", 16, "bold")).pack(pady=(18, 4))
    ttk.Label(root, text="Choose the microphone ForeverVoice should use.").pack(pady=(0, 12))

    values = [f"{i}: {name}" for i, name in devices]
    combo = ttk.Combobox(root, values=values, state="readonly", width=65)
    combo.pack()
    if values:
        combo.current(0)

    def save():
        if combo.current() < 0:
            messagebox.showerror("ForeverVoice", "Choose a microphone first.")
            return
        idx = devices[combo.current()][0]
        cfg = load_local_config()
        cfg["input_device"] = idx
        save_local_config(cfg)
        messagebox.showinfo("ForeverVoice", "Microphone saved. Restart ForeverVoice Helper.")
        root.destroy()

    ttk.Button(root, text="Save microphone", command=save).pack(pady=18)
    root.mainloop()

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--wow-dir", default=str(default_wow_dir()))
    p.add_argument("--input-device", type=int)
    p.add_argument("--model", default="base")
    p.add_argument("--any-app", action="store_true")
    p.add_argument("--setup", action="store_true")
    p.add_argument("--list-devices", action="store_true")
    args = p.parse_args()

    if args.list_devices:
        print(sd.query_devices())
        return
    if args.setup:
        setup_mic()
        return
    App(args).run()

if __name__ == "__main__":
    main()
