# ForeverVoice

Controller-first local speech-to-text chat for WoW Forever.

## End-user install

Public users should download and run:

`ForeverVoiceSetup-v0.3.0.exe`

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

- `release/ForeverVoiceSetup-v0.3.0.exe`
- `release/ForeverVoiceSetup-v0.3.0-SHA256.txt`

The legacy `install.ps1` and `run-helper.ps1` scripts remain available for development only.

## Architecture

The helper owns microphone capture, Whisper transcription, XInput input, and the real recording/channel state.

The addon owns onboarding, HUD presentation, SavedVariables, and temporary WoW-side D-pad suppression while recording.

Speech transcription is local to the PC.
