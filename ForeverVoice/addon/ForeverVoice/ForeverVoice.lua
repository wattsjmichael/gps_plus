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
  controllerDownChannel = "reply",
  controllerLeftChannel = "party",
  firstRunComplete = false,
}

for k, v in pairs(DEFAULTS) do
  if ForeverVoiceDB[k] == nil or ForeverVoiceDB[k] == "" then
    ForeverVoiceDB[k] = v
  end
end

local function setting(key)
  local value = ForeverVoiceDB[key]
  if value == nil or value == "" then
    value = DEFAULTS[key]
    ForeverVoiceDB[key] = value
  end
  return value
end

local state = "idle"
local channel = "general"
local preview = false
local captureTarget = nil

local CHANNEL_INFO = {
  general = { label = "1", name = "General /1" },
  trade = { label = "2", name = "Trade /2" },
  party = { label = "P", name = "Party /p" },
  guild = { label = "G", name = "Guild /g" },
  say = { label = "S", name = "Say /s" },
  reply = { label = "R", name = "Reply to last whisper /r" },
  raid = { label = "R", name = "Raid /raid" },
  instance = { label = "I", name = "Instance /i" },
  custom = { label = "#", name = "Numbered channel" },
  off = { label = "-", name = "Off" },
}

local function channelInfo(which)
  if which and string.match(which, "^channel:%d+$") then
    local id = string.match(which, "^channel:(%d+)$")
    return { label = "#", name = "Channel /" .. tostring(id) }
  end
  return CHANNEL_INFO[which] or CHANNEL_INFO.general
end

local function savePosition(frame)
  local point, _, relativePoint, x, y = frame:GetPoint(1)
  ForeverVoiceDB.point = point
  ForeverVoiceDB.relativePoint = relativePoint
  ForeverVoiceDB.x = x
  ForeverVoiceDB.y = y
end

-- HUD ------------------------------------------------------------------------
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
  local info = channelInfo(channel)
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

-- Recording-only D-pad suppression -------------------------------------------
local overrideOwner = CreateFrame("Frame", "ForeverVoiceOverrideOwner", UIParent)
CreateFrame("Button", "ForeverVoiceSwallowUp", UIParent, "SecureActionButtonTemplate")
CreateFrame("Button", "ForeverVoiceSwallowRight", UIParent, "SecureActionButtonTemplate")
CreateFrame("Button", "ForeverVoiceSwallowDown", UIParent, "SecureActionButtonTemplate")
CreateFrame("Button", "ForeverVoiceSwallowLeft", UIParent, "SecureActionButtonTemplate")

local overridesInstalled = false
local overrideDeferred = false

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
    print("|cffffa500ForeverVoice|r: D-pad suppression will activate when combat ends.")
    return false
  end

  ClearOverrideBindings(overrideOwner)
  SetOverrideBindingClick(overrideOwner, true, tostring(setting("controllerUpButton")), "ForeverVoiceSwallowUp", "LeftButton")
  SetOverrideBindingClick(overrideOwner, true, tostring(setting("controllerRightButton")), "ForeverVoiceSwallowRight", "LeftButton")
  SetOverrideBindingClick(overrideOwner, true, tostring(setting("controllerDownButton")), "ForeverVoiceSwallowDown", "LeftButton")
  SetOverrideBindingClick(overrideOwner, true, tostring(setting("controllerLeftButton")), "ForeverVoiceSwallowLeft", "LeftButton")
  overridesInstalled = true
  overrideDeferred = false
  return true
end

local function syncRecordingOverrides()
  if state == "recording" then
    if not overridesInstalled then installRecordingOverrides() end
  elseif overridesInstalled or overrideDeferred then
    clearRecordingOverrides()
  end
end

