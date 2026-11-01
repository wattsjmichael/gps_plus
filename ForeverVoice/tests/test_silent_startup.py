import importlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

HELPER = Path(__file__).resolve().parents[1] / 'helper'
sys.path.insert(0, str(HELPER))
import fv_runtime as runtime

# Audio/keyboard/model stubs allow testing the application without devices, GPU or WoW.
for name in ('numpy', 'sounddevice', 'faster_whisper', 'pynput', 'pynput.keyboard'):
    sys.modules[name] = types.ModuleType(name)
sys.modules['faster_whisper'].WhisperModel = Mock()
sys.modules['pynput.keyboard'].Controller = Mock()
sys.modules['pynput.keyboard'].Key = types.SimpleNamespace(**{
    name: name for name in ['f5','f6','f7','f8','f9','f10','f11','f12','home','end',
                            'page_down','ctrl','alt','shift','enter']})
import forevervoice as fv


class LifecycleTests(unittest.TestCase):
    def test_duplicate_lock_and_recovery(self):
        with tempfile.TemporaryDirectory() as d:
            first = runtime.InstanceLock(Path(d))
            self.assertTrue(first.acquire())
            code = ('import sys; from pathlib import Path; from fv_runtime import InstanceLock; '
                    'x=InstanceLock(Path(sys.argv[1])); sys.exit(0 if x.acquire() else 3)')
            result = subprocess.run([sys.executable, '-c', code, d],
                                    env={**os.environ, 'PYTHONPATH': str(HELPER)})
            self.assertEqual(result.returncode, 3)
            self.assertTrue(first.request.exists())
            first.close()
            recovered = runtime.InstanceLock(Path(d))
            self.assertTrue(recovered.acquire())
            recovered.close()

    def make_app(self):
        with patch.object(fv, 'load_local_config', return_value={}):
            return fv.App(types.SimpleNamespace(input_device=None, model='base', wow_dir='/missing', any_app=False))

    def test_test_microphone_never_sends_keys(self):
        app = self.make_app()
        app.recorder = Mock()
        app.recorder.stop.return_value = [0.2]
        app.model = Mock()
        app.model.transcribe.return_value = ([types.SimpleNamespace(text=' hello world ')], None)
        app.stopping.wait = Mock(return_value=False)
        app.bridge_signal = Mock()
        app.deliver = Mock()
        reports = []
        app.test_microphone(reports.append)
        self.assertEqual(reports[-1], 'hello world')
        app.bridge_signal.assert_not_called()
        app.deliver.assert_not_called()
        self.assertEqual(app.state, 'idle')
        app.recorder.start.assert_called_once()

    def test_busy_test_does_not_touch_microphone(self):
        app = self.make_app(); app.state = 'recording'; app.recorder = Mock()
        app.test_microphone(Mock())
        app.recorder.start.assert_not_called()

    def test_model_failure_is_visible(self):
        app = self.make_app()
        with self.assertLogs(level='ERROR'), patch.object(fv, 'WhisperModel', side_effect=RuntimeError('offline')):
            app.load_model()
        self.assertIn('Failed: offline', app.model_status)
        self.assertIsNone(app.model)

    def test_controller_mapping_preserved(self):
        app = self.make_app(); app.start_recording = Mock(); app.send_recording = Mock()
        app.on_controller_press('PADDUP', False)
        app.start_recording.assert_called_once()
        app.state = 'recording'
        app.on_controller_press('PADDRIGHT', True)
        self.assertEqual((app.channel, app.prefix), ('trade', '/2 '))
        app.on_controller_press('PADDUP', False)
        app.send_recording.assert_called_once()

    def test_shutdown_prevents_transcript_delivery(self):
        app = self.make_app(); app.stopping.set(); app.model = Mock()
        app.model.transcribe.return_value = ([types.SimpleNamespace(text='hello')], None)
        app.deliver = Mock(); app.bridge_signal = Mock()
        app.finish([0.1]); app.deliver.assert_not_called()

    def test_startup_registry_and_legacy_cleanup(self):
        fake = Mock(); fake.HKEY_CURRENT_USER = 1; fake.REG_SZ = 1
        fake.CreateKey.return_value.__enter__ = Mock(return_value='key')
        fake.CreateKey.return_value.__exit__ = Mock(return_value=False)
        with tempfile.TemporaryDirectory() as d:
            startup = Path(d) / 'Microsoft/Windows/Start Menu/Programs/Startup'
            startup.mkdir(parents=True)
            for name in ('ForeverVoice Helper.cmd', 'ForeverVoice Helper.lnk', 'Other.cmd'):
                (startup / name).touch()
            with patch.dict(sys.modules, winreg=fake), patch.object(runtime, 'os', types.SimpleNamespace(name='nt', environ={**os.environ, 'APPDATA': d})):
                runtime.set_startup(True, ['C:\\App Path\\ForeverVoiceHelper.exe'])
                command = fake.SetValueEx.call_args.args[-1]
                self.assertEqual(command, '"C:\\App Path\\ForeverVoiceHelper.exe" --background')
                runtime.set_startup(False)
                fake.DeleteValue.assert_called_once_with('key', 'ForeverVoice')
            self.assertTrue((startup / 'Other.cmd').exists())
            self.assertFalse((startup / 'ForeverVoice Helper.cmd').exists())
            self.assertFalse((startup / 'ForeverVoice Helper.lnk').exists())

    def test_microphone_failure_recovers_state(self):
        app = self.make_app(); app.model = Mock(); app.recorder = Mock()
        app.recorder.start.side_effect = RuntimeError('permission denied')
        reports = []
        with self.assertLogs(level='ERROR'):
            app.test_microphone(reports.append)
        self.assertIn('permission denied', reports[-1])
        self.assertEqual(app.state, 'idle')
        app.recorder.stop.assert_called()

    def test_controller_shutdown_guard(self):
        app = self.make_app(); app.stopping.set(); app.start_recording = Mock()
        app.on_controller_press('PADDUP', False)
        app.start_recording.assert_not_called()

    def test_background_and_windowless_build_paths(self):
        root = HELPER.parent
        self.assertIn('--noconsole', (root / 'build-helper.ps1').read_text())
        self.assertIn('--noconsole', (root / 'build-setup.ps1').read_text())
        self.assertIn('pythonw.exe', (root / 'run-helper.ps1').read_text())

    def test_record_start_failure_closes_stream(self):
        stream = Mock(); stream.start.side_effect = RuntimeError('unavailable')
        with patch.object(fv.sd, 'InputStream', return_value=stream, create=True):
            recorder = fv.Recorder()
            with self.assertRaises(RuntimeError): recorder.start()
            stream.close.assert_called_once()
            self.assertIsNone(recorder.stream)


if __name__ == '__main__':
    unittest.main()
