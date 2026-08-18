#!/usr/bin/env python3
"""
================================================================================
🤖 CLAP-JARVIS for Windows
Iron Man Butler & Overhead Flight Radar Assistant
================================================================================
Runs silently in the background on Windows. Listens for 3 claps / snaps (or wake-word "Jarvis").
1. Greets the user in an ultra-realistic British Butler neural voice ("Sir").
2. Queries live FlightRadar24 / OpenSky data to detect overhead aircraft within 150 km.
3. If aircraft is detected: announces callsign, route, intercept time, and opens FlightRadar24.
4. If no aircraft: delivers witty, butler lines from phrases.json.
================================================================================
"""

import sys
import os
import time
import json
import math
import random
import asyncio
import tempfile
import threading
import argparse
import webbrowser
import http.server
import socketserver
import urllib.parse
from collections import deque
from typing import Optional, Dict, Any, List, Tuple

import numpy as np

# Audio input library
try:
    import sounddevice as sd
except ImportError:
    sd = None

# Audio playback library
try:
    import pygame
    import pygame.mixer
except ImportError:
    pygame = None

# Neural TTS library
try:
    import edge_tts
except ImportError:
    edge_tts = None

# Offline Windows SAPI fallback
try:
    import pyttsx3
except ImportError:
    pyttsx3 = None

# HTTP requests for FlightRadar24
try:
    import requests
except ImportError:
    requests = None

# Optional SpeechRecognition for wake-word
try:
    import speech_recognition as sr
except ImportError:
    sr = None


# ==============================================================================
# 1. CONSTANTS & AIRPORT DATABASE
# ==============================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
PHRASES_PATH = os.path.join(BASE_DIR, "phrases.json")

# Pre-populated ICAO/IATA Airport Code dictionary for lightning-fast resolution
AIRPORT_DB: Dict[str, str] = {
    # India
    "DEL": "Delhi", "VIDP": "Delhi", "BOM": "Mumbai", "VABB": "Mumbai",
    "BLR": "Bengaluru", "VOBL": "Bengaluru", "MAA": "Chennai", "VOMM": "Chennai",
    "CCU": "Kolkata", "VECC": "Kolkata", "HYD": "Hyderabad", "VOHS": "Hyderabad",
    "COK": "Kochi", "VOCI": "Kochi", "AMD": "Ahmedabad", "VAAH": "Ahmedabad",
    "PNQ": "Pune", "VAPO": "Pune", "GOI": "Goa Dabolim", "VAGO": "Goa Dabolim",
    "GOX": "Goa Mopa", "VOGA": "Goa Mopa", "JAI": "Jaipur", "VIJP": "Jaipur",
    "LKO": "Lucknow", "VILK": "Lucknow", "IXC": "Chandigarh", "VICG": "Chandigarh",
    "ATQ": "Amritsar", "VIAR": "Amritsar", "SXR": "Srinagar", "VISR": "Srinagar",
    "IXB": "Bagdogra", "VEBD": "Bagdogra", "GAU": "Guwahati", "VEGT": "Guwahati",
    "TRV": "Thiruvananthapuram", "VOTV": "Thiruvananthapuram",
    # United Kingdom & Europe
    "LHR": "London Heathrow", "EGLL": "London Heathrow", "LGW": "London Gatwick", "EGKK": "London Gatwick",
    "STN": "London Stansted", "EGSS": "London Stansted", "MAN": "Manchester", "EGCC": "Manchester",
    "EDI": "Edinburgh", "EGPH": "Edinburgh", "CDG": "Paris Charles de Gaulle", "LFPG": "Paris Charles de Gaulle",
    "ORY": "Paris Orly", "LFPO": "Paris Orly", "FRA": "Frankfurt", "EDDF": "Frankfurt",
    "MUC": "Munich", "EDDM": "Munich", "AMS": "Amsterdam Schiphol", "EHAM": "Amsterdam Schiphol",
    "MAD": "Madrid Barajas", "LEMD": "Madrid Barajas", "BCN": "Barcelona", "LEBL": "Barcelona",
    "FCO": "Rome Fiumicino", "LIRF": "Rome Fiumicino", "ZRH": "Zurich", "LSZH": "Zurich",
    "VIE": "Vienna", "LOWW": "Vienna", "IST": "Istanbul", "LTFM": "Istanbul",
    "SAW": "Istanbul Sabiha", "LTFJ": "Istanbul Sabiha", "DUB": "Dublin", "EIDW": "Dublin",
    # Middle East
    "DXB": "Dubai", "OMDB": "Dubai", "DWC": "Dubai Al Maktoum", "OMDW": "Dubai Al Maktoum",
    "AUH": "Abu Dhabi", "OMAA": "Abu Dhabi", "DOH": "Doha", "OTHH": "Doha",
    "RUH": "Riyadh", "OERK": "Riyadh", "JED": "Jeddah", "OEJN": "Jeddah",
    "BAH": "Bahrain", "OBBI": "Bahrain", "KWI": "Kuwait", "OKBK": "Kuwait",
    "MCT": "Muscat", "OOMS": "Muscat",
    # North America
    "JFK": "New York JFK", "KJFK": "New York JFK", "EWR": "Newark", "KEWR": "Newark",
    "LGA": "New York LaGuardia", "KLGA": "New York LaGuardia", "LAX": "Los Angeles", "KLAX": "Los Angeles",
    "SFO": "San Francisco", "KSFO": "San Francisco", "ORD": "Chicago O'Hare", "KORD": "Chicago O'Hare",
    "ATL": "Atlanta", "KATL": "Atlanta", "DFW": "Dallas Fort Worth", "KDFW": "Dallas Fort Worth",
    "MIA": "Miami", "KMIA": "Miami", "SEA": "Seattle", "KSEA": "Seattle",
    "BOS": "Boston", "KBOS": "Boston", "YVR": "Vancouver", "CYVR": "Vancouver",
    "YYZ": "Toronto Pearson", "CYYZ": "Toronto Pearson",
    # Asia Pacific
    "SIN": "Singapore Changi", "WSSS": "Singapore Changi", "HKG": "Hong Kong", "VHHH": "Hong Kong",
    "HND": "Tokyo Haneda", "RJTT": "Tokyo Haneda", "NRT": "Tokyo Narita", "RJAA": "Tokyo Narita",
    "ICN": "Seoul Incheon", "RKSI": "Seoul Incheon", "BKK": "Bangkok Suvarnabhumi", "VTBS": "Bangkok Suvarnabhumi",
    "DMK": "Bangkok Don Mueang", "VTBD": "Bangkok Don Mueang", "KUL": "Kuala Lumpur", "WMKK": "Kuala Lumpur",
    "SYD": "Sydney", "YSSY": "Sydney", "MEL": "Melbourne", "YMML": "Melbourne"
}

