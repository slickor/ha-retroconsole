# Installation & Configuration Guide

This guide helps you set up **Home Assistant - for retroconsoles** on your handheld device (e.g., TrimUI Smart Pro, R36S). The application is **PortMaster compatible**.

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
   - Copy the launcher script (`Home Assistant - for retroconsoles.sh`) into `/roms/ports/` (or `/ports/` on R36S).
   - Copy the `ha-retroconsole` data folder into the `/ports/` directory on your SD card.
4. **Structure Check**: Your SD card should look like this:
   - `[SD]/roms/ports/Home Assistant - for retroconsoles.sh` (Launcher)
   - `[SD]/ports/ha-retroconsole/ha_client.py` (Data)
   - `[SD]/ports/ha-retroconsole/assets/...`

---

## 3. Configuration (`config.json`)

The app requires a `config.json` file in the `ha-retroconsole` folder. You can rename `config.example.json` or create a new one:

```json
{
  "base_url": "http://192.168.1.100:8123",
  "alternative_url": "https://your-ha.myfritz.net:8123",
  "token": "YOUR_LONG_LIVED_ACCESS_TOKEN",
  "control_layout": "auto",
  "favorites": []
}
```

### Critical Settings:
- **base_url**: **Use the IP address.** Most handheld Linux distributions (muOS, Spruce, ArkOS) do not support mDNS, so `homeassistant.local` will likely fail.
- **alternative_url**: (Optional) A secondary URL (e.g., an external domain, Nabu Casa link, or VPN address) to use as a fallback if the primary `base_url` is unreachable. The app checks connectivity on startup and falls back automatically.
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
- **Y (North)**: Toggle Favorite (Entities) or Toggle Sort Mode (Categories/Favorites).
- **X (West)**: Force refresh all states.
- **L1 / R1**: Page Up / Page Down in entity lists.
- **L2 / R2**: Scroll through the console log history.
- **Start**: Open Settings (to change button layouts).

### Context-Sensitive Controls (Settings -> Server Connection)
- **Confirm (A or B)**: Manually switch to the selected URL and force a data refresh.
- **Y (North)**: Open the On-Screen Keyboard to edit the highlighted URL.