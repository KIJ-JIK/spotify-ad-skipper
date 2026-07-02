"""
Spotify Monitor — Core ad detection, process management, and restart logic.

Uses the Windows Media Session API (via PowerShell + WinRT) to detect ads
by reading actual media metadata (title, artist, album, duration).
This works reliably with the Microsoft Store version of Spotify,
where window titles do NOT change during ads.
"""

import ctypes
from ctypes import wintypes
import psutil
import subprocess
import time
import threading

from media_keys import press_play_pause
from media_session import get_spotify_media_info, is_ad, format_now_playing

user32 = ctypes.windll.user32

# Callback type for EnumWindows
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)


def is_spotify_running() -> bool:
    """Check if any Spotify.exe process is running."""
    for proc in psutil.process_iter(["name"]):
        try:
            name = proc.info["name"]
            if name and name.lower() == "spotify.exe":
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False


def get_spotify_window_title() -> str | None:
    """
    Find the main Spotify window and return its title.
    Used as a fallback and for detecting when Spotify has fully launched.
    """
    spotify_pids = set()
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            name = proc.info["name"]
            if name and name.lower() == "spotify.exe":
                spotify_pids.add(proc.info["pid"])
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    if not spotify_pids:
        return None

    titles = []

    def _enum_callback(hwnd, _lparam):
        if user32.IsWindowVisible(hwnd):
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value in spotify_pids:
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buf = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buf, length + 1)
                    title = buf.value.strip()
                    if title:
                        titles.append(title)
        return True

    user32.EnumWindows(WNDENUMPROC(_enum_callback), 0)

    if not titles:
        return None

    return max(titles, key=len)


