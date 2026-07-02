"""
Debug script — Shows what the Windows Media Session API reports for Spotify.
Run this while Spotify is playing music AND when an ad plays.
This shows the ACTUAL metadata Windows sees, which is what we use to detect ads.

Usage:
    python debug_spotify.py
    
Then play a song and wait for an ad. Press Ctrl+C to stop.
"""

import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from media_session import get_spotify_media_info, is_ad, format_now_playing
from monitor import is_spotify_running, get_spotify_window_title


if __name__ == "__main__":
    print("=" * 65)
    print("  SPOTIFY DEBUG — Media Session Inspector")
    print("=" * 65)
    print()
    print("  This polls every 2 seconds. Press Ctrl+C to stop.")
    print("  Play a song, then wait for an ad to see metadata changes.")
    print()

    try:
        while True:
            timestamp = time.strftime("%H:%M:%S")
            print(f"[{timestamp}] " + "─" * 50)

            # Check if Spotify is running
            running = is_spotify_running()
            if not running:
                print("  ⚠  Spotify is NOT running")
                print()
                time.sleep(2)
                continue

            print("  ✓  Spotify is running")

            # Window title (for comparison)
            win_title = get_spotify_window_title()
            print(f"  Window Title : \"{win_title}\"")

            # Media Session info (the reliable approach)
            info = get_spotify_media_info()

            if info is None:
                print("  ⚠  Could not read media session (PowerShell error)")
            else:
                print(f"  ── Media Session ──")
                print(f"  Title        : \"{info.get('title', '')}\"")
                print(f"  Artist       : \"{info.get('artist', '')}\"")
                print(f"  Album Title  : \"{info.get('albumTitle', '')}\"")
                print(f"  Album Artist : \"{info.get('albumArtist', '')}\"")
                print(f"  Track #      : {info.get('trackNumber', 'N/A')}")
                print(f"  Duration     : {info.get('endTime', 0)}s")
                print(f"  Position     : {info.get('position', 0)}s")
                print(f"  Status       : {info.get('playbackStatus', 'N/A')}")
                print(f"  Type         : {info.get('playbackType', 'N/A')}")
                print(f"  Source       : {info.get('source', 'N/A')}")

                # Ad detection result
                ad_detected = is_ad(info)
                if ad_detected:
                    print(f"  ── 🚨 AD DETECTED! Would close Spotify ──")
                else:
                    display = format_now_playing(info)
                    print(f"  ── ✅ Normal playback: {display} ──")

            print()
            time.sleep(2)

    except KeyboardInterrupt:
        print("\n  Stopped.")
