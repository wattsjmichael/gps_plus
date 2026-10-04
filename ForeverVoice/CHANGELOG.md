# Changelog

## 0.3.0 — Release candidate

- Added controller-first Start / Send flow.
- Added recording-only channel selection.
- Added temporary D-pad suppression while recording so channel changes do not fire gameplay abilities.
- Added configurable channel slots.
- Added Reply to Last Whisper using `/r`.
- Added General, Trade, Say, Party, Guild, Raid, Instance, numbered-channel, and Off slot options.
- Added context-aware in-game onboarding with `/fv setup`.
- Added recording/transcribing/channel HUD.
- Added direct Windows XInput controller handling.
- Added persistent microphone selection.
- Added Windows Startup integration.
- Added standalone `ForeverVoiceHelper.exe` build path.
- Added release ZIP and SHA256 packaging script.

### Known limitation

WoW restricts changing secure override bindings during combat. If recording begins while already in combat, D-pad suppression may not activate until combat ends.
