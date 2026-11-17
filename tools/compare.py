#!/usr/bin/env python3
# Usage: compare.py DIR_A DIR_B [--out DIR] [--max-offset N]
# Compares the shot_NNN.png sequences from capture.py. Attract-mode timing differs between emulators, so
# the two sequences are aligned: the shot offset k (B index = A index + k) with the lowest mean difference
# over the overlap is chosen, then every aligned pair is diffed. Writes into --out (default DIR_A/../diff):
#   pair_NNN.png  A | B | amplified diff, side by side;   report.txt  per-pair stats.
# Stats per pair: mean abs diff (0-255), % pixels differing > 16, bounding box of differences.
import argparse, glob, os, sys
from PIL import Image, ImageChops, ImageStat
a = argparse.ArgumentParser(); a.add_argument("a"); a.add_argument("b"); a.add_argument("--out"); a.add_argument("--max-offset", type=int, default=15)
a.add_argument("--exact", action="store_true", help="pair shots with identical file names (capture_frames.py output); no alignment search")
o = a.parse_args()
A = sorted(glob.glob(f"{o.a}/shot_*.png")); B = sorted(glob.glob(f"{o.b}/shot_*.png"))
if o.exact:
    common = sorted({os.path.basename(p) for p in A} & {os.path.basename(p) for p in B})
    A = [f"{o.a}/{n}" for n in common]; B = [f"{o.b}/{n}" for n in common]
    names = [n[5:-4] for n in common]
out = o.out or os.path.join(os.path.dirname(os.path.abspath(o.a)), "diff"); os.makedirs(out, exist_ok=True)
for f in glob.glob(f"{out}/pair_*.png"): os.remove(f)
def load(p): return Image.open(p).convert("RGB")
def dist(x, y):
    if x.size != y.size: return 255.0
    return sum(ImageStat.Stat(ImageChops.difference(x, y)).mean) / 3
ia = [load(p) for p in A]; ib = [load(p) for p in B]
print(f"A: {len(ia)} shots {ia[0].size}   B: {len(ib)} shots {ib[0].size}")
if ia[0].size != ib[0].size: print("WARNING: sizes differ; capture both with the same screenshot settings")
best = None
for k in ([0] if o.exact else range(-o.max_offset, o.max_offset + 1)):
    ds = [dist(ia[i], ib[i + k]) for i in range(len(ia)) if 0 <= i + k < len(ib)]
    if len(ds) < (1 if o.exact else 10): continue
    m = sum(ds) / len(ds)
    if best is None or m < best[0]: best = (m, k, len(ds))
m, k, n = best
print(f"best alignment: B = A + {k} shots (mean diff {m:.2f} over {n} pairs)")
lines = [f"alignment k={k} (B index = A index + k), mean diff {m:.3f}", "pair  A  B   meandiff  pct>16  bbox"]
worst = []
for i in range(len(ia)):
    j = i + k
    if not 0 <= j < len(ib) or ia[i].size != ib[j].size: continue
    d = ImageChops.difference(ia[i], ib[j]); md = sum(ImageStat.Stat(d).mean) / 3
    g = d.convert("L"); mask = g.point(lambda v: 255 if v > 16 else 0)
    pct = 100.0 * (mask.histogram()[255]) / (g.size[0] * g.size[1]); bb = mask.getbbox()
    lines.append(f"{i:3d} {i:3d} {j:3d}   {md:7.2f}  {pct:6.2f}  {bb}")
    worst.append((md, i, j))
    w, h = ia[i].size; sheet = Image.new("RGB", (w * 3 + 8, h), (255, 0, 255))
    sheet.paste(ia[i], (0, 0)); sheet.paste(ib[j], (w + 4, 0)); sheet.paste(d.point(lambda v: min(255, v * 4)), (2 * w + 8, 0))
    sheet.save(f"{out}/pair_{names[i] if o.exact else format(i, '03d')}.png")
open(f"{out}/report.txt", "w").write("\n".join(lines) + "\n")
worst.sort(reverse=True)
print("most different pairs (meandiff, A, B):", [(round(x, 2), i, j) for x, i, j in worst[:5]])
print(f"identical-ish pairs (<0.5): {sum(1 for x,_,_ in worst if x < 0.5)}/{len(worst)}")
print(f"report + side-by-side images in {out}")
