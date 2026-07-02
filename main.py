"""
Spotify Ad Skipper — Main Application
A modern, dark-themed desktop app that monitors Spotify for ads,
closes it completely, reopens it, and resumes your music.
"""

import customtkinter as ctk
import threading
import time
from datetime import datetime, timedelta

from monitor import SpotifyMonitor

# ─── Color Palette ────────────────────────────────────────────────────────────
BG_DARK = "#0d1117"
BG_CARD = "#161b22"
BG_CARD_HOVER = "#1c2129"
BG_INPUT = "#0d1117"
BORDER_COLOR = "#30363d"

SPOTIFY_GREEN = "#1DB954"
SPOTIFY_GREEN_HOVER = "#1ed760"
SPOTIFY_GREEN_DIM = "#164b2a"

TEXT_PRIMARY = "#e6edf3"
TEXT_SECONDARY = "#8b949e"
TEXT_DIM = "#484f58"

RED_ACCENT = "#f85149"
RED_BG = "#3d1a1a"
ORANGE_ACCENT = "#d29922"
ORANGE_BG = "#3d2e0f"
BLUE_ACCENT = "#58a6ff"
BLUE_BG = "#1a2d3d"
PURPLE_ACCENT = "#bc8cff"


class SpotifyAdSkipper(ctk.CTk):
    """Main application window."""

    def __init__(self):
        super().__init__()

        # ── Window Setup ──
        self.title("Spotify Ad Skipper")
        self.geometry("540x760")
        self.minsize(480, 680)
        self.configure(fg_color=BG_DARK)
        self.resizable(True, True)

        # ── App State ──
        self.monitor = None
        self.is_monitoring = False
        self.ads_blocked = 0
        self.start_time = None
        self._current_song = ""
        self._status_text = "Ready"
        self._status_color = TEXT_SECONDARY

        # ── Theme Setup ──
        ctk.set_appearance_mode("dark")

        # ── Build UI ──
        self._build_ui()

        # ── Start uptime clock ──
        self._update_uptime()

        # ── Handle window close ──
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ══════════════════════════════════════════════════════════════════════════
    # UI CONSTRUCTION
    # ══════════════════════════════════════════════════════════════════════════

    def _build_ui(self):
        """Build the complete user interface."""

        # Main scrollable container
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        self.main_frame.grid_columnconfigure(0, weight=1)

        row = 0

        # ── HEADER ──
        self._build_header(row)
        row += 1

        # ── STATUS CARD ──
        self._build_status_card(row)
        row += 1

        # ── LOG CARD ──
        self._build_log_card(row)
        row += 1

        # ── CONTROL BUTTON ──
        self._build_controls(row)
        row += 1

        # ── SETTINGS ──
        self._build_settings(row)
        row += 1

        # ── FOOTER ──
        self._build_footer(row)

    def _build_header(self, row):
        """App title and branding."""
        header = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        header.grid(row=row, column=0, sticky="ew", pady=(0, 16))

        # Icon + Title row
        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(anchor="w")

        icon_label = ctk.CTkLabel(
            title_frame,
            text="🎵",
            font=ctk.CTkFont(size=28),
            text_color=SPOTIFY_GREEN,
        )
        icon_label.pack(side="left", padx=(0, 10))

        title_label = ctk.CTkLabel(
            title_frame,
            text="SPOTIFY AD SKIPPER",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color=TEXT_PRIMARY,
        )
        title_label.pack(side="left")

        subtitle = ctk.CTkLabel(
            header,
            text="Automatically skip ads by restarting Spotify",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=TEXT_SECONDARY,
        )
        subtitle.pack(anchor="w", pady=(2, 0))

        # Divider
        divider = ctk.CTkFrame(header, fg_color=BORDER_COLOR, height=1)
        divider.pack(fill="x", pady=(12, 0))

    def _build_status_card(self, row):
        """Status display with current state, now playing, and stats."""
        card = ctk.CTkFrame(
            self.main_frame,
            fg_color=BG_CARD,
            corner_radius=12,
            border_width=1,
            border_color=BORDER_COLOR,
        )
        card.grid(row=row, column=0, sticky="ew", pady=(0, 12))
        card.grid_columnconfigure(0, weight=1)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=20, pady=16)
        inner.grid_columnconfigure(1, weight=1)

        # ── Status indicator row ──
        status_row = ctk.CTkFrame(inner, fg_color="transparent")
        status_row.pack(fill="x", pady=(0, 12))

        self.status_dot = ctk.CTkLabel(
            status_row,
            text="●",
            font=ctk.CTkFont(size=14),
            text_color=TEXT_SECONDARY,
            width=20,
        )
        self.status_dot.pack(side="left")

        self.status_label = ctk.CTkLabel(
            status_row,
            text="READY",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=TEXT_SECONDARY,
        )
        self.status_label.pack(side="left", padx=(4, 0))

        # ── Now Playing ──
        now_playing_frame = ctk.CTkFrame(
            inner,
            fg_color=BG_INPUT,
            corner_radius=8,
            border_width=1,
            border_color=BORDER_COLOR,
        )
        now_playing_frame.pack(fill="x", pady=(0, 14))

        np_inner = ctk.CTkFrame(now_playing_frame, fg_color="transparent")
        np_inner.pack(fill="x", padx=14, pady=10)

        np_icon = ctk.CTkLabel(
            np_inner,
            text="♫",
            font=ctk.CTkFont(size=16),
            text_color=SPOTIFY_GREEN,
        )
        np_icon.pack(side="left")

        self.now_playing_label = ctk.CTkLabel(
            np_inner,
            text="Not playing",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=TEXT_DIM,
            anchor="w",
        )
        self.now_playing_label.pack(side="left", padx=(8, 0), fill="x", expand=True)

        # ── Stats row ──
        stats_row = ctk.CTkFrame(inner, fg_color="transparent")
        stats_row.pack(fill="x")
        stats_row.grid_columnconfigure((0, 1), weight=1)

        # Ads blocked
        ads_frame = ctk.CTkFrame(
            stats_row,
            fg_color=SPOTIFY_GREEN_DIM,
            corner_radius=8,
        )
        ads_frame.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        ads_inner = ctk.CTkFrame(ads_frame, fg_color="transparent")
        ads_inner.pack(padx=12, pady=8)

        ctk.CTkLabel(
            ads_inner,
            text="🛡️",
            font=ctk.CTkFont(size=14),
        ).pack(side="left")

        ctk.CTkLabel(
            ads_inner,
            text="Ads Blocked",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=TEXT_SECONDARY,
        ).pack(side="left", padx=(6, 8))

        self.ads_count_label = ctk.CTkLabel(
            ads_inner,
            text="0",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=SPOTIFY_GREEN,
        )
        self.ads_count_label.pack(side="left")

        # Uptime
        uptime_frame = ctk.CTkFrame(
            stats_row,
            fg_color=BLUE_BG,
            corner_radius=8,
        )
        uptime_frame.grid(row=0, column=1, sticky="ew", padx=(6, 0))

        uptime_inner = ctk.CTkFrame(uptime_frame, fg_color="transparent")
        uptime_inner.pack(padx=12, pady=8)

        ctk.CTkLabel(
            uptime_inner,
            text="⏱️",
            font=ctk.CTkFont(size=14),
        ).pack(side="left")

        ctk.CTkLabel(
            uptime_inner,
            text="Uptime",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=TEXT_SECONDARY,
        ).pack(side="left", padx=(6, 8))

        self.uptime_label = ctk.CTkLabel(
            uptime_inner,
            text="0m",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=BLUE_ACCENT,
        )
        self.uptime_label.pack(side="left")

    def _build_log_card(self, row):
        """Scrollable activity log."""
        card = ctk.CTkFrame(
            self.main_frame,
            fg_color=BG_CARD,
            corner_radius=12,
            border_width=1,
            border_color=BORDER_COLOR,
        )
        card.grid(row=row, column=0, sticky="nsew", pady=(0, 12))
        self.main_frame.grid_rowconfigure(row, weight=1)

        # Header
        log_header = ctk.CTkFrame(card, fg_color="transparent")
        log_header.pack(fill="x", padx=20, pady=(14, 6))

        ctk.CTkLabel(
            log_header,
            text="📋  Activity Log",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).pack(side="left")

        self.clear_log_btn = ctk.CTkButton(
            log_header,
            text="Clear",
            font=ctk.CTkFont(size=11),
            width=50,
            height=24,
            corner_radius=6,
            fg_color="transparent",
            text_color=TEXT_SECONDARY,
            hover_color=BG_CARD_HOVER,
            command=self._clear_log,
        )
        self.clear_log_btn.pack(side="right")

        # Log text box
        self.log_textbox = ctk.CTkTextbox(
            card,
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color=BG_INPUT,
            text_color=TEXT_SECONDARY,
            corner_radius=8,
            border_width=1,
            border_color=BORDER_COLOR,
            activate_scrollbars=True,
            wrap="word",
        )
        self.log_textbox.pack(fill="both", expand=True, padx=16, pady=(0, 14))
        self.log_textbox.configure(state="disabled")

        # Add welcome message
        self._add_log("Welcome! Click 'Start Monitoring' to begin.", "info")

    def _build_controls(self, row):
        """Start/Stop toggle button."""
        control_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        control_frame.grid(row=row, column=0, sticky="ew", pady=(0, 12))
        control_frame.grid_columnconfigure(0, weight=1)

        self.toggle_btn = ctk.CTkButton(
            control_frame,
            text="▶   START MONITORING",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            height=50,
            corner_radius=12,
            fg_color=SPOTIFY_GREEN,
            hover_color=SPOTIFY_GREEN_HOVER,
            text_color="#000000",
            command=self._toggle_monitoring,
        )
        self.toggle_btn.grid(row=0, column=0, sticky="ew")

    def _build_settings(self, row):
        """Configurable delay settings."""
        card = ctk.CTkFrame(
            self.main_frame,
            fg_color=BG_CARD,
            corner_radius=12,
            border_width=1,
            border_color=BORDER_COLOR,
        )
        card.grid(row=row, column=0, sticky="ew", pady=(0, 12))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=20, pady=14)
        inner.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            inner,
            text="⚙️  Settings",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 12))

        # Restart delay
        ctk.CTkLabel(
            inner,
            text="Restart Delay",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=TEXT_SECONDARY,
        ).grid(row=1, column=0, sticky="w", padx=(0, 12))

        self.restart_slider = ctk.CTkSlider(
            inner,
            from_=1,
            to=10,
            number_of_steps=9,
            width=200,
            progress_color=SPOTIFY_GREEN,
            button_color=SPOTIFY_GREEN,
            button_hover_color=SPOTIFY_GREEN_HOVER,
            command=self._on_restart_delay_change,
        )
        self.restart_slider.set(2)
        self.restart_slider.grid(row=1, column=1, sticky="ew", padx=8)

        self.restart_delay_label = ctk.CTkLabel(
            inner,
            text="2s",
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            text_color=SPOTIFY_GREEN,
            width=35,
        )
        self.restart_delay_label.grid(row=1, column=2, sticky="e")

        # Startup wait
        ctk.CTkLabel(
            inner,
            text="Startup Wait",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=TEXT_SECONDARY,
        ).grid(row=2, column=0, sticky="w", padx=(0, 12), pady=(10, 0))

        self.startup_slider = ctk.CTkSlider(
            inner,
            from_=3,
            to=15,
            number_of_steps=12,
            width=200,
            progress_color=SPOTIFY_GREEN,
            button_color=SPOTIFY_GREEN,
            button_hover_color=SPOTIFY_GREEN_HOVER,
            command=self._on_startup_delay_change,
        )
        self.startup_slider.set(6)
        self.startup_slider.grid(row=2, column=1, sticky="ew", padx=8, pady=(10, 0))

        self.startup_delay_label = ctk.CTkLabel(
            inner,
            text="6s",
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            text_color=SPOTIFY_GREEN,
            width=35,
        )
        self.startup_delay_label.grid(row=2, column=2, sticky="e", pady=(10, 0))

    def _build_footer(self, row):
        """Footer with attribution."""
        footer = ctk.CTkLabel(
            self.main_frame,
            text="Use at your own discretion  •  Not affiliated with Spotify",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=TEXT_DIM,
        )
        footer.grid(row=row, column=0, pady=(0, 4))

    # ══════════════════════════════════════════════════════════════════════════
    # MONITORING CONTROLS
    # ══════════════════════════════════════════════════════════════════════════

    def _toggle_monitoring(self):
        """Toggle monitoring on/off."""
        if self.is_monitoring:
            self._stop_monitoring()
        else:
            self._start_monitoring()

    def _start_monitoring(self):
        """Start the Spotify ad monitor."""
        self.is_monitoring = True
        self.start_time = datetime.now()

        # Create and configure monitor
        self.monitor = SpotifyMonitor(callback=self._on_monitor_event)
        self.monitor.restart_delay = int(self.restart_slider.get())
        self.monitor.startup_delay = int(self.startup_slider.get())
        self.monitor.start()

        # Update UI
        self.toggle_btn.configure(
            text="⏹   STOP MONITORING",
            fg_color=RED_ACCENT,
            hover_color="#da3633",
            text_color="#ffffff",
        )
        self._set_status("MONITORING", SPOTIFY_GREEN)
        self._add_log("Monitoring started — watching for ads...", "success")

    def _stop_monitoring(self):
        """Stop the monitor."""
        self.is_monitoring = False
        if self.monitor:
            self.monitor.stop()
            self.monitor = None

        # Update UI
        self.toggle_btn.configure(
            text="▶   START MONITORING",
            fg_color=SPOTIFY_GREEN,
            hover_color=SPOTIFY_GREEN_HOVER,
            text_color="#000000",
        )
        self._set_status("STOPPED", TEXT_SECONDARY)
        self.now_playing_label.configure(text="Not playing", text_color=TEXT_DIM)
        self._add_log("Monitoring stopped.", "info")

    # ══════════════════════════════════════════════════════════════════════════
    # MONITOR EVENT HANDLER
    # ══════════════════════════════════════════════════════════════════════════

    def _on_monitor_event(self, event_type: str, data):
        """
        Handle events from the monitor thread.
        Schedules UI updates on the main thread via after().
        """
        self.after(0, lambda: self._process_event(event_type, data))

    def _process_event(self, event_type: str, data):
        """Process a monitor event on the main thread."""
        if event_type == "now_playing":
            self._current_song = data
            display = data if len(data) <= 45 else data[:42] + "..."
            self.now_playing_label.configure(text=display, text_color=TEXT_PRIMARY)

        elif event_type == "ad_detected":
            self._set_status("AD DETECTED", RED_ACCENT)
            self._add_log(f"⚠  Ad detected! Closing Spotify...", "warning")

        elif event_type == "killing":
            self._add_log("   Terminating Spotify processes...", "info")

        elif event_type == "killed":
            self._add_log("   ✕ Spotify closed", "info")

        elif event_type == "waiting_restart":
            self._set_status("RESTARTING", ORANGE_ACCENT)
            self._add_log(f"   Waiting {data}s before restart...", "info")

        elif event_type == "launching":
            self._add_log("   ↻ Reopening Spotify...", "info")

        elif event_type == "waiting_startup":
            self._set_status("WAITING", ORANGE_ACCENT)
            self._add_log("   Waiting for Spotify to load...", "info")

        elif event_type == "resuming":
            self._add_log("   ▶ Sending play command...", "info")

        elif event_type == "resumed":
            self._set_status("MONITORING", SPOTIFY_GREEN)
            self._add_log("   ✓ Playback resumed!", "success")

        elif event_type == "ad_blocked":
            self.ads_blocked = data
            self.ads_count_label.configure(text=str(data))

        elif event_type == "error":
            self._add_log(f"✕ Error: {data}", "error")

        elif event_type == "spotify_not_running":
            self._set_status("WAITING FOR SPOTIFY", ORANGE_ACCENT)
            self.now_playing_label.configure(
                text="Spotify not detected — open Spotify to begin",
                text_color=TEXT_DIM,
            )

        elif event_type == "status":
            pass  # Generic status — handled by specific events above

    # ══════════════════════════════════════════════════════════════════════════
    # UI HELPERS
    # ══════════════════════════════════════════════════════════════════════════

    def _set_status(self, text: str, color: str):
        """Update the status indicator."""
        self.status_dot.configure(text_color=color)
        self.status_label.configure(text=text, text_color=color)

    def _add_log(self, message: str, level: str = "info"):
        """Add a timestamped entry to the activity log."""
        timestamp = datetime.now().strftime("%H:%M:%S")

        color_map = {
            "info": TEXT_SECONDARY,
            "success": SPOTIFY_GREEN,
            "warning": ORANGE_ACCENT,
            "error": RED_ACCENT,
        }

        self.log_textbox.configure(state="normal")
        entry = f"[{timestamp}]  {message}\n"
        self.log_textbox.insert("end", entry)
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def _clear_log(self):
        """Clear the activity log."""
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        self.log_textbox.configure(state="disabled")
        self._add_log("Log cleared.", "info")

    def _update_uptime(self):
        """Update the uptime display every second."""
        if self.start_time and self.is_monitoring:
            delta = datetime.now() - self.start_time
            total_seconds = int(delta.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)

            if hours > 0:
                text = f"{hours}h {minutes}m"
            elif minutes > 0:
                text = f"{minutes}m {seconds}s"
            else:
                text = f"{seconds}s"

            self.uptime_label.configure(text=text)

        self.after(1000, self._update_uptime)

    def _on_restart_delay_change(self, value):
        """Handle restart delay slider change."""
        val = int(value)
        self.restart_delay_label.configure(text=f"{val}s")
        if self.monitor:
            self.monitor.restart_delay = val

    def _on_startup_delay_change(self, value):
        """Handle startup delay slider change."""
        val = int(value)
        self.startup_delay_label.configure(text=f"{val}s")
        if self.monitor:
            self.monitor.startup_delay = val

    def _on_close(self):
        """Handle window close — stop monitor gracefully."""
        if self.monitor:
            self.monitor.stop()
        self.destroy()


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = SpotifyAdSkipper()
    app.mainloop()
