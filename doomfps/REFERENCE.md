# Project Reference — DOOM-style FPS

Handoff document for anyone continuing this codebase. For user-facing docs see
`README.md`; for the chronological record of decisions and changes see
`TRANSCRIPT.md`. This file answers "where is X and how does it work?".

There is **no git repository** here, so `TRANSCRIPT.md` is the change history.

---

## Quick start

```bash
.venv\Scripts\python.exe main.py     # Windows
```

Three separate `pygame.Window`s are created:

| Window | Size | Purpose |
| --- | --- | --- |
| `DOOM // FIRST PERSON` | 960×600 (`WIN_W×WIN_H`) | Menu, editor, 3D view + HUD |
| `MAP` | 280×280 | Fog-of-war minimap |
| `INVENTORY` | 600×560 | Vitals, two-column inventory, stats, controls |

The 3D view is rendered at 480×300 and scaled ×2 for a retro look (`SCALE = 2`).

---

## File map

| Path | Role |
| --- | --- |
| `main.py` | Entry point: `Game().run()` |
| `doomfps/config.py` | All balance/layout constants, weapon + enemy stats, pickup labels |
| `doomfps/game.py` | **Central hub**: state machine, input, simulation, pickups/items, level lifecycle, drawing dispatch, main loop |
| `doomfps/entities.py` | `Player`, `Enemy`, `Pickup`, `Particle` data and behaviour |
| `doomfps/level.py` | Campaign blueprints, random generation, `Level` collision/raycasting/pathfinding |
| `doomfps/renderer.py` | Raycast walls, billboard sprites, held weapon, muzzle flash |
| `doomfps/assets.py` | All textures/sprites/weapons generated procedurally; fonts; cached weapon icons/silhouettes |
| `doomfps/ui.py` | `draw_hud`, `draw_minimap`, `draw_inventory` |
| `doomfps/menu.py` | Main menu, level select, Custom Levels, Settings/rebinding, clear/gameover overlays |
| `doomfps/editor.py` | Grid level editor with tool palette, drag paint/erase, save/test |
| `doomfps/custom.py` | Custom level JSON load/save/validation |
| `doomfps/settings.py` | Persistent settings, key bindings, campaign progress |
| `campaign_progress.json` | Saved highest unlocked campaign index |
| `settings.json` | Saved sensitivities + bindings (created on first rebind/slider change) |
| `custom_levels/*.json` | Shareable custom levels |

---

## Runtime architecture

`Game.__init__` creates the windows/assets/settings/menu and loads level 1 as a
menu backdrop. `Game.run()` is a fixed loop:

```python
dt = min(0.05, clock.tick(FPS) / 1000.0)
handle_events()
update(dt)
render_all()
```

States in `Game.state`:

- `menu` — `menu.draw()` on the main window; side windows show STANDBY.
- `editor` — `editor.draw()` on the main window; side windows show STANDBY.
- `playing` — full simulation + raycast rendering + HUD + side windows.
- `cleared` / `gameover` — last rendered frame with a menu overlay drawn on top.

`render_all()` dispatches by state (see `game.py` lines ~550–593). Mouse capture
is handled in `capture_mouse()` / `release_mouse()` and re-asserted each frame
in `update()`.

---

## Level lifecycle and origin routing

`Game.level_origin` records where the current level came from. Launchers set it:

| Launcher | Origin | Completion destination |
| --- | --- | --- |
| `start_campaign_level()` | `campaign` | Clear overlay → next level / level select / menu |
| `start_random_level()` | `random` | Clear overlay → menu via `next_level()` |
| `play_custom_blueprint(bp, origin="custom")` | `custom` | Straight to the Custom Levels screen with "LEVEL CLEARED" notice |
| `play_custom_blueprint(bp, origin="editor")` (from `LevelEditor.test()`) | `editor` | Straight back into the editor with "TEST COMPLETE - LEVEL CLEARED" |

`complete_level()` branches on this field before the generic clear overlay.
`retry_level()` deliberately does **not** reset it, so retrying an editor test
still returns to the editor on completion.

Campaign progress is saved in `complete_level()` only for `campaign_mode`.

---

## Input and bindings

`doomfps/settings.py`:

- `DEFAULT_BINDINGS` maps actions to `pygame.K_*` constants. Defaults: WASD move,
  ←/→ turn, Space fire, Shift run, 1/2/3 weapons, **E use medkit**, **Q use armor kit**.
