"""Custom level files: folder management, JSON I/O and validation."""

import json
import re
from pathlib import Path

from . import config as C

_ROOT = Path(__file__).resolve().parent.parent
CUSTOM_DIR = _ROOT / "custom_levels"


def ensure_dir():
    CUSTOM_DIR.mkdir(parents=True, exist_ok=True)
    return CUSTOM_DIR


def custom_files():
    ensure_dir()
    return sorted(CUSTOM_DIR.glob("*.json"))


def sanitize_name(name):
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", str(name)).strip("_")
    return cleaned or "custom_level"


def save_blueprint(name, blueprint):
    ensure_dir()
    filename = sanitize_name(name) + ".json"
    path = CUSTOM_DIR / filename
    data = dict(blueprint)
    data["name"] = str(name).strip() or sanitize_name(name)
    with path.open("w", encoding="utf-8") as fp:
        json.dump(data, fp, indent=2)
        fp.write("\n")
    return path


def load_blueprint(path):
    with Path(path).open(encoding="utf-8") as fp:
        data = json.load(fp)
    if not isinstance(data, dict):
        raise ValueError("Level file must contain a JSON object")
    return data


def validate_blueprint(data):
    """Return (cleaned_blueprint, error_message)."""
    grid = data.get("grid")
    if (not isinstance(grid, list) or len(grid) != C.MAP_H or
            any(not isinstance(row, list) or len(row) != C.MAP_W
                for row in grid)):
        return None, f"Grid must be {C.MAP_W}x{C.MAP_H}"
    try:
        grid = [[max(0, min(4, int(cell))) for cell in row] for row in grid]
    except (TypeError, ValueError):
        return None, "Grid contains invalid cells"

    floors = {(x, y) for y in range(C.MAP_H) for x in range(C.MAP_W)
              if grid[y][x] == 0}
    if len(floors) < 4:
        return None, "Level needs more open floor space"

    def cell_of(value, label):
        if (not isinstance(value, (list, tuple)) or len(value) < 2):
            raise ValueError(f"Invalid {label}")
        x, y = int(value[0]), int(value[1])
        if (x, y) not in floors:
            raise ValueError(f"{label} is inside a wall")
        return x, y

    try:
        spawn = data.get("player_spawn")
        px, py = cell_of(spawn, "player spawn")
        angle = float(spawn[2]) if len(spawn) > 2 else 0.0
        ex, ey = cell_of(data.get("exit"), "exit")

        enemies = []
        for item in data.get("enemy_spawns", []):
            x, y = cell_of(item, "enemy spawn")
            kind = str(item[2]) if len(item) > 2 else "grunt"
            if kind not in ("grunt", "brute"):
                kind = "grunt"
            enemies.append((x + 0.5, y + 0.5, kind))

        pickups = []
        for item in data.get("pickup_spawns", []):
            x, y = cell_of(item, "pickup spawn")
            kind = str(item[2]) if len(item) > 2 else "health"
            if kind not in C.PICKUP_INFO:
                kind = "health"
            pickups.append((x + 0.5, y + 0.5, kind))
    except (TypeError, ValueError, IndexError) as exc:
        return None, str(exc)

    if (px, py) == (ex, ey):
        return None, "Player spawn and exit must be different cells"

    # The exit must be reachable from the spawn.
    seen = {(px, py)}
    queue = [(px, py)]
    while queue:
        x, y = queue.pop(0)
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if (nx, ny) in seen or (nx, ny) not in floors:
                continue
            seen.add((nx, ny))
            queue.append((nx, ny))
    if (ex, ey) not in seen:
        return None, "Exit is not reachable from the player spawn"

    # Every imp must be killable or the exit can never unlock.
    for ex, ey, _ in enemies:
        if (int(ex), int(ey)) not in seen:
            return None, "An enemy spawn is unreachable from the player spawn"

    cleaned = {
        "name": str(data.get("name", "CUSTOM LEVEL")).strip()[:40] or "CUSTOM LEVEL",
        "theme": str(data.get("theme", "mixed")),
        "grid": grid,
        "preserve_grid": True,
        "rooms": [],
        "corridors": [],
        "blocks": [],
        "player_spawn": (px + 0.5, py + 0.5, angle),
        "enemy_spawns": enemies,
        "pickup_spawns": pickups,
        "exit": (ex + 0.5, ey + 0.5),
    }
    cleaned["enemies"] = len(enemies)
    return cleaned, None
