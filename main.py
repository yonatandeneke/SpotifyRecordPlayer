import pygame
import spotify
import urllib.request
from io import BytesIO
from PIL import Image
import threading
import time

def pil_to_pygame(pil_image):
    if pil_image.mode != 'RGB':
        pil_image = pil_image.convert('RGB')
    image_str = pil_image.tobytes()
    size = pil_image.size
    return pygame.image.fromstring(image_str, size, 'RGB')


def load_album_art(url, size):
    try:
        with urllib.request.urlopen(url) as response:
            data = response.read()
        pil_img = Image.open(BytesIO(data)).convert('RGBA')
        pil_img = pil_img.resize((size, size), Image.LANCZOS)

        mask = Image.new('L', (size, size), 0)
        from PIL import ImageDraw
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, size, size), fill=255)

        result = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        result.paste(pil_img, (0, 0))
        result.putalpha(mask)

        raw = result.tobytes()
        surf = pygame.image.fromstring(raw, (size, size), 'RGBA')
        return surf.convert_alpha()
    except Exception as e:
        print(f"Failed to load album art: {e}")
        return None


def make_vinyl_surface(disc_surface, album_surf, disc_size):
    vinyl = disc_surface.copy()

    if album_surf:
        art_size = album_surf.get_width()
        x = (disc_size[0] - art_size) // 2
        y = (disc_size[1] - art_size) // 2
        vinyl.blit(album_surf, (x, y))

    center = (disc_size[0] // 2, disc_size[1] // 2)
    pygame.draw.circle(vinyl, (20, 20, 20, 255), center, 18)
    pygame.draw.circle(vinyl, (40, 40, 40, 255), center, 18, 2)

    return vinyl


pygame.init()
pygame.mixer.quit()

WIDTH, HEIGHT = 1080, 1080
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.WINDOWMOVED)
pygame.display.set_caption("Spotify Record Player")
pygame.mouse.set_visible(False)


def load_control_images(size=(64, 64)):
    paths = {
        'previous': 'imgs/previous.png',
        'play':     'imgs/play.png',
        'pause':    'imgs/pause.png',
        'skip':     'imgs/skip.png',
        'menu':     'imgs/menu.png',
        'banner':   'imgs/banner.png',
        'disc':     'imgs/disc.png'
    }
    loaded = {}
    for k, p in paths.items():
        try:
            img = pygame.image.load(p).convert_alpha()
            img = pygame.transform.smoothscale(img, size)
            loaded[k] = img
        except Exception:
            loaded[k] = None
    return loaded


controls = load_control_images(size=(80, 80))

DISC_SIZE = (WIDTH, HEIGHT)
disc_base = None
try:
    disc_img = pygame.image.load('imgs/disc.png').convert()
    disc_base = pygame.transform.smoothscale(disc_img, DISC_SIZE)
except Exception:
    disc_base = None

ALBUM_ART_SIZE = int(min(WIDTH, HEIGHT) * 0.38)
current_art_url = None
album_art_surf = None
vinyl_surface = None
disc_angle = 0.0
is_playing_cached = False
latest_art_url = None
state_lock = threading.Lock()
stop_polling = threading.Event()

SPIN_DEG_PER_SEC = 80.0

def refresh_vinyl():
    global current_art_url, album_art_surf, vinyl_surface
    with state_lock:
        url = latest_art_url
    if url and url != current_art_url:
        current_art_url = url
        album_art_surf = load_album_art(url, ALBUM_ART_SIZE)
    if disc_base:
        vinyl_surface = make_vinyl_surface(disc_base, album_art_surf, DISC_SIZE)

def polling_worker(playback_interval_s=1.0, art_interval_s=5.0):
    global is_playing_cached, latest_art_url
    next_playback = 0.0
    next_art = 0.0
    while not stop_polling.is_set():
        now = time.monotonic()
        did_work = False

        if now >= next_playback:
            did_work = True
            next_playback = now + playback_interval_s
            try:
                playing = bool(spotify.isPlaying())
                with state_lock:
                    is_playing_cached = playing
            except Exception:
                pass

        if now >= next_art:
            did_work = True
            next_art = now + art_interval_s
            try:
                url = spotify.get_disc_image()
                if url:
                    with state_lock:
                        latest_art_url = url
            except Exception:
                pass

        if not did_work:
            stop_polling.wait(0.05)

