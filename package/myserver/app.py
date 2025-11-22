# myserver/app.py

import time
from datetime import datetime

def run():
    """Fake server loop."""

    print("Starting app. Press Ctrl+C to stop.")
    try:
        while True:
            print(f"[{datetime.now().isoformat(timespec='seconds')}] my app is running...")
            time.sleep(2)
    except KeyboardInterrupt:
        print("App received KeyboardInterrupt, shutting down.")