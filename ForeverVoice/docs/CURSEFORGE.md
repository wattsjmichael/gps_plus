# ForeverVoice

**Controller-first local speech-to-text chat for WoW Forever.**

ForeverVoice lets you dictate WoW chat without taking your hands off the controller.

## First-time setup

Download and run **ForeverVoice Setup** once. The Setup EXE finds WoW, installs the addon and local helper, lets you choose a microphone, enables autostart, and starts ForeverVoice.

There is no Python or command-line setup for end users.

After installation, type `/fv setup` in WoW to configure your controller.

## Controller flow

Press your Voice button once to start recording. While recording, hold your Channel Select modifier and press a D-pad direction to choose a destination. Press the Voice button again to transcribe and send.

ForeverVoice temporarily suppresses those D-pad gameplay bindings while recording, so selecting a channel does not also fire an ability.

## Configurable channel slots

Each direction can be assigned to General, Trade, Say, Party, Guild, Raid, Instance, Reply to Last Whisper, any joined numbered channel, or Off.

Recommended default:

- LT + Up → General
- LT + Right → Trade
- LT + Down → Reply
- LT + Left → Party

## Local transcription

ForeverVoice performs speech-to-text locally on your Windows PC. ForeverVoice does not send your microphone audio to a hosted transcription service.

## Commands

- `/fv setup` — controller and channel setup
- `/fv slots` — display channel assignments
- `/fv move` — move the recording indicator
- `/fv hide` — hide preview
- `/fv reset` — reset HUD position

## Requirements

- Windows
- WoW Forever
- XInput-compatible controller
- Microphone

The Windows release is distributed as a single Setup EXE with a SHA256 checksum.
