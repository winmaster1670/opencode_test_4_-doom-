"""Player, enemies, pickups and short-lived visual particles."""

import math
import random

from . import config as C


class Player:
    def __init__(self, x, y, angle):
        self.x = x
        self.y = y
        self.angle = angle

        self.health = C.MAX_HEALTH
        self.armor = 0
        self.ammo = {"bullets": 40, "shells": 8}
        self.weapons_owned = [True, False, False]
        self.weapon = 0

        self.score = 0
        self.kills = 0
        self.items = 0
        self.medkits = 0
        self.armor_kits = 0

        self.fire_timer = 0.0
        self.muzzle = 0.0
        self.recoil = 0.0
        self.bob = 0.0
        self.damage_flash = 0.0

    @property
    def weapon_info(self):
        return C.WEAPONS[self.weapon]

    def take_damage(self, amount):
        absorbed = min(self.armor, amount * C.ARMOR_ABSORB)
        self.armor -= absorbed
        self.health -= amount - absorbed
        self.damage_flash = 0.45
        return self.health <= 0

    def add_ammo(self, kind, amount):
        caps = {"bullets": 250, "shells": 60}
        self.ammo[kind] = min(caps[kind], self.ammo[kind] + amount)

    def use_medkit(self):
        if self.medkits <= 0 or self.health >= C.MAX_HEALTH:
            return False
        self.medkits -= 1
        self.health = min(C.MAX_HEALTH, self.health + C.MEDKIT_HEAL)
        return True

    def use_armor(self):
        if self.armor_kits <= 0 or self.armor >= C.MAX_ARMOR:
            return False
        self.armor_kits -= 1
        self.armor = min(C.MAX_ARMOR, self.armor + C.ARMOR_BOOST)
        return True

    def switch_weapon(self, index):
        if 0 <= index < len(C.WEAPONS) and self.weapons_owned[index]:
            if index != self.weapon:
                self.weapon = index
                self.fire_timer = 0.18  # brief raise delay
                return True
        return False

    def cycle_weapon(self, direction):
        count = len(C.WEAPONS)
        for step in range(1, count + 1):
            index = (self.weapon + direction * step) % count
            if self.weapons_owned[index]:
                return self.switch_weapon(index)
        return False


