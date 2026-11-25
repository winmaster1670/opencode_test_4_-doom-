"""Software raycasting renderer for the first-person window."""

import math
import random

import pygame

from . import config as C
from .assets import Assets


class Renderer:
    def __init__(self, assets: Assets, level):
        self.assets = assets
        self.level = level
        self.surface = pygame.Surface((C.VIEW_W, C.VIEW_H))
        self.zbuffer = [0.0] * C.VIEW_W
        self.horizon = C.VIEW_H // 2

        # Ceiling: a static vertical gradient (darker towards the horizon).
        self.ceiling = pygame.Surface((C.VIEW_W, self.horizon))
        top = (58, 54, 64)
        bottom = (17, 16, 22)
        for y in range(self.horizon):
            t = y / max(1, self.horizon - 1)
            color = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
            pygame.draw.line(self.ceiling, color, (0, y), (C.VIEW_W, y))

        # Floor: one shaded line per row (fog + subtle depth banding).
        self.floor_colors = []
        for y in range(self.horizon, C.VIEW_H):
            row_dist = (0.5 * C.VIEW_H) / max(1, y - self.horizon + 1)
            intensity = 1.0 / (1.0 + 0.075 * row_dist)
            band = 0.87 if int(row_dist * 3) % 2 else 1.0
            self.floor_colors.append(tuple(
                int(base * intensity * band) for base in (100, 84, 66)))

        # Per-weapon placement and muzzle-tip offsets (in view pixels).
        self.weapon_offsets = [(26, 14), (10, 14), (0, 12)]
        self.muzzle_offsets = [(118, 22), (132, 46), (142, 50)]

    # -- main entry point ---------------------------------------------------

    def render(self, player, enemies, pickups, particles, dt):
        surf = self.surface
        surf.blit(self.ceiling, (0, 0))
        for i, color in enumerate(self.floor_colors):
            pygame.draw.line(surf, color, (0, self.horizon + i),
                             (C.VIEW_W, self.horizon + i))

        dir_x = math.cos(player.angle)
        dir_y = math.sin(player.angle)
        plane_x = -dir_y * C.PLANE_LEN
        plane_y = dir_x * C.PLANE_LEN
        self._draw_walls(player, dir_x, dir_y, plane_x, plane_y)

        # Sprites are painter's-algorithm sorted: far ones go down first.
        drawables = []
        if self.level.exit:
            ex, ey = self.level.exit
            drawables.append(((ex - player.x) ** 2 + (ey - player.y) ** 2,
                              "exit", None))
        for enemy in enemies:
            if not enemy.dead:
                drawables.append(((enemy.x - player.x) ** 2 +
                                  (enemy.y - player.y) ** 2, "enemy", enemy))
        for pickup in pickups:
            if not pickup.dead:
                drawables.append(((pickup.x - player.x) ** 2 +
                                  (pickup.y - player.y) ** 2, "pickup", pickup))
        for particle in particles:
            drawables.append(((particle.x - player.x) ** 2 +
                              (particle.y - player.y) ** 2, "particle", particle))
        drawables.sort(key=lambda item: item[0], reverse=True)

        for _, kind, obj in drawables:
            if kind == "enemy":
                images = self.assets.creatures[obj.kind][int(obj.walk_time) % 2]
                if obj.hit_flash > 0:
                    images = [images[-1]] * C.SHADE_LEVELS
                brightness = 1.0 / (1.0 + 0.10 * math.sqrt(
                    (obj.x - player.x) ** 2 + (obj.y - player.y) ** 2))
                center_height = 0.5 * obj.scale
                self._draw_sprite(images, obj.x, obj.y, obj.scale,
                                  center_height, brightness,
                                  player, dir_x, dir_y, plane_x, plane_y)
            elif kind == "exit":
                images = self.assets.exits[1 if self.level.exit_open else 0]
                brightness = 1.0 / (1.0 + 0.08 * math.sqrt(
                    (self.level.exit[0] - player.x) ** 2 +
                    (self.level.exit[1] - player.y) ** 2))
                self._draw_sprite(images, self.level.exit[0],
                                  self.level.exit[1], 1.05, 0.55, brightness,
                                  player, dir_x, dir_y, plane_x, plane_y)
            elif kind == "pickup":
                bob = math.sin(obj.phase) * 0.10
                images = self.assets.pickups[obj.kind]
                brightness = 1.0 / (1.0 + 0.09 * math.sqrt(
                    (obj.x - player.x) ** 2 + (obj.y - player.y) ** 2))
                self._draw_sprite(images, obj.x, obj.y, 0.62,
                                  0.50 + bob, brightness,
                                  player, dir_x, dir_y, plane_x, plane_y)
            else:
                images = self.assets.particles[obj.kind]
                fade = max(0.0, obj.life / obj.max_life)
                self._draw_sprite(images, obj.x, obj.y, 0.20 * fade + 0.05,
                                  obj.z, 1.0,
                                  player, dir_x, dir_y, plane_x, plane_y)

        self._draw_weapon(player)
        return surf

    # -- walls --------------------------------------------------------------

    def _draw_walls(self, p, dir_x, dir_y, plane_x, plane_y):
        surf = self.surface
        level = self.level
        grid = level.grid
        px, py = p.x, p.y

        for x in range(C.VIEW_W):
            camera_x = 2.0 * x / C.VIEW_W - 1.0
            ray_x = dir_x + plane_x * camera_x
            ray_y = dir_y + plane_y * camera_x

            map_x, map_y = int(px), int(py)
            delta_x = 1e30 if ray_x == 0 else abs(1.0 / ray_x)
            delta_y = 1e30 if ray_y == 0 else abs(1.0 / ray_y)
            if ray_x < 0:
                step_x, side_x = -1, (px - map_x) * delta_x
            else:
                step_x, side_x = 1, (map_x + 1 - px) * delta_x
            if ray_y < 0:
                step_y, side_y = -1, (py - map_y) * delta_y
            else:
                step_y, side_y = 1, (map_y + 1 - py) * delta_y

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
                if level.is_wall_cell(map_x, map_y):
                    wall = grid[map_y][map_x] if (
                        0 <= map_x < C.MAP_W and 0 <= map_y < C.MAP_H) else 1
                    break
                if distance > C.MAX_VIEW_DIST:
                    wall, distance = 0, C.MAX_VIEW_DIST
                    break

            distance = max(0.05, distance)
            self.zbuffer[x] = distance

            line_height = int(C.VIEW_H / distance)
            draw_start = -line_height / 2.0 + self.horizon
            draw_end = line_height / 2.0 + self.horizon
            vis_top = max(0, int(draw_start))
            vis_bottom = min(C.VIEW_H, int(draw_end))
            if vis_bottom <= vis_top or wall == 0:
                continue

            wall_x = py + distance * ray_y if side == 0 else px + distance * ray_x
            wall_x -= math.floor(wall_x)
            tex_x = int(wall_x * C.TEX_SIZE)
            if (side == 0 and ray_x > 0) or (side == 1 and ray_y < 0):
                tex_x = C.TEX_SIZE - tex_x - 1

            brightness = 1.0 / (1.0 + 0.11 * distance)
            if side == 1:
                brightness *= 0.72
            texture = self.assets.walls.get(wall, self.assets.walls[1])[
                Assets.shade_index(brightness)]

            t0 = (vis_top - draw_start) / line_height
            t1 = (vis_bottom - draw_start) / line_height
            sy0 = max(0, int(t0 * C.TEX_SIZE))
            sy1 = min(C.TEX_SIZE, max(sy0 + 1, int(t1 * C.TEX_SIZE)))
            strip = texture.subsurface(tex_x, sy0, 1, sy1 - sy0)
            strip = pygame.transform.scale(strip, (1, vis_bottom - vis_top))
            surf.blit(strip, (x, vis_top))

    # -- billboard sprites --------------------------------------------------

    def _draw_sprite(self, images, wx, wy, scale, center_height, brightness,
                     player, dir_x, dir_y, plane_x, plane_y):
        sprite_x, sprite_y = wx - player.x, wy - player.y
        inv_det = 1.0 / (plane_x * dir_y - dir_x * plane_y)
        transform_x = inv_det * (dir_y * sprite_x - dir_x * sprite_y)
        transform_y = inv_det * (-plane_y * sprite_x + plane_x * sprite_y)
        if transform_y <= 0.15:
            return

        screen_x = int((C.VIEW_W / 2) * (1 + transform_x / transform_y))
        image = images[Assets.shade_index(brightness)]
        tex_w, tex_h = image.get_size()
        sprite_h = abs(int(C.VIEW_H * scale / transform_y))
        sprite_w = int(sprite_h * tex_w / tex_h)
        if sprite_h < 1 or sprite_w < 1:
            return

        center_y = self.horizon + C.VIEW_H * (0.5 - center_height) / transform_y
        draw_start_y = int(center_y - sprite_h / 2)
        draw_start_x = int(screen_x - sprite_w / 2)
        draw_end_y = draw_start_y + sprite_h

        vis_top = max(0, draw_start_y)
        vis_bottom = min(C.VIEW_H, draw_end_y)
        if vis_bottom <= vis_top:
            return
        ty0 = max(0, int((vis_top - draw_start_y) / sprite_h * tex_h))
        ty1 = min(tex_h, max(ty0 + 1,
                             int((vis_bottom - draw_start_y) / sprite_h * tex_h)))

        left = max(0, draw_start_x)
        right = min(C.VIEW_W, draw_start_x + sprite_w)
        strip_height = vis_bottom - vis_top
        surf = self.surface
        for stripe in range(left, right):
            if transform_y >= self.zbuffer[stripe]:
                continue
            tex_x = int((stripe - draw_start_x) * tex_w / sprite_w)
            if tex_x >= tex_w:
                tex_x = tex_w - 1
            strip = image.subsurface(tex_x, ty0, 1, ty1 - ty0)
            strip = pygame.transform.scale(strip, (1, strip_height))
            surf.blit(strip, (stripe, vis_top))

    # -- held weapon --------------------------------------------------------

    def _draw_weapon(self, player):
        surf = self.surface
        image = self.assets.weapon_views[player.weapon]
        bob_x = int(math.sin(player.bob) * 7)
        bob_y = int(abs(math.cos(player.bob)) * 5)
        off_x, off_y = self.weapon_offsets[player.weapon]
        x = C.VIEW_W // 2 - image.get_width() // 2 + off_x + bob_x
        y = C.VIEW_H - image.get_height() + off_y + bob_y + int(player.recoil)
        surf.blit(image, (x, y))

        if player.muzzle > 0:
            ox, oy = self.muzzle_offsets[player.weapon]
            cx, cy = x + ox, y + oy
            size = 10 + int(player.muzzle * 34)
            rnd = random.Random(int(player.muzzle * 1000) + player.weapon)
            points = [(cx, cy)]
            for i in range(8):
                a = i * math.tau / 8 + rnd.uniform(-0.12, 0.12)
                r = size * rnd.uniform(0.55, 1.25)
                points.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
            pygame.draw.polygon(surf, (255, 170, 40), points)
            inner = [(cx + (px - cx) * 0.55, cy + (py - cy) * 0.55)
                     for px, py in points]
            pygame.draw.polygon(surf, (255, 248, 190), inner)
