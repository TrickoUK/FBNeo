#!/usr/bin/env python3
# Usage: smoke.py <seconds> <romset>... - boot each romset in RetroArch (distrobox mame-dev), check it is
# still alive after N seconds, screenshot via RetroArch's own SCREENSHOT command, then kill it.
# Results go to $OUT (default /tmp/fbneo-smoke).
import os, sys, time, subprocess, re, socket, glob, shutil
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE = os.environ.get("CORE", f"{ROOT}/src/burner/libretro/fbneo_libretro.so")
ROMS = "/var/home/bazzite/Projects/mame-roms/fbneo"
OUT = os.environ.get("OUT", "/tmp/fbneo-smoke"); SHOTS = os.path.join(OUT, "shots")
os.makedirs(SHOTS, exist_ok=True)
secs = int(sys.argv[1]); names = sys.argv[2:]
cfg = os.path.join(OUT, "append.cfg")
open(cfg, "w").write(f'video_vsync = "false"\nnetwork_cmd_enable = "true"\nscreenshot_directory = "{SHOTS}"\nauto_screenshot_filename = "true"\n')

def screenshot(dest):
    before = set(glob.glob(f"{SHOTS}/*.png"))
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.sendto(b"SCREENSHOT", ("127.0.0.1", 55355)); s.close()
    for _ in range(50):
        new = set(glob.glob(f"{SHOTS}/*.png")) - before
        if new:
            time.sleep(0.3); shutil.move(new.pop(), dest); return True
        time.sleep(0.1)
    return False

def pids():
    return subprocess.run(["pgrep", "-x", "retroarch"], capture_output=True, text=True).stdout.split()

for n in names:
    assert not pids(), "retroarch already running"
    logp = os.path.join(OUT, n + ".log")
    p = subprocess.Popen(["distrobox", "enter", "mame-dev", "--", "retroarch", "-v", "--appendconfig", cfg,
                          "-L", CORE, f"{ROMS}/{n}.zip"], stdout=open(logp, "wb"), stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
    time.sleep(secs)
    alive = bool(pids()); shot = screenshot(os.path.join(OUT, n + ".png")) if alive else False
    while pids():
        subprocess.run(["pkill", "-9", "-x", "retroarch"]); time.sleep(0.3)
    p.kill()
    txt = open(logp, "rb").read().decode("latin1")
    bad = [l for l in txt.splitlines() if re.search(r"(?i)fatal|segmentation|core dumped|\[ERROR\]", l)]
    print(f"{n:10} alive_after_{secs}s={alive} screenshot={shot} errors={len(bad)} {bad[:3]}", flush=True)
