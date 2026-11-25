"""Dungeon layouts, procedural random levels, collision and ray casting."""

import math
import random

from . import config as C


# ---------------------------------------------------------------------------
# Prebuilt campaign blueprints (each has a genuinely different shape)
# ---------------------------------------------------------------------------

BLUEPRINTS = [
    {
        "name": "THE CROSSING",
        "theme": "dungeon",
        "rooms": [
            (2, 2, 8, 7), (15, 2, 21, 7),
            (2, 16, 8, 21), (15, 16, 21, 21),
            (9, 9, 14, 14),
        ],
        "corridors": [
            (8, 4, 8, 9), (8, 9, 9, 9),
            (15, 4, 15, 9), (14, 9, 15, 9),
            (5, 7, 5, 16), (18, 7, 18, 16),
            (8, 11, 9, 11), (14, 11, 15, 11),
            (8, 18, 15, 18),
        ],
        "blocks": [(5, 4, 5, 4), (18, 19, 18, 19),
                   (11, 11, 11, 11), (12, 12, 12, 12)],
        "enemies": 7,
        "exit": (21.5, 21.5),
        "pickups": ["health", "ammo", "shells", "health", "shotgun",
                    "armor", "ammo", "health", "shells"],
    },
    {
        "name": "THE VAULTS",
        "theme": "tech",
        "rooms": [
            (2, 10, 21, 13),
            (2, 2, 7, 7), (9, 2, 14, 7), (16, 2, 21, 7),
            (2, 16, 7, 21), (9, 16, 14, 21), (16, 16, 21, 21),
        ],
        "corridors": [
            (4, 7, 4, 10), (11, 7, 11, 10), (18, 7, 18, 10),
            (4, 13, 4, 16), (11, 13, 11, 16), (18, 13, 18, 16),
        ],
        "blocks": [(10, 11, 10, 12), (13, 11, 13, 12)],
        "enemies": 8,
        "exit": (2.5, 2.5),
        "pickups": ["health", "ammo", "shells", "armor", "health",
                    "shotgun", "ammo", "shells", "health", "armor"],
    },
    {
        "name": "THE SPIRAL",
        "theme": "ruins",
        "rooms": [
            (2, 2, 6, 5), (17, 2, 21, 6),
            (2, 18, 6, 21), (17, 18, 21, 21),
            (9, 10, 13, 14),
        ],
        "corridors": [
            (2, 2, 21, 3), (20, 2, 21, 21), (2, 20, 21, 21), (2, 3, 3, 21),
            (2, 5, 18, 6), (17, 5, 18, 18), (5, 18, 18, 19), (5, 6, 6, 18),
            (5, 8, 15, 9), (14, 8, 15, 15), (8, 15, 15, 16), (8, 9, 9, 15),
            (8, 11, 12, 12),
        ],
        "blocks": [(10, 11, 10, 11), (12, 13, 12, 13)],
        "enemies": 9,
        "exit": (21.5, 21.5),
        "pickups": ["health", "ammo", "shells", "health", "shotgun",
                    "armor", "ammo", "health", "shells", "ammo"],
    },
    {
        "name": "THE ARENA",
        "theme": "metal",
        "rooms": [
            (2, 2, 21, 3), (2, 20, 21, 21),
            (2, 2, 3, 21), (20, 2, 21, 21),
            (5, 5, 18, 18),
        ],
        "corridors": [
            (11, 3, 12, 5), (11, 18, 12, 20),
            (3, 11, 5, 12), (18, 11, 20, 12),
        ],
        "blocks": [
            (8, 8, 10, 9), (14, 14, 16, 15),
            (8, 14, 10, 15), (14, 8, 16, 9),
        ],
        "enemies": 10,
        "exit": (2.5, 21.5),
        "pickups": ["health", "ammo", "shells", "armor", "health",
                    "shotgun", "ammo", "health", "shells", "chaingun", "armor"],
    },
    {
        "name": "FORTRESS",
        "theme": "tech",
        "rooms": [
            (2, 2, 10, 8), (13, 2, 21, 6), (16, 8, 21, 15),
            (8, 12, 15, 21), (2, 16, 7, 21), (2, 10, 6, 14),
        ],
        "corridors": [
            (10, 4, 13, 4), (17, 6, 17, 8), (15, 12, 16, 12),
            (7, 18, 8, 18), (4, 8, 4, 10), (6, 14, 6, 16),
            (10, 8, 10, 10), (10, 10, 13, 10), (13, 10, 13, 12),
        ],
        "blocks": [(5, 5, 5, 5), (18, 11, 18, 11), (11, 16, 11, 16)],
        "enemies": 10,
        "exit": (15.5, 21.5),
        "pickups": ["health", "ammo", "shells", "armor", "health",
                    "shotgun", "ammo", "chaingun", "health", "shells", "armor"],
    },
]


