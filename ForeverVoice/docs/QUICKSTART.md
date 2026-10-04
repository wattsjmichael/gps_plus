# ForeverVoice — 2-minute setup

## 1. Run ForeverVoice Setup

Download and double-click:

`ForeverVoiceSetup-v0.3.1.exe`

The setup app automatically:

- finds WoW Forever
- detects an Xbox/XInput controller
- lets you choose your microphone
- installs the WoW addon
- installs ForeverVoice Helper under your Windows profile
- enables Windows autostart
- starts the helper

No Python, PowerShell, or manual addon copying is required.

## 2. Configure it in WoW

Start WoW Forever and type:

`/reload`

Then:

`/fv setup`

Choose your Start / Send button, Channel Select modifier, and four channel slots.

Recommended layout:

- LT + Up → General
- LT + Right → Trade
- LT + Down → Reply to last whisper
- LT + Left → Party

## 3. Talk

Press Start / Send once to begin recording.

While recording, hold the Channel Select modifier and press a D-pad direction. Press Start / Send again to transcribe and send.

ForeverVoice temporarily suppresses normal D-pad gameplay bindings while recording so choosing a channel does not fire an ability.

Speech transcription runs locally on your PC.


## Uninstall

Open **Windows Settings → Apps → Installed apps**, find **ForeverVoice**, and choose **Uninstall**.

You can also reopen ForeverVoice Setup and click **Uninstall ForeverVoice**.

The uninstaller removes the local helper, microphone/config settings, Windows Startup entry, and the WoW addon.
