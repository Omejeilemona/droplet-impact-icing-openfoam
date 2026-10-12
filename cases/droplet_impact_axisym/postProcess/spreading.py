#!/usr/bin/env python3
"""
Spreading factor beta(t) = D(t)/D0 from the alpha.water = 0.5 isosurface.

Reads   <case>/postProcessing/interface/<time>/*.raw   (written by controlDict)
Writes  <case>/beta_t.csv, <case>/beta_t.png
        and, with --summary, beta_max vs We against literature correlations.

Two diameters are reported:
  beta       : maximum radial extent of the interface (what a top-view camera sees;
               the quantity used by the beta_max correlations)
  beta_wet   : wetted (contact-line) diameter, interface points in the first cell
               layer above the wall

usage:  python3 spreading.py <case>
        python3 spreading.py <case1> <case2> ... --summary out.png
        python3 spreading.py <case1> <case2> ... --overlay out.png --label nr
"""
import argparse
import glob
import math
import os
import re
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


# ----------------------------------------------------------------------------- input
def read_params(case):
    """Scalar entries of caseParameters (name value;)."""
    params = {}
    with open(os.path.join(case, "caseParameters")) as f:
        for line in f:
            line = line.split("//")[0]
            m = re.match(r"^\s*(\w+)\s+([-+0-9.eE]+)\s*;", line)
            if m:
                params[m.group(1)] = float(m.group(2))
    return params


def read_raw(path):
    """Points (x, y, z) of an OpenFOAM raw surface file; '#' lines are headers."""
    try:
        data = np.loadtxt(path, comments="#", ndmin=2)
    except (ValueError, OSError):
        return np.empty((0, 3))
    if data.size == 0:
        return np.empty((0, 3))
    return data[:, :3]


def spreading_history(case):
    p = read_params(case)
    D0 = 2.0 * p["R"]
    U0 = abs(p["Uimpact"])
    dy = p["Hmm"] * 1e-3 / p["nz"]        # cell height
    t_contact = (p["yc"] - p["R"]) / U0  # free-fall time across the initial gap

    root = os.path.join(case, "postProcessing", "interface")
    rows = []
    for tdir in glob.glob(os.path.join(root, "*")):
        try:
            t = float(os.path.basename(tdir))
        except ValueError:
            continue
        files = glob.glob(os.path.join(tdir, "**", "*.raw"), recursive=True)
        if not files:
            continue
        pts = np.vstack([read_raw(f) for f in files])
        if len(pts) == 0:
            continue
        r = np.hypot(pts[:, 0], pts[:, 2])          # wedge: radius from x and z
        beta = 2.0 * r.max() / D0
        near = r[pts[:, 1] < 1.5 * dy]
        beta_wet = 2.0 * near.max() / D0 if len(near) else 0.0
        tstar = (t - t_contact) * U0 / D0
        rows.append((t, tstar, beta, beta_wet))

    if not rows:
        sys.exit(f"No isosurface data found under {root}")
    rows = np.array(sorted(rows))
    return p, rows


# ----------------------------------------------------------------------------- physics
def dimensionless(p):
    D0 = 2.0 * p["R"]
    U0 = abs(p["Uimpact"])
    We = p["rhoL"] * U0**2 * D0 / p["sigma"]
    Re = U0 * D0 / p["nuL"]
    return We, Re


def correlations(We, Re, theta_deg):
    """beta_max from common correlations."""
    th = math.radians(theta_deg)
    return {
        # Clanet et al., J. Fluid Mech. 517 (2004): capillary regime, We*Re^-0.8 < 1
        "Clanet 2004": 0.9 * We**0.25,
        # Pasandideh-Fard et al., Phys. Fluids 8 (1996): energy balance
        "Pasandideh-Fard 1996": math.sqrt((We + 12.0)
                                          / (3.0 * (1.0 - math.cos(th)) + 4.0 * We / math.sqrt(Re))),
        # Roisman, Phys. Fluids 21 (2009): viscous-capillary
        "Roisman 2009": 0.87 * Re**0.2 - 0.40 * Re**0.4 * We**-0.5,
    }


