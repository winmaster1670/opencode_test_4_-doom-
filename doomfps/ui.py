"""HUD, minimap and inventory window drawing helpers."""

import math

import pygame

from . import config as C


def _text(surface, font, message, x, y, color=(235, 235, 225), shadow=True):
    if shadow:
        surface.blit(font.render(message, True, (0, 0, 0)), (x + 2, y + 2))
    return surface.blit(font.render(message, True, color), (x, y))


def _bar(surface, x, y, w, h, fraction, color):
    pygame.draw.rect(surface, (12, 14, 18), (x - 1, y - 1, w + 2, h + 2))
    pygame.draw.rect(surface, (55, 55, 62), (x, y, w, h))
    filled = int(w * max(0.0, min(1.0, fraction)))
    if filled:
        pygame.draw.rect(surface, color, (x, y, filled, h))
        pygame.draw.rect(surface, tuple(min(255, c + 45) for c in color),
                         (x, y, filled, max(2, h // 5)))


# ---------------------------------------------------------------------------
# Main-window HUD
# ---------------------------------------------------------------------------

def draw_hud(surface, assets, game):
    player = game.player
    fonts = assets.fonts
    w, h = surface.get_size()

    # Damage vignette / flash.
    if player.damage_flash > 0:
        alpha = int(120 * min(1.0, player.damage_flash / 0.45))
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((190, 20, 20, alpha))
        surface.blit(overlay, (0, 0))

    # Crosshair.
    cx, cy = w // 2, h // 2
    gap = 5 + (3 if player.muzzle > 0 else 0)
    length = 9
    cross_color = (255, 220, 90) if player.muzzle > 0 else (235, 240, 225)
    for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
        if dx:
            start = (cx + dx * gap, cy)
            end = (cx + dx * (gap + length), cy)
        else:
            start = (cx, cy + dy * gap)
            end = (cx, cy + dy * (gap + length))
        pygame.draw.line(surface, (0, 0, 0), start, end, 4)
        pygame.draw.line(surface, cross_color, start, end, 2)

    # Score, top-left.
    _text(surface, fonts["small"], f"SCORE  {player.score:06d}", 14, 12, (255, 215, 110))
    _text(surface, fonts["small"], f"KILLS  {player.kills}", 14, 34, (170, 200, 170))

    # Status bar.
    bar_top = h - 70
    panel = pygame.Surface((w, 70), pygame.SRCALPHA)
    panel.fill((8, 9, 12, 205))
    pygame.draw.line(panel, (130, 110, 70), (0, 0), (w, 0), 2)
    surface.blit(panel, (0, bar_top))

    _text(surface, fonts["tiny"], "HEALTH", 18, bar_top + 8, (220, 190, 180))
    _bar(surface, 18, bar_top + 26, 150, 16,
         player.health / C.MAX_HEALTH, (200, 55, 45))
    _text(surface, fonts["small"], str(max(0, int(player.health))), 176, bar_top + 22)

    _text(surface, fonts["tiny"], "ARMOR", 240, bar_top + 8, (175, 205, 235))
    _bar(surface, 240, bar_top + 26, 110, 16,
         player.armor / C.MAX_ARMOR, (60, 130, 210))
    _text(surface, fonts["small"], str(int(player.armor)), 358, bar_top + 22)

    weapon = player.weapon_info
    ammo_key = weapon["ammo"]
    _text(surface, fonts["tiny"], ammo_key.upper(), w - 250, bar_top + 8,
          (235, 215, 140))
    _text(surface, fonts["small"], f"{player.ammo[ammo_key]:03d}",
          w - 250, bar_top + 24, (255, 235, 150))
    _text(surface, fonts["normal"], weapon["name"], w - 135, bar_top + 20,
          (245, 245, 235))
    _text(surface, fonts["tiny"], f"{player.weapon + 1}/{len(C.WEAPONS)}",
          w - 40, bar_top + 44, (150, 150, 150))

    # Transient messages.
    for i, (message, timer) in enumerate(reversed(game.messages[:4])):
        color = (255, 230, 140, min(255, int(timer * 400)))
        msg = fonts["small"].render(message, True, color)
        surface.blit(msg, (w // 2 - msg.get_width() // 2, h - 130 - i * 24))

    # Low-health warning pulse.
    if player.health <= 25 and player.health > 0:
        pulse = int(150 + 105 * math.sin(game.elapsed * 8))
        _text(surface, fonts["big"], "LOW HEALTH", w // 2 - 100, 60,
              (pulse, 40, 40))


# ---------------------------------------------------------------------------
# Minimap window
# ---------------------------------------------------------------------------

def draw_minimap(surface, assets, level, player, enemies, pickups):
    surface.fill((9, 11, 15))
    fonts = assets.fonts
    title = f"MAP  //  {level.name[:18]}"
    _text(surface, fonts["small"], title, 12, 8, (225, 200, 130))

    pad = 22
    cell = min((C.MINIMAP_W - pad * 2) // C.MAP_W,
               (C.MINIMAP_H - pad * 2 - 20) // C.MAP_H)
    ox = (C.MINIMAP_W - cell * C.MAP_W) // 2
    oy = 36

    pygame.draw.rect(surface, (16, 18, 24),
                     (ox - 2, oy - 2, cell * C.MAP_W + 4, cell * C.MAP_H + 4))

    for y in range(C.MAP_H):
        for x in range(C.MAP_W):
            if (x, y) not in level.visited:
                continue
            rect = (ox + x * cell, oy + y * cell, cell, cell)
            if level.grid[y][x]:
                base = C.WALL_COLORS.get(level.grid[y][x], (110, 110, 110))
                color = tuple(max(0, c - 45) for c in base)
                pygame.draw.rect(surface, color, rect)
                pygame.draw.rect(surface, tuple(min(255, c + 20) for c in color),
                                 rect, 1)
            else:
                pygame.draw.rect(surface, (34, 36, 42), rect)

    def to_screen(wx, wy):
        return (ox + wx * cell, oy + wy * cell)

    if level.exit:
        ex, ey = to_screen(*level.exit)
        color = (90, 245, 150) if level.exit_open else (255, 80, 70)
        pygame.draw.rect(surface, color, (int(ex) - 5, int(ey) - 5, 10, 10))
        pygame.draw.rect(surface, (245, 245, 235),
                         (int(ex) - 5, int(ey) - 5, 10, 10), 1)

    for pickup in pickups:
        if pickup.dead or (int(pickup.x), int(pickup.y)) not in level.visited:
            continue
        color = C.PICKUP_INFO[pickup.kind]["color"]
        px, py = to_screen(pickup.x, pickup.y)
        pygame.draw.circle(surface, color, (int(px), int(py)), 2)

    for enemy in enemies:
        if enemy.dead or (int(enemy.x), int(enemy.y)) not in level.visited:
            continue
        if math.hypot(enemy.x - player.x, enemy.y - player.y) > C.ENEMY_MAP_RANGE:
            continue
        px, py = to_screen(enemy.x, enemy.y)
        color = (255, 80, 70) if enemy.alerted else (185, 70, 65)
        pygame.draw.circle(surface, (10, 0, 0), (int(px), int(py)), 4)
        pygame.draw.circle(surface, color, (int(px), int(py)), 3)

    # Player arrow.
    px, py = to_screen(player.x, player.y)
    a = player.angle
    tip = (px + math.cos(a) * cell * 0.95, py + math.sin(a) * cell * 0.95)
    left = (px + math.cos(a + 2.5) * cell * 0.7,
            py + math.sin(a + 2.5) * cell * 0.7)
    right = (px + math.cos(a - 2.5) * cell * 0.7,
             py + math.sin(a - 2.5) * cell * 0.7)
    pygame.draw.polygon(surface, (255, 225, 70), [tip, left, right])
    pygame.draw.circle(surface, (255, 255, 190), (int(px), int(py)), 2)

    _text(surface, fonts["tiny"], "YOU", 12, C.MINIMAP_H - 20, (255, 225, 70))
    _text(surface, fonts["tiny"], "ENEMY", 50, C.MINIMAP_H - 20, (255, 90, 80))
    _text(surface, fonts["tiny"], "ITEM", 120, C.MINIMAP_H - 20, (120, 220, 140))


# ---------------------------------------------------------------------------
# Inventory window
# ---------------------------------------------------------------------------

def draw_inventory(surface, assets, player, game):
    surface.fill((12, 14, 18))
    fonts = assets.fonts
    w = C.INVENTORY_W
    b = game.settings.bindings
    _key = lambda action: pygame.key.name(b[action]).upper()

    pygame.draw.rect(surface, (28, 30, 36), (0, 0, w, 46))
    _text(surface, fonts["normal"], "INVENTORY", 16, 12, (240, 215, 140))
    pygame.draw.line(surface, (120, 100, 60), (0, 46), (w, 46), 2)

    # Vitals sit above both columns.
    _text(surface, fonts["small"], "VITALS", 16, 54, (180, 190, 200))
    _text(surface, fonts["tiny"], "HEALTH", 16, 78, (220, 190, 180))
    _text(surface, fonts["small"], str(max(0, int(player.health))), 244, 76)
    _bar(surface, 16, 94, 220, 14, player.health / C.MAX_HEALTH, (200, 55, 45))
    _text(surface, fonts["tiny"], "ARMOR", 296, 78, (175, 205, 235))
    _text(surface, fonts["small"], str(int(player.armor)), 524, 76)
    _bar(surface, 296, 94, 220, 14, player.armor / C.MAX_ARMOR, (60, 130, 210))

    pygame.draw.line(surface, (60, 62, 70), (10, 120), (w - 10, 120), 1)
    col_w = (w - 48) // 2
    left_x = 16
    right_x = w - 16 - col_w
    _text(surface, fonts["small"], "WEAPONS", left_x, 128, (180, 190, 200))
    _text(surface, fonts["small"], "SUPPLIES", right_x, 128, (180, 190, 200))

    # Left column: weapon cards. Locked weapons show a flat black silhouette.
    for i, weapon in enumerate(C.WEAPONS):
        y = 152 + i * 74
        owned = player.weapons_owned[i]
        selected = player.weapon == i
        box = (left_x, y, col_w, 66)
        pygame.draw.rect(surface, (40, 43, 50) if not owned else (22, 24, 30), box)
        color = (235, 205, 110) if selected else (
            (135, 140, 150) if owned else (65, 68, 74))
        pygame.draw.rect(surface, color, box, 2 if selected else 1)
        icon = assets.weapon_icons[i] if owned else assets.weapon_silhouettes[i]
        surface.blit(icon, (left_x + 8, y + 7))
        tx = left_x + 94
        _text(surface, fonts["small"], f"{i + 1}. {weapon['name']}", tx, y + 8,
              color if owned else (90, 92, 98))
        if owned:
            ammo = player.ammo[weapon["ammo"]]
            _text(surface, fonts["tiny"],
                  f"{weapon['ammo'].upper()}: {ammo}", tx, y + 32, (200, 200, 190))
            if selected:
                _text(surface, fonts["tiny"], "EQUIPPED", tx, y + 48, (255, 225, 120))
        else:
            _text(surface, fonts["tiny"], "NOT FOUND", tx, y + 32, (90, 92, 98))

    # Right column: ammo and stored kits, with their carry caps.
    rows = [
        ((215, 185, 60), "BULLETS", f"{player.ammo['bullets']:03d}", None),
        ((210, 135, 55), "SHELLS", f"{player.ammo['shells']:03d}", None),
        ((230, 235, 240), "MEDKITS",
         f"{player.medkits:02d} / {C.MAX_MEDKITS:02d}", _key("use_health")),
        ((90, 170, 230), "ARMOR KITS",
         f"{player.armor_kits:02d} / {C.MAX_ARMOR_KITS:02d}", _key("use_armor")),
    ]
    for i, (color, label, value, hint) in enumerate(rows):
        y = 152 + i * 56
        pygame.draw.rect(surface, (18, 20, 25), (right_x, y, col_w, 50))
        pygame.draw.rect(surface, color, (right_x + 8, y + 10, 12, 12))
        _text(surface, fonts["small"], label, right_x + 32, y + 6)
        _text(surface, fonts["small"], value, right_x + col_w - 70, y + 6)
        if hint:
            _text(surface, fonts["tiny"], f"{hint} TO USE", right_x + 32, y + 28,
                  (150, 158, 168))

    pygame.draw.line(surface, (60, 62, 70), (10, 386), (w - 10, 386), 1)
    _text(surface, fonts["small"], "STATS", 16, 394, (180, 190, 200))
    _text(surface, fonts["tiny"],
          f"KILLS {player.kills}    ITEMS {player.items}    "
          f"SCORE {player.score}    TIME {int(getattr(game, 'elapsed', 0))}s",
          16, 418)

    # Controls, pinned to the bottom.
    controls = [
        f"{_key('forward')}/{_key('back')}/{_key('strafe_left')}/{_key('strafe_right')} move"
        f"   {_key('run')} run   ESC release/menu",
        f"{_key('turn_left')}/{_key('turn_right')} or MOUSE look"
        f"   {_key('fire')}/CLICK fire",
        f"{_key('weapon1')}{_key('weapon2')}{_key('weapon3')}/WHEEL weapon"
        f"   {_key('use_health')} medkit   {_key('use_armor')} armor kit",
    ]
    top = C.INVENTORY_H - 74
    pygame.draw.rect(surface, (18, 20, 25), (0, top, w, 74))
    pygame.draw.line(surface, (60, 62, 70), (0, top), (w, top), 1)
    for i, line in enumerate(controls):
        _text(surface, fonts["tiny"], line, 16, top + 8 + i * 21,
              (150, 158, 168), shadow=False)
