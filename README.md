# 👏 clap-jarvis (Windows Edition)
> **Iron Man British Butler & Live Overhead Flight Radar Assistant for Windows**

`clap-jarvis` is your personal Windows background assistant inspired by Iron Man's JARVIS. It runs quietly 24/7 in the background with near-zero CPU footprint. Snap or clap **3 times** (or say *"Jarvis"*), and JARVIS will respond in an ultra-realistic British Butler neural voice and automatically open FlightRadar24 focused on any airplane flying overhead!

---

## 🎯 How It Works Day-to-Day

### 1. Triggering JARVIS
Just clap your hands 3 times or snap your fingers 3 times in quick succession anywhere near your Windows PC microphone:

- 👏 **3 Hand Claps**
- 🤌 **3 Finger Snaps** *(even light / quiet snaps work!)*
- 🗣️ **Wake-Word**: Spoken *"Jarvis"* activation (optional)

### 2. What Happens Next
1. **Airspace Intercept Check**: JARVIS queries live FlightRadar24 API for aircraft flying overhead within 150 km of your GPS coordinates.
2. **Airplane Overhead Detected**: JARVIS announces the flight details aloud (e.g., *"Good day Sir. Attention: Aircraft AIC101, traveling from Delhi to London Heathrow at 35,000 feet..."*) and automatically opens FlightRadar24 directly focusing on that exact plane in your default browser.
3. **Clear Airspace**: If no airplane is overhead, JARVIS greets you with a witty Iron Man butler line from `phrases.json` (e.g., *"Hello Sir, welcome back. Preferred choice of vibe today: Tame Impala or ACDC?"*).

---

## 🚀 Step-by-Step Setup Guide (Windows)

### Step 1: Prerequisites
- Installed **Python 3.10+** on Windows ([python.org](https://www.python.org/downloads/)).
- ⚠️ Make sure **"Add Python to PATH"** was checked during installation.

### Step 2: Download / Clone Project
```cmd
git clone https://github.com/SarvyagyaPrakash/jarvis4windows.git
cd jarvis4windows
```

### Step 3: Installation (1-Click)
Double-click **`install.bat`** or run in Command Prompt:
```cmd
install.bat
```
*Creates `.venv` virtual environment and automatically installs all dependencies (`sounddevice`, `numpy`, `edge-tts`, `pygame`, `pyttsx3`, `requests`, `SpeechRecognition`).*

---

## 🎛️ How to Turn JARVIS ON & OFF

You can manage JARVIS in the background using quick batch scripts or PowerShell:

### Method A: Double-Click Batch Scripts (Easiest)
- **`start.bat`**: Starts JARVIS silently in background (`pythonw.exe`) with `JARVIS 🟢 Active` Windows Toast notification.
- **`stop.bat`**: Deactivates the background process with `JARVIS 🛑 Stopped` Toast notification.
- **`toggle.bat`**: Double-click to instantly toggle JARVIS ON 🟢 or OFF 🛑.

### Method B: Terminal / Command Line
```cmd
# Run in terminal window:
.venv\Scripts\python.exe clap_jarvis.py

# Run in silent headless daemon mode:
.venv\Scripts\python.exe clap_jarvis.py --headless
```

---

## 💬 Customizing What JARVIS Says (`phrases.json`)

You can edit, add, or remove butler dialogue lines anytime by opening `phrases.json` in any text editor:

```json
[
  "Hello Sir, welcome back. Preferred choice of vibe today: Tame Impala or ACDC?",
  "Terrific timing, Sir. Your suit is 80% charged. Iced coffee is on the table.",
  "Good to see you again, Sir. Your Porsche will reach by tonight.",
  "One hundred missed calls from your girlfriend. Good luck, Sir. I am muting myself.",
  "Welcome back, Sir. Your Pizza is on the way. Do you want me to turn on the Xbox?",
  "Sir, Peter Parker has sent a message: Need Money for Web Fluid!"
]
```
💡 Save the file and JARVIS updates his dialogue lines instantly—**no restart needed!**

---

## 🗺️ Setting Your Location for Overhead Flight Tracking (`config.json`)

Open `config.json` to configure your GPS coordinates and scan radius:

```json
{
  "latitude": 28.6139,
  "longitude": 77.2090,
  "radius_km": 150.0,
  "voice": "en-GB-RyanNeural",
  "threshold_peak": 0.22,
  "threshold_snap_peak": 0.12,
  "min_crest_factor": 4.0,
  "required_claps": 3,
  "window_seconds": 4.5,
  "cooldown_seconds": 5.0,
  "enable_flight_check": true,
  "auto_open_browser": true
}
```

Replace `latitude` and `longitude` with your coordinates (obtainable from Google Maps or GPS apps).

---

## 🔍 Diagnostics & Sensitivity Calibration

### Live VU Meter Calibration
To test your microphone and adjust clap/snap detection sensitivity:
```cmd
.venv\Scripts\python.exe clap_jarvis.py --calibrate
```
Clap or snap near your mic. The 30-second live ASCII meter will display real-time Peak, RMS, and Crest Factor values so you can fine-tune `threshold_peak` or `min_crest_factor` in `config.json`.

### Testing Commands
```cmd
# Test British Butler speech output:
.venv\Scripts\python.exe clap_jarvis.py --test-speech

# Test live FlightRadar24 overhead scan:
.venv\Scripts\python.exe clap_jarvis.py --test-flight
```

---

## 🗑️ How to Uninstall
To stop all background instances and clean up:
```cmd
uninstall.bat
```
