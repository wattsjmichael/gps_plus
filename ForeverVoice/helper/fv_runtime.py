"""Desktop lifecycle helpers; no audio/model imports."""
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import subprocess
import sys

RUN_KEY = r'Software\Microsoft\Windows\CurrentVersion\Run'
STARTUP_NAME = 'ForeverVoice'


def configure_logging(directory):
    directory.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(directory / 'forevervoice.log', maxBytes=2_000_000,
                                  backupCount=3, encoding='utf-8')
    logging.basicConfig(level=logging.INFO, handlers=[handler],
                        format='%(asctime)s %(levelname)s %(message)s', force=True)
    # Windowless Python has no stdout/stderr. Native libraries may still write to them.
    stream = open(directory / 'native.log', 'a', encoding='utf-8', buffering=1)
    sys.stdout = sys.stderr = stream
    sys.excepthook = lambda *exc: logging.critical('Unhandled error', exc_info=exc)
    import threading
    threading.excepthook = lambda args: logging.error(
        'Worker failed', exc_info=(args.exc_type, args.exc_value, args.exc_traceback))
    return stream


def launch_command():
    if getattr(sys, 'frozen', False):
        return [sys.executable]
    pythonw = Path(sys.executable).with_name('pythonw.exe')
    return [str(pythonw if os.name == 'nt' else sys.executable),
            str(Path(__file__).with_name('forevervoice.py'))]


def startup_enabled():
    if os.name != 'nt':
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            return bool(winreg.QueryValueEx(key, STARTUP_NAME)[0])
    except FileNotFoundError:
        return False


def set_startup(enabled, command=None):
    if os.name != 'nt':
        raise OSError('Start with Windows is only available on Windows')
    import winreg
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
        if enabled:
            winreg.SetValueEx(key, STARTUP_NAME, 0, winreg.REG_SZ,
                             subprocess.list2cmdline((command or launch_command()) + ['--background']))
        else:
            try:
                winreg.DeleteValue(key, STARTUP_NAME)
            except FileNotFoundError:
                pass
    # Only entries created by the two ForeverVoice installers.
    startup = Path(os.environ['APPDATA']) / 'Microsoft/Windows/Start Menu/Programs/Startup'
    for name in ('ForeverVoice Helper.cmd', 'ForeverVoice Helper.lnk'):
        (startup / name).unlink(missing_ok=True)


def migrate_startup():
    if os.name == 'nt':
        startup = Path(os.environ['APPDATA']) / 'Microsoft/Windows/Start Menu/Programs/Startup'
        if any((startup / name).exists() for name in
               ('ForeverVoice Helper.cmd', 'ForeverVoice Helper.lnk')):
            set_startup(True)


class InstanceLock:
    """OS-released lock shared by frozen/source launches. No PID-based killing."""
    def __init__(self, directory):
        self.path = directory / 'instance.lock'
        self.request = directory / 'open.request'
        self.file = None

    def acquire(self):
        self.file = open(self.path, 'a+b')
        self.file.seek(0)
        if not self.file.read(1):
            self.file.write(b'0'); self.file.flush()
        self.file.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.file.close(); self.file = None
            self.request.touch()
            return False
        return True

    def close(self):
        if self.file:
            self.file.close(); self.file = None
