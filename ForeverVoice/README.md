# ForeverVoice

Controller-first local speech-to-text chat for WoW Forever.

ForeverVoice has two pieces:

- WoW addon: onboarding, channel slots, recording HUD, and temporary D-pad suppression while recording.
- Windows helper: microphone capture, local Whisper transcription, XInput controller handling, and typing the final message into WoW.

Speech is transcribed locally on the PC.

## Controller flow

Default behavior:

- D-pad Up: Start / Send
- While recording, hold LT and use the D-pad to choose a destination.
- During recording, the addon temporarily suppresses normal D-pad gameplay bindings so channel selection does not fire abilities.
- When recording ends, normal bindings return.

The four directions are channel slots, not fixed channels. In /fv setup, each slot can be assigned to:

- General /1
- Trade /2
- Say /s
- Party /p
- Guild /g when available
- Raid /raid when available
- Instance /i when available
- Reply to last whisper /r
- Numbered channels currently joined
- Off

Default new-user layout:

- LT + Up: General
- LT + Right: Trade
- LT + Down: Reply to last whisper
- LT + Left: Party

## In-game onboarding

Type:

    /fv setup

On first install, the setup window opens automatically.

The setup screen lets the player capture Start / Send, capture the Channel Select modifier, and choose a destination for each directional slot. Save + Reload writes those choices to SavedVariables so the Windows helper can pick them up.

Useful commands:

    /fv setup
    /fv slots
    /fv move
    /fv hide
    /fv reset

## Helper microphone setup

The helper stores Windows-side settings in:

    %APPDATA%\ForeverVoice\config.json

Choose a microphone with:

    .\run-helper.ps1 --setup

or, after building the packaged helper:

    .\helper\dist\ForeverVoiceHelper.exe --setup

## Development install

    cd D:\gps_plus\ForeverVoice
    .\install.ps1

The installer detects WoW Forever, installs the addon, and creates a per-user Windows Startup shortcut.

If a packaged helper exists, the installer uses it. Otherwise it falls back to the Python development helper.

## Build standalone Helper.exe

From the ForeverVoice directory:

    .\build-helper.ps1

Output:

    helper\dist\ForeverVoiceHelper.exe

Then rerun:

    .\install.ps1

The installer will prefer the packaged executable. End users do not need Python at runtime when the packaged helper is distributed.

## Architecture

The Windows helper is authoritative for recording state and channel selection.

The addon receives helper state through hidden keyboard status chords and handles presentation/configuration plus WoW-side D-pad suppression. Controller input itself is read through Windows XInput.

This prevents the addon and helper from maintaining conflicting copies of recording state.

## v0.3 target

- Working controller voice flow
- Reply-to-whisper
- Configurable channel slots
- Context-aware setup
- Local microphone persistence
- Standalone Helper.exe build path
- Windows autostart

Before public release, the helper executable should be code-signed and distributed with checksums and source links so users can verify what they are installing.
