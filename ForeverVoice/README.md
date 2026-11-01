# ForeverVoice

Controller-first local speech-to-text chat for WoW Forever.

## End-user install

Public users should download and run:

`ForeverVoiceSetup-v0.3.1.exe`

The Setup app:

- detects WoW Forever
- detects an XInput controller
- lets the user choose a microphone
- installs the addon
- installs the helper to `%LOCALAPPDATA%\ForeverVoice`
- saves microphone settings to `%APPDATA%\ForeverVoice\config.json`
- adds the helper to Windows Startup
- starts the helper

The WoW addon itself cannot install or launch Windows software, so the Setup EXE is the one-time bootstrap. After that, the helper starts automatically with Windows.

## In-game setup

Type:

`/fv setup`

The four D-pad directions are configurable channel slots. Supported destinations include General, Trade, Say, Party, Guild, Raid, Instance, Reply to Last Whisper, numbered channels, and Off.

## Development

Build the public one-click installer:

`./build-setup.ps1`

Output:

`installer/dist/ForeverVoiceSetup.exe`

Prepare the versioned release artifact and SHA256:

`./release.ps1`

Output:

- `release/ForeverVoiceSetup-v0.3.1.exe`
- `release/ForeverVoiceSetup-v0.3.1-SHA256.txt`

The legacy `install.ps1` and `run-helper.ps1` scripts remain available for development only.

## Architecture

The helper owns microphone capture, Whisper transcription, XInput input, and the real recording/channel state.

The addon owns onboarding, HUD presentation, SavedVariables, and temporary WoW-side D-pad suppression while recording.

Speech transcription is local to the PC.


## Uninstall

ForeverVoice registers itself with Windows. Remove it from:

**Settings → Apps → Installed apps → ForeverVoice → Uninstall**

You can also reopen `ForeverVoiceSetup.exe` and click **Uninstall ForeverVoice**.

Uninstall removes the helper, saved microphone settings, Windows Startup entry, and the WoW addon folder.

## v0.4.0 development (unreleased)

Open the helper to view standalone diagnostics, even with WoW closed. Closing the
window keeps the helper in the tray. Use tray **Open**, **Start with Windows**, or
**Exit**. **Test Microphone** records three seconds and displays a transcription;
it does not type into WoW. Whisper must finish loading before recording is enabled.
A second launch opens the existing window rather than starting another helper.

Startup uses `HKCU\Software\Microsoft\Windows\CurrentVersion\Run\ForeverVoice`.
The helper migrates the known `ForeverVoice Helper.cmd` and `.lnk` Startup entries
on first launch. Exit disables no startup setting; the toggle controls the next sign-in.
Logs: `%APPDATA%\ForeverVoice\forevervoice.log` (rotating application/errors) and
`native.log` (native library output). Logs can contain transcripts; inspect before sharing.
Exit stops controller polling and recording and waits for current model/transcription
work to finish. No separate Whisper daemon or unrelated Python process is killed.

Validation and Windows smoke-test steps: [docs/V0.4.0-VALIDATION.md](docs/V0.4.0-VALIDATION.md).