- `ACTION_LABELS` drives the Settings screen rows (13 actions).
- `rebind()` prevents duplicate keys by swapping with the previous owner.
- Saved to `settings.json`; `load()` tolerates missing/corrupt files.
- The Settings screen (`menu.py`) lays rows out in **3 columns × 5 rows**.

Event handling split:

- `Game.handle_events()` — discrete `KEYDOWN`/mouse events: escape, fire edge,
  the two item-use keys, weapon slots, mouse capture/fire/wheel.
- `Game.update()` — polled `pygame.key.get_pressed()` for movement, running and
  keyboard turning. Turning uses the bound arrows only; there are no hardcoded
  Q/E turn keys any more.

Held item keys use key repeat, so holding E/Q can consume several kits; no
cooldown exists yet.

---

## Player, combat, and items

`entities.py::Player` important fields:

- `health`, `armor` (caps `MAX_HEALTH`/`MAX_ARMOR` = 100).
- `ammo = {"bullets", "shells"}`, `weapons_owned`, `weapon`.
- `medkits`, `armor_kits` (caps `MAX_MEDKITS`/`MAX_ARMOR_KITS` = 6).
- `score`, `kills`, `items`; recoil/muzzle/bob/damage_flash timers.

Key methods:

- `take_damage(amount)` — armor absorbs `ARMOR_ABSORB` (0.4) of the hit first.
- `add_ammo(kind, amount)` — caps bullets 250 / shells 60.
- `use_medkit()` / `use_armor()` — refuse when empty or at full vitals, otherwise
  consume one and heal `MEDKIT_HEAL` (28) / add `ARMOR_BOOST` (35).
- `switch_weapon()` / `cycle_weapon()`.

Weapon definitions (damage, cooldown, spread, pellets, range, kick, auto) live in
`config.py::WEAPONS`. Firing is `Game.try_fire()` plus `Game._burst()` particles.
Enemies use `Enemy.update()` with sight cone/range (config `ENEMY_FOV`, sight per
archetype), `Level.line_of_sight()` and `Level.find_path()`. `on_enemy_killed()`
adds score/kills and may drop a health or ammo pickup.

Pickups (`Game.collect()`):

- Health/armor pickups **always store** a kit if below the cap; at the cap the
  pickup is left on the floor with a rate-limited "LIMIT REACHED" message.
- Ammo, shells and weapons apply immediately as before.
- `Game.use_item(kind)` consumes stored kits and shows "NO ...", "ALREADY FULL"
  or the heal/armor amount message.

---

## Inventory screen (`ui.py::draw_inventory`)

Window is **600×560** — wider than tall. Layout:

- Header `y=0..46`, vitals across the top (`y=54..108`).
- Divider at `y=120`; two columns of width `(W-48)//2`.
- **Left column**: three weapon cards. Owned weapons show their scaled view-model
  icon, name and ammo. Locked weapons show a flat black silhouette (generated in
  `Assets` with `BLEND_RGBA_MULT`) and "NOT FOUND".
- **Right column**, top to bottom: bullets, shells, medkits (`NN / 06`), armor
  kits (`NN / 06`), with E/Q use hints on the kit rows.
- Divider at `y=386`, stats line at `y=418` (kills/items/score/time).
- Three-line controls panel pinned to the bottom (`H-74`).

All key names are read from `game.settings.bindings`, so rebinds show up in the UI.

---

## Levels, custom files, and the editor

`level.py`:

- `BLUEPRINTS` — five hand-designed campaign missions (rooms/corridors/blocks/enemy count/pickups).
- `build_level(blueprint, stage=0, seed=None)` — turns a blueprint into a grid + spawns.
- `generate_random_blueprint(seed=None)` — procedural connected dungeon.
- `Level` — `grid`, `visited`, `exit`, `exit_open`, plus `move()`, `ray_cast()`,
  `line_of_sight()`, `find_path()` (A*), `mark_visited()`, `open_exit()`,
  `at_exit()`.

`custom.py`:

- Files live in `custom_levels/*.json`; names are sanitized.
- `validate_blueprint()` requires a 24×24 grid, ≥4 floor cells, spawn and exit on
  floor and reachable, every enemy reachable, and returns a cleaned blueprint.
- Blueprint fields: `name`, `theme`, `grid`, `preserve_grid`, `rooms`, `corridors`,
  `blocks`, `player_spawn [x,y,angle]`, `exit [x,y]`, `enemy_spawns [[x,y,kind]]`,
  `pickup_spawns [[x,y,kind]]`.

