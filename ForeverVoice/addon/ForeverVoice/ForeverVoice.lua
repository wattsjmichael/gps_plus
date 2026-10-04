local ADDON_NAME = ...
BINDING_HEADER_FOREVERVOICE = "ForeverVoice"
BINDING_NAME_FOREVERVOICE_TOGGLE = "Voice: Start / Stop"
BINDING_NAME_FOREVERVOICE_GENERAL = "Voice Channel: General"
BINDING_NAME_FOREVERVOICE_TRADE = "Voice Channel: Trade"
BINDING_NAME_FOREVERVOICE_PARTY = "Voice Channel: Party"
BINDING_NAME_FOREVERVOICE_GUILD = "Voice Channel: Guild"
BINDING_NAME_FOREVERVOICE_SAY = "Voice Channel: Say"

ForeverVoiceDB = ForeverVoiceDB or {}

local state = "idle"
local channel = "general"
local preview = false

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

-- Small draggable status icon.
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
    ForeverVoiceDB.point,
    UIParent,
    ForeverVoiceDB.relativePoint or ForeverVoiceDB.point,
    ForeverVoiceDB.x or 0,
    ForeverVoiceDB.y or 0
  )
else
  icon:SetPoint("TOP", UIParent, "TOP", 0, -105)
end

icon:SetScript("OnDragStart", function(self)
  self:StartMoving()
end)

icon:SetScript("OnDragStop", function(self)
  self:StopMovingOrSizing()
  savePosition(self)
end)

icon.mic = icon:CreateTexture(nil, "ARTWORK")
icon.mic:SetSize(27, 27)
icon.mic:SetPoint("CENTER")
icon.mic:SetTexture("Interface\\COMMON\\VoiceChat-Speaker")
icon.mic:SetVertexColor(1, 1, 1, 1)

-- Small channel badge in the lower-right corner.
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
icon.badge.text:SetPoint("CENTER", 0, 0)
icon.badge.text:SetText("1")

-- Status dot: red while recording, gold while transcribing.
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

icon:SetScript("OnEnter", function(self)
  GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
  GameTooltip:AddLine("ForeverVoice")
  local info = CHANNELS[channel] or CHANNELS.general
  GameTooltip:AddLine("Channel: " .. info.name, 1, 1, 1)
  if state == "recording" then
    GameTooltip:AddLine("Recording", 1, 0.25, 0.25)
  elseif state == "transcribing" then
    GameTooltip:AddLine("Transcribing", 1, 0.82, 0.15)
  else
    GameTooltip:AddLine("Drag to move", 0.7, 0.7, 0.7)
  end
  GameTooltip:Show()
end)
icon:SetScript("OnLeave", GameTooltip_Hide)

function ForeverVoice_Toggle()
  if state == "idle" then
    preview = false
    state = "recording"
  elseif state == "recording" then
    state = "transcribing"
    C_Timer.After(8, function()
      if state == "transcribing" then
        state = "idle"
        applyVisualState()
      end
    end)
  else
    return
  end
  applyVisualState()
end

function ForeverVoice_SelectChannel(which)
  if CHANNELS[which] then
    channel = which
    applyVisualState()
  end
end

-- The helper listens to these globally. This observer mirrors the same keys
-- inside WoW so the HUD updates without requiring the user to create bindings.
local observer = CreateFrame("Frame", "ForeverVoiceKeyboardObserver", UIParent)
observer:SetSize(1, 1)
observer:SetPoint("CENTER")
observer:EnableKeyboard(true)
observer:SetPropagateKeyboardInput(true)
observer:Show()

observer:SetScript("OnKeyDown", function(_, key)
  if key == "INSERT" then
    ForeverVoice_Toggle()
  elseif key == "PAGEUP" then
    ForeverVoice_SelectChannel("general")
  elseif key == "DELETE" then
    ForeverVoice_SelectChannel("trade")
  elseif key == "END" then
    ForeverVoice_SelectChannel("party")
  elseif key == "PAGEDOWN" then
    ForeverVoice_SelectChannel("guild")
  elseif key == "HOME" then
    ForeverVoice_SelectChannel("say")
  end
end)

SLASH_FOREVERVOICE1 = "/fv"
SlashCmdList.FOREVERVOICE = function(msg)
  msg = (msg or ""):lower():gsub("^%s+",""):gsub("%s+$","")

  if msg == "show" or msg == "move" then
    preview = true
    state = "idle"
    applyVisualState()
    print("|cff69ccf0ForeverVoice|r: preview shown. Drag the icon, then type /fv hide.")
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
    print("|cff69ccf0ForeverVoice|r: icon position reset.")
  elseif CHANNELS[msg] then
    ForeverVoice_SelectChannel(msg)
    print("|cff69ccf0ForeverVoice|r: channel = " .. CHANNELS[msg].name)
  else
    print("|cff69ccf0ForeverVoice|r")
    print("Insert = record / stop")
    print("PageUp = General, Delete = Trade, End = Party, PageDown = Guild, Home = Say")
    print("/fv move - show and drag the icon")
    print("/fv hide - hide preview")
    print("/fv reset - reset icon position")
  end
end

local events = CreateFrame("Frame")
events:RegisterEvent("PLAYER_LOGIN")
events:SetScript("OnEvent", function()
  applyVisualState()
  print("|cff69ccf0ForeverVoice|r loaded. /fv move to position the status icon.")
end)
