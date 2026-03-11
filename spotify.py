import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
import os
import time

load_dotenv()

scope = (
    "user-read-playback-state "
    "user-modify-playback-state "
    "user-read-currently-playing"
)

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=os.getenv("CLIENT_ID"),
    client_secret=os.getenv("CLIENT_SECRET"),
    redirect_uri=os.getenv("REDIRECT_URI"),
    scope=scope
))

def get_current_track():
    current = sp.current_playback()
    if current and current["item"]:
        track = current["item"]
        print("Now playing:", track["name"])
        print("Artist:", track["artists"][0]["name"])
        print("Album:", track["album"]["name"])
        print("Is playing:", current["is_playing"])
    else:
        print("Nothing is currently playing.")

def get_disc_image():
    current = sp.current_playback()
    if current and current["item"]:
        track = current["item"]
        images = track["album"]["images"]
        if images:
            return images[0]["url"]
    return None

def isPlaying():
    playback = sp.current_playback()
    return playback and playback['is_playing']

def isConnected():
    devices = sp.devices()
    if devices['devices']:
        active = [d for d in devices['devices'] if d['is_active']]
        return active
    return False

def play():
    sp.start_playback()
    print("Playback started")

def pause():
    sp.pause_playback()
    print("Playback paused")

def skip_next():
    sp.next_track()
    print("Skipped to next track")

def skip_previous():
    sp.previous_track()
    print("Went to previous track")