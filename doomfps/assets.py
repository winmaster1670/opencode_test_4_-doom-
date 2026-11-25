"""Procedurally generated textures, sprites and fonts.

No external image files are needed: everything is drawn with pygame at startup
and cached, including pre-shaded copies used by the raycaster for distance fog.
"""

import math
import random

import pygame

from . import config as C


def _shade_variants(surface, count=C.SHADE_LEVELS):
    """Return ``count`` copies of *surface* darkened by successive gray levels."""
    variants = []
    for i in range(count):
        level = int(255 * (0.14 + 0.86 * i / (count - 1)))
        copy = surface.copy()
        copy.fill((level, level, level, 255), special_flags=pygame.BLEND_MULT)
        variants.append(copy)
    return variants


# ---------------------------------------------------------------------------
# Wall textures
# ---------------------------------------------------------------------------

def _brick():
    rnd = random.Random(11)
    s = pygame.Surface((C.TEX_SIZE, C.TEX_SIZE))
    s.fill((65, 32, 28))
    for row in range(4):
        y = row * 16
        offset = 0 if row % 2 == 0 else 16
        for bx in range(-offset, C.TEX_SIZE, 32):
            shade = rnd.randint(-14, 14)
            col = (max(0, min(255, 150 + shade)),
                   max(0, min(255, 58 + shade // 2)),
                   max(0, min(255, 44 + shade // 2)))
            pygame.draw.rect(s, col, (bx + 1, y + 1, 30, 14))
        pygame.draw.rect(s, (38, 20, 18), (0, y, C.TEX_SIZE, 2))
        pygame.draw.rect(s, (35, 18, 16), (0, y + 15, C.TEX_SIZE, 1))
    for _ in range(140):
        x, y = rnd.randrange(64), rnd.randrange(64)
        s.set_at((x, y), rnd.choice([(180, 85, 65), (90, 40, 35), (60, 28, 25)]))
    return s


def _stone():
    rnd = random.Random(22)
    s = pygame.Surface((C.TEX_SIZE, C.TEX_SIZE))
    s.fill((42, 48, 60))
    for by in range(0, 64, 16):
        for bx in range(0, 64, 16):
            d = rnd.randint(-12, 12)
            col = (76 + d, 88 + d, 105 + d)
            pygame.draw.rect(s, col, (bx + 1, by + 1, 14, 14))
            pygame.draw.rect(s, (55 + d // 2, 64 + d // 2, 78 + d // 2),
                             (bx + 1, by + 12, 14, 3))
        pygame.draw.rect(s, (30, 34, 44), (0, by, 64, 2))
        pygame.draw.rect(s, (30, 34, 44), (by, 0, 2, 64))
    for _ in range(110):
        x, y = rnd.randrange(64), rnd.randrange(64)
        s.set_at((x, y), rnd.choice([(120, 132, 150), (34, 38, 48)]))
    return s


def _metal():
    rnd = random.Random(33)
    s = pygame.Surface((C.TEX_SIZE, C.TEX_SIZE))
    s.fill((40, 62, 52))
    for bx in range(0, 64, 16):
        pygame.draw.rect(s, (24, 40, 33), (bx, 0, 2, 64))
        pygame.draw.rect(s, (62, 92, 76), (bx + 3, 0, 1, 64))
    pygame.draw.rect(s, (22, 38, 31), (0, 30, 64, 4))
    pygame.draw.rect(s, (70, 105, 88), (0, 29, 64, 1))
    for bx in (4, 20, 36, 52):
        for by in (4, 18, 40, 54):
            pygame.draw.circle(s, (18, 30, 25), (bx + 1, by + 1), 2)
            pygame.draw.circle(s, (150, 180, 160), (bx, by), 1)
    for _ in range(70):
        x, y = rnd.randrange(64), rnd.randrange(64)
        s.set_at((x, y), (28, 46, 38))
    return s


def _tech():
    rnd = random.Random(44)
    s = pygame.Surface((C.TEX_SIZE, C.TEX_SIZE))
    s.fill((52, 24, 30))
    pygame.draw.rect(s, (34, 14, 20), (0, 0, 64, 4))
    pygame.draw.rect(s, (80, 30, 36), (0, 60, 64, 4))
    for _ in range(16):
        x = rnd.randrange(0, 64, 8)
        y = rnd.randrange(0, 64, 8)
        col = rnd.choice([(200, 70, 60), (235, 140, 70), (150, 45, 50)])
        length = rnd.choice([8, 16, 24])
        if rnd.random() < 0.5:
            pygame.draw.line(s, col, (x, y), (min(63, x + length), y), 2)
            pygame.draw.rect(s, col, (min(60, x + length) - 2, y - 2, 5, 5))
        else:
            pygame.draw.line(s, col, (x, y), (x, min(63, y + length)), 2)
            pygame.draw.rect(s, col, (x - 2, min(60, y + length) - 2, 5, 5))
    for _ in range(60):
        x, y = rnd.randrange(64), rnd.randrange(64)
        s.set_at((x, y), (90, 40, 42))
    return s


WALL_BUILDERS = {1: _brick, 2: _stone, 3: _metal, 4: _tech}


# ---------------------------------------------------------------------------
# Sprites
# ---------------------------------------------------------------------------

def _creature(body, head, limb, horn, eye, frame=0, scale=1.0):
    s = pygame.Surface((64, 64), pygame.SRCALPHA)
    gait = 3 if frame == 0 else -3
    arm = 2 if frame == 0 else -2

    # legs
    pygame.draw.rect(s, limb, (19 + gait, 46, 10, 17))
    pygame.draw.rect(s, limb, (35 - gait, 46, 10, 17))
    pygame.draw.rect(s, limb, (17 + gait, 60, 14, 4))
    pygame.draw.rect(s, limb, (33 - gait, 60, 14, 4))

    # torso
    pygame.draw.ellipse(s, body, (13, 25, 38, 29))
    pygame.draw.ellipse(s, head, (24, 33, 16, 16))
    pygame.draw.rect(s, limb, (9 + arm, 29, 11, 19))
    pygame.draw.rect(s, limb, (44 - arm, 29, 11, 19))
    pygame.draw.rect(s, body, (6 + arm, 43, 12, 6))
    pygame.draw.rect(s, body, (46 - arm, 43, 12, 6))

    # head, horns, eyes
    pygame.draw.ellipse(s, head, (19, 8, 26, 23))
    pygame.draw.polygon(s, horn, [(21, 11), (14, 0), (27, 9)])
    pygame.draw.polygon(s, horn, [(43, 11), (50, 0), (37, 9)])
    pygame.draw.rect(s, eye, (25, 18, 6, 5))
    pygame.draw.rect(s, eye, (34, 18, 6, 5))
    pygame.draw.rect(s, (15, 8, 8), (27, 19, 2, 3))
    pygame.draw.rect(s, (15, 8, 8), (37, 19, 2, 3))
    pygame.draw.rect(s, (28, 10, 10), (27, 27, 11, 4))
    pygame.draw.rect(s, (235, 235, 200), (29, 28, 2, 2))
    pygame.draw.rect(s, (235, 235, 200), (35, 28, 2, 2))

    if scale != 1.0:
        w = int(64 * scale)
        h = int(64 * scale)
        s = pygame.transform.scale(s, (w, h))
    return s


def _pickup_base(bg):
    s = pygame.Surface((64, 64), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (0, 0, 0, 90), (12, 52, 40, 8))
    pygame.draw.rect(s, bg, (14, 16, 36, 38))
    pygame.draw.rect(s, (255, 255, 255, 60), (16, 18, 32, 6))
    pygame.draw.rect(s, (0, 0, 0, 90), (14, 48, 36, 6))
    return s


def _health_sprite():
    s = _pickup_base((225, 230, 235))
    pygame.draw.rect(s, (205, 45, 45), (28, 22, 9, 26))
    pygame.draw.rect(s, (205, 45, 45), (20, 30, 25, 9))
    return s


def _armor_sprite():
    s = pygame.Surface((64, 64), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (0, 0, 0, 90), (12, 54, 40, 7))
    pygame.draw.polygon(s, (70, 130, 200), [(20, 14), (44, 14), (52, 30), (46, 52),
                                            (18, 52), (12, 30)])
    pygame.draw.polygon(s, (150, 200, 245), [(24, 18), (40, 18), (45, 30), (40, 46),
                                             (24, 46), (19, 30)])
    pygame.draw.rect(s, (35, 80, 140), (28, 22, 8, 24))
    return s


def _ammo_sprite():
    s = _pickup_base((215, 185, 60))
    for x in (22, 30, 38):
        pygame.draw.rect(s, (110, 80, 35), (x, 20, 5, 22))
        pygame.draw.rect(s, (235, 205, 90), (x, 20, 5, 6))
    pygame.draw.rect(s, (120, 95, 40), (16, 44, 32, 5))
    return s


def _shells_sprite():
    s = _pickup_base((210, 135, 55))
    for x in (22, 30, 38):
        pygame.draw.rect(s, (180, 40, 35), (x, 20, 6, 24))
        pygame.draw.rect(s, (235, 220, 160), (x, 20, 6, 5))
    return s


def _shotgun_sprite():
    s = pygame.Surface((64, 64), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (0, 0, 0, 90), (10, 54, 44, 7))
    pygame.draw.rect(s, (120, 75, 40), (8, 34, 20, 13))
    pygame.draw.rect(s, (95, 60, 32), (8, 40, 16, 8))
    pygame.draw.rect(s, (150, 155, 165), (26, 28, 30, 6))
    pygame.draw.rect(s, (150, 155, 165), (26, 36, 30, 6))
    pygame.draw.rect(s, (60, 62, 70), (52, 28, 5, 14))
    return s


def _chaingun_sprite():
    s = pygame.Surface((64, 64), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (0, 0, 0, 90), (10, 54, 44, 7))
    pygame.draw.rect(s, (60, 66, 74), (10, 28, 26, 22))
    pygame.draw.rect(s, (95, 102, 110), (14, 32, 18, 10))
    for y in (24, 32, 40):
        pygame.draw.rect(s, (150, 155, 165), (34, y, 24, 5))
        pygame.draw.rect(s, (45, 48, 55), (56, y, 4, 5))
    pygame.draw.rect(s, (40, 44, 50), (16, 50, 10, 8))
    return s


def _exit_sprite(open_state):
    """Wall-mounted exit door: barred red when locked, glowing green when open."""
    s = pygame.Surface((64, 96), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (0, 0, 0, 110), (6, 86, 52, 8))
    pygame.draw.rect(s, (58, 52, 46), (6, 4, 52, 86))
    pygame.draw.rect(s, (122, 106, 78), (11, 9, 42, 77))

    if open_state:
        pygame.draw.rect(s, (8, 32, 30), (16, 14, 32, 68))
        pygame.draw.ellipse(s, (45, 220, 150), (16, 12, 32, 26))
        pygame.draw.rect(s, (90, 245, 175), (20, 20, 24, 58))
        pygame.draw.rect(s, (170, 255, 215), (23, 24, 18, 50))
        pygame.draw.circle(s, (225, 255, 235), (32, 18), 5)
        pygame.draw.rect(s, (55, 180, 120), (12, 82, 40, 5))
    else:
        pygame.draw.rect(s, (42, 38, 36), (16, 14, 32, 68))
        for y in (22, 38, 54):
            pygame.draw.rect(s, (145, 45, 40), (18, y, 28, 6))
            pygame.draw.rect(s, (225, 110, 80), (18, y, 28, 2))
        pygame.draw.circle(s, (190, 50, 42), (32, 68), 7)
        pygame.draw.circle(s, (255, 145, 100), (32, 68), 3)
        pygame.draw.rect(s, (90, 40, 35), (12, 82, 40, 5))

    pygame.draw.rect(s, (150, 130, 90), (6, 4, 52, 5))
    return s


def _particle(color, size=8):
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(s, color, (size // 2, size // 2), size // 2)
    pygame.draw.circle(s, (255, 255, 255, 150), (size // 2 - 1, size // 2 - 1), 1)
    return s


# ---------------------------------------------------------------------------
# First-person weapon view models
# ---------------------------------------------------------------------------

def _view_pistol():
    s = pygame.Surface((220, 165), pygame.SRCALPHA)
    pygame.draw.polygon(s, (55, 58, 66), [(80, 165), (150, 165), (140, 70), (95, 70)])
    pygame.draw.rect(s, (85, 90, 100), (98, 26, 34, 55))
    pygame.draw.rect(s, (40, 42, 48), (103, 18, 24, 12))
    pygame.draw.rect(s, (150, 155, 165), (110, 18, 10, 6))
    pygame.draw.polygon(s, (35, 38, 44), ([(78, 80), (98, 70), (96, 128), (72, 138)]))
    pygame.draw.rect(s, (28, 30, 35), (92, 120, 16, 45))
    pygame.draw.rect(s, (120, 124, 132), (130, 60, 8, 40))
    return s


def _view_shotgun():
    s = pygame.Surface((260, 175), pygame.SRCALPHA)
    pygame.draw.rect(s, (125, 72, 38), (92, 120, 58, 55))
    pygame.draw.rect(s, (95, 55, 30), (94, 150, 52, 25))
    pygame.draw.rect(s, (145, 150, 160), (120, 58, 26, 78))
    pygame.draw.rect(s, (175, 180, 190), (122, 44, 10, 90))
    pygame.draw.rect(s, (175, 180, 190), (134, 44, 10, 90))
    pygame.draw.rect(s, (55, 58, 66), (120, 118, 30, 30))
    pygame.draw.rect(s, (70, 74, 82), (98, 126, 34, 34))
    return s


def _view_chaingun():
    """Chunky six-barrel minigun: hub, clustered barrels, ammo box and grips."""
    s = pygame.Surface((260, 190), pygame.SRCALPHA)

    # Grips and trigger housing.
    pygame.draw.rect(s, (35, 38, 44), (88, 150, 26, 40))
    pygame.draw.rect(s, (35, 38, 44), (150, 150, 26, 40))
    pygame.draw.rect(s, (22, 24, 28), (90, 184, 22, 6))
    pygame.draw.rect(s, (22, 24, 28), (152, 184, 22, 6))

    # Ammunition box and feed belt on the left.
    pygame.draw.rect(s, (42, 48, 56), (10, 108, 66, 72))
    pygame.draw.rect(s, (95, 105, 115), (16, 116, 54, 22))
    pygame.draw.rect(s, (150, 145, 60), (18, 146, 50, 8))
    pygame.draw.rect(s, (170, 160, 70), (74, 122, 24, 12))

    # Receiver.
    pygame.draw.rect(s, (58, 64, 72), (70, 118, 120, 72))
    pygame.draw.rect(s, (108, 116, 126), (82, 130, 96, 28))
    pygame.draw.rect(s, (40, 44, 50), (70, 180, 120, 10))

    # Rotating barrel hub.
    pygame.draw.circle(s, (72, 80, 90), (142, 110), 40)
    pygame.draw.circle(s, (125, 133, 145), (142, 110), 28)
    pygame.draw.circle(s, (45, 50, 58), (142, 110), 13)
    for i in range(6):
        a = i * math.tau / 6
        pygame.draw.line(s, (80, 88, 98), (142, 110),
                         (142 + math.cos(a) * 30, 110 + math.sin(a) * 30), 4)

    # Six barrels in a hexagonal cluster. They are foreshortened so the muzzle
    # tips stay below the horizon instead of pointing up into the sky.
    barrels = [(112, 60), (126, 54), (142, 50), (158, 54), (172, 60), (142, 66)]
    for bx, by in barrels:
        pygame.draw.rect(s, (155, 162, 172), (bx - 6, by, 12, 104 - by))
        pygame.draw.rect(s, (95, 102, 112), (bx - 6, by, 4, 104 - by))
    pygame.draw.rect(s, (70, 76, 86), (104, 96, 76, 14))
    return s


# ---------------------------------------------------------------------------
# Asset bundle
# ---------------------------------------------------------------------------

class Assets:
    def __init__(self):
        pygame.font.init()
        self.walls = {}
        for wall_id, builder in WALL_BUILDERS.items():
            self.walls[wall_id] = _shade_variants(builder())

        grunt = [_creature((190, 55, 45), (225, 85, 65), (120, 35, 32),
                           (215, 205, 175), (255, 225, 70), frame=f)
                 for f in (0, 1)]
        brute = [_creature((70, 150, 70), (105, 195, 90), (45, 100, 50),
                           (200, 220, 180), (255, 70, 60), frame=f, scale=1.25)
                 for f in (0, 1)]
        # creatures[kind][frame] -> list of shaded variants
        self.creatures = {
            kind: [_shade_variants(frame) for frame in frames]
            for kind, frames in {"grunt": grunt, "brute": brute}.items()
        }

        self.pickups = {
            "health": _shade_variants(_health_sprite()),
            "armor": _shade_variants(_armor_sprite()),
            "ammo": _shade_variants(_ammo_sprite()),
            "shells": _shade_variants(_shells_sprite()),
            "shotgun": _shade_variants(_shotgun_sprite()),
            "chaingun": _shade_variants(_chaingun_sprite()),
        }

        self.exits = [
            _shade_variants(_exit_sprite(False)),
            _shade_variants(_exit_sprite(True)),
        ]

        self.particles = {
            "spark": _shade_variants(_particle((255, 210, 90), 8)),
            "blood": _shade_variants(_particle((200, 35, 35), 10)),
            "smoke": _shade_variants(_particle((130, 130, 140, 190), 10)),
        }

        self.weapon_views = [
            _view_pistol(),
            _view_shotgun(),
            _view_chaingun(),
        ]

        # Small inventory icons, plus flat black silhouettes for locked weapons.
        self.weapon_icons = []
        self.weapon_silhouettes = []
        for view in self.weapon_views:
            height = 52
            width = max(1, int(view.get_width() * height / view.get_height()))
            icon = pygame.transform.scale(view, (width, height))
            silhouette = icon.copy()
            silhouette.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MULT)
            self.weapon_icons.append(icon)
            self.weapon_silhouettes.append(silhouette)

        self.fonts = {
            "tiny": pygame.font.Font(None, 16),
            "small": pygame.font.Font(None, 19),
            "normal": pygame.font.Font(None, 24),
            "big": pygame.font.Font(None, 34),
            "huge": pygame.font.Font(None, 48),
        }

    @staticmethod
    def shade_index(brightness):
        return max(0, min(C.SHADE_LEVELS - 1,
                          int(brightness * C.SHADE_LEVELS)))
