import os
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth
import qrcode

load_dotenv()

def generate_qr_code(): 
    auth_manager = SpotifyOAuth(os.getenv("CLIENT_ID"),
                                               os.getenv("CLIENT_SECRET"),
                                               os.getenv("REDIRECT_URI"),
                                               scope="user-read-playback-state,user-modify-playback-state,user-read-currently-playing")
    
    auth_url = auth_manager.get_authorize_url()

    qr = qrcode.QRCode(box_size=10, border=4)
    qr.add_data(auth_url)
    qr.make()
    
    return qr.make_image(fill_color="black", back_color="white")
