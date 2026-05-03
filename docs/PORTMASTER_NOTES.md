# PortMaster Notes

Expected package structure:

```text
homeassistant/
  port.json
  README.md
  gameinfo.xml
  screenshot.png
  Home Assistant.sh
  homeassistant/
    homeassistant.aarch64
    conf/
      config.example.json
    licenses/
```

The app should be considered `Ready to Run`, but for actual use the user must create their own `config.json` with the Home Assistant URL and token.

Important design decision: no WebView / Lovelace clone. The app uses the Home Assistant REST API directly and may optionally add WebSocket events later.

