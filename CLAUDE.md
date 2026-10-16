# CLAUDE.md

Fork of FinalBurn Neo (https://github.com/TrickoUK/FBNeo), used here for the **libretro core** (`src/burner/libretro/`). Other front-ends (win32, SDL) are not built on this machine.

Sibling project with the same workflow: the libretro MAME fork at `/var/home/bazzite/Projects/libretro/mame` (its `fork-specific/tools/smoke.py` is the model for the smoke test below).

## Build (must happen inside the distrobox)

The host has glibc 2.43 but RetroArch runs inside the Distrobox `mame-dev` (Fedora rawhide, glibc 2.44). Build in the box so the core matches the RetroArch that loads it.

```
cd src/burner/libretro
distrobox enter mame-dev -- make -j6
```

- Output: `src/burner/libretro/fbneo_libretro.so`.
- Use a modest `-j` (MAME needed `-j4`; `-j8`+ tripped the harness low-memory guard and killed builds).
- Missing build deps: `distrobox enter mame-dev -- sudo dnf install -y <pkg>`. Layering packages on the immutable host needs a reboot, so don't.
- Make does not rebuild when only flags/defines change; delete the stale `.o` files.
- If a build was force-killed, run `find . -name "*.o" -size 0 -delete` and rebuild, otherwise truncated objects link fine and fail at dlopen with undefined symbols.
- A clean compile proves little for emulator code: always boot a real game.

## Run / test

- RetroArch is the native one inside `mame-dev`. $HOME and `/var/home/...` paths are identical inside and outside the box.
- Test ROMs live in `/var/home/bazzite/Projects/mame-roms/fbneo` (e.g. `1942.zip`). When the user says "launch game X", use `<that dir>/X.zip`. Launch from there; never copy ROMs elsewhere.
- Launch (absolute paths, `timeout` goes INSIDE the box or the emulator gets orphaned):

```
distrobox enter mame-dev -- timeout 60 retroarch -v \
  -L /var/home/bazzite/Projects/libretro/FBNeo/src/burner/libretro/fbneo_libretro.so \
  /var/home/bazzite/Projects/mame-roms/fbneo/1942.zip
```

- Afterwards `pgrep -a retroarch` and `pkill -9 -x retroarch` any leftovers.
- Config: `~/.config/retroarch/retroarch.cfg`; core options in `~/.config/retroarch/config/FinalBurn Neo/FinalBurn Neo.opt` (edit only between runs, RetroArch rewrites it); system dir `~/.config/retroarch/system/`; states in `~/.config/retroarch/states/`.
- FBNeo specifics: needs `~/.config/retroarch/system/fbneo/` for samples/hiscores/NeoGeo-style BIOS if a game wants them (check the `-v` log for missing-file messages).
- Not truly headless: needs the user's Wayland session. A hidden/minimised window can stall on vsync; set `video_vsync = "false"` in the append config.
- The Flatpak RetroArch cannot load host/box-built cores (glibc mismatch). Don't use it.

### Screenshots / verification

Use RetroArch's own network command only, never desktop capture tools (spectacle, grim) which can grab the wrong window.

Append config (`--appendconfig <file>`):
```
video_vsync = "false"
network_cmd_enable = "true"
screenshot_directory = "<dir>"
auto_screenshot_filename = "true"
```
Then send UDP `SCREENSHOT` (or `PAUSE_TOGGLE` first) to `127.0.0.1:55355` with python3 `socket` (no `nc` installed). `tools/smoke.py <secs> <romset>...` (CORE/OUT env overrides) does boot + wait + screenshot + kill + log scan.

A good boot: `-v` log shows the core loading, a geometry line, and no `fatal`/`segmentation`/`[ERROR]` lines.

Test saves (`.state`, nvram) are disposable; delete stale ones if they block a boot.

## Conventions

- Match surrounding code style; FBNeo drivers live in `src/burn/drv/`, libretro glue in `src/burner/libretro/` (`libretro.cpp`, `retro_input.cpp`, `retro_memory.cpp`).
- Comments: capitalise TODO/FIXME/NOTE; describe what the code does, not what changed.
- Git: do NOT add Co-Authored-By or other Claude trailers to commits. Do not commit or push unless asked.
- Don't pick laserdisc, music/rhythm or similar exotic titles as test games.
- Host CPU governor is powersave, so performance numbers are noisy; don't blame it for slow frames without evidence.
