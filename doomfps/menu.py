"""Main menu, campaign level select, settings and overlay screens."""

import pygame

from . import config as C
from . import custom
from . import settings as S
from .level import BLUEPRINTS


class Button:
    def __init__(self, rect, label, action, enabled=True, sublabel=None):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.action = action
        self.enabled = enabled
        self.sublabel = sublabel

    def draw(self, surface, fonts, hovered, selected=False):
        color = (26, 29, 36) if self.enabled else (18, 19, 23)
        border = (225, 185, 90) if selected else (
            (150, 155, 165) if self.enabled else (55, 57, 62))
        if hovered and self.enabled:
            color = (48, 44, 38)
            border = (255, 220, 120)
        pygame.draw.rect(surface, color, self.rect)
        pygame.draw.rect(surface, border, self.rect, 2 if selected else 1)
        text_color = (240, 236, 220) if self.enabled else (95, 96, 100)
        font = fonts["normal"]
        surface.blit(font.render(self.label, True, text_color),
                     (self.rect.x + 16, self.rect.y + 9))
        if self.sublabel:
            sub = fonts["tiny"].render(self.sublabel, True,
                                       (180, 170, 140) if self.enabled else (80, 80, 84))
            surface.blit(sub, (self.rect.right - sub.get_width() - 14,
                               self.rect.y + 15))


class Slider:
    def __init__(self, rect, label, setting_key, minimum, maximum, formatter):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.key = setting_key
        self.minimum = minimum
        self.maximum = maximum
        self.formatter = formatter

    def fraction(self, settings):
        value = getattr(settings, self.key)
        return (value - self.minimum) / (self.maximum - self.minimum)

    def click(self, pos, settings):
        if not self.rect.collidepoint(pos):
            return False
        fraction = (pos[0] - self.rect.x) / self.rect.width
        fraction = max(0.0, min(1.0, fraction))
        setattr(settings, self.key,
                self.minimum + fraction * (self.maximum - self.minimum))
        settings.save()
        return True

    def draw(self, surface, fonts, settings):
        surface.blit(fonts["small"].render(self.label, True, (220, 220, 210)),
                     (self.rect.x, self.rect.y - 24))
        pygame.draw.rect(surface, (18, 20, 25), self.rect)
        pygame.draw.rect(surface, (80, 84, 92), self.rect, 1)
        filled = int(self.rect.width * self.fraction(settings))
        pygame.draw.rect(surface, (200, 155, 65),
                         (self.rect.x + 2, self.rect.y + 2,
                          max(0, filled - 4), self.rect.height - 4))
        knob_x = self.rect.x + filled
        pygame.draw.rect(surface, (255, 225, 130),
                         (knob_x - 5, self.rect.y - 5, 10, self.rect.height + 10))
        value = self.formatter(getattr(settings, self.key))
        label = fonts["small"].render(value, True, (255, 225, 140))
        surface.blit(label, (self.rect.right + 14, self.rect.y - 4))


