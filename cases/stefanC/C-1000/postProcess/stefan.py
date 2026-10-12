#!/usr/bin/env python3
"""
One-phase Stefan problem: liquid at Tm, wall held at Tw < Tm from t = 0.

Analytical front position (Carslaw & Jaeger; Alexiades & Solomon 1993):
    s(t) = 2 lam sqrt(alpha_s t),   alpha_s = k_s / (rho_s c_s)
    lam exp(lam^2) erf(lam) = St / sqrt(pi),   St = c_s (Tm - Tw) / L
Ice temperature:
    T(y, t) = Tw + (Tm - Tw) erf(y / (2 sqrt(alpha_s t))) / erf(lam)

The simulated front is s = V_ice / A, from the iceVolume function object.

usage:  python3 stefan.py <case> [<case2> ...] [--out stefan.png]
"""
import argparse
import glob
import math
import os
import re

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

AREA = 1e-8   # column cross-section [m2] (0.1 mm x 0.1 mm)


def read_params(case):
    p = {}
    with open(os.path.join(case, "caseParameters")) as f:
        for line in f:
            m = re.match(r"^\s*(\w+)\s+([-+0-9.eE]+)\s*;", line.split("//")[0])
            if m:
                p[m.group(1)] = float(m.group(2))
    return p


def stefan_lambda(St):
    f = lambda x: x * math.exp(x * x) * math.erf(x) - St / math.sqrt(math.pi)
    a, b = 1e-6, 5.0
    for _ in range(200):
        m = 0.5 * (a + b)
        if f(a) * f(m) <= 0:
            b = m
        else:
            a = m
    return 0.5 * (a + b)


def analytical(p):
    alpha_s = p["kS"] / (p["rhoS"] * p["CpS"])
    St = p["CpS"] * (p["Tm"] - p["Twall"]) / p["Lf"]
    lam = stefan_lambda(St)
    return alpha_s, St, lam


def front(case):
    files = glob.glob(os.path.join(case, "postProcessing", "iceVolume", "*", "volFieldValue.dat"))
    if not files:
        raise SystemExit(f"no iceVolume data in {case}")
    d = np.vstack([np.loadtxt(f, comments="#", ndmin=2) for f in files])
    d = d[np.argsort(d[:, 0])]
    return d[:, 0], d[:, 1] / AREA


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cases", nargs="+")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    p0 = read_params(a.cases[0])
    alpha_s, St, lam = analytical(p0)
    print(f"St = {St:.4f}   lambda = {lam:.4f}   alpha_ice = {alpha_s:.3e} m2/s")
    print(f"analytical: s(t) = {2*lam*math.sqrt(alpha_s)*1e3:.4f} mm * sqrt(t/s)\n")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    tt = np.linspace(0, 1, 400)
    print(f"{'case':>28s} {'Cfreeze':>9s} {'s(end) mm':>10s} {'exact mm':>9s} {'error':>8s}")
    tmax = 0
    for c in a.cases:
        p = read_params(c)
        t, s = front(c)
        tmax = max(tmax, t.max())
        se = 2 * lam * np.sqrt(alpha_s * t)
        ax1.plot(np.sqrt(t), s * 1e3, label=f"C = {p['Cfreeze']:g} 1/s")
        mask = t > 0.05 * t.max()
        err = 100 * (s[mask] - se[mask]) / se[mask]
        ax2.plot(t[mask], err, label=f"C = {p['Cfreeze']:g} 1/s")
        print(f"{c:>28s} {p['Cfreeze']:9g} {s[-1]*1e3:10.4f} {se[-1]*1e3:9.4f} {err[-1]:+7.2f}%")
    tt = np.linspace(0, tmax, 400)
    ax1.plot(np.sqrt(tt), 2 * lam * np.sqrt(alpha_s * tt) * 1e3, "k--", label="analytical")
    ax1.set_xlabel(r"$\sqrt{t}$ (s$^{1/2}$)")
    ax1.set_ylabel("ice thickness s (mm)")
    ax1.set_title(f"Stefan problem, St = {St:.3f}")
    ax1.legend()
    ax2.axhline(0, color="k", lw=0.8)
    ax2.set_xlabel("t (s)")
    ax2.set_ylabel("error in s (%)")
    ax2.set_title("Front position error")
    ax2.legend()
    fig.tight_layout()
    out = a.out or os.path.join(a.cases[0], "stefan.png")
    fig.savefig(out, dpi=150)
    print(f"\nplot: {out}")


if __name__ == "__main__":
    main()
