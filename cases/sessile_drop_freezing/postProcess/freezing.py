#!/usr/bin/env python3
"""
Sessile droplet freezing: frozen fraction, droplet height, final shape, animation.

Reads   <case>/postProcessing/phaseVolumes/*/volFieldValue.dat
        <case>/postProcessing/interfaces/<time>/*outline*.raw   (alpha.air = 0.5)
        <case>/postProcessing/interfaces/<time>/*iceFront*.raw  (alpha.solid = 0.5)
Writes  <case>/freezing.png, <case>/freezing.gif (with --gif)

usage:  python3 freezing.py <case> [--gif] [--every 2] [--fps 12]
"""
import argparse
import glob
import os
import re

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def read_params(case):
    p = {}
    with open(os.path.join(case, "caseParameters")) as f:
        for line in f:
            m = re.match(r"^\s*(\w+)\s+([-+0-9.eE]+)\s*;", line.split("//")[0])
            if m:
                p[m.group(1)] = float(m.group(2))
    return p


def phase_volumes(case):
    files = glob.glob(os.path.join(case, "postProcessing", "phaseVolumes", "*", "volFieldValue.dat"))
    if not files:
        raise SystemExit("no phaseVolumes data")
    d = np.vstack([np.loadtxt(f, comments="#", ndmin=2) for f in files])
    d = d[np.argsort(d[:, 0])]
    return d[:, 0], d[:, 1], d[:, 2]          # t, V_liquid, V_solid (wedge volumes)


def surfaces(case, name):
    out = []
    for d in glob.glob(os.path.join(case, "postProcessing", "interfaces", "*")):
        try:
            t = float(os.path.basename(d))
        except ValueError:
            continue
        pts = []
        for f in glob.glob(os.path.join(d, "**", f"*{name}*.raw"), recursive=True):
            try:
                a = np.loadtxt(f, comments="#", ndmin=2)
            except ValueError:
                continue
            if a.size:
                pts.append(a[:, :3])
        if pts:
            p = np.vstack(pts)
            out.append((t, np.hypot(p[:, 0], p[:, 2]), p[:, 1]))
    out.sort(key=lambda x: x[0])
    return out


def apex_height(r, y, R, ncells):
    dx = 3 * R / ncells
    near = y[r < 2 * dx]
    return near.max() if near.size else np.nan


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("case")
    ap.add_argument("--gif", action="store_true")
    ap.add_argument("--every", type=int, default=2)
    ap.add_argument("--fps", type=int, default=12)
    a = ap.parse_args()

    p = read_params(a.case)
    R = p["R"]
    rhoL, rhoS = p["rhoL"], p["rhoS"]

    t, VL, VS = phase_volumes(a.case)
    m0 = rhoL * VL[0] + rhoS * VS[0]
    frac = rhoS * VS / (rhoL * VL + rhoS * VS)          # frozen mass fraction
    mass_err = 100 * ((rhoL * VL + rhoS * VS) / m0 - 1)
    vol_ratio = (VL + VS) / (VL[0] + VS[0])
    i99 = np.argmax(frac >= 0.99) if (frac >= 0.99).any() else None

    outl = surfaces(a.case, "outline")
    front = surfaces(a.case, "iceFront")
    th = np.array([o[0] for o in outl])
    h = np.array([apex_height(o[1], o[2], R, p["nCells"]) for o in outl])

    print(f"droplet R = {R*1e3:g} mm,  plate {p['Twall']-273.15:+.0f} C")
    print(f"frozen mass fraction at t = {t[-1]:.2f} s: {frac[-1]:.3f}")
    if i99 is not None:
        print(f"freezing time (99 % frozen): {t[i99]:.2f} s")
    print(f"apex height: initial {h[0]/R:.3f} R, final {h[-1]/R:.3f} R")
    print(f"volume ratio V/V0 at end: {vol_ratio[-1]:.4f}  "
          f"(full freezing would give {rhoL/rhoS:.4f})")
    print(f"mass change at end: {mass_err[-1]:+.3f} %")

    fig, ax = plt.subplots(1, 3, figsize=(14, 4))
    ax[0].plot(t, frac)
    ax[0].set_xlabel("t (s)")
    ax[0].set_ylabel("frozen mass fraction")
    ax[0].set_ylim(0, 1.02)
    ax[1].plot(th, h / R)
    ax[1].set_xlabel("t (s)")
    ax[1].set_ylabel("apex height / R")
    for k in np.linspace(0, len(front) - 1, min(6, len(front))).astype(int) if front else []:
        tf, rf, yf = front[k]
        ax[2].scatter(np.r_[rf, -rf] * 1e3, np.r_[yf, yf] * 1e3, s=0.6, c="0.5", lw=0)
    for o, col, lab in [(outl[0], "#1f5fa8", "initial"), (outl[-1], "k", "final")]:
        ax[2].scatter(np.r_[o[1], -o[1]] * 1e3, np.r_[o[2], o[2]] * 1e3, s=1, c=col, lw=0, label=lab)
    ax[2].set_aspect("equal")
    ax[2].set_xlabel("r (mm)")
    ax[2].set_ylabel("y (mm)")
    ax[2].set_title("outline (initial, final) and ice fronts (grey)", fontsize=9)
    ax[2].legend(markerscale=6, fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(a.case, "freezing.png"), dpi=150)
    print(f"plot: {os.path.join(a.case, 'freezing.png')}")

    if a.gif:
        from matplotlib.animation import FuncAnimation, PillowWriter
        fdict = {round(f[0], 6): f for f in front}
        frames = outl[::a.every]
        lim = 1.15 * max(max(o[1].max(), o[2].max()) for o in outl) * 1e3
        fig, axg = plt.subplots(figsize=(6.4, 3.8), dpi=100)
        axg.set_xlim(-lim, lim)
        axg.set_ylim(-0.08, lim * 1.05)
        axg.set_aspect("equal")
        axg.axhspan(-0.08, 0, color="#9db8d9")
        axg.set_xlabel("r (mm)")
        axg.set_ylabel("y (mm)")
        axg.set_title(f"Water droplet freezing on a {p['Twall']-273.15:+.0f} °C plate "
                      f"(R = {R*1e3:g} mm)", fontsize=9)
        so = axg.scatter([], [], s=1.4, c="#1f5fa8", lw=0)
        sf = axg.scatter([], [], s=1.4, c="0.35", lw=0)
        txt = axg.text(0.02, 0.95, "", transform=axg.transAxes, va="top", fontsize=9)
        fig.tight_layout()

        def update(i):
            to, ro, yo = frames[i]
            so.set_offsets(np.column_stack([np.r_[ro, -ro] * 1e3, np.r_[yo, yo] * 1e3]))
            f = fdict.get(round(to, 6))
            sf.set_offsets(np.column_stack([np.r_[f[1], -f[1]] * 1e3, np.r_[f[2], f[2]] * 1e3])
                           if f else np.empty((0, 2)))
            fr = np.interp(to, t, frac)
            txt.set_text(f"t = {to:4.2f} s   frozen = {100*fr:3.0f} %")
            return so, sf, txt

        anim = FuncAnimation(fig, update, frames=len(frames), blit=True)
        gif = os.path.join(a.case, "freezing.gif")
        anim.save(gif, writer=PillowWriter(fps=a.fps))
        print(f"animation: {gif} ({os.path.getsize(gif)/1e6:.1f} MB)")


if __name__ == "__main__":
    main()