# In-memory airport cache for dynamic online lookups
_AIRPORT_LOOKUP_CACHE: Dict[str, str] = {}


# ==============================================================================
# 2. CONFIGURATION & PHRASE DECK MANAGEMENT (HOT-RELOADABLE)
# ==============================================================================

DEFAULT_CONFIG: Dict[str, Any] = {
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
    "enable_flight_check": True,
    "enable_jarvis_wake_word": False,
    "auto_open_browser": True,
    "web_port": 8888,
    "enable_web_dashboard": True
}


def load_config() -> Dict[str, Any]:
    """Loads config.json dynamically, creating it with defaults if missing."""
    config = DEFAULT_CONFIG.copy()
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                user_cfg = json.load(f)
                config.update(user_cfg)
        except Exception as e:
            print(f"[!] Warning reading config.json: {e}. Using defaults.")
    else:
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
        except Exception:
            pass
    return config


class PhraseDeck:
    """
    Full-cycle shuffle deck algorithm.
    Guarantees every phrase is spoken once before reshuffling,
    and prevents back-to-back duplicate lines across cycle boundaries.
    """
    def __init__(self, phrases_file: str = PHRASES_PATH):
        self.phrases_file = phrases_file
        self.phrases: List[str] = []
        self.deck: List[int] = []
        self.last_phrase_index: Optional[int] = None
        self.file_mtime: float = 0
        self._reload_if_needed()

    def _reload_if_needed(self) -> None:
        if not os.path.exists(self.phrases_file):
            self.phrases = [
                "Hello Sir, welcome back. Preferred choice of vibe today: Tame Impala or ACDC?",
                "Terrific timing, Sir. Your suit is 80% charged. Iced coffee is on the table.",
                "Good to see you again, Sir. Your Porsche will reach by tonight."
            ]
            return

        try:
            mtime = os.path.getmtime(self.phrases_file)
            if mtime != self.file_mtime:
                with open(self.phrases_file, "r", encoding="utf-8") as f:
                    new_phrases = json.load(f)
                if isinstance(new_phrases, list) and new_phrases:
                    self.phrases = new_phrases
                    self.file_mtime = mtime
                    self._reshuffle()
        except Exception as e:
            print(f"[!] Error loading phrases: {e}")

    def _reshuffle(self) -> None:
        n = len(self.phrases)
        if n == 0:
            self.deck = []
            return
        indices = list(range(n))
        random.shuffle(indices)

        # Prevent duplicate across cycle boundary
        if n > 1 and self.last_phrase_index is not None and indices[0] == self.last_phrase_index:
            # Swap first element with a random subsequent element
            swap_idx = random.randint(1, n - 1)
            indices[0], indices[swap_idx] = indices[swap_idx], indices[0]

        self.deck = indices

    def get_next_phrase(self) -> str:
        """Returns the next witty dialogue line from the deck."""
        self._reload_if_needed()
        if not self.phrases:
            return "Welcome back Sir. Systems are fully operational."

        if not self.deck:
            self._reshuffle()

        idx = self.deck.pop(0)
        self.last_phrase_index = idx
        return self.phrases[idx]


# ==============================================================================
# 3. NEURAL BUTLER TTS & AUDIO PLAYBACK ENGINE
# ==============================================================================

class ButlerTTS:
    """
    Manages ultra-realistic British Butler voice output.
    Uses edge-tts (en-GB-RyanNeural) with async pygame.mixer playback.
    Safely falls back to Windows native SAPI (pyttsx3) if offline.
    """
    def __init__(self, voice: str = "en-GB-RyanNeural"):
        self.voice = voice
        self.is_speaking = False
        self._lock = threading.Lock()
        self._init_pygame()

    def _init_pygame(self) -> None:
        if pygame:
            try:
                # Initialize pygame mixer for low latency audio playback
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
            except Exception as e:
                print(f"[!] Pygame mixer init warning: {e}")

    def set_voice(self, voice: str) -> None:
        self.voice = voice

    async def _generate_edge_tts(self, text: str, output_path: str) -> bool:
        if not edge_tts:
            return False
        try:
            communicate = edge_tts.Communicate(text, self.voice, rate="+0%", pitch="+0Hz")
            await communicate.save(output_path)
            return True
        except Exception as e:
            print(f"[!] edge-tts synthesis failed: {e}")
            return False

    def _speak_pyttsx3_fallback(self, text: str) -> None:
        """Fallback to Windows SAPI native TTS voice."""
        if not pyttsx3:
            print(f"[!] TTS (Console Fallback): {text}")
            return
        try:
            engine = pyttsx3.init()
            engine.setProperty("rate", 160)
            voices = engine.getProperty("voices")
            # Try to pick a British / UK voice or male voice if available
            for v in voices:
                v_name = v.name.lower()
                if "george" in v_name or "hazel" in v_name or "uk" in v_name or "british" in v_name or "david" in v_name:
                    engine.setProperty("voice", v.id)
                    break
            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            print(f"[!] pyttsx3 fallback error: {e}")

    def _play_audio_file(self, file_path: str) -> None:
        """Plays audio file using pygame.mixer and handles Windows file lock releases."""
        if not pygame or not pygame.mixer.get_init():
            return

        try:
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.05)
            # Crucial for Windows: unload music to release file lock before deleting
            pygame.mixer.music.unload()
        except Exception as e:
            print(f"[!] Playback error: {e}")

    def speak(self, text: str) -> None:
        """Speaks the text asynchronously in a background worker thread."""
        thread = threading.Thread(target=self._speak_worker, args=(text,), daemon=True)
        thread.start()

    def _speak_worker(self, text: str) -> None:
        with self._lock:
            self.is_speaking = True
            print(f"\n🎙️ [JARVIS]: \"{text}\"\n")
            temp_mp3 = None
            try:
                # Create temporary file in Windows %TEMP%
                temp_fd, temp_mp3 = tempfile.mkstemp(suffix=".mp3", prefix="jarvis_tts_")
                os.close(temp_fd)

                # Attempt edge-tts synthesis
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                success = loop.run_until_complete(self._generate_edge_tts(text, temp_mp3))
                loop.close()

                if success and os.path.exists(temp_mp3) and os.path.getsize(temp_mp3) > 0:
                    self._play_audio_file(temp_mp3)
                else:
                    self._speak_pyttsx3_fallback(text)
            except Exception as e:
                print(f"[!] Speech worker error: {e}")
                self._speak_pyttsx3_fallback(text)
            finally:
                if temp_mp3 and os.path.exists(temp_mp3):
                    # Robust Windows file deletion loop (handling file locks)
                    for _ in range(5):
                        try:
                            os.remove(temp_mp3)
                            break
                        except Exception:
                            time.sleep(0.1)
                self.is_speaking = False


# ==============================================================================
# 4. FLIGHTRADAR24 & OPENSKY LIVE OVERHEAD RADAR TRACKER
# ==============================================================================

