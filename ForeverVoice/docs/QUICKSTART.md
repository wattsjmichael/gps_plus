# ForeverVoice — 2-minute setup

ForeverVoice gives WoW Forever controller players local speech-to-text chat.

## 1. Install

1. Extract the release ZIP.
2. Run `install.ps1` with PowerShell.
3. Pick your microphone when the helper setup window opens.
4. Start WoW Forever.
5. Type `/reload`.

## 2. Configure the controller

Type:

`/fv setup`

Choose:

- **Voice Start / Send** — press once to start recording and again to send.
- **Channel Select modifier** — normally Left Trigger.
- Four channel slots for Modifier + D-pad.

Recommended default:

- LT + Up → General
- LT + Right → Trade
- LT + Down → Reply to last whisper
- LT + Left → Party

Any slot can be changed to Off, Guild, Say, Raid, Instance, or another joined numbered channel.

## 3. Use it

Press your Voice button once. The red HUD means ForeverVoice is recording.

While recording, hold your Channel Select modifier and press a D-pad direction. The HUD badge changes to show the destination. Press the Voice button again to transcribe and send.

During recording, ForeverVoice temporarily suppresses the D-pad gameplay bindings so selecting a channel does not cast abilities. Normal controller behavior returns after sending.

## Helper

The Windows helper starts automatically when you sign in. Speech is transcribed locally on your PC.

To change microphones later, run:

`ForeverVoiceHelper.exe --setup`

In-game commands:

- `/fv setup` — controller and channel setup
- `/fv slots` — show current channel slots
- `/fv move` — move the HUD
- `/fv hide` — hide HUD preview
- `/fv reset` — reset HUD position
