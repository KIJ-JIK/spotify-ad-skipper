"""
Windows Media Key Simulation
Simulates hardware media keys (Play/Pause, Next, Previous) using the Windows API.
"""

import ctypes
import time

# --- Windows API Constants ---
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002

VK_MEDIA_PLAY_PAUSE = 0xB3
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP = 0xB2

user32 = ctypes.windll.user32


def _send_key(vk_code: int) -> None:
    """Send a single key press and release event."""
    user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY, 0)
    time.sleep(0.05)
    user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)


def press_play_pause() -> None:
    """Simulate the Media Play/Pause key."""
    _send_key(VK_MEDIA_PLAY_PAUSE)


def press_next_track() -> None:
    """Simulate the Media Next Track key."""
    _send_key(VK_MEDIA_NEXT_TRACK)


def press_prev_track() -> None:
    """Simulate the Media Previous Track key."""
    _send_key(VK_MEDIA_PREV_TRACK)


def press_stop() -> None:
    """Simulate the Media Stop key."""
    _send_key(VK_MEDIA_STOP)
