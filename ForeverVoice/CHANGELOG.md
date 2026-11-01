# Changelog

## 0.4.0 — Silent Startup & Diagnostics (unreleased)

- Use a per-user Windows Run entry and windowless helper; migrate the known
  ForeverVoice Startup `.cmd` and `.lnk` entries without touching other entries.
- Add tray Open, Start with Windows, and Exit; duplicate launches open the existing
  diagnostics window. Shutdown closes audio and waits for owned worker threads.
- Add standalone microphone, Whisper, XInput slot 0, and WoW process diagnostics.
- Add a three-second microphone transcription test that never sends game input.
- Keep rotating application error logs and native output in the configuration folder.
- Preserve controller bindings, addon/HUD bridge, and chat transcription behavior.
- Validation: 11 automated tests, Python compilation, and diff checks passed on Linux.
  Windows packaging, physical devices, sign-in startup, and in-game integration still
  require manual verification. No release created.

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
