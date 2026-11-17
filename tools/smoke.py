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
PORT = 55400 + os.getpid() % 100  # own port so we never hit another session's RetroArch
PIDF = os.path.join(OUT, "ra.pid")
open(cfg, "w").write(f'video_vsync = "false"\nnetwork_cmd_enable = "true"\nnetwork_cmd_port = "{PORT}"\nconfig_save_on_exit = "false"\nscreenshot_directory = "{SHOTS}"\nauto_screenshot_filename = "true"\n')

def screenshot(dest):
    before = set(glob.glob(f"{SHOTS}/*.png"))
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.sendto(b"SCREENSHOT", ("127.0.0.1", PORT)); s.close()
    for _ in range(50):
        new = set(glob.glob(f"{SHOTS}/*.png")) - before
        if new:
            time.sleep(0.3); shutil.move(new.pop(), dest); return True
        time.sleep(0.1)
    return False

def mypid():
    try: return int(open(PIDF).read())
    except Exception: return 0
def alive_():
    try: os.kill(mypid(), 0); return mypid() > 0
    except OSError: return False

for n in names:
    logp = os.path.join(OUT, n + ".log")
    p = subprocess.Popen(["distrobox", "enter", "mame-dev", "--", "sh", "-c", 'echo $$ > "$0"; exec timeout -s KILL 300 retroarch -v --appendconfig "$1" -L "$2" "$3"',
                          PIDF, cfg, CORE, f"{ROMS}/{n}.zip"], stdout=open(logp, "wb"), stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
    time.sleep(secs)
    alive = alive_(); shot = screenshot(os.path.join(OUT, n + ".png")) if alive else False
    if alive_(): os.kill(mypid(), 9)  # only our own process
    p.kill()
    txt = open(logp, "rb").read().decode("latin1")
    bad = [l for l in txt.splitlines() if re.search(r"(?i)fatal|segmentation|core dumped|\[ERROR\]", l)]
    print(f"{n:10} alive_after_{secs}s={alive} screenshot={shot} errors={len(bad)} {bad[:3]}", flush=True)
