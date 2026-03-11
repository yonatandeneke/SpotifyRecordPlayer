import pygame
import spotify
import urllib.request
from io import BytesIO
from PIL import Image

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
        # Sample the disc color at the album art position to use as bg
        bg_color = vinyl.get_at((x + art_size // 2, y + art_size // 2))[:3]
        flat = pygame.Surface((art_size, art_size))
        flat.fill(bg_color)
        flat.blit(album_surf, (0, 0))
        vinyl.blit(flat, (x, y))

    center = (disc_size[0] // 2, disc_size[1] // 2)
    pygame.draw.circle(vinyl, (20, 20, 20), center, 18)
    pygame.draw.circle(vinyl, (40, 40, 40), center, 18, 2)

    return vinyl.convert()


pygame.init()
pygame.mixer.quit()

WIDTH, HEIGHT = 1080, 1080
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF)
pygame.display.set_caption("Spotify Record Player")


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
    disc_base = pygame.transform.smoothscale(disc_img, DISC_SIZE).convert()
except Exception:
    disc_base = None

ALBUM_ART_SIZE = int(min(WIDTH, HEIGHT) * 0.38)
current_art_url = None
album_art_surf = None
vinyl_surface = None
disc_angle = 0.0

def refresh_vinyl():
    global current_art_url, album_art_surf, vinyl_surface
    url = spotify.get_disc_image()
    if url and url != current_art_url:
        current_art_url = url
        album_art_surf = load_album_art(url, ALBUM_ART_SIZE)
    if disc_base:
        vinyl_surface = make_vinyl_surface(disc_base, album_art_surf, DISC_SIZE)

refresh_vinyl()

CENTER_X = WIDTH // 2
CONTROL_Y = 800
SPACING = 40

surfaces = [
    controls.get('previous'),
    controls.get('pause') if spotify.isPlaying() else controls.get('play'),
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

running = True
clock = pygame.time.Clock()
art_refresh_timer = 0
ART_REFRESH_INTERVAL = 5000

def build_controls_bg(control_rects):
    valid_rects = [r for r in control_rects if r]
    if not valid_rects:
        return None, (0, 0)
    left   = min(r.left  for r in valid_rects) - 16
    right  = max(r.right for r in valid_rects) + 16
    top    = min(r.top   for r in valid_rects) - 12
    bottom = max(r.bottom for r in valid_rects) + 12
    bg_surf = pygame.Surface((right - left, bottom - top), pygame.SRCALPHA)
    bg_surf.fill((0, 0, 0, 160))
    return bg_surf, (left, top)

controls_bg, controls_bg_pos = build_controls_bg(control_rects)

while running:
    dt = clock.tick(60)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            if spotify.isPlaying():
                spotify.pause()
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            for i, rect in enumerate(control_rects):
                if rect and rect.collidepoint((mx, my)):
                    if not spotify.isConnected():
                        continue
                    if i == 1:
                        if not spotify.isPlaying() and controls.get('pause'):
                            surfaces[1] = controls.get('pause')
                            spotify.play()
                        else:
                            surfaces[1] = controls.get('play')
                            spotify.pause()
                        control_rects = layout_controls(surfaces, CENTER_X, CONTROL_Y, SPACING)
                        controls_bg, controls_bg_pos = build_controls_bg(control_rects)
                    elif i == 0:
                        spotify.skip_previous()
                        refresh_vinyl()
                    elif i == 2:
                        spotify.skip_next()
                        refresh_vinyl()

    art_refresh_timer += dt
    if art_refresh_timer >= ART_REFRESH_INTERVAL:
        art_refresh_timer = 0
        refresh_vinyl()

    if spotify.isPlaying():
        disc_angle = (disc_angle + 33 * (dt / 1000)) % 360

    screen.fill((30, 30, 30))

    if vinyl_surface:
        rotated = pygame.transform.rotate(vinyl_surface, -disc_angle)
        rot_rect = rotated.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        screen.blit(rotated, rot_rect.topleft)

    if controls_bg:
        screen.blit(controls_bg, controls_bg_pos)

    for s, r in zip(surfaces, control_rects):
        if s and r:
            screen.blit(s, r.topleft)

    pygame.display.flip()