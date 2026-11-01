"""Tray and standalone diagnostics. All Tk operations stay on the main thread."""
import logging
import queue
import threading
import tkinter as tk
from tkinter import ttk

from fv_runtime import set_startup, startup_enabled


class Desktop:
    def __init__(self, app, instance):
        self.app, self.instance = app, instance
        self.events = queue.Queue()
        self.root = tk.Tk()
        self.root.title('ForeverVoice Diagnostics')
        self.root.geometry('620x370')
        self.root.protocol('WM_DELETE_WINDOW', self.root.withdraw)
        frame = ttk.Frame(self.root, padding=16)
        frame.pack(fill='both', expand=True)
        self.status = tk.StringVar()
        ttk.Label(frame, textvariable=self.status, wraplength=580).pack(anchor='w')
        self.result = tk.StringVar(value='Test records 3 seconds and displays text here; nothing is sent to WoW.')
        ttk.Button(frame, text='Test Microphone', command=self.test).pack(anchor='w', pady=12)
        ttk.Label(frame, textvariable=self.result, wraplength=580).pack(anchor='w')
        self.startup = tk.BooleanVar(value=startup_enabled())
        ttk.Checkbutton(frame, text='Start with Windows', variable=self.startup,
                        command=self.toggle).pack(anchor='w', pady=12)
        ttk.Button(frame, text='Exit ForeverVoice', command=self.exit).pack(anchor='w')
        self.tray = None
        self.tray_thread = None
        try:
            import pystray
            from PIL import Image, ImageDraw
            image = Image.new('RGB', (64, 64), '#203348')
            ImageDraw.Draw(image).text((14, 22), 'FV', fill='white')
            self.tray = pystray.Icon('ForeverVoice', image, 'ForeverVoice', pystray.Menu(
                pystray.MenuItem('Open', lambda *_: self.events.put(('open', None)), default=True),
                pystray.MenuItem('Start with Windows', lambda *_: self.events.put(('toggle', None)),
                                  checked=lambda _: startup_enabled()),
                pystray.MenuItem('Exit', lambda *_: self.events.put(('exit', None)))))
            self.tray_thread = threading.Thread(target=self.tray.run)
            self.tray_thread.start()
        except Exception:
            logging.exception('Tray unavailable; keeping diagnostics visible')
        if app.args.background and self.tray:
            self.root.withdraw()
        self.root.after(100, self.poll)
        self.refresh()

    def test(self):
        self.app.worker(self.app.test_microphone,
                        lambda text: self.events.put(('result', text)))

    def toggle(self):
        try:
            set_startup(not startup_enabled())
        except Exception as exc:
            logging.exception('Startup toggle failed')
            self.result.set('Startup change failed: ' + str(exc))
        self.startup.set(startup_enabled())
        if self.tray:
            self.tray.update_menu()

    def refresh(self):
        import sounddevice as sd
        import psutil
        try:
            mic = sd.query_devices(self.app.recorder.device, 'input')
            sd.check_input_settings(device=self.app.recorder.device, channels=1,
                                    dtype='float32', samplerate=16000)
            microphone = mic['name'] + ' (available; use Test to verify capture)'
        except Exception as exc:
            microphone = 'Unavailable: ' + str(exc)
        try:
            wow = any((p.info['name'] or '').lower() in
                      {'wow.exe', 'wowclassic.exe', 'wowclassicb.exe', 'wowb.exe', 'wow-64.exe'}
                      for p in psutil.process_iter(['name']))
            wow_status = 'Running' if wow else 'Not running'
        except (psutil.Error, OSError):
            wow_status = 'Unable to query processes'
        watcher = self.app.watcher
        controller = ('Connected (XInput slot 0)' if watcher.connected else
                      'Disconnected (XInput slot 0)' if watcher.xinput else 'XInput unavailable')
        self.status.set('Microphone: ' + microphone + '\n\nWhisper: ' + self.app.model_status +
                        '\n\nController: ' + controller + '\n\nWoW: ' + wow_status)
        if not self.app.stopping.is_set():
            self.root.after(2000, self.refresh)

    def poll(self):
        if self.instance.request.exists():
            self.instance.request.unlink(missing_ok=True)
            self.events.put(('open', None))
        while not self.events.empty():
            action, value = self.events.get_nowait()
            if action == 'open':
                self.root.deiconify(); self.root.lift()
            elif action == 'result':
                self.result.set(value)
            elif action == 'toggle':
                self.toggle()
            elif action == 'exit':
                self.exit()
        if self.app.stopping.is_set():
            if any(w.is_alive() for w in self.app.workers):
                self.result.set('Stopping… waiting for audio/model work to finish.')
            else:
                self.app.recorder.stop()
                if self.tray:
                    self.tray.stop()
                if self.tray_thread:
                    self.tray_thread.join(timeout=2)
                self.root.destroy()
                return
        self.root.after(100, self.poll)

    def exit(self):
        self.app.stopping.set()
        self.root.deiconify()
        # Active test owns its stream until its worker observes the stop event.
        with self.app.lock:
            if self.app.state == 'recording':
                self.app.recorder.stop()
                self.app.state = 'idle'

    def run(self):
        self.root.mainloop()