-- Helper -> addon bridge ------------------------------------------------------
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
  if not (IsControlKeyDown() and IsAltKeyDown() and IsShiftKeyDown()) then return end

  if key == "F5" then state, channel = "recording", "general"
  elseif key == "F6" then state, channel = "recording", "trade"
  elseif key == "F7" then state, channel = "recording", "party"
  elseif key == "F8" then state, channel = "recording", "guild"
  elseif key == "F9" then state, channel = "recording", "say"
  elseif key == "F10" then state, channel = "recording", "reply"
  elseif key == "F11" then state, channel = "recording", "raid"
  elseif key == "F12" then state, channel = "recording", "instance"
  elseif key == "HOME" then state, channel = "recording", "custom"
  elseif key == "END" then state = "transcribing"
  elseif key == "PAGEDOWN" then state = "idle"
  else return end

  consumeBridgeKey()
  preview = false
  applyVisualState()
  syncRecordingOverrides()
end)

-- Smart channel choices -------------------------------------------------------
local function addChoice(list, value, text)
  table.insert(list, { value = value, text = text })
end

local function channelChoices()
  local list = {}
  addChoice(list, "off", "Off")
  addChoice(list, "general", "General /1")
  addChoice(list, "trade", "Trade /2")
  addChoice(list, "say", "Say /s")
  addChoice(list, "reply", "Reply to last whisper /r")

  if IsInGroup and IsInGroup() then
    addChoice(list, "party", "Party /p")
  else
    addChoice(list, "party", "Party /p (when grouped)")
  end

  if IsInGuild and IsInGuild() then
    addChoice(list, "guild", "Guild /g")
  end

  if IsInRaid and IsInRaid() then
    addChoice(list, "raid", "Raid /raid")
  end

  local instanceGroup = false
  if IsInGroup and LE_PARTY_CATEGORY_INSTANCE then
    instanceGroup = IsInGroup(LE_PARTY_CATEGORY_INSTANCE)
  end
  if instanceGroup then
    addChoice(list, "instance", "Instance /i")
  end

  if GetChannelList then
    local raw = { GetChannelList() }
    for i = 1, #raw, 3 do
      local id = tonumber(raw[i])
      local name = raw[i + 1]
      if id and name and id > 0 then
        addChoice(list, "channel:" .. tostring(id), "#" .. tostring(id) .. " " .. tostring(name))
      end
    end
  end

  return list
end

local function choiceText(value)
  for _, item in ipairs(channelChoices()) do
    if item.value == value then return item.text end
  end
  return channelInfo(value).name
end

-- Setup / onboarding ----------------------------------------------------------
local setup = CreateFrame("Frame", "ForeverVoiceSetupFrame", UIParent, "BackdropTemplate")
setup:SetSize(560, 430)
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
setup.title:SetText("ForeverVoice Setup")

setup.help = setup:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
setup.help:SetPoint("TOP", setup.title, "BOTTOM", 0, -7)
setup.help:SetWidth(500)
setup.help:SetText("Pick Start/Send, your channel modifier, then choose what each direction means. Changes are written for the helper when you Save + Reload.")

local function label(text, x, y, template)
  local fs = setup:CreateFontString(nil, "OVERLAY", template or "GameFontNormal")
  fs:SetPoint("TOPLEFT", x, y)
  fs:SetText(text)
  return fs
end

label("1. Controller", 28, -78, "GameFontNormalLarge")
label("Voice Start / Send", 42, -112)
label("Channel Select modifier", 42, -148)

local function makeCaptureButton(dbKey, y)
  local b = CreateFrame("Button", nil, setup, "UIPanelButtonTemplate")
  b:SetSize(180, 25)
  b:SetPoint("TOPRIGHT", -35, y + 5)
  b:SetText(setting(dbKey))
  b:SetScript("OnClick", function(self)
    captureTarget = { key = dbKey, button = self }
    self:SetText("Press controller button...")
  end)
  return b
end

local voiceButton = makeCaptureButton("controllerToggle", -112)
local modifierButton = makeCaptureButton("controllerModifier", -148)

label("2. Channel slots", 28, -196, "GameFontNormalLarge")
label("These only take over while recording. Set unused directions to Off.", 42, -226, "GameFontHighlightSmall")