class Enemy:
    def __init__(self, x, y, kind):
        stats = C.ENEMY_TYPES[kind]
        self.x = x
        self.y = y
        self.kind = kind
        self.name = stats["name"]
        self.max_hp = stats["hp"]
        self.hp = stats["hp"]
        self.speed = stats["speed"]
        self.damage = stats["damage"]
        self.radius = stats["radius"]
        self.scale = stats["scale"]
        self.sight = stats["sight"]
        self.score = stats["score"]

        self.alerted = False
        self.dead = False
        self.hit_flash = 0.0
        self.attack_cooldown = 0.0
        self.walk_time = random.random() * 10.0
        self.phase = random.random() * math.tau

        # Awareness / navigation state.
        self.facing = random.random() * math.tau
        self.last_seen = None
        self.path = []
        self.path_goal = None
        self.path_timer = 0.0

    # -- perception ---------------------------------------------------------

    def can_see(self, game):
        """True only when the player is in sight range, FOV and unobstructed."""
        px, py = game.player.x, game.player.y
        dx, dy = px - self.x, py - self.y
        distance = math.hypot(dx, dy)
        if distance > self.sight:
            return False

        # Very close players are noticed regardless of the exact facing angle.
        if distance > 1.4:
            bearing = math.atan2(dy, dx)
            difference = abs((bearing - self.facing + math.pi) % math.tau - math.pi)
            if difference > C.ENEMY_FOV * 0.5:
                return False

        return game.level.line_of_sight(self.x, self.y, px, py)

    # -- movement -----------------------------------------------------------

    def _step_toward(self, dt, game, target):
        dx, dy = target[0] - self.x, target[1] - self.y
        distance = math.hypot(dx, dy)
        if distance < 1e-4:
            return False

        self.facing = math.atan2(dy, dx)
        mx = dx / distance * self.speed * dt
        my = dy / distance * self.speed * dt

        # Keep monsters from standing on top of each other.
        for other in game.enemies:
            if other is self or other.dead:
                continue
            ox, oy = self.x - other.x, self.y - other.y
            gap = math.hypot(ox, oy)
            if 0 < gap < 0.75:
                mx += ox / gap * 0.9 * dt
                my += oy / gap * 0.9 * dt

        before = (self.x, self.y)
        self.x, self.y = game.level.move(self.x, self.y, mx, my, self.radius)
        moved = math.hypot(self.x - before[0], self.y - before[1]) > 1e-4
        if moved:
            self.walk_time += dt * 8.0
        return moved

    def _navigate(self, dt, game, target):
        """Follow a breadth-first path through the dungeon to the target."""
        self.path_timer -= dt
        goal_cell = (int(target[0]), int(target[1]))

        if (self.path_timer <= 0 or self.path_goal != goal_cell or
                not self.path):
            self.path = game.level.find_path(self.x, self.y, *target)
            self.path_goal = goal_cell
            self.path_timer = C.PATH_RECALC_INTERVAL + random.uniform(0.0, 0.1)

        while self.path and math.hypot(
                self.path[0][0] - self.x, self.path[0][1] - self.y) < 0.24:
            self.path.pop(0)

        if not self.path:
            # At the destination (or no route): face around for the player.
            self.facing = (self.facing + dt * 0.9) % math.tau
            return

        moved = self._step_toward(dt, game, self.path[0])
        if not moved:
            # Stuck on a corner: force a fresh route next frame.
            self.path_timer = 0.0

    # -- update -------------------------------------------------------------

    def update(self, dt, game):
        self.hit_flash = max(0.0, self.hit_flash - dt)
        self.attack_cooldown = max(0.0, self.attack_cooldown - dt)

        player = game.player
        seeing = self.can_see(game)

        if seeing:
            self.alerted = True
            self.last_seen = (player.x, player.y)
            self.facing = math.atan2(player.y - self.y, player.x - self.x)
        elif not self.alerted:
            # Idle monsters sweep their vision instead of magically tracking.
            self.facing = (self.facing + dt * 0.7) % math.tau
            self.walk_time += dt * 2.0
            return

        target = self.last_seen or (player.x, player.y)
        self._navigate(dt, game, target)

        attack_distance = math.hypot(player.x - self.x, player.y - self.y)
        if (attack_distance < 1.05 and self.attack_cooldown <= 0 and
                game.level.line_of_sight(self.x, self.y, player.x, player.y)):
            player.take_damage(self.damage)
            self.attack_cooldown = 1.05 if self.kind == "grunt" else 1.35
            game.shake = max(game.shake, 0.35 if self.kind == "grunt" else 0.6)
            game.add_message("OUCH!" if self.kind == "grunt" else "CRUSHED!")

    def hurt(self, amount):
        self.hp -= amount
        self.hit_flash = 0.14
        # Being hit is the one thing that wakes a monster without sight.
        self.alerted = True
        if self.hp <= 0:
            self.dead = True
        return self.dead


class Pickup:
    def __init__(self, x, y, kind):
        self.x = x
        self.y = y
        self.kind = kind
        self.phase = random.random() * math.tau
        self.dead = False

    def update(self, dt):
        self.phase += dt * 2.6


class Particle:
    def __init__(self, x, y, z, vx, vy, vz, kind, life):
        self.x = x
        self.y = y
        self.z = z
        self.vx = vx
        self.vy = vy
        self.vz = vz
        self.kind = kind
        self.life = life
        self.max_life = life

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.z += self.vz * dt
        self.vz -= 9.0 * dt
        self.life -= dt
        if self.z < 0.02:
            self.z = 0.02
            self.vz *= -0.25
            self.vx *= 0.6
            self.vy *= 0.6
