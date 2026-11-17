#!/usr/bin/env python3
# Usage: capture.py --core X.so --rom game.zip --out DIR [--start 5] [--interval 1] [--count 30]
# Boots a libretro core in RetroArch (distrobox mame-dev), waits --start seconds, then takes --count
# screenshots --interval seconds apart using RetroArch's own SCREENSHOT UDP command (never desktop
# capture). Files: DIR/shot_NNN.png (+ DIR/times.txt with the wall-clock offset of each), DIR/run.log.
# The append config forces software-frame screenshots (video_gpu_screenshot=false), so shots are the
# core's native frame regardless of window size. Works for any core, so the same script drives FBNeo and MAME for comparisons (see compare.py).
import argparse, os, sys, time, subprocess, re, socket, glob, shutil
a = argparse.ArgumentParser()
a.add_argument("--core", required=True); a.add_argument("--rom", required=True); a.add_argument("--out", required=True)
a.add_argument("--start", type=float, default=5); a.add_argument("--interval", type=float, default=1)
a.add_argument("--count", type=int, default=30)
o = a.parse_args()
OUT = os.path.abspath(o.out); RAW = os.path.join(OUT, "raw"); os.makedirs(RAW, exist_ok=True)
for f in glob.glob(f"{RAW}/*.png") + glob.glob(f"{OUT}/shot_*.png"): os.remove(f)
PORT = 55400 + os.getpid() % 100  # own port so we never hit another session's RetroArch
PIDF = os.path.join(OUT, "ra.pid")
cfg = os.path.join(OUT, "append.cfg")
open(cfg, "w").write(f'video_vsync = "false"\nvideo_gpu_screenshot = "false"\nvideo_shader_enable = "false"\nmenu_enable_widgets = "false"\nnetwork_cmd_enable = "true"\nnetwork_cmd_port = "{PORT}"\nconfig_save_on_exit = "false"\nscreenshot_directory = "{RAW}"\nauto_screenshot_filename = "true"\n')

def cmd(c):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.sendto(c.encode(), ("127.0.0.1", PORT)); s.close()

def shot(dest):
    before = set(glob.glob(f"{RAW}/*.png")); cmd("SCREENSHOT")
    for _ in range(50):
        new = set(glob.glob(f"{RAW}/*.png")) - before
        if new:
            time.sleep(0.2); shutil.move(new.pop(), dest); return True
        time.sleep(0.1)
    return False

def mypid():
    try: return int(open(PIDF).read())
    except Exception: return 0
def alive():
    pid = mypid()
    try: os.kill(pid, 0); return pid > 0
    except OSError: return False
log = os.path.join(OUT, "run.log")
t0 = time.time()
p = subprocess.Popen(["distrobox", "enter", "mame-dev", "--", "sh", "-c", 'echo $$ > "$0"; exec timeout -s KILL 300 retroarch -v --appendconfig "$1" -L "$2" "$3"', PIDF, cfg, o.core, o.rom],
                     stdout=open(log, "wb"), stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
times = open(os.path.join(OUT, "times.txt"), "w"); ok = 0
try:
    time.sleep(o.start)
    for i in range(o.count):
        target = o.start + i * o.interval
        time.sleep(max(0, t0 + target - time.time()))
        if not alive(): print("retroarch exited early"); break
        if shot(os.path.join(OUT, f"shot_{i:03d}.png")):
            ok += 1; times.write(f"shot_{i:03d} {time.time()-t0:.2f}\n")
finally:
    pid = mypid()  # kill only the process we started
    if pid and alive(): os.kill(pid, 9)
    p.kill(); shutil.rmtree(RAW, ignore_errors=True)
txt = open(log, "rb").read().decode("latin1")
bad = [l for l in txt.splitlines() if re.search(r"(?i)fatal|segmentation|core dumped|\[ERROR\]", l)]
print(f"{ok}/{o.count} shots in {OUT}; log errors={len(bad)} {bad[:3]}")