class FlightRadarTracker:
    """
    Tracks overhead flights within radius_km of user's coordinates.
    Calculates great-circle distance, heading, and intercept time.
    """
    def __init__(self, lat: float, lon: float, radius_km: float = 150.0):
        self.lat = lat
        self.lon = lon
        self.radius_km = radius_km

    def set_location(self, lat: float, lon: float, radius_km: float) -> None:
        self.lat = lat
        self.lon = lon
        self.radius_km = radius_km

    @staticmethod
    def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculates great-circle distance in kilometers between two GPS points."""
        r = 6371.0  # Earth's radius in km
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = (math.sin(delta_phi / 2.0) ** 2 +
             math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2)
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return r * c

    @staticmethod
    def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculates initial bearing (azimuth in degrees) from point 1 to point 2."""
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_lambda = math.radians(lon2 - lon1)

        x = math.sin(delta_lambda) * math.cos(phi2)
        y = math.cos(phi1) * math.sin(phi2) - (math.sin(phi1) * math.cos(phi2) * math.cos(delta_lambda))
        initial_bearing = math.atan2(x, y)
        return (math.degrees(initial_bearing) + 360.0) % 360.0

    @classmethod
    def resolve_airport(cls, code: Optional[str]) -> str:
        """Resolves ICAO or IATA code to a human-readable city/airport name."""
        if not code or code.strip() == "" or code.upper() in ("N/A", "NONE", "UNKNOWN", "---"):
            return "Undisclosed Location"

        clean_code = code.strip().upper()
        if clean_code in AIRPORT_DB:
            return AIRPORT_DB[clean_code]
        if clean_code in _AIRPORT_LOOKUP_CACHE:
            return _AIRPORT_LOOKUP_CACHE[clean_code]

        # Dynamic online lookup fallback using HexDB / Airport APIs
        if requests:
            try:
                resp = requests.get(f"https://hexdb.io/api/v1/airport/icao/{clean_code}", timeout=1.5)
                if resp.status_code == 200:
                    data = resp.json()
                    name = data.get("city") or data.get("name")
                    if name:
                        _AIRPORT_LOOKUP_CACHE[clean_code] = name
                        return name
            except Exception:
                pass

        # Return the code itself if unknown
        return clean_code

    def _get_bounding_box(self) -> Tuple[float, float, float, float]:
        """Calculates (lat_min, lat_max, lon_min, lon_max) for bounding box."""
        lat_delta = self.radius_km / 111.0
        lon_delta = self.radius_km / (111.0 * max(0.01, math.cos(math.radians(self.lat))))
        return (
            self.lat - lat_delta,
            self.lat + lat_delta,
            self.lon - lon_delta,
            self.lon + lon_delta
        )

    def query_flightradar24(self) -> List[Dict[str, Any]]:
        """Queries FlightRadar24 live zone API feed."""
        if not requests:
            return []

        lat_min, lat_max, lon_min, lon_max = self._get_bounding_box()
        # FlightRadar24 format: bounds=lat_max,lat_min,lon_min,lon_max
        bounds_str = f"{lat_max:.4f},{lat_min:.4f},{lon_min:.4f},{lon_max:.4f}"
        url = (
            f"https://data-cloud.flightradar24.com/zones/fcgi/feed.js"
            f"?bounds={bounds_str}&faa=1&satellite=1&mlat=1&flarm=1&adsb=1"
            f"&gnd=0&air=1&vehicles=0&estimated=1&maxage=14400&gliders=0&stats=0"
        )
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
        }

        try:
            response = requests.get(url, headers=headers, timeout=3.5)
            if response.status_code != 200:
                return []
            data = response.json()
            flights = []
            for flight_id, f_data in data.items():
                if flight_id in ("full_count", "version", "stats") or not isinstance(f_data, list) or len(f_data) < 14:
                    continue

                f_lat = f_data[1]
                f_lon = f_data[2]
                heading = f_data[3]
                altitude = f_data[4]  # in feet
                speed_knots = f_data[5]  # in knots
                origin = f_data[11]
                destination = f_data[12]
                callsign = f_data[13] or f_data[16] or flight_id

                dist = self.haversine_distance(self.lat, self.lon, f_lat, f_lon)
                if dist <= self.radius_km:
                    flights.append({
                        "id": flight_id,
                        "callsign": str(callsign).strip(),
                        "lat": f_lat,
                        "lon": f_lon,
                        "heading": heading,
                        "altitude": altitude,
                        "speed_knots": speed_knots,
                        "origin": origin,
                        "destination": destination,
                        "distance_km": dist,
                        "source": "FlightRadar24"
                    })
            return flights
        except Exception as e:
            print(f"[!] FlightRadar24 query error: {e}")
            return []

    def query_opensky(self) -> List[Dict[str, Any]]:
        """Fallback queries OpenSky Network live state API."""
        if not requests:
            return []

        lat_min, lat_max, lon_min, lon_max = self._get_bounding_box()
        url = (
            f"https://opensky-network.org/api/states/all"
            f"?lamin={lat_min:.4f}&lamax={lat_max:.4f}&lomin={lon_min:.4f}&lomax={lon_max:.4f}"
        )
        try:
            resp = requests.get(url, timeout=3.5)
            if resp.status_code != 200:
                return []
            data = resp.json()
            states = data.get("states", [])
            flights = []
            for s in states or []:
                # OpenSky state vector format:
                # [0]: icao24, [1]: callsign, [2]: origin_country, [5]: longitude, [6]: latitude,
                # [7]: baro_altitude (m), [9]: velocity (m/s), [10]: true_track
                if not s[5] or not s[6]:
                    continue
                f_lon = float(s[5])
                f_lat = float(s[6])
                callsign = (s[1] or s[0] or "AIRCRAFT").strip()
                altitude_m = s[7] or 0.0
                altitude_ft = int(altitude_m * 3.28084)
                speed_mps = s[9] or 0.0
                speed_knots = int(speed_mps * 1.94384)
                heading = s[10] or 0.0

                dist = self.haversine_distance(self.lat, self.lon, f_lat, f_lon)
                if dist <= self.radius_km:
                    flights.append({
                        "id": s[0],
                        "callsign": callsign,
                        "lat": f_lat,
                        "lon": f_lon,
                        "heading": heading,
                        "altitude": altitude_ft,
                        "speed_knots": speed_knots,
                        "origin": None,
                        "destination": None,
                        "distance_km": dist,
                        "source": "OpenSky"
                    })
            return flights
        except Exception as e:
            print(f"[!] OpenSky fallback error: {e}")
            return []

    def get_closest_aircraft(self) -> Optional[Dict[str, Any]]:
        """Finds closest aircraft within radius_km, trying FlightRadar24 first, then OpenSky."""
        flights = self.query_flightradar24()
        if not flights:
            flights = self.query_opensky()

        if not flights:
            return None

        # Sort by distance to user
        flights.sort(key=lambda x: x["distance_km"])
        closest = flights[0]

        # Calculate intercept details
        dist_km = closest["distance_km"]
        speed_kmh = max(50.0, closest["speed_knots"] * 1.852)
        bearing_to_plane = self.calculate_bearing(self.lat, self.lon, closest["lat"], closest["lon"])
        plane_heading = closest["heading"] or 0.0

        # Relative angle between plane heading and vector to user
        # Vector from plane to user is (bearing_to_plane + 180) % 360
        bearing_plane_to_user = (bearing_to_plane + 180.0) % 360.0
        angle_diff = abs((plane_heading - bearing_plane_to_user + 180) % 360 - 180)

        # Intercept prediction
        if dist_km <= 12.0:
            intercept_desc = "is currently directly overhead"
            intercept_minutes = 0
        elif angle_diff < 75.0:  # Plane is heading generally towards the user
            time_min = max(1, round((dist_km / speed_kmh) * 60))
            intercept_desc = f"is approaching, estimated to cross overhead in approximately {time_min} minutes"
            intercept_minutes = time_min
        else:
            time_passed = max(1, round((dist_km / speed_kmh) * 60))
            intercept_desc = f"is currently {round(dist_km)} kilometers away, moving away from your sector"
            intercept_minutes = -time_passed

        closest["origin_city"] = self.resolve_airport(closest.get("origin"))
        closest["dest_city"] = self.resolve_airport(closest.get("destination"))
        closest["intercept_desc"] = intercept_desc
        closest["intercept_minutes"] = intercept_minutes
        return closest


