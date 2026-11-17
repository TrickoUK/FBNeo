#!/usr/bin/env python3
"""Dump a per-retro_run fingerprint (video CRC, audio sample count and CRC) of a libretro core, to compare two builds.

Usage (inside mame-dev): python3 -I tools/seqdump.py CORE.so ROM.zip SAVEDIR OUT.txt FRAMES [boot script]
The boot script uses the lag_measure.py syntax (run:/tap:); input is otherwise none. One line per run:
  run_no video_crc audio_frames audio_crc
Set SEQ_PCM=file to also dump the raw audio. Uses lag_host.py from my-docs/tools (see my-docs/game-frame-timings.md).
"""
import os, sys, zlib, ctypes as C
sys.path.insert(0, "/var/home/bazzite/Projects/libretro/mame/my-docs/tools")
import lag_host
from lag_host import Host, ABATCH

core, rom, savedir, out, frames = sys.argv[1:6]
script = sys.argv[6] if len(sys.argv) > 6 else ""
h = Host(core, "/var/home/bazzite/.config/retroarch/system", savedir)
acc = {"n": 0, "crc": 0}
pcm = open(os.environ["SEQ_PCM"], "wb") if os.environ.get("SEQ_PCM") else None  # optional raw S16 stereo dump
def batch(data, n):
    acc["n"] += n
    raw = C.string_at(data, n * 4)
    acc["crc"] = zlib.crc32(raw, acc["crc"])
    if pcm: pcm.write(raw)
    return n
cb = ABATCH(batch)
h.lib.retro_set_audio_sample_batch(cb)
h.load(rom)
for step in [s for s in script.split(",") if s]:
    p = step.split(":")
    if p[0] == "run": h.run(int(p[1]))
    elif p[0] == "tap":
        h.press(p[1]); h.run(int(p[3]) if len(p) > 3 else 6); h.press(); h.run(int(p[2]) if len(p) > 2 else 90)
lines = []
for i in range(int(frames)):
    acc["n"] = 0; acc["crc"] = 0
    h.run(1)
    lines.append(f"{i} {zlib.crc32(h.frame[3]) if h.frame else 0} {acc['n']} {acc['crc']}")
open(out, "w").write("\n".join(lines) + "\n")
if pcm: pcm.close()
h.close()
