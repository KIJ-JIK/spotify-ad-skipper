"""
Media Session — Python wrapper for the Windows Media Session API.
Calls a PowerShell script to read the actual media metadata from
Windows' Global System Media Transport Controls (GSMTC).

This is far more reliable than window-title monitoring for
Microsoft Store Spotify, because ads change the media metadata
even when they don't change the window title.
"""

import subprocess
import json
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PS_SCRIPT = os.path.join(SCRIPT_DIR, "get_media_info.ps1")


def get_spotify_media_info() -> dict | None:
    """
    Get the current Spotify media session info from Windows.

    Returns a dict with keys:
        source, title, artist, albumTitle, albumArtist,
        trackNumber, playbackStatus, endTime, position, playbackType

    Returns None if the call fails or Spotify has no active session.
    """
    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy", "Bypass",
                "-File", PS_SCRIPT,
            ],
            capture_output=True,
            text=True,
            timeout=8,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )

        output = result.stdout.strip()
        if output:
            data = json.loads(output)
            if "error" in data:
                return None
            return data

    except subprocess.TimeoutExpired:
        pass
    except json.JSONDecodeError:
        pass
    except Exception:
        pass

    return None


def is_ad(info: dict) -> bool:
    """
    Determine if the media session info indicates a Spotify ad.

    Detection signals (any one triggers):
      1. Title or artist contains "advertisement"
      2. Artist is "Spotify" / empty (Spotify-branded promos, generic ads)
      3. No album metadata AND short duration (≤ 45s)
      4. No album metadata AND no artist AND playing
    """
    if not info:
        return False

    status = (info.get("playbackStatus") or "").strip()
    if status != "Playing":
        return False

    title = (info.get("title") or "").strip()
    artist = (info.get("artist") or "").strip()
    album = (info.get("albumTitle") or "").strip()
    album_artist = (info.get("albumArtist") or "").strip()
    duration = info.get("endTime", 0)

    title_l = title.lower()
    artist_l = artist.lower()

    # ── Signal 1: explicit "advertisement" keyword ──
    if "advertisement" in title_l or "advertisement" in artist_l:
        return True

    # ── Signal 2: Spotify-branded content (promos, house ads) ──
    if artist_l in ("spotify", "spotify free", "spotify music", ""):
        # But only if it's actually playing something (has a title)
        if title and not album:
            return True

    # ── Signal 3: no album metadata + short duration ──
    if not album and not album_artist and 0 < duration <= 45:
        return True

    # ── Signal 4: no album + no artist + has title = generic ad ──
    if not album and not album_artist and not artist and title:
        return True

    return False


def format_now_playing(info: dict) -> str:
    """Format media info as a human-readable 'Artist - Title' string."""
    if not info:
        return "Unknown"
    title = (info.get("title") or "").strip()
    artist = (info.get("artist") or "").strip()
    if artist and title:
        return f"{artist} - {title}"
    return title or artist or "Unknown"