# ==============================================================================
# 5. AUDIO TRANSIENT & PERCUSSIVE DETECTION ENGINE
# ==============================================================================

class ClapAudioDetector:
    """
    Continuous audio listener using sounddevice and numpy.
    Distinguishes sharp claps/snaps from ambient noise using:
    - Peak Amplitude
    - RMS Floor
    - Crest Factor (Peak / (RMS + 1e-6))
    - 80ms Debounce gap
    - Rolling time-window (e.g. 3 claps in 4.5s)
    - 5s cooldown after trigger
    """
    def __init__(self, on_triggered_callback, config: Dict[str, Any]):
        self.on_triggered = on_triggered_callback
        self.config = config
        self.sample_rate = int(config.get("sample_rate", 44100))
        self.block_size = int(config.get("block_size", 1024))
        self.recent_events: deque = deque()
        self.last_event_time: float = 0.0
        self.cooldown_until: float = 0.0
        self.stream: Optional[sd.InputStream] = None
        self.running: bool = False

    def update_config(self, config: Dict[str, Any]) -> None:
        self.config = config

    def set_cooldown(self, seconds: float) -> None:
        self.cooldown_until = time.time() + seconds
        self.recent_events.clear()

    def _audio_callback(self, indata, frames, time_info, status) -> None:
        if status:
            pass  # Suppress overflow warnings

        now = time.time()
        if now < self.cooldown_until:
            return

        # Convert audio buffer to mono float array
        audio_data = indata[:, 0] if indata.ndim > 1 else indata
        peak = float(np.max(np.abs(audio_data)))
        rms = float(np.sqrt(np.mean(audio_data ** 2)))
        crest_factor = peak / (rms + 1e-6)

        th_peak = float(self.config.get("threshold_peak", 0.22))
        th_snap_peak = float(self.config.get("threshold_snap_peak", 0.12))
        th_rms = float(self.config.get("threshold_rms", 0.006))
        min_crest = float(self.config.get("min_crest_factor", 4.0))
        debounce_sec = float(self.config.get("debounce_ms", 80)) / 1000.0

        is_clap = (peak >= th_peak) and (crest_factor >= min_crest) and (rms >= th_rms)
        is_snap = (peak >= th_snap_peak) and (crest_factor >= (min_crest * 1.2)) and (rms < (th_peak * 0.45))

        if is_clap or is_snap:
            if (now - self.last_event_time) >= debounce_sec:
                self.last_event_time = now
                event_type = "CLAP" if is_clap else "SNAP"
                self.recent_events.append((now, event_type))
                print(f"⚡ [{event_type}] Detected! (Peak: {peak:.3f}, Crest: {crest_factor:.1f}, RMS: {rms:.4f})")

                # Prune events outside window_seconds
                window_sec = float(self.config.get("window_seconds", 4.5))
                while self.recent_events and (now - self.recent_events[0][0]) > window_sec:
                    self.recent_events.popleft()

                required_claps = int(self.config.get("required_claps", 3))
                if len(self.recent_events) >= required_claps:
                    print(f"\n🎯 [TRIGGER REACHED]: {len(self.recent_events)} transient pulses in window! Activating JARVIS...\n")
                    self.recent_events.clear()
                    cooldown = float(self.config.get("cooldown_seconds", 5.0))
                    self.set_cooldown(cooldown)
                    # Trigger action asynchronously
                    threading.Thread(target=self.on_triggered, daemon=True).start()

    def start(self) -> None:
        if not sd:
            print("[!] sounddevice is not available. Audio detection cannot start.")
            return
        self.running = True
        self.stream = sd.InputStream(
            channels=1,
            samplerate=self.sample_rate,
            blocksize=self.block_size,
            dtype="float32",
            callback=self._audio_callback
        )
        self.stream.start()

    def stop(self) -> None:
        self.running = False
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass


# ==============================================================================
# 6. LIVE CALIBRATION CLI MODE (--calibrate)
# ==============================================================================

