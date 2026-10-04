# ForeverVoice

**Controller-first local speech-to-text chat for WoW Forever.**

> **Beta — Windows only**
>
> ForeverVoice requires the included Windows companion app. The WoW addon handles the in-game UI and controller behavior; the helper handles microphone capture and local speech-to-text.

## Download

**Latest beta:**  
https://github.com/wattsjmichael/gps_plus/releases/latest

Download:

`ForeverVoiceSetup-v0.3.1.exe`

Run it once. The setup app:

- finds WoW Forever automatically
- detects an Xbox/XInput controller
- lets you choose your microphone
- installs the WoW addon
- installs the ForeverVoice helper under your Windows profile
- enables autostart
- starts the helper

After that, launch WoW, type `/reload`, then:

`/fv setup`

## What ForeverVoice does

Press one controller button to start recording. Keep playing while you talk.

While recording, hold your channel modifier and tap a D-pad direction to choose where the message goes. Press the same Voice button again to transcribe and send.

Recommended layout:

- LT + Up → General
- LT + Right → Trade
- LT + Down → Reply to last whisper
- LT + Left → Party

Each direction can instead be assigned to:

- General
- Trade
- Say
- Party
- Guild
- Raid
- Instance
- Reply to Last Whisper
- any joined numbered channel
- Off

ForeverVoice temporarily suppresses the D-pad gameplay bindings while recording, so changing channels does **not** also fire an ability.

## Local transcription

Speech-to-text runs locally on your PC using Whisper.

ForeverVoice does not send your microphone audio to a hosted transcription service.

## In-game commands

- `/fv setup` — controller and channel setup
- `/fv slots` — show current channel assignments
- `/fv move` — move the recording HUD
- `/fv hide` — hide HUD preview
- `/fv reset` — reset HUD position

## Requirements

- Windows
- WoW Forever
- XInput-compatible controller
- microphone

## Beta feedback

If something breaks, open a GitHub issue and include:

- controller model
- whether Setup found WoW automatically
- whether your microphone worked
- what channel slot you were using
- whether LT + D-pad fired a gameplay ability
- any helper error text

Issues:  
https://github.com/wattsjmichael/gps_plus/issues

## Trust and verification

ForeverVoice is open source.

Each public Windows release includes a SHA256 checksum for the Setup EXE so testers can verify they downloaded the same file that was published.

## Uninstall

ForeverVoice appears in **Windows Settings → Apps → Installed apps**. Choose **ForeverVoice → Uninstall** to remove the helper, saved settings, Startup entry, and WoW addon. You can also reopen ForeverVoice Setup and click **Uninstall ForeverVoice**.

## Development

ForeverVoice lives in the `ForeverVoice/` directory.

Useful scripts:

- `build-setup.ps1` — build the one-click Windows installer
- `release.ps1` — create the versioned Setup EXE + SHA256
- `build-helper.ps1` — build the helper by itself

Release candidate branch:

`forevervoice/v0.3-oneclick-rc`

Known-good controller snapshot:

`forevervoice/known-good-controller`

## Status

ForeverVoice v0.3.1 is currently in beta testing.
