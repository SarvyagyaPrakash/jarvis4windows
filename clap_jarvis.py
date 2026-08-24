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
    "threshold_peak": 0.15,
    "threshold_snap_peak": 0.07,
    "min_crest_factor": 2.0,
    "threshold_rms": 0.001,
    "required_claps": 3,
    "window_seconds": 5.0,
    "cooldown_seconds": 6.0,
    "debounce_ms": 60,
    "sample_rate": 44100,
    "block_size": 1024,
    "voice": "en-GB-RyanNeural",
    "enable_flight_check": True,
    "enable_jarvis_wake_word": False,
    "auto_open_browser": True
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

    def speak(self, text: str, block: bool = False) -> None:
        """Speaks the text synchronously (if block=True) or asynchronously in a worker thread."""
        if block:
            self._speak_worker(text)
        else:
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
        self.noise_floor: float = 0.002

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

        # Smoothly track ambient background noise floor
        self.noise_floor = 0.96 * self.noise_floor + 0.04 * max(rms, 0.0005)

        th_peak = float(self.config.get("threshold_peak", 0.15))
        th_snap_peak = float(self.config.get("threshold_snap_peak", 0.07))
        th_rms = float(self.config.get("threshold_rms", 0.001))
        min_crest = float(self.config.get("min_crest_factor", 2.0))
        debounce_sec = float(self.config.get("debounce_ms", 60)) / 1000.0

        # Transient spike ratio above background noise floor
        spike_ratio = peak / (self.noise_floor + 1e-6)

        is_pulse = (peak >= th_snap_peak) and (crest_factor >= min_crest or spike_ratio >= 2.0)

        if is_pulse:
            if (now - self.last_event_time) >= debounce_sec:
                self.last_event_time = now
                event_type = "CLAP" if peak >= th_peak else "SNAP"

                # Prune events outside window_seconds first
                window_sec = float(self.config.get("window_seconds", 5.0))
                while self.recent_events and (now - self.recent_events[0][0]) > window_sec:
                    self.recent_events.popleft()

                self.recent_events.append((now, event_type))
                required_claps = int(self.config.get("required_claps", 3))
                print(f"⚡ [{event_type}] Detected! ({len(self.recent_events)}/{required_claps}) [Peak: {peak:.3f}, Crest: {crest_factor:.1f}, RMS: {rms:.4f}]")

                if len(self.recent_events) >= required_claps:
                    print(f"\n🎯 [TRIGGER REACHED]: {len(self.recent_events)} transient pulses in window! Activating JARVIS...\n")
                    self.recent_events.clear()
                    cooldown = float(self.config.get("cooldown_seconds", 4.0))
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

class JarvisAssistant:
    """
    Main background assistant controller. Coordinates audio detector,
    live FlightRadar24 tracking, British Butler neural TTS, and dynamic phrase deck.
    """
    def __init__(self):
        self.config = load_config()
        self.phrase_deck = PhraseDeck(PHRASES_PATH)
        self.tts = ButlerTTS(voice=self.config.get("voice", "en-GB-RyanNeural"))
        self.tracker = FlightRadarTracker(
            lat=float(self.config.get("latitude", 28.6139)),
            lon=float(self.config.get("longitude", 77.2090)),
            radius_km=float(self.config.get("radius_km", 150.0))
        )
        self.detector = ClapAudioDetector(self.handle_trigger, self.config)
        self.is_busy = False

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
        # Mute audio detection for 15s during execution to avoid hearing own voice
        self.detector.set_cooldown(15.0)
        self.reload_settings()

        try:
            enable_flight = self.config.get("enable_flight_check", True)
            flight_info = None

            if enable_flight:
                print("📡 Scanning overhead airspace for live aircraft...")
                flight_info = self.tracker.get_closest_aircraft()

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
                self.tts.speak(speech_text, block=True)

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
                self.tts.speak(line, block=True)

        except Exception as e:
            print(f"[!] Trigger execution error: {e}")
            self.tts.speak("Welcome back Sir. All systems are operational.", block=True)
        finally:
            # Re-enable detection after post-speech cooldown
            cooldown = float(self.config.get("cooldown_seconds", 8.0))
            self.detector.set_cooldown(cooldown)
            self.is_busy = False

    def run(self) -> None:
        """Starts the background audio stream and enters the run loop."""
        print("=" * 70)
        print("🤖 CLAP-JARVIS IS ONLINE")
        print("=" * 70)
        print("• Status: Running quietly in the background.")
        print(f"• Detection: Listening for {self.config.get('required_claps', 3)} claps/snaps within {self.config.get('window_seconds', 4.5)}s.")
        print(f"• Location: Lat {self.config.get('latitude')}, Lon {self.config.get('longitude')} (Radius: {self.config.get('radius_km')} km)")
        print(f"• Voice: {self.config.get('voice', 'en-GB-RyanNeural')}")
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
    jarvis = JarvisAssistant()
    jarvis.run()


if __name__ == "__main__":
    main()