def run_calibration_mode(duration_seconds: int = 30) -> None:
    """
    Displays a live terminal ASCII VU meter showing real-time Peak, RMS,
    Crest Factor, and event classification for easy threshold tuning.
    """
    if not sd:
        print("[!] sounddevice library is required for calibration.")
        return

    config = load_config()
    print("=" * 70)
    print("🎛️  CLAP-JARVIS MICROPHONE & TRANSIENT CALIBRATION MODE")
    print("=" * 70)
    print(f"• Listening for {duration_seconds} seconds. Please snap and clap into your microphone.")
    print("• Notice the Peak, RMS, and Crest Factor values below.")
    print("• Target: Claps usually have Peak > 0.20, Snaps have Peak > 0.12 with Crest > 4.5.\n")
    print("Press Ctrl+C at any time to exit.\n")
    print("-" * 70)

    th_peak = float(config.get("threshold_peak", 0.22))
    th_snap_peak = float(config.get("threshold_snap_peak", 0.12))
    min_crest = float(config.get("min_crest_factor", 4.0))

    start_time = time.time()
    last_event_str = "Listening..."
    last_event_time = 0.0

    def cal_callback(indata, frames, time_info, status):
        nonlocal last_event_str, last_event_time
        audio_data = indata[:, 0] if indata.ndim > 1 else indata
        peak = float(np.max(np.abs(audio_data)))
        rms = float(np.sqrt(np.mean(audio_data ** 2)))
        crest = peak / (rms + 1e-6)

        is_clap = (peak >= th_peak) and (crest >= min_crest)
        is_snap = (peak >= th_snap_peak) and (crest >= (min_crest * 1.2))

        now = time.time()
        if (is_clap or is_snap) and (now - last_event_time) > 0.1:
            last_event_time = now
            if is_clap:
                last_event_str = f"👏 [HAND CLAP]  (Peak: {peak:.3f} | Crest: {crest:.1f})"
            else:
                last_event_str = f"🤌 [FINGER SNAP] (Peak: {peak:.3f} | Crest: {crest:.1f})"

        # Visual ASCII VU bar (30 characters wide)
        bar_len = min(30, int(peak * 30 * 2))
        bar = "█" * bar_len + "░" * (30 - bar_len)

        # Clear line and print live readout
        sys.stdout.write(
            f"\r[{bar}] Peak: {peak:.3f} | RMS: {rms:.4f} | Crest: {crest:4.1f} | {last_event_str:<35}"
        )
        sys.stdout.flush()

    try:
        with sd.InputStream(channels=1, samplerate=44100, blocksize=1024, dtype="float32", callback=cal_callback):
            while (time.time() - start_time) < duration_seconds:
                time.sleep(0.05)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"\n[!] Calibration error: {e}")

    print("\n\n" + "=" * 70)
    print("✅ Calibration finished.")
    print("If claps were not registering, lower 'threshold_peak' in config.json (e.g., 0.15).")
    print("If snaps were not registering, lower 'threshold_snap_peak' in config.json (e.g., 0.08).")
    print("If background noise triggers false alarms, raise 'min_crest_factor' (e.g., 5.0).")
    print("=" * 70)


# ==============================================================================
# 7. OPTIONAL SPEECH RECOGNITION WAKE-WORD LISTENER
# ==============================================================================

def start_wake_word_listener(on_wake_callback) -> Optional[threading.Thread]:
    """Background listener for spoken wake-word 'Jarvis' using SpeechRecognition."""
    if not sr:
        return None

    def worker():
        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 300
        recognizer.dynamic_energy_threshold = True

        while True:
            try:
                with sr.Microphone() as source:
                    recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    audio = recognizer.listen(source, timeout=5, phrase_time_limit=3)
                    try:
                        text = recognizer.recognize_google(audio).lower()
                        if "jarvis" in text:
                            print(f"\n🗣️ [WAKE-WORD]: 'Jarvis' detected in speech ('{text}')!")
                            on_wake_callback()
                    except (sr.UnknownValueError, sr.RequestError):
                        pass
            except Exception:
                time.sleep(1.0)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    return thread


# ==============================================================================
# 8. MAIN JARVIS CONTROLLER & ORCHESTRATOR
# ==============================================================================

# ==============================================================================
# 7.5 BUILT-IN WEB DASHBOARD SERVER TEMPLATE
# ==============================================================================

