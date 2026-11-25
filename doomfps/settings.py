"""Persistent settings, key bindings and campaign progress."""

import json
from pathlib import Path

import pygame

from . import config as C

_ROOT = Path(__file__).resolve().parent.parent
SETTINGS_FILE = _ROOT / "settings.json"
PROGRESS_FILE = _ROOT / "campaign_progress.json"

DEFAULT_BINDINGS = {
    "forward": pygame.K_w,
    "back": pygame.K_s,
    "strafe_left": pygame.K_a,
    "strafe_right": pygame.K_d,
    "turn_left": pygame.K_LEFT,
    "turn_right": pygame.K_RIGHT,
    "use_health": pygame.K_e,
    "use_armor": pygame.K_q,
    "fire": pygame.K_SPACE,
    "run": pygame.K_LSHIFT,
    "weapon1": pygame.K_1,
    "weapon2": pygame.K_2,
    "weapon3": pygame.K_3,
}

ACTION_LABELS = [
    ("forward", "Move forward"),
    ("back", "Move back"),
    ("strafe_left", "Strafe left"),
    ("strafe_right", "Strafe right"),
    ("turn_left", "Turn left"),
    ("turn_right", "Turn right"),
    ("use_health", "Use medkit"),
    ("use_armor", "Use armor kit"),
    ("fire", "Fire weapon"),
    ("run", "Run"),
    ("weapon1", "Select pistol"),
    ("weapon2", "Select shotgun"),
    ("weapon3", "Select chaingun"),
]


class Settings:
    def __init__(self):
        self.mouse_sensitivity = 0.0024
        self.keyboard_sensitivity = 2.4
        self.bindings = dict(DEFAULT_BINDINGS)
        self.load()

    def load(self):
        try:
            with SETTINGS_FILE.open(encoding="utf-8") as fp:
                data = json.load(fp)
        except (OSError, ValueError, TypeError):
            return
        self.mouse_sensitivity = _clamp(
            float(data.get("mouse_sensitivity", self.mouse_sensitivity)),
            0.0005, 0.0100)
        self.keyboard_sensitivity = _clamp(
            float(data.get("keyboard_sensitivity", self.keyboard_sensitivity)),
            0.5, 6.0)
        saved = data.get("bindings", {})
        for action, default in DEFAULT_BINDINGS.items():
            value = saved.get(action, default)
            if isinstance(value, int) and value > 0:
                self.bindings[action] = value

    def save(self):
        data = {
            "mouse_sensitivity": round(self.mouse_sensitivity, 5),
            "keyboard_sensitivity": round(self.keyboard_sensitivity, 2),
            "bindings": self.bindings,
        }
        try:
            with SETTINGS_FILE.open("w", encoding="utf-8") as fp:
                json.dump(data, fp, indent=2)
        except OSError:
            pass

    def rebind(self, action, key):
        if action not in self.bindings or not 0 < key < 1_000_000:
            return False
        # Don't allow two actions to share a key.
        for other, bound in self.bindings.items():
            if other != action and bound == key:
                self.bindings[other] = self.bindings[action]
                break
        self.bindings[action] = key
        self.save()
        return True


def _clamp(value, low, high):
    return max(low, min(high, value))


def load_progress(level_count):
    try:
        with PROGRESS_FILE.open(encoding="utf-8") as fp:
            unlocked = int(json.load(fp).get("unlocked", 0))
    except (OSError, ValueError, TypeError):
        return 0
    return max(0, min(level_count - 1, unlocked))


def save_progress(unlocked):
    try:
        with PROGRESS_FILE.open("w", encoding="utf-8") as fp:
            json.dump({"unlocked": unlocked}, fp, indent=2)
    except OSError:
        pass
