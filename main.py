import pygame
from spotify import generate_qr_code

def pil_to_pygame(pil_image):
    if pil_image.mode != 'RGB':
        pil_image = pil_image.convert('RGB')

    image_str = pil_image.tobytes()
    size = pil_image.size

    pygame_surface = pygame.image.fromstring(image_str, size, 'RGB')

    return pygame_surface


pygame.init()

WIDTH, HEIGHT = 1080, 1080
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Spotify Record Player")

def load_control_images(size=(64, 64)):
    paths = {
        'previous': 'imgs/previous.png',
        'play': 'imgs/play.png',
        'pause': 'imgs/pause.png',
        'skip': 'imgs/skip.png',
        'menu': 'imgs/menu.png',
        'banner': 'imgs/banner.png',
        'disc': 'imgs/disc.png'
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

DISC_SIZE = (360, 360)
raw_disc = controls.get('disc')
disc_surface = None
if raw_disc:
    try:
        disc_img = pygame.image.load('imgs/disc.png').convert_alpha()
        disc_surface = pygame.transform.smoothscale(disc_img, DISC_SIZE)
    except Exception:
        try:
            disc_surface = pygame.transform.smoothscale(raw_disc, DISC_SIZE)
        except Exception:
            disc_surface = None

CENTER_X = WIDTH // 2
CONTROL_Y = 800
SPACING = 40
is_playing = False

control_order = ['previous', 'play', 'skip']
surfaces = [controls.get('previous'), controls.get('play'), controls.get('skip')]

def layout_controls(surfaces, center_x, y, spacing=40):
    widths = [s.get_width() for s in surfaces if s is not None]
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

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            for i, rect in enumerate(control_rects):
                if rect and rect.collidepoint((mx, my)):
                    if i == 1:
                        is_playing = not is_playing
                        if is_playing and controls.get('pause'):
                            surfaces[1] = controls.get('pause')
                        else:
                            surfaces[1] = controls.get('play')
                        control_rects = layout_controls(surfaces, CENTER_X, CONTROL_Y, SPACING)
                    else:
                        pass

    screen.fill((30, 30, 30))

    valid_rects = [r for r in control_rects if r]
    if disc_surface:
        disc_rect = disc_surface.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        screen.blit(disc_surface, disc_rect.topleft)
    if valid_rects:
        left = min(r.left for r in valid_rects) - 16
        right = max(r.right for r in valid_rects) + 16
        top = min(r.top for r in valid_rects) - 12
        bottom = max(r.bottom for r in valid_rects) + 12
        bg_w = right - left
        bg_h = bottom - top
        bg_surf = pygame.Surface((bg_w, bg_h), pygame.SRCALPHA)
        bg_surf.fill((0, 0, 0, 160))
        screen.blit(bg_surf, (left, top))

    for s, r in zip(surfaces, control_rects):
        if s and r:
            screen.blit(s, r.topleft)

    pygame.display.flip()
    clock.tick(60)