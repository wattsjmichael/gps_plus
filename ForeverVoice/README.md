# ForeverVoice

Clean speech-to-text chat for WoW Forever.

## Design rule

ForeverVoice does **not** detect controllers. It listens to ordinary keyboard keys. Controller software can map any physical button or paddle to those keys.

## Default controls

- Insert: start / stop recording
- PageUp: General (/1)
- End: Party (/p)
- PageDown: Guild (/g)
- Home: Say (/s)

The helper uses CPU Whisper by default to avoid CUDA setup failures.

## Install

Run PowerShell as Administrator:

```powershell
cd D:\gps_plus\ForeverVoice
.\install.ps1
```

Then start the helper:

```powershell
.\run-helper.ps1 --input-device 1
```

In WoW, enable ForeverVoice, then bind the same keys under:

Key Bindings > AddOns > ForeverVoice

The addon only displays state/channel. The helper records, transcribes, and types the final message into WoW chat.

## Public-release goals

- single Helper.exe
- first-run mic test
- automatic WoW install detection
- in-game setup panel
- helper-connected status
- controller setup guides
