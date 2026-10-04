local ADDON_NAME = ...
BINDING_HEADER_FOREVERVOICE = "ForeverVoice"
BINDING_NAME_FOREVERVOICE_TOGGLE = "Voice: Start / Send"

ForeverVoiceDB = ForeverVoiceDB or {}

local DEFAULTS = {
  controllerToggle = "PADDUP",
  controllerModifier = "PADLTRIGGER",
  controllerUpButton = "PADDUP",
  controllerRightButton = "PADDRIGHT",
  controllerDownButton = "PADDDOWN",
  controllerLeftButton = "PADDLEFT",
  controllerUpChannel = "general",
  controllerRightChannel = "trade",
  controllerDownChannel = "guild",
  controllerLeftChannel = "party",
}

for k, v in pairs(DEFAULTS) do
  if not ForeverVoiceDB[k] then ForeverVoiceDB[k] = v end
end

local state = "idle"
local channel = "general"
local preview = false
local captureTarget = nil

local CHANNELS = {
  general = { label = "1", name = "GENERAL /1" },
  trade   = { label = "2", name = "TRADE /2" },
  party   = { label = "P", name = "PARTY /p" },
  guild   = { label = "G", name = "GUILD /g" },
  say     = { label = "S", name = "SAY /s" },
}

local function savePosition(frame)
  local point, _, relativePoint, x, y = frame:GetPoint(1)
  ForeverVoiceDB.point = point
  ForeverVoiceDB.relativePoint = relativePoint
  ForeverVoiceDB.x = x
  ForeverVoiceDB.y = y
end

local icon = CreateFrame("Frame", "ForeverVoiceStatusIcon", UIParent, "BackdropTemplate")
icon:SetSize(44, 44)
icon:SetFrameStrata("HIGH")
icon:SetClampedToScreen(true)
icon:SetMovable(true)
icon:EnableMouse(true)
icon:RegisterForDrag("LeftButton")
icon:SetBackdrop({
  bgFile = "Interface\\Buttons\\WHITE8X8",
  edgeFile = "Interface\\Buttons\\WHITE8X8",
  edgeSize = 1,
})
icon:SetBackdropColor(0.04, 0.04, 0.04, 0.88)
icon:SetBackdropBorderColor(0.25, 0.25, 0.25, 1)

if ForeverVoiceDB.point then
  icon:SetPoint(
    ForeverVoiceDB.point, UIParent,
    ForeverVoiceDB.relativePoint or ForeverVoiceDB.point,
    ForeverVoiceDB.x or 0, ForeverVoiceDB.y or 0
  )
else
  icon:SetPoint("TOP", UIParent, "TOP", 0, -105)
end

icon:SetScript("OnDragStart", function(self) self:StartMoving() end)
icon:SetScript("OnDragStop", function(self)
  self:StopMovingOrSizing()
  savePosition(self)
end)

icon.mic = icon:CreateTexture(nil, "ARTWORK")
icon.mic:SetSize(27, 27)
icon.mic:SetPoint("CENTER")
icon.mic:SetTexture("Interface\\COMMON\\VoiceChat-Speaker")

icon.badge = CreateFrame("Frame", nil, icon, "BackdropTemplate")
icon.badge:SetSize(18, 18)
icon.badge:SetPoint("BOTTOMRIGHT", icon, "BOTTOMRIGHT", 4, -4)
icon.badge:SetBackdrop({
  bgFile = "Interface\\Buttons\\WHITE8X8",
  edgeFile = "Interface\\Buttons\\WHITE8X8",
  edgeSize = 1,
})
icon.badge:SetBackdropColor(0.05, 0.05, 0.05, 0.96)
icon.badge:SetBackdropBorderColor(0.7, 0.7, 0.7, 1)
icon.badge.text = icon.badge:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
icon.badge.text:SetPoint("CENTER")

icon.dot = icon:CreateTexture(nil, "OVERLAY")
icon.dot:SetSize(9, 9)
icon.dot:SetPoint("TOPLEFT", icon, "TOPLEFT", 4, -4)
icon.dot:SetTexture("Interface\\Buttons\\WHITE8X8")

local pulse = icon:CreateAnimationGroup()
pulse:SetLooping("BOUNCE")
local fade = pulse:CreateAnimation("Alpha")
fade:SetFromAlpha(1)
fade:SetToAlpha(0.35)
fade:SetDuration(0.55)
fade:SetSmoothing("IN_OUT")