# ----------------------------------------------------------------------------- output
def single_case(case):
    p, rows = spreading_history(case)
    We, Re = dimensionless(p)
    imax = rows[:, 2].argmax()
    bmax, tmax = rows[imax, 2], rows[imax, 1]

    np.savetxt(os.path.join(case, "beta_t.csv"), rows, delimiter=",",
               header="t_s,t_star,beta,beta_wet", comments="", fmt="%.6e")

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(rows[:, 1], rows[:, 2], label=r"$\beta$ (max extent)")
    ax.plot(rows[:, 1], rows[:, 3], "--", label=r"$\beta_{wet}$ (contact line)")
    ax.set_xlabel(r"$t^* = tU_0/D_0$")
    ax.set_ylabel(r"$\beta = D/D_0$")
    ax.set_xlim(left=0)
    ax.set_title(f"We = {We:.1f}, Re = {Re:.0f}, θ = {p['theta']:.0f}°")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(case, "beta_t.png"), dpi=150)
    plt.close(fig)

    print(f"case     : {case}")
    print(f"We = {We:.1f}   Re = {Re:.0f}   Oh = {math.sqrt(We)/Re:.4f}   "
          f"P = We*Re^-0.8 = {We*Re**-0.8:.3f}")
    print(f"beta_max = {bmax:.3f}  at t* = {tmax:.2f}")
    print("correlation             beta_max   rel. diff")
    for name, val in correlations(We, Re, p["theta"]).items():
        print(f"{name:22s}  {val:8.3f}   {100*(bmax-val)/val:+6.1f} %")
    return p, We, Re, bmax


def summary(results, out):
    We = np.array([r[1] for r in results])
    Re = np.array([r[2] for r in results])
    bm = np.array([r[3] for r in results])
    theta = results[0][0]["theta"]
    order = We.argsort()

    fig, ax = plt.subplots(figsize=(6, 4.5))
    ax.plot(We[order], bm[order], "ko", label="OpenFOAM (interFoam)")
    for name in correlations(1.0, 1.0, theta):
        vals = [correlations(w, r, theta)[name] for w, r in zip(We[order], Re[order])]
        ax.plot(We[order], vals, "-", label=name)
    ax.set_xscale("log")
    ax.set_xlabel("We")
    ax.set_ylabel(r"$\beta_{max}$")
    ax.set_title(f"Maximum spreading, θ = {theta:.0f}°")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)

    print("\n   We       Re    beta_max")
    for i in order:
        print(f"{We[i]:6.1f}  {Re[i]:7.0f}   {bm[i]:6.3f}")
    print(f"summary plot: {out}")


def overlay(cases, out, label):
    """beta(t) of several cases on one plot (mesh study, parameter sweeps)."""
    fig, ax = plt.subplots(figsize=(6, 4))
    print(f"\n{'case':>24s} {label:>8s}  beta_max   t*_max")
    for c in cases:
        p, rows = spreading_history(c)
        val = p[label]
        tag = f"N = {val/6:.0f}" if label == "nr" else f"{label} = {val:g}"
        ax.plot(rows[:, 1], rows[:, 2], label=tag)
        i = rows[:, 2].argmax()
        print(f"{c:>24s} {val:8g}  {rows[i,2]:7.3f}   {rows[i,1]:6.2f}")
    ax.set_xlabel(r"$t^* = tU_0/D_0$")
    ax.set_ylabel(r"$\beta = D/D_0$")
    ax.set_xlim(left=0)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"overlay plot: {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cases", nargs="+")
    ap.add_argument("--summary", metavar="PNG")
    ap.add_argument("--overlay", metavar="PNG")
    ap.add_argument("--label", default="nr",
                    help="caseParameters entry used to label overlay curves")
    a = ap.parse_args()
    results = [single_case(c) for c in a.cases]
    if a.summary:
        summary(results, a.summary)
    if a.overlay:
        overlay(a.cases, a.overlay, a.label)
