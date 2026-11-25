"""Central configuration and game balance constants."""

import math

# --- Internal render resolution (scaled up to the window for a retro look) ---
VIEW_W = 480
VIEW_H = 300
SCALE = 2
WIN_W = VIEW_W * SCALE
WIN_H = VIEW_H * SCALE

# --- Field of view ---
FOV = math.radians(66)
PLANE_LEN = math.tan(FOV / 2.0)

# --- World / textures ---
MAP_W = 24
MAP_H = 24
TEX_SIZE = 64
SHADE_LEVELS = 16
MAX_VIEW_DIST = 32.0

# --- Side windows ---
MINIMAP_W = 280
MINIMAP_H = 280
INVENTORY_W = 600
INVENTORY_H = 560

# --- Player / movement ---
PLAYER_RADIUS = 0.22
WALK_SPEED = 3.2
RUN_MULT = 1.7
MOUSE_SENSITIVITY = 0.0024
KEY_TURN_SPEED = 2.4
MAX_HEALTH = 100
MAX_ARMOR = 100
ARMOR_ABSORB = 0.4  # fraction of damage absorbed by armor
MEDKIT_HEAL = 28
ARMOR_BOOST = 35
MAX_MEDKITS = 6
MAX_ARMOR_KITS = 6

FPS = 60

# --- Wall appearance by type ---
WALL_COLORS = {
    1: (120, 55, 45),   # brick
    2: (80, 95, 120),   # stone
    3: (60, 110, 85),   # metal
    4: (140, 55, 60),   # tech
}

# --- Weapons: indexable, first is the starter ---
WEAPONS = [
    {
        "name": "PISTOL",
        "ammo": "bullets",
        "damage": 24,
        "cooldown": 0.30,
        "spread": 0.010,
        "pellets": 1,
        "range": 20.0,
        "kick": 5,
        "auto": False,
    },
    {
        "name": "SHOTGUN",
        "ammo": "shells",
        "damage": 12,
        "cooldown": 0.78,
        "spread": 0.085,
        "pellets": 8,
        "range": 13.0,
        "kick": 13,
        "auto": False,
    },
    {
        "name": "CHAINGUN",
        "ammo": "bullets",
        "damage": 11,
        "cooldown": 0.09,
        "spread": 0.038,
        "pellets": 1,
        "range": 22.0,
        "kick": 3,
        "auto": True,
    },
]

# --- Enemy awareness / radar ---
ENEMY_FOV = math.radians(140)      # enemies only notice the player inside this cone
ENEMY_MAP_RANGE = 8.0             # radar only reveals enemies within this distance
PATH_RECALC_INTERVAL = 0.35       # seconds between A* path refreshes

# --- Enemy archetypes ---
ENEMY_TYPES = {
    "grunt": {
        "name": "IMP",
        "hp": 50,
        "speed": 1.75,
        "damage": 9,
        "radius": 0.27,
        "scale": 0.95,
        "sight": 11.0,
        "score": 100,
        "color": (210, 70, 55),
    },
    "brute": {
        "name": "BARON",
        "hp": 140,
        "speed": 1.15,
        "damage": 19,
        "radius": 0.38,
        "scale": 1.35,
        "sight": 12.0,
        "score": 400,
        "color": (90, 190, 90),
    },
}

# --- Pickup effect tables ---
PICKUP_INFO = {
    "health": {"label": "MEDKIT", "color": (230, 235, 240)},
    "armor": {"label": "ARMOR", "color": (90, 170, 230)},
    "ammo": {"label": "AMMO BOX", "color": (230, 200, 70)},
    "shells": {"label": "SHELLS", "color": (240, 150, 60)},
    "shotgun": {"label": "SHOTGUN", "color": (190, 150, 90)},
    "chaingun": {"label": "CHAINGUN", "color": (150, 160, 170)},
}