def kill_spotify() -> bool:
    """
    Kill all Spotify.exe processes. Returns True if any were killed.
    Uses both psutil and taskkill as fallback for MS Store permissions.
    """
    killed = False

    for proc in psutil.process_iter(["pid", "name"]):
        try:
            name = proc.info["name"]
            if name and name.lower() == "spotify.exe":
                proc.kill()
                killed = True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    if not killed:
        # Fallback for Microsoft Store apps with restricted permissions
        try:
            result = subprocess.run(
                ["taskkill", "/f", "/im", "Spotify.exe"],
                capture_output=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if result.returncode == 0:
                killed = True
        except Exception:
            pass

    # Give processes time to fully terminate
    time.sleep(0.5)
    return killed


def launch_spotify() -> None:
    """Launch Spotify using the spotify: URI protocol (works for Microsoft Store installs)."""
    try:
        subprocess.Popen(
            ["cmd", "/c", "start", "spotify:"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except Exception as e:
        # Fallback: try explorer
        try:
            subprocess.Popen(["explorer.exe", "spotify:"])
        except Exception:
            raise RuntimeError(f"Failed to launch Spotify: {e}")


class SpotifyMonitor:
    """
    Threaded monitor that watches Spotify for ads using the Windows
    Media Session API, and handles the kill → relaunch → resume cycle.

    Events emitted via callback(event_type: str, data: any):
        - "status"              : General status text
        - "now_playing"         : Current song (data = "Artist - Title")
        - "media_info"          : Raw media session dict (for debug display)
        - "ad_detected"         : Ad was detected (data = description)
        - "killing"             : About to kill Spotify
        - "killed"              : Spotify was killed
        - "waiting_restart"     : Waiting before restart (data = seconds)
        - "launching"           : About to launch Spotify
        - "waiting_startup"     : Waiting for Spotify to initialize
        - "resuming"            : Sending play command
        - "resumed"             : Playback resumed
        - "ad_blocked"          : Ad was blocked (data = total count)
        - "error"               : An error occurred (data = error message)
        - "spotify_not_running" : Spotify is not detected
    """

    def __init__(self, callback=None):
        self.callback = callback
        self._running = False
        self._thread = None
        self._last_ad_time = 0
        self._last_song_info = None       # Last known good song metadata

        # Configurable delays (seconds)
        self.restart_delay = 2     # Wait after kill before relaunch
        self.startup_delay = 6     # Wait after launch before sending play
        self.poll_interval = 2.0   # Polling frequency (2s due to PowerShell call overhead)
        self.ad_cooldown = 20      # Minimum seconds between ad detections

        # Stats
        self.ads_blocked = 0

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> None:
        """Start the monitoring thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the monitoring thread."""
        self._running = False

    def _emit(self, event_type: str, data=None) -> None:
        """Emit an event to the callback."""
        if self.callback:
            try:
                self.callback(event_type, data)
            except Exception:
                pass

    def _interruptible_sleep(self, seconds: float) -> bool:
        """Sleep in small increments, checking if we should stop. Returns True if completed."""
        intervals = int(seconds * 10)
        for _ in range(intervals):
            if not self._running:
                return False
            time.sleep(0.1)
        return True

    def _wait_for_spotify(self, timeout: float = 25) -> bool:
        """Wait for Spotify to be running with a visible window. Returns True if found."""
        start = time.time()
        while time.time() - start < timeout:
            if not self._running:
                return False
            if is_spotify_running() and get_spotify_window_title() is not None:
                return True
            time.sleep(1)
        return False

    def _monitor_loop(self) -> None:
        """
        Main monitoring loop.
        Uses the Windows Media Session API (via PowerShell) to read
        Spotify's actual media metadata for ad detection.
        """
        self._emit("status", "Monitoring started")
        spotify_was_missing = False

        while self._running:
            try:
                # ── Step 1: Check if Spotify is running ──
                if not is_spotify_running():
                    if not spotify_was_missing:
                        self._emit("spotify_not_running", None)
                        spotify_was_missing = True
                    self._interruptible_sleep(self.poll_interval)
                    continue

                spotify_was_missing = False

                # ── Step 2: Check cooldown ──
                elapsed_since_ad = time.time() - self._last_ad_time
                if elapsed_since_ad < self.ad_cooldown:
                    # During cooldown, just show what's playing
                    info = get_spotify_media_info()
                    if info and info.get("playbackStatus") == "Playing":
                        display = format_now_playing(info)
                        self._emit("now_playing", display)
                    self._interruptible_sleep(self.poll_interval)
                    continue

                # ── Step 3: Get media session info ──
                info = get_spotify_media_info()

                if info is None:
                    # Could not get media info (PowerShell error or no session)
                    # Fall back to window title for basic status
                    title = get_spotify_window_title()
                    if title and " - " in title:
                        self._emit("now_playing", title)
                    self._interruptible_sleep(self.poll_interval)
                    continue

                # Emit raw media info for debug display
                self._emit("media_info", info)

                # ── Step 4: Check for ads ──
                if is_ad(info):
                    ad_desc = format_now_playing(info)
                    self._handle_ad(ad_desc)
                elif info.get("playbackStatus") == "Playing":
                    # It's a real song — save it and display
                    self._last_song_info = info.copy()
                    display = format_now_playing(info)
                    self._emit("now_playing", display)
                else:
                    # Paused or stopped
                    self._emit("status", "Spotify paused")

            except Exception as e:
                self._emit("error", str(e))

            self._interruptible_sleep(self.poll_interval)

        self._emit("status", "Monitoring stopped")

    def _handle_ad(self, description: str) -> None:
        """Handle an ad detection: kill → wait → relaunch → resume."""
        self._emit("ad_detected", description)

        # Step 1: Kill Spotify
        if not self._running:
            return
        self._emit("killing", None)
        success = kill_spotify()
        if success:
            self._emit("killed", None)
        else:
            self._emit("error", "Failed to close Spotify")
            return

        # Step 2: Wait before restart
        if not self._running:
            return
        self._emit("waiting_restart", self.restart_delay)
        if not self._interruptible_sleep(self.restart_delay):
            return

        # Step 3: Launch Spotify
        if not self._running:
            return
        self._emit("launching", None)
        try:
            launch_spotify()
        except Exception as e:
            self._emit("error", f"Failed to launch: {e}")
            return

        # Step 4: Wait for Spotify to fully start
        if not self._running:
            return
        self._emit("waiting_startup", None)
        if not self._wait_for_spotify(timeout=25):
            self._emit("error", "Spotify did not start in time")
            return

        # Extra wait for full initialization
        if not self._interruptible_sleep(self.startup_delay):
            return

        # Step 5: Resume playback
        if not self._running:
            return
        self._emit("resuming", None)
        press_play_pause()
        self._emit("resumed", None)

        # Update stats
        self.ads_blocked += 1
        self._last_ad_time = time.time()
        self._emit("ad_blocked", self.ads_blocked)
