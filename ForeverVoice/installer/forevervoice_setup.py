from __future__ import annotations

import ctypes
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import winreg

import sounddevice as sd

APP_NAME = "ForeverVoice"
APP_VERSION = "0.3.0"
UNINSTALL_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\ForeverVoice"

WOW_CANDIDATES = [
    Path(r"D:\World of Warcraft\_classic_beta_"),
    Path(r"C:\Program Files (x86)\World of Warcraft\_classic_beta_"),
    Path(r"C:\Program Files\World of Warcraft\_classic_beta_"),
]


def resource_root() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


def payload_root() -> Path:
    return resource_root() / "payload"


def find_wow() -> Path | None:
    saved = load_config().get("wow_dir")
    if saved:
        candidate = Path(saved)
        if candidate.exists():
            return candidate

    for candidate in WOW_CANDIDATES:
        if candidate.exists():
            return candidate
    return None


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
    _fields_ = [
        ("dwPacketNumber", ctypes.c_ulong),
        ("Gamepad", XINPUT_GAMEPAD),
    ]


def controller_detected() -> bool:
    for dll in ("xinput1_4.dll", "xinput1_3.dll", "xinput9_1_0.dll"):
        try:
            xinput = ctypes.WinDLL(dll)
            for index in range(4):
                state = XINPUT_STATE()
                if xinput.XInputGetState(index, ctypes.byref(state)) == 0:
                    return True
        except OSError:
            continue
    return False


def input_devices():
    out = []
    for index, dev in enumerate(sd.query_devices()):
        if int(dev.get("max_input_channels", 0)) > 0:
            out.append((index, str(dev["name"])))
    return out


def startup_dir() -> Path:
    appdata = Path(os.environ["APPDATA"])
    return appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def config_dir() -> Path:
    return Path(os.environ["APPDATA"]) / APP_NAME


def config_path() -> Path:
    return config_dir() / "config.json"


def app_dir() -> Path:
    return Path(os.environ["LOCALAPPDATA"]) / APP_NAME


def installed_setup_path() -> Path:
    return app_dir() / "ForeverVoiceSetup.exe"


def load_config() -> dict:
    path = config_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_config(data: dict) -> None:
    cfg_dir = config_dir()
    cfg_dir.mkdir(parents=True, exist_ok=True)
    config_path().write_text(json.dumps(data, indent=2), encoding="utf-8")


def is_installed() -> bool:
    if (app_dir() / "ForeverVoiceHelper.exe").exists():
        return True
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY):
            return True
    except FileNotFoundError:
        return False


def register_uninstaller(setup_path: Path, install_path: Path) -> None:
    uninstall_cmd = f'"{setup_path}" --uninstall'
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY) as key:
        winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, "ForeverVoice")
        winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, APP_VERSION)
        winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, "ForeverVoice")
        winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, str(install_path))
        winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, uninstall_cmd)
        winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, str(setup_path))
        winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)


def unregister_uninstaller() -> None:
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY)
    except FileNotFoundError:
        pass


