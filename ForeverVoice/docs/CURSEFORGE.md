# ForeverVoice

**Controller-first local speech-to-text chat for WoW Forever.**

ForeverVoice lets you talk into your microphone and send the transcription directly to WoW chat without taking your hands off the controller.

## How it works

Press your configured Voice button once to start recording. While recording, hold your Channel Select modifier and press a D-pad direction to choose where the message goes. Press the Voice button again to transcribe and send.

ForeverVoice temporarily suppresses those D-pad gameplay bindings while recording, so choosing a chat channel does not also fire an ability.

## Configurable channel slots

Each direction can be assigned independently to General, Trade, Say, Party, Guild, Raid, Instance, Reply to Last Whisper, any joined numbered channel, or Off.

Default layout:

- LT + Up → General
- LT + Right → Trade
- LT + Down → Reply
- LT + Left → Party

Type `/fv setup` in game to configure everything.

## Local transcription

ForeverVoice uses a small Windows helper to capture your microphone and perform speech-to-text locally on your PC. Your speech is not sent to a hosted transcription service by ForeverVoice.

## Commands

- `/fv setup` — setup/onboarding
- `/fv slots` — display channel assignments
- `/fv move` — move the recording indicator
- `/fv hide` — hide preview
- `/fv reset` — reset HUD position

## Requirements

- Windows
- WoW Forever
- XInput-compatible controller
- Microphone
- ForeverVoice Helper (included in the Windows release package)

## Privacy and trust

The helper is open source. Release packages include a SHA256 checksum so users can verify the downloaded ZIP.
