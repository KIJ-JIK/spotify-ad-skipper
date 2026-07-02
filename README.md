# 🎵 Spotify Ad Skipper

A sleek Windows desktop app that automatically detects Spotify ads, closes Spotify completely, reopens it, and resumes your music — so you never have to listen to an ad again.

## How It Works

1. **Monitors** Spotify's window title in real-time (polls every 1 second)
2. **Detects** when the title changes to "Advertisement"
3. **Kills** all Spotify processes completely
4. **Relaunches** Spotify via the `spotify:` URI protocol (Microsoft Store compatible)
5. **Resumes** playback by simulating the Media Play/Pause key

## Requirements

- **Windows 10/11**
- **Python 3.10+**
- **Spotify** (Microsoft Store version)

## Setup

1. **Install Python dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

2. **Run the application:**

   ```bash
   python main.py
   ```

3. **Click "Start Monitoring"** and play music on Spotify. The app will handle the rest!

## Settings

| Setting | Default | Description |
|---------|---------|-------------|
| **Restart Delay** | 2s | How long to wait after killing Spotify before relaunching |
| **Startup Wait** | 6s | How long to wait for Spotify to fully load before sending play |

Adjust these if Spotify is restarting too fast or too slow on your machine.

## Project Structure

```
spotify-ad-skipper/
├── main.py          # GUI application (customtkinter)
├── monitor.py       # Ad detection & process management
├── media_keys.py    # Windows media key simulation
├── requirements.txt # Python dependencies
└── README.md        # This file
```

## ⚠️ Disclaimer

This is a personal utility tool. Use at your own discretion. This project is not affiliated with or endorsed by Spotify. Spotify's Terms of Service may have restrictions regarding ad-blocking tools.
