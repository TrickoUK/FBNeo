#!/usr/bin/env python3
# Usage: capture_frames.py --core X.so --rom game.zip --out DIR --frames 60:3600:60   (start:stop:step, or a,b,c)
# Frame-exact screenshots: one RetroArch run per frame using --max-frames=N --max-frames-ss, with audio sync and
# vsync off so each run takes ~2s. Output: DIR/shot_FFFFFF.png (F = frame number, native core frame size).
# Same frame number in two cores = same emulated time since launch, so no timing alignment is needed:
#   compare.py DIR_A DIR_B --exact
import argparse, os, sys, subprocess, glob
a = argparse.ArgumentParser()
a.add_argument("--core", required=True); a.add_argument("--rom", required=True); a.add_argument("--out", required=True)
a.add_argument("--frames", required=True)
o = a.parse_args()
if ":" in o.frames:
    s, e, st = map(int, o.frames.split(":")); frames = list(range(s, e + 1, st))
else:
    frames = [int(x) for x in o.frames.split(",")]
OUT = os.path.abspath(o.out); os.makedirs(OUT, exist_ok=True)
for f in glob.glob(f"{OUT}/shot_*.png"): os.remove(f)
cfg = os.path.join(OUT, "append.cfg")
open(cfg, "w").write('video_vsync = "false"\naudio_sync = "false"\naudio_enable = "false"\nvideo_gpu_screenshot = "false"\n'
                     'audio_driver = "null"\nconfig_save_on_exit = "false"\nvideo_shader_enable = "false"\nmenu_enable_widgets = "false"\n')
ok = 0
for n in frames:
    dest = f"{OUT}/shot_{n:06d}.png"
    # Runs normally take ~2s but RetroArch occasionally stalls at startup (random, ~1 in 6), so use a short
    # kill timeout INSIDE the box (no orphans) and retry.
    for attempt in range(4):
        r = subprocess.run(["distrobox", "enter", "mame-dev", "--", "timeout", "-s", "KILL", "8", "retroarch", "-v", "--appendconfig", cfg,
                            f"--max-frames={n}", "--max-frames-ss", f"--max-frames-ss-path={dest}", "-L", o.core, o.rom],
                           stdout=open(f"{OUT}/run.log", "wb"), stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
        if os.path.exists(dest): ok += 1; break
    else: print(f"frame {n}: no screenshot after retries (exit {r.returncode})")
print(f"{ok}/{len(frames)} shots in {OUT}")
