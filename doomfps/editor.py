"""Grid-based level editor drawn in the main window."""

import math

import pygame

from . import config as C
from . import custom

GRID_X, GRID_Y, CELL = 20, 60, 22
THEMES = ["dungeon", "tech", "ruins", "metal", "mixed"]

TOOLS = [
    ("floor", "FLOOR", (60, 62, 68)),
    ("wall", "WALL", (120, 70, 60)),
    ("player", "PLAYER", (255, 225, 70)),
    ("exit", "EXIT", (90, 240, 150)),
    ("grunt", "IMP", (220, 80, 65)),
    ("brute", "BARON", (95, 200, 100)),
    ("health", "MEDKIT", (230, 235, 240)),
    ("armor", "ARMOR", (90, 170, 230)),
    ("ammo", "BULLETS", (215, 185, 60)),
    ("shells", "SHELLS", (240, 150, 60)),
    ("shotgun", "SHOTGUN", (190, 150, 90)),
    ("chaingun", "CHAINGUN", (150, 160, 170)),
]


class LevelEditor:
    def __init__(self, assets):
        self.assets = assets
        self.close_requested = False
        self.tool_buttons = []
        self.action_buttons = {}
        self._build_button_rects()
        self.reset()

    def _build_button_rects(self):
        self.tool_buttons = []
        for i, (kind, label, color) in enumerate(TOOLS):
            col, row = i % 2, i // 2
            rect = (578 + col * 186, 96 + row * 40, 178, 34)
            self.tool_buttons.append((pygame.Rect(rect), kind, label, color))
        self.name_rect = pygame.Rect(578, 356, 364, 34)
        self.action_buttons = {
            "style": pygame.Rect(578, 400, 176, 34),
            "save": pygame.Rect(770, 400, 172, 34),
            "test": pygame.Rect(578, 442, 176, 34),
            "new": pygame.Rect(770, 442, 172, 34),
            "back": pygame.Rect(578, 514, 364, 38),
        }

    # -- state ---------------------------------------------------------------

    def reset(self):
        self.grid = [[1] * C.MAP_W for _ in range(C.MAP_H)]
        for y in range(3, 11):
            for x in range(3, 12):
                self.grid[y][x] = 0
        self.player_spawn = (4.5, 4.5, 0.0)
        self.exit = (11.5, 10.5)
        self.enemies = []
        self.pickups = []
        self.name = "MY LEVEL"
        self.theme_index = 0
        self.wall_type = 1
        self.tool = "floor"
        self.editing_name = False
        self.hovered = None
        self.message = "Paint the grid, then SAVE or TEST. Right-click/drag erases."
        self.close_requested = False

    def to_blueprint(self):
        return {
            "name": self.name.strip() or "CUSTOM LEVEL",
            "theme": THEMES[self.theme_index],
            "grid": [row[:] for row in self.grid],
            "preserve_grid": True,
            "rooms": [],
            "corridors": [],
            "blocks": [],
            "player_spawn": [int(self.player_spawn[0]),
                             int(self.player_spawn[1]),
                             self.player_spawn[2]],
            "exit": [int(self.exit[0]), int(self.exit[1])] if self.exit else None,
            "enemy_spawns": [[int(x), int(y), kind]
                             for x, y, kind in self.enemies],
            "pickup_spawns": [[int(x), int(y), kind]
                              for x, y, kind in self.pickups],
        }

    # -- painting ------------------------------------------------------------

    def _cell_at(self, pos):
        x = (pos[0] - GRID_X) // CELL
        y = (pos[1] - GRID_Y) // CELL
        if 0 <= x < C.MAP_W and 0 <= y < C.MAP_H:
            return x, y
        return None

    def _clear_cell(self, x, y):
        self.enemies = [e for e in self.enemies if int(e[0]) != x or int(e[1]) != y]
        self.pickups = [p for p in self.pickups if int(p[0]) != x or int(p[1]) != y]
        if self.exit and int(self.exit[0]) == x and int(self.exit[1]) == y:
            self.exit = None
        if int(self.player_spawn[0]) == x and int(self.player_spawn[1]) == y:
            self.message = "Player spawn stays there - place it elsewhere first."

    def apply_tool(self, cell, erase=False):
        x, y = cell
        if self.editing_name:
            return

        if erase or self.tool == "floor":
            self.grid[y][x] = 0
            self._clear_cell(x, y)
            return

        if self.tool == "wall":
            self.grid[y][x] = self.wall_type
            self._clear_cell(x, y)
            return

        if self.grid[y][x] != 0:
            self.message = "Carve floor here first."
            return

        wx, wy = x + 0.5, y + 0.5
        if self.tool == "player":
            self.player_spawn = (wx, wy, self.player_spawn[2])
        elif self.tool == "exit":
            self.exit = (wx, wy)
        elif self.tool in ("grunt", "brute"):
            self.enemies = [e for e in self.enemies
                            if not (int(e[0]) == x and int(e[1]) == y)]
            if len(self.enemies) < 24:
                self.enemies.append((wx, wy, self.tool))
        else:
            self.pickups = [p for p in self.pickups
                            if not (int(p[0]) == x and int(p[1]) == y)]
            if len(self.pickups) < 32:
                self.pickups.append((wx, wy, self.tool))

    # -- actions -------------------------------------------------------------

    def _validated(self):
        blueprint, error = custom.validate_blueprint(self.to_blueprint())
        if error:
            self.message = f"INVALID: {error}"
            return None
        return blueprint

    def save(self):
        blueprint = self._validated()
        if blueprint is None:
            return
        path = custom.save_blueprint(self.name, blueprint)
        self.message = f"SAVED: {path.name}"

    def test(self, game):
        blueprint = self._validated()
        if blueprint is None:
            return
        game.play_custom_blueprint(blueprint, origin="editor")
        self.message = "TESTING LEVEL"

    # -- input ---------------------------------------------------------------

    def handle_event(self, event, game):
        """Return True when the editor consumed the event."""
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self._cell_at(event.pos)
            if self.hovered:
                buttons = getattr(event, "buttons", (0, 0, 0))
                if buttons[0]:
                    self.apply_tool(self.hovered)
                elif buttons[2]:
                    self.apply_tool(self.hovered, erase=True)
            return True

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                if self.name_rect.collidepoint(event.pos):
                    self.editing_name = True
                    return True
                self.editing_name = False
                for rect, kind, _, _ in self.tool_buttons:
                    if rect.collidepoint(event.pos):
                        self.tool = kind
                        self.message = f"TOOL: {kind.upper()}"
                        return True
                actions = self.action_buttons
                if actions["style"].collidepoint(event.pos):
                    self.wall_type = self.wall_type % 4 + 1
                    self.message = f"WALL STYLE: {self.wall_type}"
                    return True
                if actions["save"].collidepoint(event.pos):
                    self.save()
                    return True
                if actions["test"].collidepoint(event.pos):
                    self.test(game)
                    return True
                if actions["new"].collidepoint(event.pos):
                    self.reset()
                    return True
                if actions["back"].collidepoint(event.pos):
                    self.close_requested = True
                    return True
                cell = self._cell_at(event.pos)
                if cell:
                    self.apply_tool(cell)
                    return True
            elif event.button == 3:
                cell = self._cell_at(event.pos)
                if cell:
                    self.apply_tool(cell, erase=True)
                    return True

        if event.type == pygame.KEYDOWN:
            if self.editing_name:
                if event.key == pygame.K_RETURN:
                    self.editing_name = False
                elif event.key == pygame.K_ESCAPE:
                    self.editing_name = False
                elif event.key == pygame.K_BACKSPACE:
                    self.name = self.name[:-1]
                else:
                    char = getattr(event, "unicode", "")
                    if char and char.isprintable() and len(self.name) < 28:
                        self.name += char
                return True
            if (event.key == pygame.K_s and
                    getattr(event, "mod", 0) & pygame.KMOD_CTRL):
                self.save()
                return True
        return False

    # -- drawing -------------------------------------------------------------

    def draw(self, surface):
        fonts = self.assets.fonts
        surface.fill((10, 12, 16))

        title = fonts["big"].render("LEVEL EDITOR", True, (235, 190, 90))
        surface.blit(title, (GRID_X, 14))
        hint = fonts["tiny"].render(
            "Click/drag to paint  -  Right-click/drag to erase  -  Ctrl+S to save",
            True, (150, 155, 165))
        surface.blit(hint, (GRID_X + 260, 26))

        # Grid.
        for y in range(C.MAP_H):
            for x in range(C.MAP_W):
                value = self.grid[y][x]
                color = (34, 36, 42) if value == 0 else C.WALL_COLORS.get(
                    value, (110, 110, 110))
                pygame.draw.rect(surface, color,
                                 (GRID_X + x * CELL, GRID_Y + y * CELL,
                                  CELL, CELL))
                pygame.draw.rect(surface, (18, 19, 23),
                                 (GRID_X + x * CELL, GRID_Y + y * CELL,
                                  CELL, CELL), 1)

        if self.hovered:
            hx, hy = self.hovered
            pygame.draw.rect(surface, (255, 255, 255),
                             (GRID_X + hx * CELL, GRID_Y + hy * CELL,
                              CELL, CELL), 1)

        # Exit marker.
        if self.exit:
            ex = GRID_X + int(self.exit[0]) * CELL
            ey = GRID_Y + int(self.exit[1]) * CELL
            pygame.draw.rect(surface, (90, 240, 150),
                             (ex + 3, ey + 3, CELL - 6, CELL - 6))
            pygame.draw.rect(surface, (235, 255, 240),
                             (ex + 3, ey + 3, CELL - 6, CELL - 6), 1)

        # Spawns.
        for px, py, kind in self.pickups:
            color = C.PICKUP_INFO[kind]["color"]
            surface.fill(color, (GRID_X + int(px) * CELL + 6,
                                 GRID_Y + int(py) * CELL + 6, 10, 10))
        for ex, ey, kind in self.enemies:
            color = (230, 80, 65) if kind == "grunt" else (95, 200, 100)
            pygame.draw.circle(surface, color,
                               (GRID_X + int(ex) * CELL + CELL // 2,
                                GRID_Y + int(ey) * CELL + CELL // 2), 7)

        sx = GRID_X + int(self.player_spawn[0]) * CELL + CELL // 2
        sy = GRID_Y + int(self.player_spawn[1]) * CELL + CELL // 2
        a = self.player_spawn[2]
        tip = (sx + math.cos(a) * 11, sy + math.sin(a) * 11)
        left = (sx + math.cos(a + 2.5) * 9, sy + math.sin(a + 2.5) * 9)
        right = (sx + math.cos(a - 2.5) * 9, sy + math.sin(a - 2.5) * 9)
        pygame.draw.polygon(surface, (255, 225, 70), [tip, left, right])

        # Toolbar.
        pygame.draw.rect(surface, (20, 23, 29), (566, 60, 374, 528))
        pygame.draw.rect(surface, (95, 85, 60), (566, 60, 374, 528), 1)
        surface.blit(fonts["small"].render("TOOLS", True, (225, 200, 130)),
                     (578, 70))

        for rect, kind, label, color in self.tool_buttons:
            active = kind == self.tool
            bg = (52, 48, 40) if active else (30, 33, 39)
            pygame.draw.rect(surface, bg, rect)
            pygame.draw.rect(surface, color if active else (70, 73, 80), rect, 1)
            text = fonts["tiny"].render(label, True,
                                        color if active else (190, 192, 198))
            surface.blit(text, (rect.x + 8, rect.y + 9))

        surface.blit(fonts["tiny"].render("LEVEL NAME", True, (200, 195, 180)),
                     (578, 334))
        pygame.draw.rect(surface, (14, 16, 20), self.name_rect)
        pygame.draw.rect(surface, (220, 185, 90) if self.editing_name else
                         (80, 84, 92), self.name_rect, 1)
        name_text = self.name + ("_" if self.editing_name and
                                 pygame.time.get_ticks() % 700 < 350 else "")
        surface.blit(fonts["small"].render(name_text, True, (240, 235, 220)),
                     (self.name_rect.x + 8, self.name_rect.y + 6))

        labels = {
            "style": f"WALL {self.wall_type}",
            "save": "SAVE LEVEL",
            "test": "TEST LEVEL",
            "new": "NEW / CLEAR",
            "back": "BACK TO MENU",
        }
        for key, rect in self.action_buttons.items():
            pygame.draw.rect(surface, (36, 39, 46), rect)
            pygame.draw.rect(surface, (120, 125, 135), rect, 1)
            text = fonts["small"].render(labels[key], True, (230, 230, 225))
            surface.blit(text, (rect.x + rect.width // 2 - text.get_width() // 2,
                                rect.y + 7))

        message = fonts["tiny"].render(self.message[:62], True, (255, 220, 120))
        surface.blit(message, (578, 562))
