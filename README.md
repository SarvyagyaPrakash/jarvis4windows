# 🤖 CLAP-JARVIS for Windows
> **Iron Man British Butler & Overhead Flight Radar Assistant**

`clap-jarvis` is a standalone Python background assistant built specifically for Windows. Inspired by Iron Man's JARVIS, it runs silently 24/7 with near-zero CPU footprint. When you clap or snap **3 times** (or say the wake-word *"Jarvis"*), JARVIS triggers:

1. **Neural British Butler Voice**: Greets you in an ultra-realistic British Butler voice (`en-GB-RyanNeural`), addressed to *"Ma'am"*.
2. **Live FlightRadar24 Overhead Tracking**: Scans live airspace within 150 km of your GPS coordinates.
3. **Flight Intercept Prediction**: If an aircraft is overhead, announces its callsign, origin, destination, and calculated intercept time, then automatically opens the live radar page in your default browser.
4. **Witty Female-Tailored Butler Dialogue**: If no aircraft is overhead, delivers witty, Iron Man-style lines from a full-cycle non-repeating shuffle deck.

---

## 📸 Key Features

- **⚡ Advanced Percussive Transient DSP**: Distinguishes sharp hand claps and finger snaps from room noise using Peak amplitude, RMS noise floor, and Crest Factor (`Peak / (RMS + 1e-6)`).
- **🛡️ Re-trigger & Echo Prevention**: 80ms minimum debounce between transients and a 5-second cooldown after speech to ensure JARVIS's voice never re-triggers the microphone.
- **✈️ FlightRadar24 + OpenSky Dual Engine**: Real-time bounding box queries with automatic fallback to OpenSky Network API, calculating Haversine great-circle distance, bearing, and estimated intercept time.
- **🎙️ Neural TTS & SAPI Fallback**: High-fidelity speech synthesis via `edge-tts` with offline fallback to native Windows SAPI voices (`pyttsx3`). Asynchronous `pygame.mixer` playback prevents audio stream interruptions.
- **🔄 Hot-Reloading & Full-Cycle Shuffle Deck**: Modify `config.json` and `phrases.json` in real time without restarting the background service. The shuffle deck ensures every phrase is spoken once before reshuffling.
- **🎛️ Live Calibration CLI Mode**: Built-in 30-second live ASCII VU meter (`python clap_jarvis.py --calibrate`) for precision threshold tuning.
- **🪟 Windows Background Native**: Headless execution via `pythonw.exe`, Windows Toast notification banners, and one-click automation batch scripts.

---

## 📁 Project Structure

```text
clap-jarvis/
├── clap_jarvis.py       # Core audio DSP, FlightRadar24 tracker, neural TTS, calibration
├── config.json          # Live settings (lat/lon, radius, audio thresholds, voice)
├── phrases.json         # Female-tailored butler dialogue lines
├── requirements.txt     # Python dependencies
├── install.bat          # 1-Click Windows installer (creates .venv, installs packages)
├── start.bat            # Silent background launcher (pythonw.exe + Toast banner)
├── stop.bat             # Background process terminator + Toast banner
├── toggle.bat           # ON/OFF toggle with Windows Toast notifications
├── uninstall.bat        # Clean uninstaller
└── README.md            # User manual and documentation
```

---

## 🚀 Quick Start (Windows)

### 1. Installation (1-Click)
Double-click **`install.bat`** or run:
```cmd
install.bat
```
This automatically creates a virtual environment (`.venv`) and installs all required dependencies.

### 2. Microphone Calibration
To test your microphone and adjust detection thresholds:
```cmd
.venv\Scripts\python.exe clap_jarvis.py --calibrate
```
Snap and clap into your microphone. Watch the live ASCII VU meter for Peak, RMS, and Crest Factor feedback.

### 3. Background Controls
- **Start JARVIS silently**: Double-click **`start.bat`** (shows `JARVIS 🟢 Active` toast).
- **Stop JARVIS**: Double-click **`stop.bat`** (shows `JARVIS 🛑 Stopped` toast).
- **Toggle ON / OFF**: Double-click **`toggle.bat`**.