class Menu:
    def __init__(self, assets, settings, game):
        self.assets = assets
        self.settings = settings
        self.game = game
        self.screen = "main"
        self.buttons = []
        self.sliders = []
        self.waiting_for_key = None
        self.notice = ""
        self.build()

    # -- screen construction ------------------------------------------------

    def build(self):
        self.buttons = []
        self.sliders = []

        if self.screen == "main":
            self._title("DOOM  FPS", "CHOOSE YOUR DESTINY")
            entries = [
                ("START CAMPAIGN", "levels"),
                ("RANDOM LEVEL", "random"),
                ("PLAY CUSTOM LEVELS", "custom"),
                ("LEVEL EDITOR", "editor"),
                ("SETTINGS", "settings"),
                ("RESTART CAMPAIGN", "reset_progress"),
                ("QUIT", "quit"),
            ]
            for i, (label, action) in enumerate(entries):
                self.buttons.append(Button((300, 190 + i * 52, 360, 46),
                                           label, action))

        elif self.screen == "levels":
            self._title("CAMPAIGN", "Select a mission")
            for i, blueprint in enumerate(BLUEPRINTS):
                unlocked = i <= self.game.unlocked
                sub = "CLEARED" if i < self.game.unlocked else (
                    "OPEN" if unlocked else "LOCKED")
                self.buttons.append(Button(
                    (260, 150 + i * 58, 440, 48),
                    f"{i + 1}. {blueprint['name']}", f"level:{i}",
                    enabled=unlocked, sublabel=sub))
            self.buttons.append(Button((380, 480, 200, 46), "BACK", "back"))

        elif self.screen == "custom":
            self._title("CUSTOM LEVELS", "Files in the custom_levels folder")
            self.custom_paths = custom.custom_files()
            if not self.custom_paths:
                self.buttons.append(Button(
                    (280, 250, 400, 50), "NO LEVELS YET - USE THE EDITOR",
                    "editor"))
            else:
                for i, path in enumerate(self.custom_paths[:8]):
                    try:
                        data = custom.load_blueprint(path)
                        label = str(data.get("name", path.stem))[:38]
                        valid = custom.validate_blueprint(data)[1] is None
                    except (OSError, ValueError):
                        label, valid = f"{path.stem} (INVALID)", False
                    self.buttons.append(Button(
                        (250, 150 + i * 50, 460, 44), label,
                        f"custom:{i}", enabled=valid,
                        sublabel="PLAY" if valid else "BAD FILE"))
                if len(self.custom_paths) > 8:
                    self.notice = "SHOWING FIRST 8 CUSTOM LEVELS"
            self.buttons.append(Button((380, 520, 200, 44), "BACK", "back"))

        elif self.screen == "settings":
            self._title("SETTINGS", "Mouse and keyboard are tuned separately")
            self.sliders.append(Slider(
                (170, 150, 430, 14), "MOUSE SENSITIVITY", "mouse_sensitivity",
                0.0005, 0.0100, lambda v: f"{v:.4f}"))
            self.sliders.append(Slider(
                (170, 210, 430, 14), "KEYBOARD SENSITIVITY",
                "keyboard_sensitivity", 0.5, 6.0, lambda v: f"{v:.1f}"))

            start_y = 285
            for i, (action, label) in enumerate(S.ACTION_LABELS):
                col = i // 5
                row = i % 5
                x = 20 + col * 310
                y = start_y + row * 36
                key_name = pygame.key.name(self.settings.bindings[action]).upper()
                self.buttons.append(Button(
                    (x, y, 300, 30),
                    f"{label}:  {key_name}", f"bind:{action}"))

            self.buttons.append(Button((55, 530, 190, 44), "BACK", "back"))
            self.buttons.append(Button((265, 530, 220, 44),
                                       "RESET DEFAULTS", "reset_bindings"))

        elif self.screen == "clear":
            pass  # overlay buttons are built by build_overlay()

        elif self.screen == "gameover":
            pass

    def _title(self, title, subtitle):
        # Stored and drawn in draw(); this helper just keeps build() readable.
        self.heading = title
        self.subheading = subtitle

    def build_overlay(self):
        self.buttons = []
        if self.screen == "clear":
            self.buttons.append(Button((350, 335, 260, 48), "CONTINUE", "next_level"))
            self.buttons.append(Button((350, 395, 260, 44), "LEVEL SELECT", "levels"))
            self.buttons.append(Button((350, 451, 260, 44), "MAIN MENU", "main"))
        elif self.screen == "gameover":
            self.buttons.append(Button((350, 335, 260, 48), "RETRY LEVEL", "retry"))
            self.buttons.append(Button((350, 395, 260, 44), "MAIN MENU", "main"))

    def show(self, screen):
        self.screen = screen
        self.waiting_for_key = None
        if screen in ("clear", "gameover"):
            self.build_overlay()
        else:
            self.build()

    # -- input --------------------------------------------------------------

    def handle_event(self, event):
        """Return True when the event was consumed by the menu."""
        if event.type == pygame.KEYDOWN:
            if self.waiting_for_key:
                if event.key != pygame.K_ESCAPE:
                    self.settings.rebind(self.waiting_for_key, event.key)
                    self.notice = f"{pygame.key.name(event.key).upper()} BOUND"
                self.waiting_for_key = None
                self.build()
                return True
            if event.key == pygame.K_ESCAPE:
                if self.screen == "main":
                    return False
                self.show("main")
                return True
            return False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = pygame.mouse.get_pos()
            for slider in self.sliders:
                if slider.click(pos, self.settings):
                    return True
            for button in self.buttons:
                if button.enabled and button.rect.collidepoint(pos):
                    self._activate(button.action)
                    return True
        return False

    def _activate(self, action):
        self.notice = ""
        if action == "quit":
            self.game.running = False
        elif action == "back":
            self.show("main")
        elif action == "main":
            self.show("main")
        elif action == "levels":
            self.show("levels")
        elif action == "settings":
            self.show("settings")
        elif action == "random":
            self.game.start_random_level()
        elif action == "custom":
            self.show("custom")
        elif action == "editor":
            self.game.open_editor()
        elif action.startswith("custom:"):
            index = int(action.split(":")[1])
            self.game.play_custom_file(self.custom_paths[index])
        elif action == "reset_progress":
            self.game.reset_campaign()
            self.notice = "CAMPAIGN PROGRESS RESET"
            self.show("levels")
            self.notice = "CAMPAIGN PROGRESS RESET"
        elif action == "reset_bindings":
            self.settings.bindings = dict(S.DEFAULT_BINDINGS)
            self.settings.save()
            self.build()
            self.notice = "BINDINGS RESET"
        elif action == "retry":
            self.game.retry_level()
        elif action == "next_level":
            self.game.next_level()
        elif action.startswith("level:"):
            self.game.start_campaign_level(int(action.split(":")[1]))
        elif action.startswith("bind:"):
            self.waiting_for_key = action.split(":")[1]
            self.notice = "PRESS A KEY (ESC TO CANCEL)"

    # -- drawing ------------------------------------------------------------

    def draw(self, surface, alpha=255):
        fonts = self.assets.fonts
        if self.screen in ("clear", "gameover"):
            self._draw_overlay(surface, alpha)
            return

        background = pygame.Surface((C.WIN_W, C.WIN_H), pygame.SRCALPHA)
        background.fill((12, 14, 20, 246))
        # Decorative bands.
        pygame.draw.rect(background, (125, 40, 40, 120), (0, 0, C.WIN_W, 8))
        pygame.draw.rect(background, (180, 140, 60, 90),
                         (0, C.WIN_H - 8, C.WIN_W, 8))
        surface.blit(background, (0, 0))

        title = fonts["huge"].render(getattr(self, "heading", "DOOM  FPS"),
                                     True, (235, 190, 90))
        sub = fonts["small"].render(getattr(self, "subheading", ""),
                                    True, (165, 170, 180))
        surface.blit(title, (C.WIN_W // 2 - title.get_width() // 2, 42))
        surface.blit(sub, (C.WIN_W // 2 - sub.get_width() // 2, 100))
        pygame.draw.line(surface, (110, 90, 55),
                         (150, 132), (C.WIN_W - 150, 132), 2)

        pos = pygame.mouse.get_pos()
        for slider in self.sliders:
            slider.draw(surface, fonts, self.settings)
        for button in self.buttons:
            selected = (self.waiting_for_key is not None and
                        button.action == f"bind:{self.waiting_for_key}")
            button.draw(surface, fonts, button.rect.collidepoint(pos), selected)

        if self.notice:
            notice = fonts["small"].render(self.notice, True, (255, 220, 110))
            surface.blit(notice, (C.WIN_W // 2 - notice.get_width() // 2,
                                  C.WIN_H - 44))

    def _draw_overlay(self, surface, alpha):
        fonts = self.assets.fonts
        overlay = pygame.Surface((C.WIN_W, C.WIN_H), pygame.SRCALPHA)
        overlay.fill((10, 8, 10, min(alpha, 205)))
        surface.blit(overlay, (0, 0))

        pygame.draw.rect(overlay, (22, 22, 28, 235), (300, 210, 360, 330))
        pygame.draw.rect(overlay, (150, 125, 70, 255), (300, 210, 360, 330), 2)
        surface.blit(overlay, (0, 0))

        if self.screen == "clear":
            title = fonts["big"].render("LEVEL CLEARED", True, (255, 215, 110))
            detail = f"{self.game.level.name}  -  {self.game.player.score} PTS"
        else:
            title = fonts["big"].render("YOU DIED", True, (230, 80, 70))
            detail = f"{self.game.level.name}  -  {self.game.player.score} PTS"
        surface.blit(title, (C.WIN_W // 2 - title.get_width() // 2, 240))
        info = fonts["small"].render(detail, True, (200, 200, 195))
        surface.blit(info, (C.WIN_W // 2 - info.get_width() // 2, 290))

        pos = pygame.mouse.get_pos()
        for button in self.buttons:
            button.draw(surface, fonts, button.rect.collidepoint(pos))