def stop_helper() -> None:
    subprocess.run(
        ["taskkill", "/IM", "ForeverVoiceHelper.exe", "/F"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def remove_addon() -> None:
    candidates: list[Path] = []
    saved = load_config().get("wow_dir")
    if saved:
        candidates.append(Path(saved))
    candidates.extend(WOW_CANDIDATES)

    seen: set[str] = set()
    for wow in candidates:
        key = str(wow).lower()
        if key in seen:
            continue
        seen.add(key)
        addon = wow / "Interface" / "AddOns" / "ForeverVoice"
        if addon.exists():
            shutil.rmtree(addon, ignore_errors=True)


def schedule_app_dir_removal() -> None:
    target = app_dir()
    # The installed setup EXE may be running from this directory. Let this
    # process exit, then remove the directory from a detached cmd process.
    command = f'ping 127.0.0.1 -n 3 > nul & rmdir /s /q "{target}"'
    subprocess.Popen(
        ["cmd.exe", "/d", "/c", command],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def uninstall_forevervoice(parent: tk.Misc | None = None, quiet: bool = False) -> bool:
    if not quiet:
        if not messagebox.askyesno(
            "Uninstall ForeverVoice",
            "Remove ForeverVoice from this PC?\n\n"
            "This removes the helper, microphone settings, Windows startup entry, "
            "and the WoW addon.",
            parent=parent,
        ):
            return False

    stop_helper()

    startup_file = startup_dir() / "ForeverVoice Helper.cmd"
    try:
        startup_file.unlink()
    except FileNotFoundError:
        pass

    remove_addon()
    unregister_uninstaller()

    shutil.rmtree(config_dir(), ignore_errors=True)
    schedule_app_dir_removal()

    if not quiet:
        messagebox.showinfo(
            "ForeverVoice",
            "ForeverVoice has been uninstalled.",
            parent=parent,
        )
    return True


class SetupApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("ForeverVoice Setup")
        self.root.geometry("620x520")
        self.root.minsize(620, 520)
        self.root.resizable(False, True)

        self.wow_path = tk.StringVar(value=str(find_wow() or ""))
        self.autostart = tk.BooleanVar(value=True)
        self.launch_now = tk.BooleanVar(value=True)
        self.devices = input_devices()

        self._build_ui()

    def _build_ui(self):
        frame = ttk.Frame(self.root, padding=24)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="ForeverVoice", font=("Segoe UI", 22, "bold")).pack(anchor="w")
        ttk.Label(
            frame,
            text="Controller-first local speech-to-text for WoW Forever",
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(0, 20))

        wow = find_wow()
        wow_text = "✓ WoW Forever found" if wow else "⚠ WoW Forever not found automatically"
        ttk.Label(frame, text=wow_text, font=("Segoe UI", 11, "bold")).pack(anchor="w")

        path_row = ttk.Frame(frame)
        path_row.pack(fill="x", pady=(6, 16))
        ttk.Entry(path_row, textvariable=self.wow_path, width=64).pack(side="left", fill="x", expand=True)
        ttk.Button(path_row, text="Browse…", command=self.browse_wow).pack(side="left", padx=(8, 0))

        controller_text = "✓ Xbox/XInput controller detected" if controller_detected() else "⚠ No XInput controller detected yet"
        ttk.Label(frame, text=controller_text, font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 18))

        ttk.Label(frame, text="Microphone", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        values = [f"{idx}: {name}" for idx, name in self.devices]
        self.mic_combo = ttk.Combobox(frame, values=values, state="readonly", width=76)
        self.mic_combo.pack(anchor="w", fill="x", pady=(6, 18))

        saved_input = load_config().get("input_device")
        selected = 0
        if saved_input is not None:
            for i, (device_index, _) in enumerate(self.devices):
                if device_index == saved_input:
                    selected = i
                    break
        if values:
            self.mic_combo.current(selected)

        ttk.Checkbutton(frame, text="Start ForeverVoice automatically with Windows", variable=self.autostart).pack(anchor="w")
        ttk.Checkbutton(frame, text="Start ForeverVoice Helper after setup", variable=self.launch_now).pack(anchor="w", pady=(4, 0))

        ttk.Separator(frame).pack(fill="x", pady=20)

        ttk.Label(
            frame,
            text="Speech transcription runs locally on this PC.",
            font=("Segoe UI", 9),
        ).pack(anchor="w")

        if is_installed():
            ttk.Label(
                frame,
                text="✓ ForeverVoice is currently installed",
                font=("Segoe UI", 9, "bold"),
            ).pack(anchor="w", pady=(6, 0))

        self.status = ttk.Label(frame, text="")
        self.status.pack(anchor="w", pady=(8, 0))

        buttons = ttk.Frame(frame)
        buttons.pack(side="bottom", fill="x", pady=(20, 0))

        if is_installed():
            ttk.Button(
                buttons,
                text="Uninstall ForeverVoice",
                command=self.start_uninstall,
            ).pack(side="left", ipadx=10, ipady=5)

        self.install_button = ttk.Button(buttons, text="Install / Update & Finish", command=self.install)
        self.install_button.pack(side="right", ipadx=16, ipady=5)

    def browse_wow(self):
        folder = filedialog.askdirectory(title="Select your WoW Forever _classic_beta_ folder")
        if folder:
            self.wow_path.set(folder)

    def set_status(self, text: str):
        self.status.configure(text=text)
        self.root.update_idletasks()

    def validate(self) -> tuple[Path, int] | None:
        wow = Path(self.wow_path.get().strip())
        if not wow.exists() or not (wow / "Interface").exists():
            messagebox.showerror("ForeverVoice", "Choose the WoW Forever _classic_beta_ folder.")
            return None
        if self.mic_combo.current() < 0 or not self.devices:
            messagebox.showerror("ForeverVoice", "Choose a microphone.")
            return None
        return wow, self.devices[self.mic_combo.current()][0]

    def start_uninstall(self):
        installed_setup = installed_setup_path()
        current = Path(sys.executable).resolve()

        if installed_setup.exists() and installed_setup.resolve() != current:
            subprocess.Popen(
                [str(installed_setup), "--uninstall"],
                cwd=str(app_dir()),
            )
            self.root.destroy()
            return

        if uninstall_forevervoice(self.root):
            self.root.destroy()

    def install(self):
        valid = self.validate()
        if not valid:
            return

        wow, mic_index = valid
        self.install_button.configure(state="disabled")

        try:
            payload = payload_root()
            addon_source = payload / "addon" / "ForeverVoice"
            helper_source = payload / "ForeverVoiceHelper.exe"
            if not addon_source.exists() or not helper_source.exists():
                raise RuntimeError("The setup payload is incomplete. Re-download ForeverVoice Setup.")

            self.set_status("Installing WoW addon…")
            addon_dest = wow / "Interface" / "AddOns" / "ForeverVoice"
            if addon_dest.exists():
                shutil.rmtree(addon_dest)
            addon_dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(addon_source, addon_dest)

            self.set_status("Installing ForeverVoice Helper…")
            target_dir = app_dir()
            target_dir.mkdir(parents=True, exist_ok=True)
            helper_dest = target_dir / "ForeverVoiceHelper.exe"
            setup_dest = installed_setup_path()

            stop_helper()
            shutil.copy2(helper_source, helper_dest)

            self.set_status("Installing Windows uninstaller…")
            current_exe = Path(sys.executable).resolve()
            if getattr(sys, "frozen", False):
                if current_exe != setup_dest.resolve():
                    shutil.copy2(current_exe, setup_dest)
            else:
                raise RuntimeError("Public setup must be run from the built ForeverVoiceSetup.exe.")

            self.set_status("Saving settings…")
            save_config(
                {
                    "input_device": mic_index,
                    "wow_dir": str(wow),
                }
            )

            startup_file = startup_dir() / "ForeverVoice Helper.cmd"
            if self.autostart.get():
                self.set_status("Enabling Windows startup…")
                startup_file.write_text(
                    '@echo off\nstart "" "' + str(helper_dest) + '"\n',
                    encoding="utf-8",
                )
            elif startup_file.exists():
                startup_file.unlink()

            register_uninstaller(setup_dest, target_dir)

            if self.launch_now.get():
                self.set_status("Starting ForeverVoice Helper…")
                subprocess.Popen(
                    [str(helper_dest)],
                    cwd=str(target_dir),
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )

            self.set_status("Installed successfully.")
            messagebox.showinfo(
                "ForeverVoice",
                "ForeverVoice is installed.\n\n"
                "You can remove it later from Windows Settings → Apps → Installed apps, "
                "or by reopening ForeverVoice Setup.\n\n"
                "Start WoW Forever, type /reload, then type /fv setup "
                "to choose your controller button and channel slots.",
            )
            self.root.destroy()
        except Exception as exc:
            self.install_button.configure(state="normal")
            self.set_status("Install failed.")
            messagebox.showerror("ForeverVoice Setup", str(exc))

    def run(self):
        self.root.mainloop()


def main():
    args = {arg.lower() for arg in sys.argv[1:]}
    if "--uninstall" in args:
        root = tk.Tk()
        root.withdraw()
        try:
            removed = uninstall_forevervoice(root, quiet="--quiet" in args)
            if removed:
                root.destroy()
        finally:
            try:
                root.destroy()
            except tk.TclError:
                pass
        return

    SetupApp().run()


if __name__ == "__main__":
    main()
