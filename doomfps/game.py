"""Game state, input handling and the main loop across all three windows."""

import math
import random

import pygame

from . import config as C
from . import custom
from .assets import Assets
from .editor import LevelEditor
from .entities import Enemy, Particle, Pickup, Player
from .level import BLUEPRINTS, build_level, generate_random_blueprint
from .menu import Menu
from .renderer import Renderer
from .settings import Settings, load_progress, save_progress
from .ui import draw_hud, draw_inventory, draw_minimap


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("DOOM FPS")

        self.main = pygame.Window("DOOM  //  FIRST PERSON",
                                  size=(C.WIN_W, C.WIN_H), position=(60, 60))
        self.map_window = pygame.Window("MAP", size=(C.MINIMAP_W, C.MINIMAP_H),
                                        position=(C.WIN_W + 90, 60))
        self.inv_window = pygame.Window("INVENTORY",
                                        size=(C.INVENTORY_W, C.INVENTORY_H),
                                        position=(C.WIN_W + 90,
                                                  60 + C.MINIMAP_H + 30))

        # pygame maps SDL windows lazily on their first flip. Show them now so
        # focus()/grab_mouse work immediately when the player clicks later.
        for window in (self.main, self.map_window, self.inv_window):
            window.get_surface().fill((0, 0, 0))
            window.flip()

        self.assets = Assets()
        self.settings = Settings()
        self.clock = pygame.time.Clock()
        self.unlocked = load_progress(len(BLUEPRINTS))
        self.menu = Menu(self.assets, self.settings, self)

        self.running = True
        self.firing = False
        self.fire_edge = False
        self.shake = 0.0
        self.mouse_captured = False
        self.mouse_center = (C.WIN_W // 2, C.WIN_H // 2)
        self.focus_lost_time = 0.0

        self.state = "menu"
        self.editor = None
        self.level_origin = "campaign"
        self.campaign_mode = False
        self.current_index = 0
        self.current_blueprint = None
        self.clear_delay = 0.0
        self._load_level(build_level(BLUEPRINTS[0], 0), False, 0)

    # -- level lifecycle -----------------------------------------------------

    def _load_level(self, level, campaign, index, inherited=None):
        self.level = level
        self.renderer = Renderer(self.assets, level)
        px, py, angle = level.player_spawn
        self.player = Player(px, py, angle)

        # Finishing a mission carries your kit forward. Dying (or retrying)
        # passes no inherited player, so you start over with the pistol.
        if inherited is not None:
            p = self.player
            p.weapons_owned = inherited.weapons_owned[:]
            p.weapon = inherited.weapon if p.weapons_owned[inherited.weapon] else 0
            p.ammo = dict(inherited.ammo)
            p.health = max(1, min(C.MAX_HEALTH, inherited.health))
            p.armor = min(C.MAX_ARMOR, inherited.armor)
            p.score = inherited.score
            p.kills = inherited.kills
            p.items = inherited.items
            p.medkits = min(C.MAX_MEDKITS, inherited.medkits)
            p.armor_kits = min(C.MAX_ARMOR_KITS, inherited.armor_kits)

        self.enemies = [Enemy(x, y, kind) for x, y, kind in level.enemy_spawns]
        self.pickups = [Pickup(x, y, kind) for x, y, kind in level.pickup_spawns]
        self.particles = []
        self.messages = []
        self.elapsed = 0.0
        self.game_over = False
        self.clear_delay = 0.0
        self.hint_cooldown = 0.0
        self.exit_unlocked_notified = False
        self.campaign_mode = campaign
        self.current_index = index
        self.level.mark_visited(self.player.x, self.player.y)

    def _begin_play(self, notice="CLICK THE GAME VIEW TO CAPTURE THE MOUSE"):
        self.state = "playing"
        self.release_mouse()
        self.main.focus()
        self.add_message(self.level.name, 2.4)
        if notice:
            self.add_message(notice, 4.0)

    def start_campaign_level(self, index, carry=False):
        index = max(0, min(len(BLUEPRINTS) - 1, index))
        blueprint = BLUEPRINTS[index]
        self.current_blueprint = blueprint
        self.level_origin = "campaign"
        inherited = self.player if carry and self.player.health > 0 else None
        self._load_level(build_level(blueprint, index), True, index, inherited)
        self._begin_play()

    def start_random_level(self):
        blueprint = generate_random_blueprint()
        self.current_blueprint = blueprint
        self.level_origin = "random"
        self._load_level(build_level(blueprint, 0), False, 0)
        self._begin_play()

    def retry_level(self):
        if self.current_blueprint is None:
            self.back_to_menu()
            return
        self._load_level(build_level(self.current_blueprint, self.current_index),
                         self.campaign_mode, self.current_index)
        self._begin_play()

    def next_level(self):
        if self.campaign_mode and self.current_index + 1 < len(BLUEPRINTS):
            self.start_campaign_level(self.current_index + 1, carry=True)
        else:
            self.back_to_menu()

    def complete_level(self):
        if self.campaign_mode:
            self.unlocked = max(self.unlocked,
                                min(len(BLUEPRINTS) - 1, self.current_index + 1))
            save_progress(self.unlocked)

        self.release_mouse()

        # Non-campaign levels return to wherever they were launched from.
        if self.level_origin == "editor":
            self.open_editor()
            self.editor.message = "TEST COMPLETE - LEVEL CLEARED"
            return
        if self.level_origin == "custom":
            self.state = "menu"
            self.menu.show("custom")
            self.menu.notice = "LEVEL CLEARED"
            self.main.focus()
            return

        self.state = "cleared"
        self.menu.show("clear")

    def die(self):
        self.state = "gameover"
        self.menu.show("gameover")
        self.release_mouse()

    def back_to_menu(self):
        self.state = "menu"
        self.menu.show("main")
        self.release_mouse()
        self.main.focus()

    def reset_campaign(self):
        self.unlocked = 0
        save_progress(0)
        self.menu.build()

    # -- custom levels / editor ---------------------------------------------

    def open_editor(self):
        if self.editor is None:
            self.editor = LevelEditor(self.assets)
        else:
            self.editor.close_requested = False
        self.state = "editor"
        self.release_mouse()
        self.main.focus()

    def close_editor(self):
        self.state = "menu"
        self.menu.show("main")
        self.main.focus()

    def play_custom_blueprint(self, blueprint, origin="custom"):
        self.current_blueprint = blueprint
        self.level_origin = origin
        self._load_level(build_level(blueprint), False, 0)
        self._begin_play(notice=None)
        self.add_message(
            "TESTING LEVEL" if origin == "editor" else "CUSTOM LEVEL", 2.0)

    def play_custom_file(self, path):
        try:
            data = custom.load_blueprint(path)
        except (OSError, ValueError) as exc:
            self.menu.notice = f"COULD NOT LOAD: {exc}"
            return
        blueprint, error = custom.validate_blueprint(data)
        if error:
            self.menu.notice = f"INVALID LEVEL: {error}"
            return
        self.play_custom_blueprint(blueprint)

    def add_message(self, text, duration=1.8):
        self.messages.insert(0, (text, duration))
        del self.messages[5:]

    # -- mouse capture -------------------------------------------------------

    def capture_mouse(self):
        """Focus the game window and confine the pointer to it."""
        self.main.focus()
        self.main.grab_mouse = True
        pygame.mouse.set_visible(False)
        pygame.mouse.set_pos(self.mouse_center)
        pygame.event.clear(pygame.MOUSEMOTION)
        pygame.event.clear(pygame.WINDOWFOCUSLOST)
        self.mouse_captured = True
        self.focus_lost_time = 0.0

    def release_mouse(self):
        self.main.grab_mouse = False
        pygame.mouse.set_visible(True)
        self.mouse_captured = False

    # -- input ---------------------------------------------------------------

    def handle_events(self):
        for event in pygame.event.get():
            if event.type in (pygame.QUIT, pygame.WINDOWCLOSE):
                self.running = False
                continue

            if self.state == "editor":
                consumed = self.editor.handle_event(event, self)
                if self.state == "editor" and self.editor.close_requested:
                    self.close_editor()
                elif not consumed and event.type == pygame.KEYDOWN and \
                        event.key == pygame.K_ESCAPE:
                    self.close_editor()
                continue

            if self.state != "playing":
                self.menu.handle_event(event)
                continue

            if event.type == pygame.KEYDOWN:
                bindings = self.settings.bindings
                if event.key == pygame.K_ESCAPE:
                    if self.mouse_captured:
                        self.release_mouse()
                    else:
                        self.back_to_menu()
                elif event.key == bindings["fire"]:
                    self.fire_edge = True
                elif event.key == bindings["use_health"]:
                    self.use_item("health")
                elif event.key == bindings["use_armor"]:
                    self.use_item("armor")
                else:
                    for i, action in enumerate(("weapon1", "weapon2", "weapon3")):
                        if event.key == bindings[action]:
                            if self.player.switch_weapon(i):
                                self.add_message(self.player.weapon_info["name"], 0.9)
                            else:
                                self.add_message(
                                    f"{C.WEAPONS[i]['name']} NOT FOUND", 1.2)
                            break

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    if not self.mouse_captured:
                        self.capture_mouse()
                    self.firing = True
                    self.fire_edge = True
                elif event.button == 4:
                    self.player.cycle_weapon(-1)
                elif event.button == 5:
                    self.player.cycle_weapon(1)

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    self.firing = False

    # -- simulation ----------------------------------------------------------

    def update(self, dt):
        if self.state != "playing":
            return

        self.elapsed += dt
        self.shake = max(0.0, self.shake - dt * 2.2)
        self.hint_cooldown = max(0.0, self.hint_cooldown - dt)
        for i in range(len(self.messages) - 1, -1, -1):
            self.messages[i] = (self.messages[i][0], self.messages[i][1] - dt)
            if self.messages[i][1] <= 0:
                del self.messages[i]

        player = self.player
        bindings = self.settings.bindings
        keys = pygame.key.get_pressed()

        # Mouse look: re-assert the grab and re-center every frame so the
        # pointer cannot escape the game window, even without a working grab.
        if self.mouse_captured:
            if self.main.focused:
                self.focus_lost_time = 0.0
            else:
                self.focus_lost_time += dt
                if self.focus_lost_time > 0.75:
                    self.release_mouse()
        if self.mouse_captured:
            if not self.main.mouse_grabbed:
                self.main.grab_mouse = True
            turn = pygame.mouse.get_rel()[0]
            if turn == 0:
                turn = pygame.mouse.get_pos()[0] - self.mouse_center[0]
            player.angle += turn * self.settings.mouse_sensitivity
            pygame.mouse.set_pos(self.mouse_center)

        # Keyboard turning. Q/E are reserved for using items.
        turn_speed = self.settings.keyboard_sensitivity
        if keys[bindings["turn_left"]]:
            player.angle -= turn_speed * dt
        if keys[bindings["turn_right"]]:
            player.angle += turn_speed * dt
        player.angle %= math.tau

        # Movement.
        forward = int(keys[bindings["forward"]]) - int(keys[bindings["back"]])
        strafe = int(keys[bindings["strafe_right"]]) - int(
            keys[bindings["strafe_left"]])
        speed = C.WALK_SPEED * (C.RUN_MULT if keys[bindings["run"]] else 1.0)
        if forward or strafe:
            length = math.hypot(forward, strafe)
            forward /= length
            strafe /= length
            dx = math.cos(player.angle) * forward - math.sin(player.angle) * strafe
            dy = math.sin(player.angle) * forward + math.cos(player.angle) * strafe
            player.x, player.y = self.level.move(
                player.x, player.y, dx * speed * dt, dy * speed * dt,
                C.PLAYER_RADIUS)
            player.bob += dt * 10.0
        else:
            player.bob += dt * 1.5
        self.level.mark_visited(player.x, player.y)

        # Weapon timers and firing.
        player.fire_timer = max(0.0, player.fire_timer - dt)
        player.muzzle = max(0.0, player.muzzle - dt)
        player.recoil = max(0.0, player.recoil - dt * 55)
        player.damage_flash = max(0.0, player.damage_flash - dt)

        wants_fire = self.firing or keys[bindings["fire"]]
        if wants_fire and (player.weapon_info["auto"] or self.fire_edge):
            self.try_fire()
        self.fire_edge = False

        # Entities.
        for enemy in self.enemies:
            if not enemy.dead:
                enemy.update(dt, self)
        self.enemies = [e for e in self.enemies if not e.dead]

        for pickup in self.pickups:
            if pickup.dead:
                continue
            pickup.update(dt)
            if math.hypot(pickup.x - player.x, pickup.y - player.y) < 0.62:
                self.collect(pickup)

        for particle in self.particles:
            particle.update(dt)
        self.particles = [p for p in self.particles if p.life > 0]

        # End conditions: clearing the imps only unlocks the exit door; the
        # level is finished when the player actually walks through it.
        if player.health <= 0:
            self.die()
            return

        if not self.enemies and not self.level.exit_open:
            self.level.open_exit()
            if not self.exit_unlocked_notified:
                self.exit_unlocked_notified = True
                self.add_message("ALL IMPS DOWN - EXIT UNLOCKED", 3.5)
                if self.level.exit:
                    self._burst(self.level.exit[0], self.level.exit[1],
                                0.6, "spark", 16)

        if self.level.exit and self.level.at_exit(player.x, player.y):
            if self.level.exit_open:
                self.complete_level()
            elif self.hint_cooldown <= 0:
                self.hint_cooldown = 1.6
                self.add_message(f"EXIT LOCKED - {len(self.enemies)} IMP(S) LEFT",
                                 1.6)

    # -- combat -------------------------------------------------------------

    def try_fire(self):
        player = self.player
        if player.fire_timer > 0:
            return
        weapon = player.weapon_info
        ammo_type = weapon["ammo"]
        if player.ammo[ammo_type] <= 0:
            player.fire_timer = 0.35
            self.add_message("OUT OF AMMO", 1.0)
            return

        player.ammo[ammo_type] -= 1
        player.fire_timer = weapon["cooldown"]
        player.muzzle = 0.11
        player.recoil = weapon["kick"]
        self.shake = max(self.shake, min(0.35, weapon["kick"] * 0.014))

        # Gunfire does not wake monsters; they must actually see the player
        # (or be hit) before they start chasing.

        for _ in range(weapon["pellets"]):
            angle = player.angle + random.gauss(0, weapon["spread"])
            dx, dy = math.cos(angle), math.sin(angle)
            wall_dist, _, _ = self.level.ray_cast(
                player.x, player.y, dx, dy, weapon["range"])

            best_t = wall_dist
            target = None
            for enemy in self.enemies:
                if enemy.dead:
                    continue
                ex, ey = enemy.x - player.x, enemy.y - player.y
                t = ex * dx + ey * dy
                if t <= 0 or t >= best_t:
                    continue
                if abs(ex * dy - ey * dx) < enemy.radius + 0.08:
                    best_t = t
                    target = enemy

            hit_x = player.x + dx * best_t
            hit_y = player.y + dy * best_t
            if target is not None:
                killed = target.hurt(weapon["damage"])
                self._burst(hit_x, hit_y, 0.55, "blood", 5)
                if killed:
                    self.on_enemy_killed(target)
            elif wall_dist < weapon["range"] - 0.1:
                self._burst(hit_x, hit_y, 0.5 + random.random() * 0.4,
                            "spark", 3)

    def on_enemy_killed(self, enemy):
        self.player.kills += 1
        self.player.score += enemy.score
        self.add_message(f"{enemy.name} DOWN  +{enemy.score}")
        enemy.dead = True
        self._burst(enemy.x, enemy.y, 0.5, "blood", 14)
        if random.random() < 0.32:
            self.pickups.append(Pickup(enemy.x, enemy.y,
                                       random.choice(["health", "ammo"])))

    def _burst(self, x, y, z, kind, count):
        for _ in range(count):
            a = random.random() * math.tau
            speed = random.uniform(0.5, 2.6)
            self.particles.append(Particle(
                x, y, z, math.cos(a) * speed, math.sin(a) * speed,
                random.uniform(1.0, 3.2), kind, random.uniform(0.25, 0.6)))

    # -- pickups ------------------------------------------------------------

    def collect(self, pickup):
        player = self.player
        kind = pickup.kind

        if kind == "health" and player.medkits >= C.MAX_MEDKITS:
            if self.hint_cooldown <= 0:
                self.hint_cooldown = 1.4
                self.add_message("MEDKIT LIMIT REACHED", 1.4)
            return
        if kind == "armor" and player.armor_kits >= C.MAX_ARMOR_KITS:
            if self.hint_cooldown <= 0:
                self.hint_cooldown = 1.4
                self.add_message("ARMOR LIMIT REACHED", 1.4)
            return

        pickup.dead = True
        player.items += 1

        if kind == "health":
            player.medkits += 1
            key = pygame.key.name(self.settings.bindings["use_health"]).upper()
            self.add_message(f"+1 MEDKIT  [{key} TO USE]", 2.0)
        elif kind == "armor":
            player.armor_kits += 1
            key = pygame.key.name(self.settings.bindings["use_armor"]).upper()
            self.add_message(f"+1 ARMOR KIT  [{key} TO USE]", 2.0)
        elif kind == "ammo":
            player.add_ammo("bullets", 25)
            self.add_message("+25 BULLETS")
        elif kind == "shells":
            player.add_ammo("shells", 8)
            self.add_message("+8 SHELLS")
        elif kind in ("shotgun", "chaingun"):
            index = 1 if kind == "shotgun" else 2
            player.weapons_owned[index] = True
            ammo = C.WEAPONS[index]["ammo"]
            amount = 8 if ammo == "shells" else 40
            player.add_ammo(ammo, amount)
            key = pygame.key.name(
                self.settings.bindings[f"weapon{index + 1}"]).upper()
            self.add_message(
                f"{C.WEAPONS[index]['name']} ACQUIRED - PRESS {key}", 2.6)

    def use_item(self, kind):
        player = self.player
        if kind == "health":
            if player.medkits <= 0:
                self.add_message("NO MEDKITS", 1.2)
            elif player.health >= C.MAX_HEALTH:
                self.add_message("HEALTH ALREADY FULL", 1.2)
            elif player.use_medkit():
                self.add_message(f"+{C.MEDKIT_HEAL} HEALTH")
        elif kind == "armor":
            if player.armor_kits <= 0:
                self.add_message("NO ARMOR KITS", 1.2)
            elif player.armor >= C.MAX_ARMOR:
                self.add_message("ARMOR ALREADY FULL", 1.2)
            elif player.use_armor():
                self.add_message(f"+{C.ARMOR_BOOST} ARMOR")

    # -- drawing ------------------------------------------------------------

    def _draw_standby_windows(self):
        for window, title in ((self.map_window, "MAP"),
                              (self.inv_window, "INVENTORY")):
            standby = window.get_surface()
            standby.fill((10, 12, 16))
            font = self.assets.fonts["normal"]
            label = font.render(f"{title}  //  STANDBY", True, (95, 100, 110))
            standby.blit(label, (20, 20))

    def render_all(self):
        main_surface = self.main.get_surface()

        if self.state == "editor":
            self.editor.draw(main_surface)
            self._draw_standby_windows()
            self.main.flip()
            self.map_window.flip()
            self.inv_window.flip()
            return

        if self.state == "menu":
            main_surface.fill((10, 12, 16))
            self.menu.draw(main_surface)
            self._draw_standby_windows()
            self.main.flip()
            self.map_window.flip()
            self.inv_window.flip()
            return

        view = self.renderer.render(self.player, self.enemies, self.pickups,
                                    self.particles, 0.0)
        scaled = pygame.transform.scale(view, (C.WIN_W, C.WIN_H))

        if self.shake > 0 and self.state == "playing":
            magnitude = int(self.shake * 9)
            ox = random.randint(-magnitude, magnitude)
            oy = random.randint(-magnitude, magnitude)
        else:
            ox = oy = 0
        main_surface.blit(scaled, (ox, oy))
        draw_hud(main_surface, self.assets, self)

        draw_minimap(self.map_window.get_surface(), self.assets, self.level,
                     self.player, self.enemies, self.pickups)
        draw_inventory(self.inv_window.get_surface(), self.assets,
                       self.player, self)

        if self.state in ("cleared", "gameover"):
            self.menu.draw(main_surface)

        self.main.flip()
        self.map_window.flip()
        self.inv_window.flip()

    # -- loop ---------------------------------------------------------------

    def run(self):
        while self.running:
            dt = min(0.05, self.clock.tick(C.FPS) / 1000.0)
            self.handle_events()
            self.update(dt)
            self.render_all()
        pygame.quit()