local function applyVisualState()
  local info = CHANNELS[channel] or CHANNELS.general
  icon.badge.text:SetText(info.label)

  if state == "recording" then
    icon.mic:SetVertexColor(1.0, 0.25, 0.25, 1)
    icon.dot:SetColorTexture(1.0, 0.1, 0.1, 1)
    if not pulse:IsPlaying() then pulse:Play() end
    icon:Show()
  elseif state == "transcribing" then
    if pulse:IsPlaying() then pulse:Stop() end
    icon:SetAlpha(1)
    icon.mic:SetVertexColor(1.0, 0.82, 0.15, 1)
    icon.dot:SetColorTexture(1.0, 0.72, 0.0, 1)
    icon:Show()
  elseif preview then
    if pulse:IsPlaying() then pulse:Stop() end
    icon:SetAlpha(1)
    icon.mic:SetVertexColor(0.35, 0.8, 1.0, 1)
    icon.dot:SetColorTexture(0.35, 0.8, 1.0, 1)
    icon:Show()
  else
    if pulse:IsPlaying() then pulse:Stop() end
    icon:SetAlpha(1)
    icon:Hide()
  end
end

-- Recording-only controller swallow layer -----------------------------------
-- While the helper is recording, reserve the configured modifier+D-pad chords
-- so WoW does not also execute their normal gameplay bindings.
local overrideOwner = CreateFrame("Frame", "ForeverVoiceOverrideOwner", UIParent)
local swallowUp = CreateFrame("Button", "ForeverVoiceSwallowUp", UIParent, "SecureActionButtonTemplate")
local swallowRight = CreateFrame("Button", "ForeverVoiceSwallowRight", UIParent, "SecureActionButtonTemplate")
local swallowDown = CreateFrame("Button", "ForeverVoiceSwallowDown", UIParent, "SecureActionButtonTemplate")
local swallowLeft = CreateFrame("Button", "ForeverVoiceSwallowLeft", UIParent, "SecureActionButtonTemplate")

local overridesInstalled = false
local overrideDeferred = false

local function controllerChord(button)
  return tostring(ForeverVoiceDB.controllerModifier) .. "-" .. tostring(button)
end

local function clearRecordingOverrides()
  if InCombatLockdown and InCombatLockdown() then
    overrideDeferred = true
    return false
  end
  ClearOverrideBindings(overrideOwner)
  overridesInstalled = false
  overrideDeferred = false
  return true
end

local function installRecordingOverrides()
  if InCombatLockdown and InCombatLockdown() then
    overrideDeferred = true
    print("|cffffa500ForeverVoice|r: channel button suppression is unavailable until combat ends.")
    return false
  end

  ClearOverrideBindings(overrideOwner)

  SetOverrideBindingClick(overrideOwner, true, controllerChord(ForeverVoiceDB.controllerUpButton), "ForeverVoiceSwallowUp", "LeftButton")
  SetOverrideBindingClick(overrideOwner, true, controllerChord(ForeverVoiceDB.controllerRightButton), "ForeverVoiceSwallowRight", "LeftButton")
  SetOverrideBindingClick(overrideOwner, true, controllerChord(ForeverVoiceDB.controllerDownButton), "ForeverVoiceSwallowDown", "LeftButton")
  SetOverrideBindingClick(overrideOwner, true, controllerChord(ForeverVoiceDB.controllerLeftButton), "ForeverVoiceSwallowLeft", "LeftButton")

  overridesInstalled = true
  overrideDeferred = false
  return true
end

local function syncRecordingOverrides()
  if state == "recording" then
    if not overridesInstalled then
      installRecordingOverrides()
    end
  elseif overridesInstalled or overrideDeferred then
    clearRecordingOverrides()
  end
end

-- Helper -> addon bridge ------------------------------------------------------
-- Helper owns the real state. Ctrl+Alt+Shift+F5..F11 are reserved status
-- signals because WoW reliably exposes these ordinary function keys.
local bridge = CreateFrame("Frame", "ForeverVoiceBridgeObserver", UIParent)
bridge:SetSize(1, 1)
bridge:SetPoint("CENTER")
bridge:EnableKeyboard(true)
bridge:SetPropagateKeyboardInput(true)
bridge:Show()

local function consumeBridgeKey()
  bridge:SetPropagateKeyboardInput(false)
  C_Timer.After(0, function()
    bridge:SetPropagateKeyboardInput(true)
  end)
end

bridge:SetScript("OnKeyDown", function(_, key)
  if not (IsControlKeyDown() and IsAltKeyDown() and IsShiftKeyDown()) then
    return
  end

  if key == "F5" then
    state = "recording"
    channel = "general"
  elseif key == "F6" then
    state = "recording"
    channel = "trade"
  elseif key == "F7" then
    state = "recording"
    channel = "party"
  elseif key == "F8" then
    state = "recording"
    channel = "guild"
  elseif key == "F9" then
    state = "recording"
    channel = "say"
  elseif key == "F10" then
    state = "transcribing"
  elseif key == "F11" then
    state = "idle"
  else
    return
  end

  consumeBridgeKey()
  preview = false
  applyVisualState()
  syncRecordingOverrides()
end)