poll_thread = threading.Thread(target=polling_worker, daemon=True)
poll_thread.start()

refresh_vinyl()

CENTER_X = WIDTH // 2
CONTROL_Y = 800
SPACING = 40

surfaces = [
    controls.get('previous'),
    controls.get('pause') if is_playing_cached else controls.get('play'),
    controls.get('skip')
]


def layout_controls(surfaces, center_x, y, spacing=40):
    widths  = [s.get_width()  for s in surfaces if s is not None]
    heights = [s.get_height() for s in surfaces if s is not None]
    if not widths:
        return []
    total_width = sum(widths) + spacing * (len(widths) - 1)
    start_x = center_x - total_width // 2
    rects = []
    x = start_x
    for s in surfaces:
        if s is None:
            rects.append(None)
            continue
        rect = s.get_rect()
        rect.topleft = (x, y - rect.height // 2)
        rects.append(rect)
        x += rect.width + spacing
    return rects


control_rects = layout_controls(surfaces, CENTER_X, CONTROL_Y, SPACING)
controls_bg_surf = None
controls_bg_pos = (0, 0)

def rebuild_controls_bg():
    global controls_bg_surf, controls_bg_pos
    valid_rects = [r for r in control_rects if r]
    if not valid_rects:
        controls_bg_surf = None
        return
    left   = min(r.left  for r in valid_rects) - 16
    right  = max(r.right for r in valid_rects) + 16
    top    = min(r.top   for r in valid_rects) - 12
    bottom = max(r.bottom for r in valid_rects) + 12
    bg_w = right - left
    bg_h = bottom - top
    bg = pygame.Surface((bg_w, bg_h), pygame.SRCALPHA)
    bg.fill((0, 0, 0, 160))
    controls_bg_surf = bg
    controls_bg_pos = (left, top)

rebuild_controls_bg()

running = True
clock = pygame.time.Clock()
art_refresh_timer = 0
ART_REFRESH_INTERVAL = 5000
playback_refresh_timer = 0
PLAYBACK_REFRESH_INTERVAL = 1000

while running:
    dt = clock.tick(60)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            if is_playing_cached:
                spotify.pause()
            stop_polling.set()
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                stop_polling.set()
                running = False
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            for i, rect in enumerate(control_rects):
                if rect and rect.collidepoint((mx, my)):
                    if not spotify.isConnected():
                        continue
                    if i == 1:
                        if not is_playing_cached and controls.get('pause'):
                            surfaces[1] = controls.get('pause')
                            spotify.play()
                            is_playing_cached = True
                        else:
                            surfaces[1] = controls.get('play')
                            spotify.pause()
                            is_playing_cached = False
                        control_rects = layout_controls(surfaces, CENTER_X, CONTROL_Y, SPACING)
                        rebuild_controls_bg()
                    elif i == 0:
                        spotify.skip_previous()
                    elif i == 2:
                        spotify.skip_next()
                        
    art_refresh_timer += dt
    if art_refresh_timer >= ART_REFRESH_INTERVAL:
        art_refresh_timer = 0
        refresh_vinyl()

    playback_refresh_timer += dt
    if playback_refresh_timer >= PLAYBACK_REFRESH_INTERVAL:
        playback_refresh_timer = 0
        with state_lock:
            playing_now = is_playing_cached
        desired = controls.get('pause') if playing_now else controls.get('play')
        if desired and surfaces[1] is not desired:
            surfaces[1] = desired
            control_rects = layout_controls(surfaces, CENTER_X, CONTROL_Y, SPACING)
            rebuild_controls_bg()
        refresh_vinyl()

    with state_lock:
        playing_now = is_playing_cached
    if playing_now:
        disc_angle = (disc_angle + SPIN_DEG_PER_SEC * (dt / 1000.0)) % 360

    screen.fill((30, 30, 30))

    if vinyl_surface:
        rotated = pygame.transform.rotate(vinyl_surface, disc_angle)
        screen.blit(rotated, rotated.get_rect(center=(WIDTH // 2, HEIGHT // 2)))

    if controls_bg_surf:
        screen.blit(controls_bg_surf, controls_bg_pos)

    for s, r in zip(surfaces, control_rects):
        if s and r:
            screen.blit(s, r.topleft)

    pygame.display.flip()