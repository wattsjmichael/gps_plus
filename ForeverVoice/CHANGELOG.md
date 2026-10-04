# Changelog

## 0.3.1 — Beta

- Added a proper Windows uninstall entry under **Settings → Apps → Installed apps**.
- Setup now copies an installed uninstaller to `%LOCALAPPDATA%\ForeverVoice`.
- Added **Uninstall ForeverVoice** to the Setup app when an installation is detected.
- Uninstall removes the helper, saved microphone/config settings, Windows Startup entry, and the WoW addon.
- Setup now saves the WoW installation path so uninstall removes the correct addon folder.
- Setup can be run again to install/update an existing ForeverVoice installation.

## 0.3.0 — Beta

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
- Added one-click Windows Setup EXE and SHA256 release packaging.

### Known limitation

WoW restricts changing secure override bindings during combat. If recording begins while already in combat, D-pad suppression may not activate until combat ends.
