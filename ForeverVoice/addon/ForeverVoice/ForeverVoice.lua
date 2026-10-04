local ADDON_NAME = ...
BINDING_HEADER_FOREVERVOICE = "ForeverVoice"
BINDING_NAME_FOREVERVOICE_TOGGLE = "Voice: Start / Stop"
BINDING_NAME_FOREVERVOICE_GENERAL = "Voice Channel: General"
BINDING_NAME_FOREVERVOICE_PARTY = "Voice Channel: Party"
BINDING_NAME_FOREVERVOICE_GUILD = "Voice Channel: Guild"
BINDING_NAME_FOREVERVOICE_SAY = "Voice Channel: Say"

local state = "idle"
local channel = "general"

local CHANNELS = {
  general = "GENERAL /1",
  party = "PARTY /p",
  guild = "GUILD /g",
  say = "SAY /s",
}

local frame = CreateFrame("Frame", "ForeverVoiceHUD", UIParent)
frame:SetSize(340, 54)
frame:SetPoint("TOP", UIParent, "TOP", 0, -90)
frame:SetFrameStrata("HIGH")

frame.bg = frame:CreateTexture(nil, "BACKGROUND")
frame.bg:SetAllPoints()
frame.bg:SetColorTexture(0, 0, 0, 0.60)

frame.title = frame:CreateFontString(nil, "OVERLAY", "GameFontNormalLarge")
frame.title:SetPoint("TOP", 0, -7)

frame.channel = frame:CreateFontString(nil, "OVERLAY", "GameFontHighlight")
frame.channel:SetPoint("TOP", frame.title, "BOTTOM", 0, -4)
frame:Hide()

local function refresh()
  if state == "idle" then
    frame:Hide()
    return
  end
  if state == "recording" then
    frame.title:SetText("|cffff4040●|r Recording")
  else
    frame.title:SetText("|cffffd100…|r Transcribing")
  end
  frame.channel:SetText(CHANNELS[channel] or channel)
  frame:Show()
end

function ForeverVoice_Toggle()
  if state == "idle" then
    state = "recording"
  elseif state == "recording" then
    state = "transcribing"
    C_Timer.After(8, function()
      if state == "transcribing" then
        state = "idle"
        refresh()
      end
    end)
  else
    return
  end
  refresh()
end

function ForeverVoice_SelectChannel(which)
  if CHANNELS[which] then
    channel = which
    if state ~= "idle" then refresh() end
  end
end

SLASH_FOREVERVOICE1 = "/fv"
SlashCmdList.FOREVERVOICE = function(msg)
  msg = (msg or ""):lower():gsub("^%s+",""):gsub("%s+$","")
  if msg == "test" then
    state = "recording"
    refresh()
  elseif CHANNELS[msg] then
    ForeverVoice_SelectChannel(msg)
    print("|cff69ccf0ForeverVoice|r: channel = " .. CHANNELS[msg])
  else
    print("|cff69ccf0ForeverVoice|r")
    print("Bind these under Key Bindings > AddOns > ForeverVoice:")
    print("  Voice: Start / Stop")
    print("  Voice Channel: General / Party / Guild / Say")
    print("Helper defaults: Insert=toggle, PageUp=General, End=Party, PageDown=Guild, Home=Say")
  end
end

local events = CreateFrame("Frame")
events:RegisterEvent("PLAYER_LOGIN")
events:SetScript("OnEvent", function()
  print("|cff69ccf0ForeverVoice|r loaded. Type /fv for setup.")
end)
