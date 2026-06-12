import os
import sys
import time
import subprocess

try:
    import pyautogui
    import pygetwindow as gw
except ImportError:
    print("Please install the required modules: pip install pyautogui pygetwindow Pillow pyscreeze")
    sys.exit(1)

# --- Configuration ---
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "screenshots")
CONFIG_SRC = os.path.join(os.path.dirname(__file__), "..", "config.json")
APP_SCRIPT = os.path.join(os.path.dirname(__file__), "ha_sdl2.py")
APP_DIR = os.path.dirname(__file__)

# Window frame offsets (Windows)
BORDER_LEFT = 8
BORDER_RIGHT = 8
BORDER_TOP = 31
BORDER_BOTTOM = 8

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def main():
    if not os.path.exists(CONFIG_SRC):
        print(f"Error: config.json not found at {CONFIG_SRC}")
        return

    print("Starting application...")
    # Start the app directly with the current config.json
    process = subprocess.Popen(
        [sys.executable, APP_SCRIPT, "--config", CONFIG_SRC],
        cwd=APP_DIR
    )

    print("Waiting 10 seconds for startup and first connection...")
    time.sleep(10)

    try:
        count = 1
        while process.poll() is None:
            screenshot_path = os.path.join(OUTPUT_DIR, f"live_screenshot_{count:03d}.png")
            
            # Find the window
            app_window = None
            for title in gw.getAllTitles():
                if "Home Assistant" in title or "HA Retro" in title:
                    app_window = gw.getWindowsWithTitle(title)[0]
                    break
            
            if app_window:
                try:
                    app_window.activate() # Try to bring the window to the foreground
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
                print("[Warning] Window not found. Taking a fullscreen screenshot instead...")
                pyautogui.screenshot(screenshot_path)
                print(f"Fullscreen screenshot {count} saved: {screenshot_path}")

            count += 1
            print("Waiting another 10 seconds...")
            time.sleep(10)
            
    except KeyboardInterrupt:
        print("\nScreenshot automation aborted by user (Ctrl+C).")
    finally:
        print("Terminating the application...")
        if process.poll() is None:
            process.terminate()
            process.wait()

if __name__ == "__main__":
    print("Starting continuous screenshot automation...")
    print("The app will start and a screenshot will be created every 10 seconds.")
    print("Can be cancelled at any time with Ctrl+C.")
    main()