-- Controller setup panel ------------------------------------------------------
local setup = CreateFrame("Frame", "ForeverVoiceSetupFrame", UIParent, "BackdropTemplate")
setup:SetSize(390, 245)
setup:SetPoint("CENTER")
setup:SetFrameStrata("DIALOG")
setup:SetMovable(true)
setup:EnableMouse(true)
setup:RegisterForDrag("LeftButton")
setup:SetScript("OnDragStart", setup.StartMoving)
setup:SetScript("OnDragStop", setup.StopMovingOrSizing)
setup:SetBackdrop({
  bgFile = "Interface\\DialogFrame\\UI-DialogBox-Background",
  edgeFile = "Interface\\DialogFrame\\UI-DialogBox-Border",
  tile = true, tileSize = 32, edgeSize = 32,
  insets = { left = 11, right = 12, top = 12, bottom = 11 },
})
setup:Hide()

setup.title = setup:CreateFontString(nil, "OVERLAY", "GameFontNormalLarge")
setup.title:SetPoint("TOP", 0, -20)
setup.title:SetText("ForeverVoice Controller")

setup.help = setup:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
setup.help:SetPoint("TOP", setup.title, "BOTTOM", 0, -8)
setup.help:SetWidth(340)
setup.help:SetText("The helper owns recording. The addon only saves controller mappings and displays helper status.")

local function makeLabel(text, y)
  local fs = setup:CreateFontString(nil, "OVERLAY", "GameFontNormal")
  fs:SetPoint("TOPLEFT", 28, y)
  fs:SetText(text)
  return fs
end

local function makeCaptureButton(dbKey, y)
  local b = CreateFrame("Button", nil, setup, "UIPanelButtonTemplate")
  b:SetSize(145, 24)
  b:SetPoint("TOPRIGHT", -28, y + 5)
  b:SetText(ForeverVoiceDB[dbKey])
  b:SetScript("OnClick", function(self)
    captureTarget = { key = dbKey, button = self }
    self:SetText("Press controller button...")
  end)
  return b
end

makeLabel("Voice Start / Send", -82)
local voiceButton = makeCaptureButton("controllerToggle", -82)
makeLabel("Channel modifier", -118)
local modifierButton = makeCaptureButton("controllerModifier", -118)

local mapText = setup:CreateFontString(nil, "OVERLAY", "GameFontHighlight")
mapText:SetPoint("TOPLEFT", 28, -158)
mapText:SetText("While recording:\nLT + Up = General /1\nLT + Right = Trade /2\nLT + Down = Guild /g\nLT + Left = Party /p")

local save = CreateFrame("Button", nil, setup, "UIPanelButtonTemplate")
save:SetSize(115, 24)
save:SetPoint("BOTTOMRIGHT", -28, 22)
save:SetText("Save + Reload")
save:SetScript("OnClick", function()
  setup:Hide()
  ReloadUI()
end)

local close = CreateFrame("Button", nil, setup, "UIPanelButtonTemplate")
close:SetSize(80, 24)
close:SetPoint("RIGHT", save, "LEFT", -8, 0)
close:SetText("Close")
close:SetScript("OnClick", function() setup:Hide() end)

-- This observer is ONLY for mapping capture now. It never changes recording
-- state or channels; the helper is authoritative.
local controllerCapture = CreateFrame("Frame", "ForeverVoiceControllerCapture", UIParent)
controllerCapture:EnableGamePadButton(true)
controllerCapture:SetPropagateKeyboardInput(true)
controllerCapture:Show()

controllerCapture:SetScript("OnGamePadButtonDown", function(_, button)
  if not captureTarget then return end
  ForeverVoiceDB[captureTarget.key] = button
  captureTarget.button:SetText(button)
  captureTarget = nil
end)

SLASH_FOREVERVOICE1 = "/fv"
SlashCmdList.FOREVERVOICE = function(msg)
  msg = (msg or ""):lower():gsub("^%s+",""):gsub("%s+$","")
  if msg == "setup" or msg == "controller" then
    voiceButton:SetText(ForeverVoiceDB.controllerToggle)
    modifierButton:SetText(ForeverVoiceDB.controllerModifier)
    setup:Show()
  elseif msg == "show" or msg == "move" then
    preview = true
    state = "idle"
    applyVisualState()
  elseif msg == "hide" then
    preview = false
    state = "idle"
    applyVisualState()
  elseif msg == "reset" then
    icon:ClearAllPoints()
    icon:SetPoint("TOP", UIParent, "TOP", 0, -105)
    savePosition(icon)
    preview = true
    applyVisualState()
  else
    print("|cff69ccf0ForeverVoice|r")
    print("/fv setup - controller mapping")
    print("/fv move - move status icon")
    print("HUD state comes from the helper; controller capture only saves mappings.")
  end
end

local events = CreateFrame("Frame")
events:RegisterEvent("PLAYER_LOGIN")
events:RegisterEvent("PLAYER_REGEN_ENABLED")
events:SetScript("OnEvent", function(_, event)
  if event == "PLAYER_LOGIN" then
    state = "idle"
    preview = false
    applyVisualState()
    syncRecordingOverrides()
    print("|cff69ccf0ForeverVoice|r loaded. /fv setup for controller mapping.")
  elseif event == "PLAYER_REGEN_ENABLED" and overrideDeferred then
    syncRecordingOverrides()
  end
end)