# ---------------------------------------------------------------------------
# Level construction helpers
# ---------------------------------------------------------------------------

def _blank_grid():
    return [[1] * C.MAP_W for _ in range(C.MAP_H)]


def _carve(grid, rect):
    x0, y0, x1, y1 = rect
    for y in range(max(0, y0), min(C.MAP_H, y1 + 1)):
        for x in range(max(0, x0), min(C.MAP_W, x1 + 1)):
            grid[y][x] = 0


def _fill(grid, rect, value=4):
    x0, y0, x1, y1 = rect
    for y in range(max(0, y0), min(C.MAP_H, y1 + 1)):
        for x in range(max(0, x0), min(C.MAP_W, x1 + 1)):
            grid[y][x] = value


def _apply_theme(grid, theme):
    for y in range(C.MAP_H):
        for x in range(C.MAP_W):
            if grid[y][x] == 0:
                continue
            if theme == "dungeon":
                if 8 <= x <= 15 and 8 <= y <= 15:
                    value = 4
                elif y <= 8:
                    value = 1
                elif y <= 16:
                    value = 2
                else:
                    value = 3
            elif theme == "tech":
                value = 4 if (x // 4 + y // 5) % 4 else 2
            elif theme == "ruins":
                value = 1 if (x // 5 + y // 4) % 3 else 2
            elif theme == "metal":
                value = 3 if (x // 6 + y // 6) % 4 else 4
            else:
                value = 1 + (x // 5 + y // 5) % 4
            grid[y][x] = value


def _center_of(rect):
    x0, y0, x1, y1 = rect
    return ((x0 + x1) / 2 + 0.5, (y0 + y1) / 2 + 0.5)


def _position_is_free(grid, x, y, radius):
    """Check every collision corner, not just the center cell."""
    for dx in (-radius, radius):
        for dy in (-radius, radius):
            mx, my = int(x + dx), int(y + dy)
            if mx < 0 or my < 0 or mx >= C.MAP_W or my >= C.MAP_H:
                return False
            if grid[my][mx] != 0:
                return False
    return True


def _pick_spawns(grid, blueprint, rnd, stage):
    floors = [(x, y) for y in range(C.MAP_H) for x in range(C.MAP_W)
              if grid[y][x] == 0]

    rooms = blueprint.get("rooms") or []
    if rooms:
        px, py = _center_of(rooms[0])
    else:
        px, py = (floors[0][0] + 0.5, floors[0][1] + 0.5)

    # A room center can land on a cell boundary (e.g. y=5.0) where the player's
    # collision radius clips an adjacent wall/pillar. Snap to the nearest
    # floor-cell center that leaves the whole body clear.
    radius = C.PLAYER_RADIUS + 0.08
    if floors and not _position_is_free(grid, px, py, radius):
        ordered = sorted(floors, key=lambda c: (c[0] + 0.5 - px) ** 2 +
                                               (c[1] + 0.5 - py) ** 2)
        for cell in ordered:
            cx, cy = cell[0] + 0.5, cell[1] + 0.5
            if _position_is_free(grid, cx, cy, radius):
                px, py = cx, cy
                break
        else:
            cx, cy = floors[0]
            px, py = cx + 0.5, cy + 0.5

    # Face the most distant reachable floor cell so the opening view is interesting.
    farthest = max(floors, key=lambda c: (c[0] + 0.5 - px) ** 2 +
                                         (c[1] + 0.5 - py) ** 2)
    angle = math.atan2(farthest[1] + 0.5 - py, farthest[0] + 0.5 - px)
    player_spawn = (px, py, angle)

    def free(cell, others, spacing):
        return all((cell[0] - o[0]) ** 2 + (cell[1] - o[1]) ** 2 >= spacing ** 2
                   for o in others)

    exit_pos = blueprint.get("exit")
    candidates = [c for c in floors
                  if math.hypot(c[0] + 0.5 - px, c[1] + 0.5 - py) >= 4.5
                  and (c[0] + 0.5, c[1] + 0.5) != exit_pos]
    rnd.shuffle(candidates)

    enemy_cells = []
    for cell in candidates:
        if len(enemy_cells) >= blueprint.get("enemies", 6):
            break
        if free(cell, [player_spawn[:2]] + enemy_cells, 2.2):
            enemy_cells.append(cell)

    brute_chance = min(0.45, 0.05 + stage * 0.09)
    enemy_spawns = []
    for cell in enemy_cells:
        kind = "brute" if rnd.random() < brute_chance else "grunt"
        enemy_spawns.append((cell[0] + 0.5, cell[1] + 0.5, kind))

    used = enemy_cells[:]
    pickup_cells = []
    for cell in candidates:
        if len(pickup_cells) >= len(blueprint.get("pickups", [])):
            break
        if free(cell, [player_spawn[:2]] + used + pickup_cells, 1.6):
            pickup_cells.append(cell)
    pickup_spawns = [(cell[0] + 0.5, cell[1] + 0.5, kind)
                     for cell, kind in zip(pickup_cells, blueprint.get("pickups", []))]

    return player_spawn, enemy_spawns, pickup_spawns


def build_level(blueprint, stage=0, seed=None):
    """Create a playable Level from a blueprint dict."""
    rnd = random.Random(seed if seed is not None else
                        sum(ord(ch) for ch in blueprint["name"]) + stage * 977)
    if blueprint.get("grid") is not None:
        # Random levels hand us their fully carved grid (corridors included).
        grid = [row[:] for row in blueprint["grid"]]
    else:
        grid = _blank_grid()
        for rect in blueprint.get("rooms", []):
            _carve(grid, rect)
        for rect in blueprint.get("corridors", []):
            _carve(grid, rect)
    if not blueprint.get("preserve_grid"):
        _apply_theme(grid, blueprint.get("theme", "dungeon"))
    for rect in blueprint.get("blocks", []):
        _fill(grid, rect, 4)

    if blueprint.get("player_spawn") is not None:
        player = tuple(blueprint["player_spawn"])
    else:
        player = None

    if (blueprint.get("enemy_spawns") is not None and
            blueprint.get("pickup_spawns") is not None):
        enemies = [tuple(e) for e in blueprint["enemy_spawns"]]
        pickups = [tuple(p) for p in blueprint["pickup_spawns"]]
        if player is None:
            player, _, _ = _pick_spawns(grid, blueprint, rnd, stage)
    else:
        generated, enemies, pickups = _pick_spawns(grid, blueprint, rnd, stage)
        player = player or generated

    return Level(blueprint["name"], grid, player, enemies, pickups,
                 blueprint.get("exit"))


def generate_random_blueprint(seed=None):
    """Procedurally generate a connected, non-grid-shaped dungeon."""
    rnd = random.Random(seed)
    grid = _blank_grid()
    rooms = []
    for _ in range(240):
        if len(rooms) >= rnd.randint(7, 10):
            break
        w, h = rnd.randint(3, 7), rnd.randint(3, 7)
        x = rnd.randint(1, C.MAP_W - w - 2)
        y = rnd.randint(1, C.MAP_H - h - 2)
        rect = (x, y, x + w - 1, y + h - 1)
        if any(not (rect[2] < r[0] - 1 or rect[0] > r[2] + 1 or
                    rect[3] < r[1] - 1 or rect[1] > r[3] + 1) for r in rooms):
            continue
        rooms.append(rect)
        _carve(grid, rect)

    if not rooms:
        rooms = [(3, 3, 10, 10)]
        _carve(grid, rooms[0])

    # Connect every room to its nearest already-connected room.
    for i in range(1, len(rooms)):
        ax, ay = _center_of(rooms[i])
        bx, by = min((_center_of(r) for r in rooms[:i]),
                     key=lambda c: (c[0] - ax) ** 2 + (c[1] - ay) ** 2)
        ix, iy = int(ax), int(ay)
        jx, jy = int(bx), int(by)
        if rnd.random() < 0.5:
            _carve(grid, (min(ix, jx), iy, max(ix, jx), iy))
            _carve(grid, (jx, min(iy, jy), jx, max(iy, jy)))
        else:
            _carve(grid, (ix, min(iy, jy), ix, max(iy, jy)))
            _carve(grid, (min(ix, jx), jy, max(ix, jx), jy))

    # A couple of extra connections make loops instead of a pure tree.
    for _ in range(2 if len(rooms) > 1 else 0):
        a, b = rnd.sample(rooms, 2)
        ax, ay = _center_of(a)
        bx, by = _center_of(b)
        ix, iy, jx, jy = int(ax), int(ay), int(bx), int(by)
        _carve(grid, (min(ix, jx), iy, max(ix, jx), iy))
        _carve(grid, (jx, min(iy, jy), jx, max(iy, jy)))

    # Scatter a few pillars inside the bigger rooms.
    blocks = []
    for rect in rooms:
        if rect[2] - rect[0] >= 5 and rnd.random() < 0.65:
            x = rnd.randint(rect[0] + 1, rect[2] - 1)
            y = rnd.randint(rect[1] + 1, rect[3] - 1)
            blocks.append((x, y, x, y))

    # Put the exit in a far, low-connectivity corner so the locked door never
    # cuts off the rest of the level.
    floors = [(x, y) for y in range(C.MAP_H) for x in range(C.MAP_W)
              if grid[y][x] == 0]
    origin = _center_of(rooms[0])
    def connections(cell):
        x, y = cell
        return sum(grid[ny][nx] == 0 for nx, ny in
                   ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))
                   if 0 <= nx < C.MAP_W and 0 <= ny < C.MAP_H)
    edge_cells = [c for c in floors if connections(c) <= 2] or floors
    exit_cell = max(edge_cells, key=lambda c: (c[0] + 0.5 - origin[0]) ** 2 +
                                              (c[1] + 0.5 - origin[1]) ** 2)
    exit_pos = (exit_cell[0] + 0.5, exit_cell[1] + 0.5)
    blocks = [b for b in blocks if not (b[0] == exit_cell[0] and
                                        b[1] == exit_cell[1])]

    theme = rnd.choice(["dungeon", "tech", "ruins", "metal", "mixed"])
    count = len(floors)
    return {
        "name": f"RANDOM {rnd.randrange(1000, 9999)}",
        "theme": theme,
        "rooms": rooms,
        "corridors": [],
        "grid": grid,
        "blocks": blocks,
        "enemies": min(11, max(5, count // 16)),
        "exit": exit_pos,
        "pickups": ["health", "ammo", "shells", "health", "shotgun",
                    "armor", "ammo", "shells", "health", "chaingun"],
    }


# ---------------------------------------------------------------------------
# Level object
# ---------------------------------------------------------------------------

class Level:
    def __init__(self, name, grid, player_spawn, enemy_spawns, pickup_spawns,
                 exit_pos=None):
        self.name = name
        self.grid = grid
        self.player_spawn = player_spawn
        self.enemy_spawns = enemy_spawns
        self.pickup_spawns = pickup_spawns
        self.exit = exit_pos
        self.exit_open = False
        self.visited = set()

    # -- grid queries -------------------------------------------------------

    def is_wall_cell(self, mx, my):
        if mx < 0 or my < 0 or mx >= C.MAP_W or my >= C.MAP_H:
            return True
        return self.grid[my][mx] != 0

    def solid_at(self, x, y):
        return self.is_wall_cell(int(x), int(y))

    def can_occupy(self, x, y, radius):
        for dx in (-radius, radius):
            for dy in (-radius, radius):
                if self.solid_at(x + dx, y + dy):
                    return False
                # The exit is a solid door until every imp is dead.
                if self.exit and not self.exit_open:
                    ex, ey = self.exit
                    if abs(x + dx - ex) < 0.42 and abs(y + dy - ey) < 0.42:
                        return False
        return True

    def open_exit(self):
        self.exit_open = True

    def at_exit(self, x, y):
        return bool(self.exit) and math.hypot(x - self.exit[0],
                                              y - self.exit[1]) < 0.5

    def move(self, x, y, dx, dy, radius):
        """Move with simple axis-separated sliding collision."""
        nx = x + dx
        if self.can_occupy(nx, y, radius):
            x = nx
        ny = y + dy
        if self.can_occupy(x, ny, radius):
            y = ny
        return x, y

    # -- ray casting --------------------------------------------------------

    def ray_cast(self, px, py, dx, dy, max_dist=C.MAX_VIEW_DIST):
        """Return (distance, wall_type, side) for a normalized direction."""
        map_x, map_y = int(px), int(py)
        delta_x = 1e30 if dx == 0 else abs(1.0 / dx)
        delta_y = 1e30 if dy == 0 else abs(1.0 / dy)

        if dx < 0:
            step_x = -1
            side_x = (px - map_x) * delta_x
        else:
            step_x = 1
            side_x = (map_x + 1 - px) * delta_x

        if dy < 0:
            step_y = -1
            side_y = (py - map_y) * delta_y
        else:
            step_y = 1
            side_y = (map_y + 1 - py) * delta_y

        side = 0
        while True:
            if side_x < side_y:
                side_x += delta_x
                map_x += step_x
                side = 0
                distance = side_x - delta_x
            else:
                side_y += delta_y
                map_y += step_y
                side = 1
                distance = side_y - delta_y

            if distance > max_dist:
                return max_dist, 0, side
            if self.is_wall_cell(map_x, map_y):
                wall = self.grid[map_y][map_x] if (
                    0 <= map_x < C.MAP_W and 0 <= map_y < C.MAP_H) else 1
                return distance, wall, side

    def line_of_sight(self, x1, y1, x2, y2):
        dx, dy = x2 - x1, y2 - y1
        length = math.hypot(dx, dy)
        if length < 1e-6:
            return True
        dx, dy = dx / length, dy / length
        distance, _, _ = self.ray_cast(x1, y1, dx, dy, max_dist=length)
        return distance >= length - 0.05

    def find_path(self, sx, sy, tx, ty):
        """Breadth-first path to (tx, ty) as floor-cell centers.

        Returns [] when no route exists. The final waypoint is replaced with
        the exact target position so enemies arrive smoothly at the player.
        """
        from collections import deque

        start = (int(sx), int(sy))
        goal = (int(tx), int(ty))
        if self.is_wall_cell(*start) or self.is_wall_cell(*goal):
            return []
        if start == goal:
            return [(tx, ty)]

        previous = {start: None}
        queue = deque([start])
        found = False
        while queue and not found:
            x, y = queue.popleft()
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if (nx, ny) in previous or self.is_wall_cell(nx, ny):
                    continue
                previous[(nx, ny)] = (x, y)
                if (nx, ny) == goal:
                    found = True
                    break
                queue.append((nx, ny))

        if goal not in previous:
            return []

        cells = []
        cell = goal
        while cell != start:
            cells.append(cell)
            cell = previous[cell]
        cells.reverse()

        path = [(x + 0.5, y + 0.5) for x, y in cells]
        path[-1] = (tx, ty)
        return path

    # -- map discovery ------------------------------------------------------

    def mark_visited(self, px, py, radius=5.5):
        cx, cy = int(px), int(py)
        r = int(radius) + 1
        r2 = radius * radius
        for y in range(cy - r, cy + r + 1):
            for x in range(cx - r, cx + r + 1):
                if 0 <= x < C.MAP_W and 0 <= y < C.MAP_H:
                    if (x + 0.5 - px) ** 2 + (y + 0.5 - py) ** 2 <= r2:
                        self.visited.add((x, y))
