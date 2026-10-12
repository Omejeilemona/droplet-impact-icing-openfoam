#!/usr/bin/env python3
"""
Animation of the droplet interface (alpha.water = 0.5) as a GIF.

Reads   <case>/postProcessing/interface/<time>/*.raw   (written by controlDict)
Writes  <out>.gif  (default <case>/impact.gif)

The axisymmetric wedge is mirrored about the axis so the full droplet is shown.

usage:  python3 animate.py <case> [--out impact.gif] [--every 5] [--fps 15]
"""
import argparse
import glob
import os
import re

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter


def read_params(case):
    params = {}
    with open(os.path.join(case, "caseParameters")) as f:
        for line in f:
            m = re.match(r"^\s*(\w+)\s+([-+0-9.eE]+)\s*;", line.split("//")[0])
            if m:
                params[m.group(1)] = float(m.group(2))
    return params


def load_frames(case):
    root = os.path.join(case, "postProcessing", "interface")
    frames = []
    for d in glob.glob(os.path.join(root, "*")):
        try:
            t = float(os.path.basename(d))
        except ValueError:
            continue
        pts = []
        for f in glob.glob(os.path.join(d, "**", "*.raw"), recursive=True):
            try:
                a = np.loadtxt(f, comments="#", ndmin=2)
            except ValueError:
                continue
            if a.size:
                pts.append(a[:, :3])
        if pts:
            p = np.vstack(pts)
            frames.append((t, np.hypot(p[:, 0], p[:, 2]), p[:, 1]))
    frames.sort(key=lambda fr: fr[0])
    return frames


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("case")
    ap.add_argument("--out", default=None)
    ap.add_argument("--every", type=int, default=5, help="use every n-th interface sample")
    ap.add_argument("--fps", type=int, default=15)
    a = ap.parse_args()

    p = read_params(a.case)
    R, U0 = p["R"], abs(p["Uimpact"])
    D0 = 2 * R
    t_contact = (p["yc"] - R) / U0
    We = p["rhoL"] * U0**2 * D0 / p["sigma"]
    Re = U0 * D0 / p["nuL"]

    frames = load_frames(a.case)[::a.every]
    if not frames:
        raise SystemExit("no interface data found")

    rmax = max(fr[1].max() for fr in frames) * 1e3
    ymax = max(fr[2].max() for fr in frames) * 1e3
    xl = 1.1 * rmax
    yl = min(1.1 * ymax, p.get("Hmm", 8.0))

    fig, ax = plt.subplots(figsize=(6.4, 6.4 * (yl + 0.3) / (2 * xl) + 0.6), dpi=100)
    ax.set_xlim(-xl, xl)
    ax.set_ylim(-0.15, yl)
    ax.set_aspect("equal")
    ax.axhspan(-0.15, 0, color="0.55")
    ax.axvline(0, color="0.85", lw=0.6, zorder=0)
    ax.set_xlabel("r (mm)")
    ax.set_ylabel("y (mm)")
    ax.set_title(f"Droplet impact, D0 = {D0*1e3:g} mm, U0 = {U0:g} m/s, "
                 f"We = {We:.0f}, Re = {Re:.0f}, θ = {p['theta']:.0f}°", fontsize=9)
    sc = ax.scatter([], [], s=1.2, c="#1f5fa8", lw=0)
    txt = ax.text(0.02, 0.96, "", transform=ax.transAxes, va="top", fontsize=9)
    fig.tight_layout()

    def update(i):
        t, r, y = frames[i]
        xy = np.column_stack([np.r_[r, -r] * 1e3, np.r_[y, y] * 1e3])
        sc.set_offsets(xy)
        ts = (t - t_contact) * U0 / D0
        txt.set_text(f"t = {t*1e3:5.2f} ms   t* = {ts:5.2f}   β = {2*r.max()/D0:4.2f}")
        return sc, txt

    out = a.out or os.path.join(a.case, "impact.gif")
    anim = FuncAnimation(fig, update, frames=len(frames), blit=True)
    anim.save(out, writer=PillowWriter(fps=a.fps))
    print(f"{len(frames)} frames -> {out} ({os.path.getsize(out)/1e6:.1f} MB)")


if __name__ == "__main__":
    main()
