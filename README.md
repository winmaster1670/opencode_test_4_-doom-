# DOOM-style FPS (three windows)

A small, self-contained first-person shooter built with **pygame-ce** using a
Wolfenstein/Doom-style raycasting renderer. No external assets: every texture,
sprite and weapon is generated procedurally at startup.

## Windows

1. **DOOM // FIRST PERSON** — the 3D view, weapon, crosshair and HUD.
2. **MAP** — top-down minimap with fog of war, enemies, items and your position.
3. **INVENTORY** — two columns: weapons on the left (locked ones shown as black
   silhouettes), and bullets, shells, medkits and armor kits on the right.
   Vitals and run stats sit above/below both columns (updates live).

## Run

```bash
.venv/bin/python main.py
```

## Main menu

The first-person window starts on a menu:

- **Start campaign** — five hand-designed missions. Missions unlock as you clear
  them; progress is saved to `campaign_progress.json`.
- **Random level** — generates a fresh connected dungeon with random rooms,
  corridors, pillars, theme and spawns every time.
- **Play custom levels** — lists shareable `.json` files from the
  `custom_levels/` folder and lets you play them; clearing one returns to this
  list.
- **Level editor** — paint floors, walls, the player spawn, exit, enemies and
  pickups on a 24×24 grid. Save exports a level file into `custom_levels/`;
  **Test** plays it immediately. Copy that folder/file to a friend to share it.
- **Settings** — separate mouse and keyboard sensitivity sliders, plus rebinding
  for every action (move, turn, use medkit, use armor kit, fire, run, weapon
  slots). Saved to `settings.json`.
- **Restart campaign** — re-locks every mission except the first.
- **Quit** — exit the game.

After clearing or dying you get an overlay with retry / next level / menu buttons.

## Controls (defaults)

| Input | Action |
| --- | --- |
| `W` / `S` | Move forward / back |
| `A` / `D` | Strafe left / right |
| Mouse | Look (click the game window to capture) |
| `←` / `→` | Turn (works without mouse capture) |
| Left click / `Space` | Fire |
| `1` `2` `3` or mouse wheel | Switch weapon |
| `E` | Use a stored medkit |
| `Q` | Use a stored armor kit |
| `Shift` | Run |
| `Esc` | Release mouse, then open the menu |

All keyboard controls can be changed in **Settings**. The pointer is confined to the game view while
captured (it is re-centered every frame). Clicking another window releases it;
click the game view again to re-capture.

## Level editor

- Click or drag on the grid to paint with the selected tool; right-click or
  right-drag erases.
- Tools include floor, four wall styles, player spawn, exit, Imps/Barons and all
  pickup types. Use **Wall** repeatedly with **Wall style** to change texture.
- Click the name field to type a level name. **Save level** writes
  `custom_levels/<name>.json` after validating that the exit *and every enemy*
  are reachable from the player spawn (an unreachable imp would make the exit
  impossible to unlock). **Test level** plays the current design without saving;
  clearing it drops you back into the editor. `Ctrl+S` also saves.

## Gameplay

- Start with a pistol; find the **shotgun** and **chaingun** to expand the
  inventory. Pick up medkits, armor and ammo scattered through the dungeon.
  Medkits and armor are stored as supplies instead of being used automatically —
  press `E` or `Q` when you need them. You can carry up to 6 of each; extra
  pickups are left on the floor.
- Enemies only wake when they actually **see** you (inside their vision cone,
  in range and unobstructed), or when you hit them. Gunfire no longer alerts
  them through walls. Once alerted they use pathfinding to navigate around
  walls to your last known position, and attack at close range. Armor absorbs
  part of incoming damage.
- The minimap only reveals enemies within a short radar range, even in explored
  areas. Kills grant score, and enemies can drop extra pickups.
- Killing every imp **unlocks the exit door** (shown in red/green on the
  minimap). Walk into the green exit to finish the mission — enemies alone no
  longer end the level. The locked door physically blocks you until it opens.
- Weapons, ammo, armor, stored medkits/armor kits and score carry over to the
  next campaign mission. Dying (or choosing Retry) resets you to the pistol and
  starting ammo.

## Layout

```
main.py              launcher
doomfps/
  config.py          constants, weapon and enemy stats
  assets.py          procedural textures, sprites, shaded variants, fonts
  level.py           campaign blueprints, random generation, collision, ray casting
  entities.py        player, enemies, pickups, particles
  renderer.py        raycast walls, billboard sprites, held weapon
  ui.py              HUD, minimap, inventory
  menu.py            main menu, level select, settings, overlays
  editor.py          grid-based custom level editor
  custom.py          custom level JSON I/O and validation
  settings.py        saved settings, bindings and campaign progress
  game.py            state, input, combat and main loop
custom_levels/       shareable custom level .json files (created on first save)
```
