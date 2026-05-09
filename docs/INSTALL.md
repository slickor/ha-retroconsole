# Installation & Configuration Guide

This guide helps you set up **Home Assistant - for retroconsoles** on your handheld device (e.g., TrimUI Smart Pro, R36S) via PortMaster.

---

## 1. Home Assistant Preparation

### Create a Long-Lived Access Token
1. Log in to your Home Assistant instance.
2. Click on your **User Profile** (bottom left).
3. Select the **Security** tab.
4. Scroll to the bottom to **Long-lived access tokens**.
5. Click **Create Token**, name it (e.g., "RetroConsole"), and copy the generated string. 
   > **Note:** Store this token safely; it will not be displayed again.

---

## 2. Handheld Installation (PortMaster)

1. **Download** the latest release ZIP (`ha-retroconsole.zip`).
2. **Access SD Card**: Connect your handheld's SD card to your computer.
3. **Copy Files**:
   - Extract the `ha-retroconsole` folder into the `/roms/ports/` directory on your SD card.
   - Move the launcher script (`Home Assistant - for retroconsoles.sh`) from inside that folder directly into the `/roms/ports/` directory.
4. **Structure Check**: Your SD card should look like this:
   - `/roms/ports/Home Assistant - for retroconsoles.sh`
   - `/roms/ports/ha-retroconsole/tools/...`
   - `/roms/ports/ha-retroconsole/assets/...`

---

## 3. Configuration (`config.json`)

The app requires a `config.json` file in the `ha-retroconsole` folder. You can rename `config.example.json` or create a new one:

```json
{
  "base_url": "http://192.168.1.100:8123",
  "token": "YOUR_LONG_LIVED_ACCESS_TOKEN",
  "control_layout": "auto",
  "favorites": []
}
```

### Critical Settings:
- **base_url**: **Use the IP address.** Most handheld Linux distributions (muOS, Spruce, ArkOS) do not support mDNS, so `homeassistant.local` will likely fail.
- **control_layout**: 
  - `"auto"`: Tries to detect your OS (Spruce vs. muOS).
  - `"muos"`: Uses A for Confirm, B for Cancel.
  - `"spruce"`: Uses B for Confirm, A for Cancel.

---

## 4. Controls

- **D-Pad Up/Down**: Navigate through Domain or Entity lists.
- **D-Pad Left/Right**: Switch focus between the Domain column and the Entity column.
- **Confirm (A or B)**: Toggle the selected entity or activate a scene/script.
- **Cancel (B or A)**: Back or Exit.
- **Y (North)**: Open/Close the Favorites Editor.
- **X (West)**: Force refresh all states.
- **Start**: Open Settings (to change button layouts).
- **Select**: Display version info.