`editor.py` (`GRID_X=20`, `GRID_Y=60`, `CELL=22`):

- 12 tools in `TOOLS`; left click/drag paints the selected tool.
- Right click **or right-drag** erases via `MOUSEMOTION.buttons[2]`.
- Buttons: wall style, save, test, new/clear, back to menu. `Ctrl+S` also saves.
- `test()` validates then calls `game.play_custom_blueprint(bp, origin="editor")`.

---

## Rendering and assets

`renderer.py::Renderer`:

- Ceiling gradient + floor banding cached at construction.
- `_draw_walls()` DDA raycasting into `zbuffer`; `_draw_sprite()` billboards
  enemies/pickups/particles with shade variants from `assets`.
- `_draw_weapon()` blits the held view-model with bob/recoil and draws the muzzle
  flash. Per-weapon `weapon_offsets` and `muzzle_offsets` are in `__init__`.
- Chaingun barrels are foreshortened and have **no visible muzzle openings**;
  the flash is aligned to the flat barrel tip (y offset 50).

`assets.py::Assets` generates everything at startup: wall textures, creature and
pickup sprites with shade variants, weapon view models, particles, exits, fonts,
and cached `weapon_icons` / `weapon_silhouettes` for the inventory.

---

## Persistence

| File | Written by | Contents |
| --- | --- | --- |
| `settings.json` | `Settings.save()` | `mouse_sensitivity`, `keyboard_sensitivity`, `bindings` |
| `campaign_progress.json` | `save_progress()` | `{"unlocked": n}` |
| `custom_levels/<name>.json` | `custom.save_blueprint()` | Validated blueprint |

All loaders tolerate missing/invalid files.

---

## Key constants cheat sheet (`config.py`)

| Constant | Value | Meaning |
| --- | --- | --- |
| `VIEW_W`, `VIEW_H`, `SCALE` | 480, 300, 2 | Internal render size and upscale |
| `WIN_W`, `WIN_H` | 960, 600 | Main window |
| `MINIMAP_W/H` | 280, 280 | Map window |
| `INVENTORY_W/H` | 600, 560 | Inventory window |
| `MAP_W`, `MAP_H` | 24, 24 | Grid size |
| `MAX_HEALTH`, `MAX_ARMOR` | 100, 100 | Vitals caps |
| `ARMOR_ABSORB` | 0.4 | Damage absorbed by armor |
| `MEDKIT_HEAL`, `ARMOR_BOOST` | 28, 35 | Item effects |
| `MAX_MEDKITS`, `MAX_ARMOR_KITS` | 6, 6 | Carry caps |
| `WALK_SPEED`, `RUN_MULT` | 3.2, 1.7 | Movement |
| `FPS` | 60 | Tick rate |
| `ENEMY_FOV`, `ENEMY_MAP_RANGE` | 140°, 8.0 | Awareness / radar |
| `PICKUP_INFO` | table | Labels and colors for pickups |

---

## "Where do I change…?"

| Task | File |
| --- | --- |
| Balance damage/healing/caps | `config.py` |
| Add/rename a key binding | `settings.py` (`DEFAULT_BINDINGS`, `ACTION_LABELS`) + `game.py` input if it needs new handling |
| Change inventory layout | `ui.py::draw_inventory` + `config.py` window constants |
| Change weapon sprite/model | `assets.py::_view_*` and the offsets in `renderer.py` |
| Change item pickup/use rules | `game.py::collect` / `use_item`, `entities.py::Player` |
| Change completion destinations | `game.py::complete_level`, `level_origin` setters |
| Change editor tools/behaviour | `editor.py::TOOLS`, `handle_event` |
| Add a campaign mission | `level.py::BLUEPRINTS` |
| Change custom level rules | `custom.py::validate_blueprint` |
| Change settings screen layout | `menu.py::build` (`screen == "settings"`) |

---

## Verification notes

- No automated test suite exists. Use
  `.venv\Scripts\python.exe -m py_compile doomfps/*.py` for syntax checks.
- Previous sessions used small headless scripts in
  `C:\Users\ethan\AppData\Local\Temp\opencode\` with `SDL_VIDEODRIVER=dummy` to
  exercise state/geometry/UI without opening windows.
- The game has **not** been launched for a full playthrough check; sprite
  appearance is currently inferred from geometry tests and user feedback.
- Open items are tracked at the bottom of `TRANSCRIPT.md`.