HTML_DASHBOARD_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🤖 CLAP-JARVIS HUD Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #070b14;
            --card-bg: rgba(15, 23, 42, 0.75);
            --border: rgba(0, 243, 255, 0.2);
            --cyan: #00f3ff;
            --blue: #0077ff;
            --gold: #ffd700;
            --green: #00ff88;
            --red: #ff3366;
            --text: #e2e8f0;
            --muted: #94a3b8;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Outfit', sans-serif; }

        body {
            background-color: var(--bg);
            background-image: 
                radial-gradient(circle at 10% 20%, rgba(0, 243, 255, 0.08) 0%, transparent 40%),
                radial-gradient(circle at 90% 80%, rgba(0, 119, 255, 0.08) 0%, transparent 40%);
            color: var(--text);
            min-height: 100vh;
            padding: 2rem;
            display: flex;
            flex-direction: column;
            align-items: center;
        }

        .container {
            max-width: 1000px;
            width: 100%;
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }

        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1.5rem 2rem;
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 16px;
            backdrop-filter: blur(12px);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4), 0 0 20px rgba(0, 243, 255, 0.1);
        }

        .brand { display: flex; align-items: center; gap: 1rem; }
        .arc-reactor {
            width: 42px; height: 42px;
            border-radius: 50%;
            border: 2px solid var(--cyan);
            box-shadow: 0 0 15px var(--cyan), inset 0 0 10px var(--cyan);
            display: flex; justify-content: center; align-items: center;
            animation: pulse 2s infinite ease-in-out;
        }
        .arc-inner { width: 18px; height: 18px; border-radius: 50%; background: var(--cyan); box-shadow: 0 0 10px var(--cyan); }

        @keyframes pulse {
            0%, 100% { transform: scale(1); opacity: 0.8; }
            50% { transform: scale(1.08); opacity: 1; filter: drop-shadow(0 0 12px var(--cyan)); }
        }

        h1 { font-size: 1.6rem; font-weight: 700; background: linear-gradient(135deg, #fff, var(--cyan)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .subtitle { font-size: 0.85rem; color: var(--muted); letter-spacing: 0.5px; }

        .badge {
            display: flex; align-items: center; gap: 0.5rem;
            padding: 0.5rem 1rem; border-radius: 20px;
            background: rgba(0, 255, 136, 0.1); border: 1px solid var(--green);
            color: var(--green); font-size: 0.85rem; font-weight: 600;
        }
        .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--green); box-shadow: 0 0 8px var(--green); }

        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem; }

        .card {
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 1.5rem;
            backdrop-filter: blur(12px);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            display: flex; flex-direction: column; gap: 1rem;
        }

        .card-title {
            font-size: 1.1rem; font-weight: 600; color: var(--cyan);
            display: flex; align-items: center; justify-content: space-between;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08); padding-bottom: 0.75rem;
        }

        .stat-row { display: flex; justify-content: space-between; align-items: center; font-size: 0.95rem; }
        .stat-label { color: var(--muted); }
        .stat-value { font-weight: 600; font-family: 'JetBrains Mono', monospace; color: #fff; }

        .btn {
            background: linear-gradient(135deg, var(--cyan), var(--blue));
            color: #000; border: none; padding: 0.85rem 1.4rem;
            border-radius: 10px; font-weight: 700; font-size: 0.95rem;
            cursor: pointer; transition: all 0.2s ease;
            display: flex; align-items: center; justify-content: center; gap: 0.6rem;
            box-shadow: 0 4px 15px rgba(0, 243, 255, 0.25);
        }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0, 243, 255, 0.4); }
        .btn:active { transform: translateY(0); }
        .btn-sec { background: rgba(255, 255, 255, 0.08); color: var(--text); border: 1px solid rgba(255, 255, 255, 0.15); box-shadow: none; }
        .btn-sec:hover { background: rgba(255, 255, 255, 0.15); border-color: var(--cyan); }

        .flight-hud {
            background: rgba(0, 243, 255, 0.05); border: 1px solid rgba(0, 243, 255, 0.15);
            border-radius: 12px; padding: 1rem; display: flex; flex-direction: column; gap: 0.5rem;
        }
        .flight-callsign { font-size: 1.4rem; font-weight: 700; color: var(--gold); font-family: 'JetBrains Mono', monospace; }
        .flight-route { font-size: 0.95rem; color: var(--text); }

        .form-group { display: flex; flex-direction: column; gap: 0.4rem; }
        .form-group label { font-size: 0.85rem; color: var(--muted); }
        .form-control {
            background: rgba(0, 0, 0, 0.4); border: 1px solid rgba(255, 255, 255, 0.15);
            color: #fff; padding: 0.6rem 0.8rem; border-radius: 8px; font-size: 0.9rem;
            font-family: 'JetBrains Mono', monospace; outline: none; transition: border 0.2s;
        }
        .form-control:focus { border-color: var(--cyan); box-shadow: 0 0 8px rgba(0, 243, 255, 0.3); }

        footer { margin-top: auto; font-size: 0.85rem; color: var(--muted); text-align: center; padding: 1rem; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="brand">
                <div class="arc-reactor"><div class="arc-inner"></div></div>
                <div>
                    <h1>CLAP-JARVIS HUD</h1>
                    <div class="subtitle">Iron Man Butler & Live Airspace Radar Assistant</div>
                </div>
            </div>
            <div class="badge"><div class="dot"></div> ONLINE (Port <span id="port-display">8888</span>)</div>
        </header>

        <div class="grid">
            <!-- Controls & Quick Actions -->
            <div class="card">
                <div class="card-title">⚡ Quick Actions</div>
                <button class="btn" onclick="triggerButler()">🎤 Trigger Butler Voice</button>
                <button class="btn btn-sec" onclick="scanAirspace()">📡 Scan Overhead Airspace</button>
                <button class="btn btn-sec" onclick="testSpeech()">🔊 Test TTS Voice Output</button>
                <div id="action-status" style="font-size: 0.85rem; color: var(--gold); min-height: 1.2rem;"></div>
            </div>

            <!-- Live Status HUD -->
            <div class="card">
                <div class="card-title">📊 System Telemetry</div>
                <div class="stat-row"><span class="stat-label">Butler Voice:</span><span class="stat-value" id="voice-val">en-GB-RyanNeural</span></div>
                <div class="stat-row"><span class="stat-label">GPS Latitude:</span><span class="stat-value" id="lat-val">28.6139</span></div>
                <div class="stat-row"><span class="stat-label">GPS Longitude:</span><span class="stat-value" id="lon-val">77.2090</span></div>
                <div class="stat-row"><span class="stat-label">Scan Radius:</span><span class="stat-value" id="radius-val">150 km</span></div>
                <div class="stat-row"><span class="stat-label">Clap Threshold (Peak):</span><span class="stat-value" id="peak-val">0.22</span></div>
                <div class="stat-row"><span class="stat-label">Snap Threshold (Peak):</span><span class="stat-value" id="snap-val">0.12</span></div>
                <div class="stat-row"><span class="stat-label">Required Claps:</span><span class="stat-value" id="claps-val">3</span></div>
            </div>
        </div>

        <!-- Airspace Scan Output -->
        <div class="card">
            <div class="card-title">✈️ Airspace Radar Intercept</div>
            <div id="flight-container" class="flight-hud">
                <div class="flight-callsign" id="flight-callsign">AIRSPACE SEARCH READY</div>
                <div class="flight-route" id="flight-details">Click "Scan Overhead Airspace" or trigger JARVIS with 3 claps to scan live airspace.</div>
            </div>
        </div>

        <!-- Configuration Deck -->
        <div class="card">
            <div class="card-title">⚙️ Live Settings Deck</div>
            <form id="config-form" onsubmit="saveConfig(event)">
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem;">
                    <div class="form-group">
                        <label>Latitude</label>
                        <input type="number" step="0.0001" class="form-control" id="cfg-lat">
                    </div>
                    <div class="form-group">
                        <label>Longitude</label>
                        <input type="number" step="0.0001" class="form-control" id="cfg-lon">
                    </div>
                    <div class="form-group">
                        <label>Radius (km)</label>
                        <input type="number" step="1" class="form-control" id="cfg-radius">
                    </div>
                    <div class="form-group">
                        <label>Voice</label>
                        <select class="form-control" id="cfg-voice">
                            <option value="en-GB-RyanNeural">en-GB-RyanNeural (British Ryan)</option>
                            <option value="en-GB-ThomasNeural">en-GB-ThomasNeural (British Thomas)</option>
                            <option value="en-GB-SoniaNeural">en-GB-SoniaNeural (British Sonia)</option>
                            <option value="en-US-GuyNeural">en-US-GuyNeural (American Guy)</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Clap Sensitivity Peak (0.10 - 0.40)</label>
                        <input type="number" step="0.01" class="form-control" id="cfg-peak">
                    </div>
                    <div class="form-group">
                        <label>Dashboard Web Port</label>
                        <input type="number" step="1" class="form-control" id="cfg-port">
                    </div>
                </div>
                <button type="submit" class="btn" style="margin-top: 1rem; width: 100%;">💾 Save & Hot-Reload Settings</button>
            </form>
        </div>

        <footer>🤖 JARVIS Background Daemon • Created for Windows</footer>
    </div>

    <script>
        async function fetchStatus() {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();
                const cfg = data.config;
                
                document.getElementById('port-display').innerText = data.port || 8888;
                document.getElementById('voice-val').innerText = cfg.voice || 'en-GB-RyanNeural';
                document.getElementById('lat-val').innerText = cfg.latitude;
                document.getElementById('lon-val').innerText = cfg.longitude;
                document.getElementById('radius-val').innerText = cfg.radius_km + ' km';
                document.getElementById('peak-val').innerText = cfg.threshold_peak;
                document.getElementById('snap-val').innerText = cfg.threshold_snap_peak;
                document.getElementById('claps-val').innerText = cfg.required_claps;

                // Form defaults
                if (!document.getElementById('cfg-lat').value) {
                    document.getElementById('cfg-lat').value = cfg.latitude;
                    document.getElementById('cfg-lon').value = cfg.longitude;
                    document.getElementById('cfg-radius').value = cfg.radius_km;
                    document.getElementById('cfg-voice').value = cfg.voice || 'en-GB-RyanNeural';
                    document.getElementById('cfg-peak').value = cfg.threshold_peak;
                    document.getElementById('cfg-port').value = cfg.web_port || 8888;
                }
            } catch(e) { console.error("Error loading status:", e); }
        }

        async function triggerButler() {
            document.getElementById('action-status').innerText = "⏳ Triggering JARVIS Butler voice...";
            try {
                const res = await fetch('/api/trigger', { method: 'POST' });
                const data = await res.json();
                document.getElementById('action-status').innerText = "✅ " + data.message;
            } catch(e) { document.getElementById('action-status').innerText = "❌ Error: " + e.message; }
        }

        async function scanAirspace() {
            document.getElementById('action-status').innerText = "📡 Scanning overhead airspace...";
            document.getElementById('flight-callsign').innerText = "SCANNING AIRSPACE...";
            document.getElementById('flight-details').innerText = "Querying live FlightRadar24 and OpenSky API...";

            try {
                const res = await fetch('/api/test-flight', { method: 'POST' });
                const data = await res.json();
                if (data.aircraft) {
                    const f = data.aircraft;
                    document.getElementById('flight-callsign').innerText = "✈️ " + f.callsign;
                    document.getElementById('flight-details').innerText = 
                        `Route: ${f.origin_city} → ${f.dest_city} | Altitude: ${f.altitude} ft | Speed: ${f.speed_knots} kts | Distance: ${f.distance_km.toFixed(1)} km (${f.intercept_desc})`;
                    document.getElementById('action-status').innerText = "✅ Aircraft detected overhead: " + f.callsign;
                } else {
                    document.getElementById('flight-callsign').innerText = "CLEAR AIRSPACE";
                    document.getElementById('flight-details').innerText = "No aircraft overhead within " + (data.radius_km || 150) + " km radius right now.";
                    document.getElementById('action-status').innerText = "ℹ️ No aircraft overhead right now.";
                }
            } catch(e) {
                document.getElementById('flight-callsign').innerText = "SCAN ERROR";
                document.getElementById('flight-details').innerText = e.message;
                document.getElementById('action-status').innerText = "❌ Scan failed.";
            }
        }

        async function testSpeech() {
            document.getElementById('action-status').innerText = "🔊 Playing Butler speech test...";
            try {
                const res = await fetch('/api/test-speech', { method: 'POST' });
                const data = await res.json();
                document.getElementById('action-status').innerText = "✅ " + data.message;
            } catch(e) { document.getElementById('action-status').innerText = "❌ Speech error: " + e.message; }
        }

        async function saveConfig(e) {
            e.preventDefault();
            document.getElementById('action-status').innerText = "💾 Saving configuration...";
            const payload = {
                latitude: parseFloat(document.getElementById('cfg-lat').value),
                longitude: parseFloat(document.getElementById('cfg-lon').value),
                radius_km: parseFloat(document.getElementById('cfg-radius').value),
                voice: document.getElementById('cfg-voice').value,
                threshold_peak: parseFloat(document.getElementById('cfg-peak').value),
                web_port: parseInt(document.getElementById('cfg-port').value)
            };

            try {
                const res = await fetch('/api/config', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                document.getElementById('action-status').innerText = "✅ Config saved & reloaded!";
                fetchStatus();
            } catch(err) { document.getElementById('action-status').innerText = "❌ Save error: " + err.message; }
        }

        fetchStatus();
        setInterval(fetchStatus, 5000);
    </script>
</body>
</html>"""


# ==============================================================================
# 8. MAIN JARVIS CONTROLLER & ORCHESTRATOR
# ==============================================================================

class JarvisAssistant:
    """
    Main background assistant controller. Coordinates audio detector,
    live FlightRadar24 tracking, British Butler neural TTS, and dynamic phrase deck.
    Also starts built-in Web HUD Dashboard HTTP server on configurable port.
    """
    def __init__(self, port_override: Optional[int] = None):
        self.config = load_config()
        if port_override:
            self.config["web_port"] = port_override
        self.port = int(self.config.get("web_port", 8888))
        self.phrase_deck = PhraseDeck(PHRASES_PATH)
        self.tts = ButlerTTS(voice=self.config.get("voice", "en-GB-RyanNeural"))
        self.tracker = FlightRadarTracker(
            lat=float(self.config.get("latitude", 28.6139)),
            lon=float(self.config.get("longitude", 77.2090)),
            radius_km=float(self.config.get("radius_km", 150.0))
        )
        self.detector = ClapAudioDetector(self.handle_trigger, self.config)
        self.is_busy = False
        self.last_flight_info: Optional[Dict[str, Any]] = None
        self.httpd = None

    def start_web_server(self) -> None:
        """Starts HTTP web server for the JARVIS HUD dashboard in a daemon thread."""
        assistant_self = self

        class DashboardHandler(http.server.BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass  # Suppress standard HTTP access logs

            def do_GET(self):
                parsed = urllib.parse.urlparse(self.path)
                if parsed.path == "/" or parsed.path == "/index.html":
                    self.send_response(200)
                    self.send_header("Content-type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(HTML_DASHBOARD_TEMPLATE.encode("utf-8"))
                elif parsed.path == "/api/status":
                    self.send_response(200)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    status_data = {
                        "status": "online",
                        "port": assistant_self.port,
                        "config": assistant_self.config,
                        "last_flight": assistant_self.last_flight_info,
                        "is_busy": assistant_self.is_busy
                    }
                    self.wfile.write(json.dumps(status_data).encode("utf-8"))
                elif parsed.path == "/api/config":
                    self.send_response(200)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(assistant_self.config).encode("utf-8"))
                else:
                    self.send_error(404, "Not Found")

            def do_POST(self):
                parsed = urllib.parse.urlparse(self.path)
                content_len = int(self.headers.get("Content-Length", 0))
                post_body = self.rfile.read(content_len) if content_len > 0 else b""

                if parsed.path == "/api/trigger":
                    threading.Thread(target=assistant_self.handle_trigger, daemon=True).start()
                    self.send_response(200)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"success": True, "message": "Butler trigger executed!"}).encode("utf-8"))

                elif parsed.path == "/api/test-flight":
                    flight = assistant_self.tracker.get_closest_aircraft()
                    assistant_self.last_flight_info = flight
                    self.send_response(200)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"aircraft": flight, "radius_km": assistant_self.config.get("radius_km", 150)}).encode("utf-8"))

                elif parsed.path == "/api/test-speech":
                    phrase = assistant_self.phrase_deck.get_next_phrase()
                    threading.Thread(target=assistant_self.tts.speak, args=(phrase,), daemon=True).start()
                    self.send_response(200)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"success": True, "message": f"Speaking: '{phrase}'"}).encode("utf-8"))

                elif parsed.path == "/api/config":
                    try:
                        new_cfg = json.loads(post_body.decode("utf-8"))
                        assistant_self.config.update(new_cfg)
                        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                            json.dump(assistant_self.config, f, indent=2)
                        assistant_self.reload_settings()
                        self.send_response(200)
                        self.send_header("Content-type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps({"success": True, "config": assistant_self.config}).encode("utf-8"))
                    except Exception as e:
                        self.send_response(400)
                        self.send_header("Content-type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
                else:
                    self.send_error(404, "Endpoint Not Found")

        def run_server():
            try:
                socketserver.TCPServer.allow_reuse_address = True
                self.httpd = socketserver.TCPServer(("0.0.0.0", self.port), DashboardHandler)
                print(f"🌐 JARVIS Web Dashboard listening on http://localhost:{self.port}")
                self.httpd.serve_forever()
            except Exception as e:
                print(f"[!] Could not start Web Dashboard on port {self.port}: {e}")

        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()

    def reload_settings(self) -> None:
        """Hot-reloads config.json and updates tracker, TTS, and audio detector."""
        self.config = load_config()
        self.tts.set_voice(self.config.get("voice", "en-GB-RyanNeural"))
        self.tracker.set_location(
            lat=float(self.config.get("latitude", 28.6139)),
            lon=float(self.config.get("longitude", 77.2090)),
            radius_km=float(self.config.get("radius_km", 150.0))
        )
        self.detector.update_config(self.config)

    def handle_trigger(self) -> None:
        """Executed upon 3-clap/snap transient detection or 'Jarvis' wake-word."""
        if self.is_busy:
            return

        self.is_busy = True
        self.reload_settings()

        try:
            enable_flight = self.config.get("enable_flight_check", True)
            flight_info = None

            if enable_flight:
                print("📡 Scanning overhead airspace for live aircraft...")
                flight_info = self.tracker.get_closest_aircraft()
                self.last_flight_info = flight_info

            if flight_info:
                # Airplane overhead detected!
                callsign = flight_info.get("callsign", "Flight")
                origin = flight_info.get("origin_city", "Undisclosed")
                dest = flight_info.get("dest_city", "Undisclosed")
                alt = flight_info.get("altitude", 0)
                intercept = flight_info.get("intercept_desc", "overhead")

                speech_text = (
                    f"Good day Sir. Attention: Aircraft {callsign}, traveling from {origin} to {dest} "
                    f"at {alt} feet, {intercept}."
                )
                self.tts.speak(speech_text)

                # Automatically open FlightRadar24 in default browser
                if self.config.get("auto_open_browser", True):
                    flight_id = flight_info.get("id")
                    if flight_id and flight_info.get("source") == "FlightRadar24":
                        url = f"https://www.flightradar24.com/{flight_id}"
                    else:
                        f_lat = flight_info.get("lat")
                        f_lon = flight_info.get("lon")
                        url = f"https://www.flightradar24.com/{f_lat},{f_lon}/12"
                    print(f"🌐 Launching FlightRadar24: {url}")
                    webbrowser.open(url)
            else:
                # No aircraft overhead -> Speak witty butler line
                line = self.phrase_deck.get_next_phrase()
                self.tts.speak(line)

        except Exception as e:
            print(f"[!] Trigger execution error: {e}")
            self.tts.speak("Welcome back Sir. All systems are operational.")
        finally:
            # Re-enable detection after cooldown
            cooldown = float(self.config.get("cooldown_seconds", 5.0))
            self.detector.set_cooldown(cooldown)
            self.is_busy = False

    def run(self) -> None:
        """Starts the background audio stream and enters the run loop."""
        if self.config.get("enable_web_dashboard", True):
            self.start_web_server()

        print("=" * 70)
        print("🤖 CLAP-JARVIS IS ONLINE")
        print("=" * 70)
        print("• Status: Running quietly in the background.")
        print(f"• Detection: Listening for {self.config.get('required_claps', 3)} claps/snaps within {self.config.get('window_seconds', 4.5)}s.")
        print(f"• Location: Lat {self.config.get('latitude')}, Lon {self.config.get('longitude')} (Radius: {self.config.get('radius_km')} km)")
        print(f"• Voice: {self.config.get('voice', 'en-GB-RyanNeural')}")
        print(f"• Web HUD Dashboard: http://localhost:{self.port}")
        print("• Press Ctrl+C in this window to stop.\n")

        self.detector.start()

        if self.config.get("enable_jarvis_wake_word", False):
            print("• Wake-word: 'Jarvis' voice detection enabled.")
            start_wake_word_listener(self.handle_trigger)

        try:
            while True:
                time.sleep(1.0)
        except KeyboardInterrupt:
            print("\n🛑 Shutting down CLAP-JARVIS gracefully...")
        finally:
            self.detector.stop()


# ==============================================================================
# 9. CLI ENTRY POINT
# ==============================================================================

def main():
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except Exception:
            pass
    parser = argparse.ArgumentParser(
        description="CLAP-JARVIS: Iron Man Butler & Overhead Flight Radar Assistant for Windows"
    )
    parser.add_argument("--calibrate", action="store_true", help="Run 30-second audio calibration VU meter")
    parser.add_argument("--test-speech", action="store_true", help="Test British neural butler TTS output")
    parser.add_argument("--test-flight", action="store_true", help="Test live FlightRadar24 overhead scan")
    parser.add_argument("--headless", action="store_true", help="Run in silent background daemon mode")
    parser.add_argument("--port", type=int, default=None, help="Port to run JARVIS Web Dashboard on (default: 8888)")

    args = parser.parse_args()

    if args.calibrate:
        run_calibration_mode()
        return

    if args.test_speech:
        config = load_config()
        deck = PhraseDeck(PHRASES_PATH)
        phrase = deck.get_next_phrase()
        tts = ButlerTTS(voice=config.get("voice", "en-GB-RyanNeural"))
        print(f"Testing speech: '{phrase}'")
        tts.speak(phrase)
        time.sleep(6.0)
        return

    if args.test_flight:
        config = load_config()
        tracker = FlightRadarTracker(
            lat=float(config.get("latitude", 28.6139)),
            lon=float(config.get("longitude", 77.2090)),
            radius_km=float(config.get("radius_km", 150.0))
        )
        print(f"Scanning airspace around ({tracker.lat}, {tracker.lon}) radius {tracker.radius_km} km...")
        closest = tracker.get_closest_aircraft()
        if closest:
            print(f"✈️ Aircraft Found: {closest['callsign']}")
            print(f"   Route: {closest['origin_city']} -> {closest['dest_city']}")
            print(f"   Altitude: {closest['altitude']} ft | Speed: {closest['speed_knots']} knots")
            print(f"   Distance: {closest['distance_km']:.1f} km")
            print(f"   Intercept: {closest['intercept_desc']}")
        else:
            print("No aircraft found within the specified radius right now.")
        return

    # Default run mode
    jarvis = JarvisAssistant(port_override=args.port)
    jarvis.run()


if __name__ == "__main__":
    main()

