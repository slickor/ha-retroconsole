# PortMaster Notes

Voraussichtliche Paketstruktur:

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

Die App sollte als `Ready to Run` gelten koennen, aber fuer echte Nutzung muss der Nutzer eine eigene `config.json` mit Home-Assistant-URL und Token anlegen.

Wichtige Designentscheidung: kein WebView/Lovelace-Clone. Die App nutzt die Home-Assistant-REST-API direkt und spaeter optional WebSocket-Events.