local slotDefs = {
  { key = "controllerUpChannel", text = "Modifier + Up", y = -258 },
  { key = "controllerRightChannel", text = "Modifier + Right", y = -294 },
  { key = "controllerDownChannel", text = "Modifier + Down", y = -330 },
  { key = "controllerLeftChannel", text = "Modifier + Left", y = -366 },
}
local slotButtons = {}

local function cycleChoice(dbKey, button)
  local choices = channelChoices()
  local current = setting(dbKey)
  local index = 0
  for i, item in ipairs(choices) do
    if item.value == current then index = i break end
  end
  index = index + 1
  if index > #choices then index = 1 end
  ForeverVoiceDB[dbKey] = choices[index].value
  button:SetText(choices[index].text)
end

for _, def in ipairs(slotDefs) do
  label(def.text, 42, def.y)
  local b = CreateFrame("Button", nil, setup, "UIPanelButtonTemplate")
  b:SetSize(230, 25)
  b:SetPoint("TOPRIGHT", -35, def.y + 5)
  b:SetText(choiceText(setting(def.key)))
  b:SetScript("OnClick", function(self) cycleChoice(def.key, self) end)
  slotButtons[def.key] = b
end

local save = CreateFrame("Button", nil, setup, "UIPanelButtonTemplate")
save:SetSize(130, 26)
save:SetPoint("BOTTOMRIGHT", -28, 20)
save:SetText("Save + Reload")
save:SetScript("OnClick", function()
  ForeverVoiceDB.firstRunComplete = true
  setup:Hide()
  ReloadUI()
end)

local close = CreateFrame("Button", nil, setup, "UIPanelButtonTemplate")
close:SetSize(85, 26)
close:SetPoint("RIGHT", save, "LEFT", -8, 0)
close:SetText("Close")
close:SetScript("OnClick", function() setup:Hide() end)

local function refreshSetup()
  voiceButton:SetText(setting("controllerToggle"))
  modifierButton:SetText(setting("controllerModifier"))
  for _, def in ipairs(slotDefs) do
    slotButtons[def.key]:SetText(choiceText(setting(def.key)))
  end
end

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

-- Slash commands --------------------------------------------------------------
SLASH_FOREVERVOICE1 = "/fv"
SlashCmdList.FOREVERVOICE = function(msg)
  msg = (msg or ""):lower():gsub("^%s+",""):gsub("%s+$","")
  if msg == "setup" or msg == "controller" then
    refreshSetup()
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
  elseif msg == "slots" then
    print("|cff69ccf0ForeverVoice|r slots:")
    print("  Up: " .. choiceText(setting("controllerUpChannel")))
    print("  Right: " .. choiceText(setting("controllerRightChannel")))
    print("  Down: " .. choiceText(setting("controllerDownChannel")))
    print("  Left: " .. choiceText(setting("controllerLeftChannel")))
  else
    print("|cff69ccf0ForeverVoice|r")
    print("/fv setup - controller + channel onboarding")
    print("/fv slots - show current channel slots")
    print("/fv move - move status icon")
  end
end

-- Events ---------------------------------------------------------------------
local events = CreateFrame("Frame")
events:RegisterEvent("PLAYER_LOGIN")
events:RegisterEvent("PLAYER_REGEN_ENABLED")
events:RegisterEvent("GROUP_ROSTER_UPDATE")
events:RegisterEvent("PLAYER_GUILD_UPDATE")
events:SetScript("OnEvent", function(_, event)
  if event == "PLAYER_LOGIN" then
    state = "idle"
    preview = false
    applyVisualState()
    syncRecordingOverrides()
    C_Timer.After(1.0, function()
      if not ForeverVoiceDB.firstRunComplete then
        refreshSetup()
        setup:Show()
      end
    end)
    print("|cff69ccf0ForeverVoice|r loaded. /fv setup to configure controller and channel slots.")
  elseif event == "PLAYER_REGEN_ENABLED" and overrideDeferred then
    syncRecordingOverrides()
  elseif setup:IsShown() then
    refreshSetup()
  end
end)