---

## ⚙️ Configuration (`config.json`)

Settings reload automatically on every trigger—no restart needed!

```json
{
  "latitude": 28.6139,
  "longitude": 77.2090,
  "radius_km": 150.0,
  "threshold_peak": 0.22,
  "threshold_snap_peak": 0.12,
  "min_crest_factor": 4.0,
  "threshold_rms": 0.006,
  "required_claps": 3,
  "window_seconds": 4.5,
  "cooldown_seconds": 5.0,
  "debounce_ms": 80,
  "sample_rate": 44100,
  "block_size": 1024,
  "voice": "en-GB-RyanNeural",
  "enable_flight_check": true,
  "enable_jarvis_wake_word": false,
  "auto_open_browser": true
}
```

### Parameter Reference
| Parameter | Default | Description |
| :--- | :--- | :--- |
| `latitude` / `longitude` | `28.6139`, `77.2090` | Your GPS coordinates (replace with your location) |
| `radius_km` | `150.0` | Airspace detection radius around your location |
| `threshold_peak` | `0.22` | Minimum peak amplitude for hand claps (0.0 to 1.0) |
| `threshold_snap_peak` | `0.12` | Minimum peak amplitude for finger snaps |
| `min_crest_factor` | `4.0` | Transient sharpness ratio (`Peak / RMS`) |
| `required_claps` | `3` | Number of claps/snaps required to trigger JARVIS |
| `window_seconds` | `4.5` | Time window to record required claps |
| `cooldown_seconds` | `5.0` | Cooldown period after speaking to prevent self-trigger |
| `voice` | `en-GB-RyanNeural` | Microsoft Neural Butler voice (`en-GB-RyanNeural`, `en-GB-ThomasNeural`) |
| `enable_flight_check` | `true` | Enable live overhead flight scanning |
| `enable_jarvis_wake_word`| `false` | Enable spoken "Jarvis" wake-word detection |
| `auto_open_browser` | `true` | Open FlightRadar24 flight link when aircraft is overhead |

---

## 💬 Customizing Butler Dialogue (`phrases.json`)

Edit `phrases.json` at any time with your favorite lines:

```json
[
  "Hello ma'am, welcome back. Preferred choice of vibe today: Tame Impala or ACDC?",
  "Terrific timing, ma'am. Your suit is 80% charged. Iced coffee is on the table.",
  "Good to see you again, ma'am. Your Porsche will reach by tonight.",
  "One hundred missed calls from your boyfriend. Good luck, ma'am. I am muting myself.",
  "Welcome back, ma'am. Your Pizza is on the way. Do you want me to turn on the Xbox?",
  "Ma'am, Peter Parker has sent a message: Need Money for Web Fluid!"
]
```

---

## 🛠️ CLI Diagnostics & Testing

```cmd
# Test neural speech output:
.venv\Scripts\python.exe clap_jarvis.py --test-speech

# Test live FlightRadar24 overhead airspace scan:
.venv\Scripts\python.exe clap_jarvis.py --test-flight

# Run live ASCII VU meter calibration:
.venv\Scripts\python.exe clap_jarvis.py --calibrate
```

---

## 💡 Troubleshooting for Windows

1. **Microphone not triggering?**
   - Run `--calibrate` to inspect your input levels.
   - If your microphone is quiet, lower `threshold_peak` to `0.15` and `threshold_snap_peak` to `0.08` in `config.json`.
2. **False triggers from music or speech?**
   - Increase `min_crest_factor` to `5.0` or `5.5` in `config.json`.
3. **No sound playing?**
   - Check Windows default audio output device.
   - Ensure an internet connection is active for `edge-tts`. If offline, JARVIS automatically falls back to Windows native SAPI (`pyttsx3`).
4. **Auto-Start on Windows Boot (Optional)**:
   - Press `Win + R`, type `shell:startup`, and press Enter.
   - Create a shortcut to `start.bat` in this folder.
