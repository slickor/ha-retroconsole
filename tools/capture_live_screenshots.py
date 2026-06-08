import os
import sys
import time
import subprocess

try:
    import pyautogui
    import pygetwindow as gw
except ImportError:
    print("Bitte installiere die benötigten Module: pip install pyautogui pygetwindow Pillow pyscreeze")
    sys.exit(1)

# --- Konfiguration ---
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "screenshots")
CONFIG_SRC = os.path.join(os.path.dirname(__file__), "..", "config.json")
APP_SCRIPT = os.path.join(os.path.dirname(__file__), "ha_sdl2.py")
APP_DIR = os.path.dirname(__file__)

# Offset-Werte für Fensterrahmen (Windows)
BORDER_LEFT = 8
BORDER_RIGHT = 8
BORDER_TOP = 31
BORDER_BOTTOM = 8

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def main():
    if not os.path.exists(CONFIG_SRC):
        print(f"Fehler: config.json nicht gefunden unter {CONFIG_SRC}")
        return

    print("Starte Anwendung...")
    # Starte die App direkt mit der aktuellen config.json
    process = subprocess.Popen(
        [sys.executable, APP_SCRIPT, "--config", CONFIG_SRC],
        cwd=APP_DIR
    )

    print("Warte 10 Sekunden für den Start und ersten Verbindungsaufbau...")
    time.sleep(10)

    try:
        count = 1
        while process.poll() is None:
            screenshot_path = os.path.join(OUTPUT_DIR, f"live_screenshot_{count:03d}.png")
            
            # Finde das Fenster
            app_window = None
            for title in gw.getAllTitles():
                if "Home Assistant" in title or "HA Retro" in title:
                    app_window = gw.getWindowsWithTitle(title)[0]
                    break
            
            if app_window:
                try:
                    app_window.activate() # Versuche, das Fenster in den Vordergrund zu holen
                    time.sleep(0.5)
                except Exception:
                    pass
                
                region = (
                    app_window.left + BORDER_LEFT, 
                    app_window.top + BORDER_TOP, 
                    app_window.width - BORDER_LEFT - BORDER_RIGHT, 
                    app_window.height - BORDER_TOP - BORDER_BOTTOM
                )
                pyautogui.screenshot(screenshot_path, region=region)
                print(f"Screenshot {count} gespeichert: {screenshot_path}")
            else:
                print("[Warnung] Fenster nicht gefunden. Mache stattdessen einen Vollbild-Screenshot...")
                pyautogui.screenshot(screenshot_path)
                print(f"Vollbild-Screenshot {count} gespeichert: {screenshot_path}")

            count += 1
            print("Warte weitere 10 Sekunden...")
            time.sleep(10)
            
    except KeyboardInterrupt:
        print("\nScreenshot-Automatisierung durch Benutzer abgebrochen (Strg+C).")
    finally:
        print("Beende die Anwendung...")
        if process.poll() is None:
            process.terminate()
            process.wait()

if __name__ == "__main__":
    print("Starte kontinuierliche Screenshot-Automatisierung...")
    print("Die App wird gestartet und alle 10 Sekunden wird ein Screenshot erstellt.")
    print("Abbrechen jederzeit mit Strg+C möglich.")
    main()
