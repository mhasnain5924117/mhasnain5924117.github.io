#!/usr/bin/env python3
"""Render the four research animations shown on the portfolio site.

Each animation is a 1920x1080, 30 fps dashboard-style animation: a swept parameter,
a schematic of the physical scenario, a live field computed from a simplified
model, and a result plot that draws itself as the parameter changes. The fields
and curves are illustrative (computed from reduced-order models for
presentation), not reported research data.

Usage:
    python3 render_animations.py --preview            # PNG stills into ./out/preview
    python3 render_animations.py --render             # MP4s + posters + VTT into ./out
    python3 render_animations.py --render --out ../../docs/assets/videos
    python3 render_animations.py --animation tree --render

Dependencies: Python 3.10+, Pillow, NumPy, matplotlib (colormaps and contours),
ffmpeg on PATH, and the Inter font family.
"""
from __future__ import annotations

import argparse
import math
import subprocess
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache
from pathlib import Path

import numpy as np
from matplotlib import colormaps
from matplotlib.colors import LinearSegmentedColormap
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import contourpy

HERE = Path(__file__).resolve().parent
W, H, FPS = 1920, 1080, 30

BG = "#F4F3EF"
CARD = "#FFFFFF"
INK = "#1E2B36"
INK2 = "#33414C"
MUTED = "#5B6B74"
MAROON = "#500000"
TEAL = "#007F87"
GOLD = "#B8862B"
BLUE = "#2E6FA8"
RED = "#B8323C"
LINE = "#DCE1E3"
SOLID = "#E6E9EB"

FONT_DIRS = [
    Path("/usr/share/fonts/truetype/macos"),
    Path("/usr/share/fonts/truetype/inter"),
    Path.home() / ".fonts",
]


@lru_cache(None)
def font(size: float, weight: str = "regular") -> ImageFont.FreeTypeFont:
    name = {"regular": "Inter-Regular.ttf", "medium": "Inter-Medium.ttf",
            "semibold": "Inter-SemiBold.ttf", "bold": "Inter-Bold.ttf"}[weight]
    for d in FONT_DIRS:
        if (d / name).exists():
            return ImageFont.truetype(str(d / name), int(round(size)))
    raise FileNotFoundError(f"Inter font not found: {name}")


# --------------------------------------------------------------------------- #
# Drawing helpers
# --------------------------------------------------------------------------- #
def T(d, xy, s, size=24, color=INK, weight="regular", anchor="la"):
    d.text(xy, str(s), font=font(size, weight), fill=color, anchor=anchor)


def text_width(s, size, weight="regular"):
    return font(size, weight).getlength(str(s))


def para(d, s, x, y, width, size=24, color=INK, weight="regular", leading=1.3):
    words, row = str(s).split(), ""
    f = font(size, weight)
    for word in words:
        cand = (row + " " + word).strip()
        if f.getlength(cand) > width and row:
            d.text((x, y), row, font=f, fill=color)
            y += round(size * leading)
            row = word
        else:
            row = cand
    if row:
        d.text((x, y), row, font=f, fill=color)
    return y + round(size * leading)


def line(d, pts, color=INK, width=2):
    d.line([tuple(map(float, p)) for p in pts], fill=color, width=int(round(width)), joint="curve")


def dashed(d, a, b, color=INK, width=2, dash=9, gap=7):
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    L = float(np.linalg.norm(b - a))
    if L < 1e-6:
        return
    v = (b - a) / L
    s = 0.0
    while s < L:
        e = min(L, s + dash)
        d.line([tuple(a + v * s), tuple(a + v * e)], fill=color, width=width)
        s += dash + gap


def dot(d, x, y, r, fill, outline=None, width=1):
    d.ellipse((x - r, y - r, x + r, y + r), fill=fill, outline=outline, width=width)


def arrow(d, a, b, color=INK, width=3, head=11):
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    v = b - a
    n = np.linalg.norm(v)
    if n < 1e-6:
        return
    v /= n
    p = np.array([-v[1], v[0]])
    line(d, [a, b - v * head * 0.6], color, width)
    d.polygon([tuple(b), tuple(b - head * v + head * 0.45 * p), tuple(b - head * v - head * 0.45 * p)], fill=color)


def motion(d, a, b, t, color=GOLD, count=3, speed=0.3, width=3, head=11, radius=4):
    """Arrow with tracer dots moving along it."""
    arrow(d, a, b, color, width, head)
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    for j in range(count):
        p = (t * speed + j / count) % 1.0
        q = a + (b - a) * p
        dot(d, q[0], q[1], radius, color)


def smooth(x):
    x = min(1.0, max(0.0, float(x)))
    return x * x * (3 - 2 * x)


def ease(x):
    """Smoother ease-in-out (quintic)."""
    x = min(1.0, max(0.0, float(x)))
    return x * x * x * (x * (6 * x - 15) + 10)


def sweep(t, keys):
    """Piecewise eased interpolation through (time, value) keyframes."""
    if t <= keys[0][0]:
        return keys[0][1]
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t <= t1:
            return v0 + (v1 - v0) * ease((t - t0) / max(t1 - t0, 1e-9))
    return keys[-1][1]


def hex_rgba(c, a=255):
    c = c.lstrip("#")
    return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16), a)


def overlay(im, box, fn):
    """Draw with alpha onto a transparent layer and composite into im at box."""
    x, y, w, h = [int(round(v)) for v in box]
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    fn(ImageDraw.Draw(layer), layer)
    im.alpha_composite(layer, dest=(x, y))


@lru_cache(None)
def shadow_layer(w, h, radius=18, blur=16, alpha=46):
    pad = blur * 3
    layer = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(layer).rounded_rectangle((pad, pad + 6, pad + w, pad + h + 6), radius, fill=(20, 30, 40, alpha))
    return layer.filter(ImageFilter.GaussianBlur(blur)), pad


def card(im, box, radius=18):
    x, y, w, h = box
    sh, pad = shadow_layer(w, h, radius)
    im.alpha_composite(sh, dest=(int(x - pad), int(y - pad)))
    ImageDraw.Draw(im).rounded_rectangle((x, y, x + w, y + h), radius, fill=CARD)


def card_header(d, box, index, title, subtitle):
    x, y, w, h = box
    T(d, (x + 24, y + 30), f"{index:02d}", 26, MAROON, "bold")
    T(d, (x + 72, y + 24), title, 34, INK, "bold")
    T(d, (x + 24, y + 74), subtitle, 22, MUTED)
    line(d, [(x + 24, y + 112), (x + w - 24, y + 112)], LINE, 2)


# --------------------------------------------------------------------------- #
# Colormaps and field images
# --------------------------------------------------------------------------- #
@lru_cache(None)
def lut(name):
    if name == "flow":
        cm = LinearSegmentedColormap.from_list("flow", ["#3B2A6E", "#2A4F8F", "#2A86A6", "#3EB3A3", "#A6CF5E", "#F2CF4B", "#E8842B"])
    elif name == "heat":
        cm = LinearSegmentedColormap.from_list("heat", ["#223D78", "#2E6FB0", "#36AEBA", "#9AD36E", "#F2D64B", "#F0862C", "#C9382F", "#6E0E12"])
    else:
        cm = colormaps[name]
    return (cm(np.linspace(0, 1, 256))[:, :3] * 255).astype(np.uint8)


def field_image(arr, vmin, vmax, cmap, mask=None):
    idx = np.clip((arr - vmin) / (vmax - vmin), 0, 1)
    rgb = lut(cmap)[(idx * 255).astype(np.uint8)]
    a = np.full(arr.shape, 255, np.uint8) if mask is None else (mask * 255).astype(np.uint8)
    return Image.fromarray(np.dstack([rgb, a]), "RGBA")


def colorbar(im, d, box, cmap, vmin, vmax, ticks, label, fmt="{:g}", note=None):
    x, y, w, h = box
    grad = np.tile(np.linspace(0, 1, 256)[None, :], (2, 1))
    bar = field_image(grad, 0, 1, cmap).resize((int(w), int(h)), Image.Resampling.BILINEAR)
    im.alpha_composite(bar, dest=(int(x), int(y)))
    T(d, (x, y - 36), label, 22, INK2, "medium")
    for v in ticks:
        px = x + (v - vmin) / (vmax - vmin) * w
        T(d, (px, y + h + 6), fmt.format(v), 18, MUTED, anchor="ma")
    if note:
        T(d, (x + w, y - 36), note, 18, MUTED, anchor="ra")


def contour_lines(xs, ys, Z, level):
    return contourpy.contour_generator(x=xs, y=ys, z=Z).lines(level)


# --------------------------------------------------------------------------- #
# Simple plot helper
# --------------------------------------------------------------------------- #
class Plot:
    def __init__(self, d, box, xlim, ylim):
        self.d = d
        self.x, self.y, self.w, self.h = box
        self.xlim, self.ylim = xlim, ylim

    def px(self, xv, yv):
        fx = (xv - self.xlim[0]) / (self.xlim[1] - self.xlim[0])
        fy = (yv - self.ylim[0]) / (self.ylim[1] - self.ylim[0])
        return (self.x + fx * self.w, self.y + self.h - fy * self.h)

    def axes(self, xticks, yticks, xlabel, ylabel, xfmt="{:g}", yfmt="{:g}"):
        d = self.d
        for v in xticks:
            px, _ = self.px(v, self.ylim[0])
            line(d, [(px, self.y), (px, self.y + self.h)], "#ECEFF0", 1)
            T(d, (px, self.y + self.h + 8), xfmt.format(v), 18, MUTED, anchor="ma")
        for v in yticks:
            _, py = self.px(self.xlim[0], v)
            line(d, [(self.x, py), (self.x + self.w, py)], "#ECEFF0", 1)
            T(d, (self.x - 8, py), yfmt.format(v), 18, MUTED, anchor="rm")
        d.rectangle((self.x, self.y, self.x + self.w, self.y + self.h), outline="#C9D0D3", width=1)
        T(d, (self.x + self.w / 2, self.y + self.h + 32), xlabel, 20, INK2, anchor="ma")
        T(d, (self.x - 8, self.y - 30), ylabel, 20, INK2, anchor="la")

    def curve(self, xs, ys, color, width=3, dash=False):
        pts = [self.px(a, b) for a, b in zip(xs, ys) if self.xlim[0] <= a <= self.xlim[1]]
        if len(pts) < 2:
            return
        if dash:
            for a, b in zip(pts, pts[1:]):
                dashed(self.d, a, b, color, width)
        else:
            line(self.d, pts, color, width)

    def hline(self, yv, color, width=2, dash=True):
        a, b = self.px(self.xlim[0], yv), self.px(self.xlim[1], yv)
        (dashed if dash else line)(self.d, a, b, color, width) if dash else line(self.d, [a, b], color, width)


# --------------------------------------------------------------------------- #
# Animation base class: chrome shared by all four
# --------------------------------------------------------------------------- #
KPI_BOX = (60, 205, 1800, 114)
CARDS = [(60, 342, 440, 520), (530, 342, 720, 520), (1280, 342, 580, 520)]


class Animation:
    key = "base"
    file = "Animation"
    duration = 30.0
    eyebrow = "MUHAMMAD HASNAIN  /  RESEARCH PORTFOLIO"
    tag = ""
    title = ""
    subtitle = ""
    authors = ""
    meta_right = ""
    footnote = ""
    card_titles = [("", ""), ("", ""), ("", "")]
    poster_time = 3.0
    chapters: list[tuple[float, str]] = []   # (start time, takeaway sentence)
    captions: list[tuple[float, float, str]] = []

    def __init__(self):
        self.setup()
        self._static = None

    def setup(self):
        pass

    # ---- static chrome -------------------------------------------------- #
    def static(self):
        if self._static is not None:
            return self._static
        im = Image.new("RGBA", (W, H), hex_rgba(BG))
        d = ImageDraw.Draw(im)
        d.rectangle((0, 0, W, 9), fill=MAROON)
        T(d, (56, 30), self.eyebrow, 21, MAROON, "bold")
        T(d, (1864, 30), self.tag, 20, MUTED, "medium", anchor="ra")
        T(d, (54, 64), self.title, 58, INK, "bold")
        T(d, (58, 134), self.subtitle, 28, MUTED)
        line(d, [(56, 186), (1864, 186)], LINE, 2)
        card(im, KPI_BOX, 16)
        for box, (title, sub), i in zip(CARDS, self.card_titles, (1, 2, 3)):
            card(im, box)
            card_header(ImageDraw.Draw(im), box, i, title, sub)
        d = ImageDraw.Draw(im)
        line(d, [(56, 892), (1864, 892)], LINE, 2)
        T(d, (56, 958), self.footnote, 20, MUTED)
        T(d, (56, 1004), self.authors, 21, INK2)
        T(d, (1864, 1004), self.meta_right, 21, MUTED, anchor="ra")
        self._static = im
        return im

    # ---- per-frame hooks ------------------------------------------------- #
    def kpi(self, im, d, t):
        pass

    def card1(self, im, d, box, t):
        pass

    def card2(self, im, d, box, t):
        pass

    def card3(self, im, d, box, t):
        pass

    def takeaway(self, im, t):
        """Crossfade between chapter sentences."""
        fade = 0.6
        for i, (t0, s) in enumerate(self.chapters):
            t1 = self.chapters[i + 1][0] if i + 1 < len(self.chapters) else 1e9
            a = min(1.0, (t - t0) / fade if i > 0 else 1.0) if t >= t0 else 0.0
            a = min(a, 1.0 if t < t1 else max(0.0, 1 - (t - t1) / fade))
            if a <= 0:
                continue
            def fn(dd, layer, s=s, a=a):
                dd.text((0, 0), s, font=font(31, "bold"), fill=hex_rgba(INK, int(255 * ease(a))))
            overlay(im, (56, 906, 1800, 44), fn)

    def frame(self, t):
        im = self.static().copy()
        d = ImageDraw.Draw(im)
        self.kpi(im, d, t)
        for box, fn in zip(CARDS, (self.card1, self.card2, self.card3)):
            fn(im, d, box, t)
        self.takeaway(im, t)
        a = min(1.0, t / 0.7, (self.duration - t) / 0.9)
        if a < 1:
            im = Image.blend(Image.new("RGBA", (W, H), hex_rgba(BG)), im, max(0.0, ease(a)))
        return im.convert("RGB")

    # ---- KPI strip shared drawing --------------------------------------- #
    def kpi_strip(self, d, label, value, unit, delta, slider, mid, right):
        x, y, w, h = KPI_BOX
        T(d, (x + 26, y + 20), label, 19, MUTED, "semibold")
        T(d, (x + 26, y + 44), value, 54, MAROON, "bold")
        vx = x + 26 + text_width(value, 54, "bold") + 16
        T(d, (vx, y + 71), unit, 26, MUTED)
        if delta:
            dx = vx + text_width(unit, 26) + 26
            T(d, (dx, y + 60), delta[0], 23, MAROON, "bold")
            T(d, (dx, y + 88), delta[1], 17, MUTED)
        # slider
        lo, hi, cur, ref, ref_label, lab_lo, lab_hi, lab = slider
        sx0, sx1, sy = x + 420, x + 1000, y + 70
        T(d, (sx0, y + 20), lab, 19, MUTED, "semibold")
        line(d, [(sx0, sy), (sx1, sy)], "#D5DADC", 6)
        fx = lambda v: sx0 + (v - lo) / (hi - lo) * (sx1 - sx0)
        if ref is not None:
            line(d, [(fx(ref), sy - 14), (fx(ref), sy + 14)], GOLD, 3)
            T(d, (sx1, y + 20), ref_label, 19, GOLD, "bold", anchor="ra")
            T(d, (fx(ref), sy + 22), f"{ref:g}", 17, GOLD, "semibold", anchor="ma")
            line(d, [(fx(min(ref, cur)), sy), (fx(max(ref, cur)), sy)], MAROON, 6)
        else:
            line(d, [(fx(lo), sy), (fx(cur), sy)], MAROON, 6)
        dot(d, fx(cur), sy, 9, MAROON, CARD, 3)
        T(d, (sx0, sy + 22), lab_lo, 17, MUTED, anchor="la")
        T(d, (sx1, sy + 22), lab_hi, 17, MUTED, anchor="ra")
        # dividers and info boxes
        line(d, [(x + 1052, y + 22), (x + 1052, y + h - 22)], LINE, 2)
        T(d, (x + 1080, y + 28), mid[0], 30, INK, "bold")
        T(d, (x + 1080, y + 70), mid[1], 20, MUTED)
        line(d, [(x + 1400, y + 22), (x + 1400, y + h - 22)], LINE, 2)
        T(d, (x + 1428, y + 26), right[0], 18, MAROON, "bold")
        T(d, (x + 1428, y + 52), right[1], 30, INK, "bold")
        T(d, (x + 1428, y + 88), right[2], 18, MUTED)


# --------------------------------------------------------------------------- #
# ANIMATION 1: Backward-facing step, geometry generalization
# --------------------------------------------------------------------------- #
def lr_model(h, re):
    """Illustrative reattachment length [mm] for step height h [mm] at Reynolds number re."""
    return h * (0.95 + 0.0128 * re) * (0.74 + 0.052 * h)


class BFSAnimation(Animation):
    key = "bfs"
    file = "bfs-geometry-generalization"
    duration = 36.0
    tag = "SCIENTIFIC MACHINE LEARNING  |  CFD SURROGATES"
    title = "Generalizing beyond a single geometry"
    subtitle = "Physics-regularized graph neural surrogate for backward-facing step flow"
    authors = "M. Hasnain  ·  N. K. Anand  ·  P. Kumar  ·  A. Srinivasa  ·  S. Ji"
    meta_right = "2D steady laminar flow  |  h = 2.9–6.9 mm"
    footnote = "Illustrative animation: the flow field, graph, and parity values are schematic for presentation and are not reported data."
    card_titles = [("Geometry", "Fixed inlet height, variable step"),
                   ("Velocity field", "Illustrative steady flow with moving tracers"),
                   ("Reattachment parity", "Prediction against the CFD reference")]
    poster_time = 20.0
    H_KEYS = [(0, 4.9), (2.0, 4.9), (9.0, 2.9), (11.0, 2.9), (21.0, 6.9), (23.0, 6.9), (30.5, 4.9), (36, 4.9)]
    chapters = [
        (0.0, "One surrogate, trained on a single step height."),
        (2.6, "A smaller step shortens the recirculation zone, and the surrogate follows."),
        (11.6, "A step 40% taller than anything seen in training stretches reattachment downstream."),
        (23.6, "Back at the training height: geometry, flow structure, and reattachment change together."),
        (31.0, "Geometry-generalizable surrogates make shape sweeps possible at a fraction of CFD cost."),
    ]
    captions = [
        (0, 2.6, "A graph neural surrogate trained on a single backward-facing step height, at Reynolds number 125."),
        (2.6, 11.6, "The step is lowered to 2.9 millimetres. The recirculation bubble shrinks and reattachment moves upstream."),
        (11.6, 23.6, "The step is raised to 6.9 millimetres, 40 percent beyond training. Reattachment moves downstream and the prediction stays close to the CFD reference."),
        (23.6, 31.0, "Returning to the training height. Each point on the parity plot compares predicted and CFD reattachment length."),
        (31.0, 36, "Geometry-generalizable surrogates make rapid shape sweeps possible at a fraction of the cost of CFD."),
    ]

    def setup(self):
        self.rng = np.random.default_rng(7)
        self.n_part = 90
        self.part = None
        self.last_t = None
        self.nx, self.ny = 300, 110
        # synthetic parity data set
        rng = np.random.default_rng(3)
        self.points = []
        for re in (125, 175, 225, 275, 325, 375):
            for h in np.linspace(2.9, 6.9, 9):
                cfd = lr_model(h, re)
                err = 0.07 * math.sin(1.7 * h + re / 90) + 0.03 * math.cos(2.3 * h) + rng.normal(0, 0.02)
                self.points.append((h, re, cfd, cfd * (1 + err)))

    def h_of(self, t):
        return sweep(t, self.H_KEYS)

    @staticmethod
    def gns_error(h):
        return 0.07 * math.sin(1.7 * h + 125 / 90) + 0.03 * math.cos(2.3 * h) + 0.012

    # ---- flow field ------------------------------------------------------ #
    def flow(self, h):
        Hc = 5.2 + h
        xs = np.linspace(-6, 24, self.nx)
        ys = np.linspace(0, Hc, self.ny)
        X, Y = np.meshgrid(xs, ys)
        Lr = lr_model(h, 125)
        s = np.clip(X / Lr, 0, 1)
        s = s * s * (3 - 2 * s)
        yd = h * (1 - s) ** 1.15
        yd = np.where(X < 0, h, yd)
        eta = np.clip((Y - yd) / np.maximum(Hc - yd, 1e-6), 0, 1)
        psi_main = eta ** 2 * (3 - 2 * eta)
        etab = np.clip(Y / np.maximum(yd, 1e-6), 0, 1)
        A = 0.0052 * yd * np.sin(np.pi * np.clip(X / Lr, 0, 1)) ** 0.8
        psi_b = -A * 16 * etab ** 2 * (1 - etab) ** 2
        psi = np.where(Y >= yd, psi_main, psi_b)
        solid = (X < 0) & (Y < h)
        psi[solid] = 0
        dy = ys[1] - ys[0]
        dx = xs[1] - xs[0]
        u = np.gradient(psi, dy, axis=0) * 5.2
        v = -np.gradient(psi, dx, axis=1) * 5.2
        u[solid] = 0
        v[solid] = 0
        return xs, ys, psi, u, v, solid, Lr, Hc

    def advect(self, t, xs, ys, u, v, h, Hc, Lr):
        dt = 0 if self.last_t is None else max(0.0, t - self.last_t)
        if self.part is None or dt > 0.5:
            self.part = np.column_stack([self.rng.uniform(-6, 24, self.n_part), self.rng.uniform(0, Hc, self.n_part)])
        p = self.part
        speed = 7.0  # mm per second for u/Uin = 1
        if dt > 0:
            def vel(pts):
                ix = np.clip((pts[:, 0] - xs[0]) / (xs[-1] - xs[0]) * (len(xs) - 1), 0, len(xs) - 1.001)
                iy = np.clip((pts[:, 1] - ys[0]) / (ys[-1] - ys[0]) * (len(ys) - 1), 0, len(ys) - 1.001)
                i0, j0 = iy.astype(int), ix.astype(int)
                fy, fx = iy - i0, ix - j0
                def bil(F):
                    return (F[i0, j0] * (1 - fx) * (1 - fy) + F[i0, j0 + 1] * fx * (1 - fy)
                            + F[i0 + 1, j0] * (1 - fx) * fy + F[i0 + 1, j0 + 1] * fx * fy)
                return np.column_stack([bil(u), bil(v)]) * speed
            k1 = vel(p)
            k2 = vel(p + 0.5 * dt * k1)
            p = p + dt * k2
        # reseed particles that left the domain or sit in the solid
        bad = (p[:, 0] > 24) | (p[:, 0] < -6) | (p[:, 1] < 0) | (p[:, 1] > Hc) | ((p[:, 0] < 0) & (p[:, 1] < h))
        slow = np.hypot(*(vel(p).T)) < 0.15 if dt > 0 else np.zeros(len(p), bool)
        bad |= slow & (self.rng.uniform(size=len(p)) < 0.01)
        n = int(bad.sum())
        if n:
            new = np.empty((n, 2))
            bubble = self.rng.uniform(size=n) < 0.3
            nb = int(bubble.sum())
            new[~bubble, 0] = -6 + self.rng.uniform(0, 0.3, n - nb)
            new[~bubble, 1] = self.rng.uniform(h + 0.1, Hc - 0.1, n - nb)
            new[bubble, 0] = self.rng.uniform(0.25, 0.75, nb) * Lr
            new[bubble, 1] = self.rng.uniform(0.15, 0.7, nb) * h
            p[bad] = new
        self.part = p
        self.last_t = t
        return p

    # ---- KPI ------------------------------------------------------------- #
    def kpi(self, im, d, t):
        h = self.h_of(t)
        delta = (h - 4.9) / 4.9 * 100
        tagline = "LARGER UNSEEN GEOMETRY" if h > 4.95 else "SMALLER UNSEEN GEOMETRY" if h < 4.85 else "TRAINING GEOMETRY"
        self.kpi_strip(d, "STEP HEIGHT", f"{h:.2f}", "mm", (f"{delta:+.1f}%", "vs. training"),
                       (2.9, 6.9, h, 4.9, "h = 4.9 mm", "2.9", "6.9 mm", "TRAINED AT ONE HEIGHT"),
                       ("Re = 125", "Held fixed during the sweep"),
                       (tagline, "Training: Re = 100–300", "Single geometry, five Reynolds numbers"))

    # ---- Card 1: geometry graph ----------------------------------------- #
    def card1(self, im, d, box, t):
        x, y, w, h_box = box
        h = self.h_of(t)
        gx, gy, gw, gh = x + 48, y + 152, 345, 200
        s = gh / (5.2 + 6.9)
        inlet_top = gy
        inlet_floor = gy + 5.2 * s
        floor = gy + (5.2 + h) * s
        xstep = gx + 0.3 * gw
        # solid regions
        d.rectangle((gx, inlet_floor, xstep, gy + gh + 28), fill=SOLID)
        d.rectangle((xstep, floor, gx + gw, gy + gh + 28), fill=SOLID)
        # graph nodes/edges
        def fn(dd, layer):
            cell = 1.05 * s
            cols = np.arange(0, gw + 1, cell)
            rows = np.arange(0, (5.2 + h) * s + 0.1, cell)
            pts = []
            for cx in cols:
                for cy in rows:
                    X, Y = gx + cx, inlet_top + cy
                    if X < xstep and Y > inlet_floor + 1:
                        continue
                    if Y > floor + 1:
                        continue
                    pts.append((X, Y))
            P = np.array(pts)
            for (X, Y) in pts:
                for ddx, ddy in ((cell, 0), (0, cell), (cell, cell)):
                    X2, Y2 = X + ddx, Y + ddy
                    if X2 > gx + gw + 1 or Y2 > floor + 1 or (X2 < xstep and Y2 > inlet_floor + 1):
                        continue
                    col = (0, 127, 135, 70 if ddx and ddy else 120)
                    dd.line([(X - gx + 0, Y - inlet_top + 0), (X2 - gx, Y2 - inlet_top)], fill=col, width=1)
            for (X, Y) in pts:
                dd.ellipse((X - gx - 2.2, Y - inlet_top - 2.2, X - gx + 2.2, Y - inlet_top + 2.2), fill=(0, 127, 135, 230))
        overlay(im, (gx, inlet_top, gw + 4, gh + 4), fn)
        # walls
        line(d, [(gx, inlet_top), (gx + gw, inlet_top)], INK2, 3)
        line(d, [(gx, inlet_floor), (xstep, inlet_floor), (xstep, floor), (gx + gw, floor)], INK2, 3)
        # inlet arrows
        for k in range(3):
            yy = inlet_top + (k + 1) * (inlet_floor - inlet_top) / 4
            arrow(d, (gx - 36, yy), (gx - 6, yy), TEAL, 2, 8)
        T(d, (gx, gy - 28), "FLOW", 19, TEAL, "bold")
        arrow(d, (gx + 62, gy - 18), (gx + 92, gy - 18), TEAL, 2, 8)
        T(d, (gx + gw, gy - 28), "Inlet height: 5.2 mm", 19, MUTED, anchor="ra")
        # training height dashed
        ytrain = gy + (5.2 + 4.9) * s
        dashed(d, (xstep + 4, ytrain), (gx + gw, ytrain), GOLD, 2, 8, 6)
        # h dimension
        hx = xstep - 24
        arrow(d, (hx, inlet_floor + 2), (hx, floor - 2), MAROON, 2, 9)
        arrow(d, (hx, floor - 2), (hx, inlet_floor + 2), MAROON, 2, 9)
        T(d, (hx - 12, (inlet_floor + floor) / 2), "h", 28, MAROON, "bold", anchor="rm")
        T(d, (xstep + (gx + gw - xstep) / 2, gy + gh + 40), f"h = {h:.2f} mm", 26, MAROON, "bold", anchor="mm")
        T(d, (x + 24, y + 424), "Geometry-aware graph representation", 20, INK2)
        T(d, (x + 24, y + 456), "Training height", 19, MUTED)
        dashed(d, (x + 200, y + 467), (x + 240, y + 467), GOLD, 2, 8, 6)
        T(d, (x + 252, y + 456), "4.9 mm", 19, GOLD, "bold")
        T(d, (x + 24, y + 488), "Schematic near-step view", 17, MUTED)

    # ---- Card 2: velocity field ----------------------------------------- #
    def card2(self, im, d, box, t):
        x, y, w, h_box = box
        h = self.h_of(t)
        xs, ys, psi, u, v, solid, Lr, Hc = self.flow(h)
        fx, fy, fw, fh = x + 24, y + 136, w - 48, 222
        img = field_image(u, -0.1, 1.5, "flow").resize((fw, fh), Image.Resampling.BICUBIC)
        img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        im.alpha_composite(img, dest=(fx, fy))
        sx = fw / (xs[-1] - xs[0])
        sy = fh / Hc
        def P(px, py):
            return (fx + (px - xs[0]) * sx, fy + fh - py * sy)
        # solid block upstream
        d.rectangle((fx, P(0, h)[1], P(0, 0)[0], fy + fh), fill=SOLID)
        line(d, [(P(-6, h)), P(0, h), P(0, 0)], "#50606A", 2)
        # streamlines
        def fn(dd, layer):
            levels = list(np.linspace(0.07, 0.96, 9))
            pmin = float(psi.min())
            if pmin < -1e-4:
                levels += [pmin * f for f in (0.25, 0.55, 0.85)]
            for lv in levels:
                for seg in contour_lines(xs, ys, psi, lv):
                    pts = [(fx + (a - xs[0]) * sx - fx, fy + fh - b * sy - fy) for a, b in seg]
                    if len(pts) > 1:
                        dd.line(pts, fill=(255, 255, 255, 190), width=2)
        overlay(im, (fx, fy, fw, fh), fn)
        # tracers
        p = self.advect(t, xs, ys, u, v, h, Hc, Lr)
        def fn2(dd, layer):
            for px, py in p:
                if px < 0 and py < h:
                    continue
                X, Y = (px - xs[0]) * sx, fh - py * sy
                dd.ellipse((X - 3, Y - 3, X + 3, Y + 3), fill=(255, 255, 255, 235))
        overlay(im, (fx, fy, fw, fh), fn2)
        # separation and reattachment markers
        sp = P(0, h)
        dot(d, sp[0], sp[1], 6, RED, CARD, 2)
        rp = P(Lr, 0)
        dot(d, rp[0], rp[1], 6, TEAL, CARD, 2)
        if rp[0] + 130 < fx + fw:
            T(d, (rp[0] + 10, rp[1] - 30), "reattachment", 17, CARD, "semibold")
        else:
            T(d, (rp[0] - 10, rp[1] - 30), "reattachment", 17, CARD, "semibold", anchor="ra")
        yy = fy + fh + 22
        line(d, [(P(0, 0)[0], fy + fh + 6), (P(0, 0)[0], yy + 10)], TEAL, 1)
        line(d, [(rp[0], fy + fh + 6), (rp[0], yy + 10)], TEAL, 1)
        arrow(d, (P(0, 0)[0], yy), (rp[0], yy), TEAL, 2, 9)
        arrow(d, (rp[0], yy), (P(0, 0)[0], yy), TEAL, 2, 9)
        T(d, ((P(0, 0)[0] + rp[0]) / 2, yy + 14), f"Lr ≈ {Lr:.1f} mm", 22, TEAL, "bold", anchor="ma")
        colorbar(im, d, (fx, y + 470, 420, 14), "flow", -0.1, 1.5, [-0.1, 0.5, 1.0, 1.5], "Streamwise velocity  u / Uin")
        T(d, (fx + 470, y + 440), "Negative values:", 17, MUTED)
        T(d, (fx + 470, y + 464), "reverse flow", 19, INK, "bold")

    # ---- Card 3: parity -------------------------------------------------- #
    def card3(self, im, d, box, t):
        x, y, w, h_box = box
        h = self.h_of(t)
        cfd = lr_model(h, 125)
        gns = cfd * (1 + self.gns_error(h))
        pl = Plot(d, (x + 82, y + 150, 262, 262), (0, 24), (0, 24))
        # ±20% band
        def fn(dd, layer):
            pts = [pl.px(0, 0), pl.px(20, 24), pl.px(24, 24), pl.px(24, 19.2)]
            pts = [(a - pl.x - 0, b - pl.y) for a, b in pts]
            pts = [(a + 0, b + 0) for a, b in pts]
            dd.polygon([(a, b) for a, b in [(p[0], p[1]) for p in pts]], fill=(184, 134, 43, 36))
        overlay(im, (pl.x, pl.y, pl.w, pl.h), fn)
        pl.axes([0, 6, 12, 18, 24], [0, 6, 12, 18, 24], "CFD reference  Lr [mm]", "Surrogate  Lr [mm]")
        line(d, [pl.px(0, 0), pl.px(24, 24)], INK2, 2)
        dashed(d, pl.px(0, 0), pl.px(20, 24), GOLD, 2, 7, 6)
        dashed(d, pl.px(0, 0), pl.px(24, 19.2), GOLD, 2, 7, 6)
        for (hh, re, c, g) in self.points:
            if c > 24 or g > 24:
                continue
            px, py = pl.px(c, g)
            if re == 125:
                dot(d, px, py, 5, CARD, TEAL, 2)
            else:
                dot(d, px, py, 3.5, CARD, "#B7C3C9", 1)
        # guide lines + selected point
        sx, sy = pl.px(cfd, gns)
        dashed(d, (pl.x, sy), (sx, sy), "#A8B2B8", 1, 5, 5)
        dashed(d, (sx, pl.y + pl.h), (sx, sy), "#A8B2B8", 1, 5, 5)
        dot(d, sx, sy, 8, MAROON, CARD, 2)
        # legend
        lx, ly = x + 400, y + 160
        line(d, [(lx, ly + 10), (lx + 30, ly + 10)], INK2, 2)
        T(d, (lx + 40, ly), "y = x", 19, INK2)
        dashed(d, (lx, ly + 50), (lx + 30, ly + 50), GOLD, 2, 6, 5)
        T(d, (lx + 40, ly + 40), "±20%", 19, GOLD)
        dot(d, lx + 15, ly + 90, 5, CARD, TEAL, 2)
        T(d, (lx + 40, ly + 80), "Re = 125", 19, INK2)
        dot(d, lx + 15, ly + 130, 4, CARD, "#B7C3C9", 1)
        T(d, (lx + 40, ly + 120), "Other Re", 19, MUTED)
        dot(d, lx + 15, ly + 170, 7, MAROON, CARD, 2)
        T(d, (lx + 40, ly + 160), "Selected", 19, MAROON)
        err = (gns - cfd) / cfd * 100
        T(d, (lx, ly + 232), "Relative error", 19, MUTED)
        T(d, (lx, ly + 256), f"{err:+.1f}%", 30, MAROON, "bold")
        by = y + 478
        T(d, (x + 24, by), "CFD", 20, TEAL, "bold")
        T(d, (x + 76, by - 6), f"≈ {cfd:.1f} mm", 27, TEAL, "bold")
        T(d, (x + 290, by), "Surrogate", 20, MAROON, "bold")
        T(d, (x + 408, by - 6), f"≈ {gns:.1f} mm", 27, MAROON, "bold")


# --------------------------------------------------------------------------- #
# ANIMATION 2: Tree stem fire injury
# --------------------------------------------------------------------------- #
def fire_flux_factor(tau):
    """Normalized surface-fire heat flux history: rapid rise, peak near 150 s, then the fire front passes."""
    rise = 1 - math.exp(-(tau / 80.0) ** 2)
    decay = math.exp(-max(0.0, tau - 150) / 110.0)
    return rise * (0.02 + 0.98 * decay) if tau > 150 else rise


def simulate_tree():
    N = 128
    Lbox = 0.136
    dx = Lbox / N
    R = 0.06
    bark = 0.008
    xs = (np.arange(N) + 0.5) * dx - Lbox / 2
    X, Y = np.meshgrid(xs, xs)
    r = np.hypot(X, Y)
    theta = np.arctan2(Y, X)
    inside = r < R
    boundary = inside & (r > R - 1.15 * dx)
    k = np.where(r > R - bark, 0.11, 0.19)
    rho_c = np.where(r > R - bark, 520 * 1900.0, 650 * 2600.0)
    # moisture in living wood: evaporation near 100 C absorbs energy (latent sink)
    moisture_energy = np.where(r > R - bark, 0.15, 0.6) * 520.0 * 2.26e6   # J/m3 to evaporate all water
    wet = np.ones((N, N))
    T = np.full((N, N), 20.0)
    Tamb = 20.0
    exposure = np.clip(np.cos(theta), 0, 1) ** 1.6
    exposure = exposure * 0.9 + 0.1 * np.clip(np.cos(theta), 0, 1) ** 0.5
    qmax = 33e3
    hconv = 18.0
    sigma = 5.67e-8
    dt = 0.8
    steps = int(1200 / dt)
    snaps, tmax_snaps = [], []
    probes = {0: [], 5: [], 10: [], 15: []}
    ray = (np.abs(theta) < math.radians(6)) & inside
    Tmax = T.copy()
    kx = 2 * k[:, 1:] * k[:, :-1] / (k[:, 1:] + k[:, :-1])
    ky = 2 * k[1:, :] * k[:-1, :] / (k[1:, :] + k[:-1, :])
    okx = inside[:, 1:] & inside[:, :-1]
    oky = inside[1:, :] & inside[:-1, :]
    snap_every = int(4 / dt)
    depths = R - r
    for n in range(steps + 1):
        tau = n * dt
        if n % snap_every == 0:
            snaps.append(T.astype(np.float32).copy())
            tmax_snaps.append(Tmax.astype(np.float32).copy())
            for dmm in probes:
                sel = ray & (np.abs(depths - dmm / 1000.0) < 0.75 * dx)
                probes[dmm].append(float(T[sel].mean()) if sel.any() else float("nan"))
        fx = np.zeros_like(T)
        fy = np.zeros_like(T)
        flux_x = np.where(okx, kx * (T[:, 1:] - T[:, :-1]) / dx, 0)
        flux_y = np.where(oky, ky * (T[1:, :] - T[:-1, :]) / dx, 0)
        div = np.zeros_like(T)
        div[:, :-1] += flux_x
        div[:, 1:] -= flux_x
        div[:-1, :] += flux_y
        div[1:, :] -= flux_y
        div /= dx
        q = qmax * fire_flux_factor(tau) * exposure
        Tk = T + 273.15
        loss = hconv * (T - Tamb) + 0.9 * sigma * (Tk ** 4 - (Tamb + 273.15) ** 4)
        src = np.where(boundary, (q - loss) / dx, 0)
        evap = np.clip(0.02 * wet / (1 + np.exp(-(T - 100.0) / 4.0)) * dt, 0, wet)
        T = T + dt / rho_c * (div + src) - evap * moisture_energy / rho_c
        wet = wet - evap
        T = np.where(inside, T, Tamb)
        Tmax = np.maximum(Tmax, T)
    necro = []
    # necrotic depth history: deepest point on the exposed ray that has reached 60 C so far,
    # interpolated between cells so the readout moves smoothly
    Tm = np.full((N, N), 20.0)
    order = np.argsort(depths[ray])
    ray_depths = depths[ray][order] * 1000
    for s in snaps:
        Tm = np.maximum(Tm, s)
        prof = Tm[ray][order]
        hot = prof >= 60
        if not hot.any():
            necro.append(0.0)
            continue
        j = int(np.argmax(~hot)) if (~hot).any() else len(prof) - 1
        if j == 0:
            necro.append(0.0)
            continue
        d0, d1 = ray_depths[j - 1], ray_depths[min(j, len(prof) - 1)]
        t0, t1 = prof[j - 1], prof[min(j, len(prof) - 1)]
        frac = 0.0 if t0 == t1 else float(np.clip((t0 - 60) / (t0 - t1), 0, 1))
        necro.append(float(d0 + (d1 - d0) * frac))
    return dict(xs=xs, snaps=snaps, tmax=tmax_snaps, dt_snap=snap_every * dt, inside=inside, R=R, bark=bark,
                probes={k_: np.array(v) for k_, v in probes.items()}, necro=np.array(necro))


class TreeAnimation(Animation):
    key = "tree"
    file = "tree-stem-fire-injury"
    duration = 32.0
    tag = "FIRE SAFETY  |  VEGETATION"
    title = "From surface fire to injury inside a tree stem"
    subtitle = "Transient heat transfer through bark and wood, and the tissue it leaves behind"
    authors = "M. U. Khan  ·  M. Hasnain  ·  H. Sezer  ·  S. P. Kozhumal  ·  M. K. Selvaraj  ·  A. Simeoni"
    meta_right = "Int. Commun. Heat Mass Transfer 180 (2026)"
    footnote = "Illustrative animation inspired by the published study: fields and curves come from a simplified model for presentation, not reported data."
    card_titles = [("Fire scenario", "One-sided surface-fire exposure"),
                   ("Temperature field", "Stem cross-section, live heat conduction"),
                   ("Tissue injury", "Temperature history and necrotic depth")]
    poster_time = 14.0
    TAU_KEYS = [(0, 0), (1.5, 0), (26.0, 900), (32, 900)]
    chapters = [
        (0.0, "A surface fire heats one side of the stem far more than the other."),
        (8.0, "Heat keeps diffusing through bark into wood long after the flames peak."),
        (16.0, "Tissue that exceeds 60 °C dies: the necrotic depth decides the stem's fate."),
        (26.5, "Validated heat-transfer models turn a fire's thermal history into mortality predictions."),
    ]
    captions = [
        (0, 8, "A surface fire exposes one side of a tree stem. Heat enters through the bark on the exposed side."),
        (8, 16, "Heat diffuses inward through bark and wood, and the interior keeps warming after the flames have peaked."),
        (16, 26.5, "Tissue that exceeds 60 degrees Celsius dies. The necrotic depth grows as the thermal wave moves inward."),
        (26.5, 32, "Validated heat-transfer models convert a fire's thermal history into tree mortality predictions."),
    ]

    def setup(self):
        self.sim = simulate_tree()

    def tau_of(self, t):
        return sweep(t, self.TAU_KEYS)

    def field_at(self, tau, key="snaps"):
        s = self.sim
        f = tau / s["dt_snap"]
        i = min(int(f), len(s[key]) - 2)
        a = f - i
        return s[key][i] * (1 - a) + s[key][i + 1] * a

    def necro_at(self, tau):
        s = self.sim
        f = tau / s["dt_snap"]
        i = min(int(f), len(s["necro"]) - 2)
        a = f - i
        return s["necro"][i] * (1 - a) + s["necro"][i + 1] * a

    def kpi(self, im, d, t):
        tau = self.tau_of(t)
        q = 33 * fire_flux_factor(tau)
        self.kpi_strip(d, "TIME SINCE IGNITION", f"{tau:,.0f}", "s", (f"{q:.0f} kW/m²", "flux at bark now"),
                       (0, 900, tau, 150, "peak fire", "0", "900 s", "FIRE EXPOSURE HISTORY"),
                       ("Stem Ø 12 cm", "Bark 8 mm · one-sided exposure"),
                       ("NECROTIC DEPTH", f"{self.necro_at(tau):.1f} mm", "Tissue that has exceeded 60 °C"))

    def card1(self, im, d, box, t):
        x, y, w, h_box = box
        tau = self.tau_of(t)
        f = fire_flux_factor(tau)
        cx, cy, R = x + 180, y + 258, 100
        # stem
        dot(d, cx, cy, R, "#8A6E4F", "#5C4632", 2)
        dot(d, cx, cy, R - 14, "#E5D5B3", "#9E8A66", 1)
        for rr in (28, 50, 70, 86):
            d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), outline="#C9B68F", width=2)
        # exposed arc glow
        def glow(dd, layer):
            for i, rr in enumerate(range(R + 46, R + 8, -4)):
                a = int(10 + 70 * f * (1 - i / 10))
                dd.pieslice((cx - rr - (x), cy - rr - y, cx + rr - x, cy + rr - y), -70, 70, fill=(232, 132, 43, max(0, a)))
        overlay(im, (x, y, w, h_box), glow)
        # flames on exposed side
        def flames(dd, layer):
            rng = np.random.default_rng(11)
            for i in range(9):
                ang = math.radians(-58 + i * 14.5)
                bx = cx + (R + 10) * math.cos(ang) - x
                by = cy + (R + 10) * math.sin(ang) - y
                flick = 0.75 + 0.25 * math.sin(t * 9 + i * 1.7) + 0.1 * math.sin(t * 17 + i)
                hgt = (26 + 22 * rng.uniform()) * f * flick
                wid = 9 + 4 * rng.uniform()
                if hgt < 2:
                    continue
                for s, col in ((1.0, (226, 92, 36, 200)), (0.68, (242, 160, 48, 220)), (0.4, (252, 222, 110, 235))):
                    hh, ww = hgt * s, wid * s
                    tip = (bx + hh * math.cos(ang) + 3 * math.sin(t * 6 + i), by + hh * math.sin(ang))
                    pts = []
                    for k in range(13):
                        a2 = ang + math.pi / 2 + k * math.pi / 12
                        rr = ww * (1 if k in (0, 12) else 1)
                        pts.append((bx + rr * math.cos(a2) * 0.9, by + rr * math.sin(a2) * 0.9))
                    pts = [pts[0], tip, pts[-1]] + pts[::-1]
                    dd.polygon(pts, fill=col)
        overlay(im, (x, y, w, h_box), flames)
        # heat arrows
        for ang in (-30, 0, 30):
            a = math.radians(ang)
            p0 = (cx + (R + 72) * math.cos(a), cy + (R + 72) * math.sin(a))
            p1 = (cx + (R + 22) * math.cos(a), cy + (R + 22) * math.sin(a))
            if f > 0.05:
                motion(d, p0, p1, t, GOLD, 2, 0.35, 2, 9, 3)
        T(d, (x + 24, y + 134), "SHELTERED SIDE", 17, MUTED, "bold", anchor="la")
        T(d, (x + w - 24, y + 134), "EXPOSED SIDE", 17, GOLD, "bold", anchor="ra")
        T(d, (cx - R - 14, cy - 40), "Bark", 19, INK, "semibold", anchor="rm")
        arrow(d, (cx - R - 10, cy - 40), (cx - R + 6, cy - 34), MUTED, 1, 7)
        T(d, (cx - R - 14, cy + 10), "Wood", 19, INK, "semibold", anchor="rm")
        arrow(d, (cx - R - 10, cy + 10), (cx - 56, cy + 20), MUTED, 1, 7)
        # flux history sparkline
        pl = Plot(d, (x + 70, y + 420, 330, 56), (0, 900), (0, 40))
        pl.axes([0, 300, 600, 900], [0, 30], "Time since ignition [s]", "Heat flux at the bark [kW/m²]")
        taus = np.linspace(0, 900, 160)
        pl.curve(taus, [33 * fire_flux_factor(v) for v in taus], "#D9C9A8", 2)
        sel = taus <= tau
        if sel.sum() > 1:
            pl.curve(taus[sel], [33 * fire_flux_factor(v) for v in taus[sel]], GOLD, 3)
        px, py = pl.px(tau, 33 * f)
        dot(d, px, py, 5, GOLD, CARD, 2)

    def card2(self, im, d, box, t):
        x, y, w, h_box = box
        tau = self.tau_of(t)
        Tf = self.field_at(tau)
        s = self.sim
        size = 330
        cx, cy = x + 24 + 340 / 2 + 10, y + 128 + size / 2
        img = field_image(Tf, 20, 320, "heat", s["inside"]).resize((size, size), Image.Resampling.BICUBIC)
        im.alpha_composite(img, dest=(int(cx - size / 2), int(cy - size / 2)))
        scale = size / (s["xs"][-1] - s["xs"][0] + (s["xs"][1] - s["xs"][0]))
        def P(a, b):
            return (cx + a * scale, cy - b * scale)
        # bark boundary, outer edge
        rb = (s["R"] - s["bark"]) * scale
        d.ellipse((cx - rb, cy - rb, cx + rb, cy + rb), outline=(255, 255, 255, 140), width=1)
        ro = s["R"] * scale
        d.ellipse((cx - ro, cy - ro, cx + ro, cy + ro), outline="#50606A", width=2)
        # necrotic zone: tissue that has exceeded 60 C at any time so far
        Tm = self.field_at(tau, "tmax")
        necro_mask = np.clip((Tm - 58.0) / 4.0, 0, 1) * s["inside"]
        maskimg = Image.fromarray((necro_mask * 255).astype(np.uint8), "L").resize((size, size), Image.Resampling.BICUBIC)
        yy, xx = np.mgrid[0:size, 0:size]
        hatch = (((xx + yy) % 9) < 3).astype(np.float32)
        alpha = (hatch * np.asarray(maskimg, np.float32) / 255 * 200).astype(np.uint8)
        nz = np.zeros((size, size, 4), np.uint8)
        nz[..., :3] = 255
        nz[..., 3] = alpha
        im.alpha_composite(Image.fromarray(nz, "RGBA"), dest=(int(cx - size / 2), int(cy - size / 2)))
        # 60 C isotherm
        def fn(dd, layer):
            for seg in contour_lines(s["xs"], s["xs"], Tf, 60.0):
                pts = [(size / 2 + a * scale, size / 2 - b * scale) for a, b in seg]
                if len(pts) > 2:
                    dd.line(pts, fill=(255, 255, 255, 240), width=3)
        overlay(im, (cx - size / 2, cy - size / 2, size, size), fn)
        # labels right
        lx = x + 400
        T(d, (lx, y + 140), "ELAPSED", 17, MAROON, "bold")
        T(d, (lx, y + 162), f"{tau:,.0f} s", 40, INK, "bold")
        T(d, (lx, y + 226), "Peak bark temperature", 18, MUTED)
        T(d, (lx, y + 250), f"{Tf[s['inside']].max():.0f} °C", 30, MAROON, "bold")
        T(d, (lx, y + 306), "Reference depths", 18, MUTED)
        for i, (dm, col) in enumerate(((0, RED), (5, GOLD), (10, TEAL))):
            line(d, [(lx, y + 346 + i * 28), (lx + 26, y + 346 + i * 28)], col, 3)
            T(d, (lx + 36, y + 335 + i * 28), f"{dm} mm" if dm else "bark surface", 18, INK2)
        line(d, [(lx, y + 432), (lx + 30, y + 432)], CARD, 3)
        d.rectangle((lx - 1, y + 428, lx + 31, y + 436), outline="#9AA5AB")
        T(d, (lx + 40, y + 422), "60 °C isotherm now", 17, INK2)
        d.rectangle((lx, y + 456, lx + 30, y + 468), fill="#3A5F8A")
        for k in range(0, 30, 6):
            line(d, [(lx + k, y + 468), (lx + k + 6, y + 456)], CARD, 2)
        T(d, (lx + 40, y + 452), "necrotic tissue", 17, INK2)
        T(d, (lx + 40, y + 472), "has exceeded 60 °C", 15, MUTED)
        colorbar(im, d, (x + 24, y + 486, 330, 14), "heat", 20, 320, [20, 100, 200, 300], "Temperature [°C]")
        # depth markers on exposed ray
        for dm, col in ((5, GOLD), (10, TEAL)):
            p = P(s["R"] - dm / 1000, 0)
            dot(d, p[0], p[1], 4, col, CARD, 1)
        p = P(s["R"] - 0.0008, 0)
        dot(d, p[0], p[1], 4, RED, CARD, 1)

    def card3(self, im, d, box, t):
        x, y, w, h_box = box
        tau = self.tau_of(t)
        s = self.sim
        pl = Plot(d, (x + 84, y + 160, 440, 222), (0, 900), (0, 500))
        pl.axes([0, 300, 600, 900], [0, 100, 200, 300, 400, 500], "Time since ignition [s]", "Temperature [°C]")
        a, b = pl.px(0, 60), pl.px(900, 60)
        dashed(d, a, b, "#9AA5AB", 2, 8, 6)
        T(d, (b[0] - 4, b[1] - 20), "60 °C threshold", 17, MUTED, anchor="ra")
        taus = np.arange(len(s["probes"][0])) * s["dt_snap"]
        sel = taus <= tau
        for dm, col in ((10, TEAL), (5, GOLD), (0, RED)):
            vals = s["probes"][dm]
            pl.curve(taus, vals, "#E4E8EA", 2)
            if sel.sum() > 1:
                pl.curve(taus[sel], vals[sel], col, 3)
                px, py = pl.px(taus[sel][-1], vals[sel][-1])
                dot(d, px, py, 5, col, CARD, 2)
        lx = x + 236
        for i, (dm, col, lab) in enumerate(((0, RED, "Bark surface"), (5, GOLD, "5 mm deep"), (10, TEAL, "10 mm deep"))):
            line(d, [(lx + i * 108, y + 139), (lx + i * 108 + 20, y + 139)], col, 3)
            T(d, (lx + i * 108 + 26, y + 129), lab, 15, INK2)
        nd = self.necro_at(tau)
        T(d, (x + 24, y + 444), "Necrotic depth", 18, MUTED)
        T(d, (x + 24, y + 464), f"{nd:.1f} mm", 34, MAROON, "bold")
        T(d, (x + 214, y + 444), "Cambium 5 mm, peak", 18, MUTED)
        peak5 = np.nanmax(s["probes"][5][sel]) if sel.any() else 20
        T(d, (x + 214, y + 464), f"{peak5:.0f} °C", 30, GOLD if peak5 < 60 else RED, "bold")
        T(d, (x + 420, y + 444), "Flames", 18, MUTED)
        f = fire_flux_factor(tau)
        T(d, (x + 420, y + 464), "active" if f > 0.15 else "passed", 30, GOLD if f > 0.15 else INK2, "bold")
        T(d, (x + 24, y + 504), "Injury deepens after the flames fade; the heat wave keeps moving inward.", 14, MUTED)


# --------------------------------------------------------------------------- #
# ANIMATION 3: Gypsum board under localized fire exposure
# --------------------------------------------------------------------------- #
def simulate_gypsum():
    nx, ny, nz = 72, 48, 7
    Lx, Ly = 0.72, 0.48
    dx = Lx / nx
    dz = 0.002
    xs = (np.arange(nx) + 0.5) * dx
    ys = (np.arange(ny) + 0.5) * dx
    X, Y = np.meshgrid(xs, ys)
    xc, yc, sig = 0.30, 0.22, 0.075
    footprint = np.exp(-((X - xc) ** 2 + (Y - yc) ** 2) / (2 * sig ** 2))
    qpeak = 50e3
    rho, c = 800.0, 1100.0
    Lw = 8.0e5
    Tamb = 20.0
    T = np.full((nz, ny, nx), Tamb)
    wfrac = np.zeros_like(T)
    dt = 1.0
    steps = 1800
    sigma = 5.67e-8
    snaps, wsnaps, cols, wcols = [], [], [], []
    probes = {0: [], 6: [], 12: []}
    ic, jc = int(yc / dx), int(xc / dx)
    every = 5
    for n in range(steps + 1):
        tau = n * dt
        if n % every == 0:
            snaps.append(T[0].astype(np.float32).copy())
            wsnaps.append(wfrac[0].astype(np.float32).copy())
            cols.append(T[:, ic, jc].astype(np.float32).copy())
            wcols.append(wfrac[:, ic, jc].astype(np.float32).copy())
            probes[0].append(float(T[0, ic, jc]))
            probes[6].append(float(T[3, ic, jc]))
            probes[12].append(float(T[6, ic, jc]))
        # calcined (dehydrated) gypsum insulates: conductivity drops with water loss
        k = 0.25 * (1 - wfrac) + 0.12 * wfrac
        lap = np.zeros_like(T)
        kx = 0.5 * (k[:, :, 1:] + k[:, :, :-1])
        ky = 0.5 * (k[:, 1:, :] + k[:, :-1, :])
        kz = 0.5 * (k[1:, :, :] + k[:-1, :, :])
        lap[:, :, 1:] += kx * (T[:, :, :-1] - T[:, :, 1:]) / dx ** 2
        lap[:, :, :-1] += kx * (T[:, :, 1:] - T[:, :, :-1]) / dx ** 2
        lap[:, 1:, :] += ky * (T[:, :-1, :] - T[:, 1:, :]) / dx ** 2
        lap[:, :-1, :] += ky * (T[:, 1:, :] - T[:, :-1, :]) / dx ** 2
        lap[1:, :, :] += kz * (T[:-1, :, :] - T[1:, :, :]) / dz ** 2
        lap[:-1, :, :] += kz * (T[1:, :, :] - T[:-1, :, :]) / dz ** 2
        ramp = min(1.0, tau / 90.0)
        Tk = T + 273.15
        loss0 = 12.0 * (T[0] - Tamb) + 0.9 * sigma * (Tk[0] ** 4 - (Tamb + 273.15) ** 4)
        lossN = 8.0 * (T[-1] - Tamb) + 0.9 * sigma * (Tk[-1] ** 4 - (Tamb + 273.15) ** 4)
        src = np.zeros_like(T)
        src[0] = (qpeak * ramp * footprint - loss0) / dz
        src[-1] = -lossN / dz
        rate = 0.004 * (1 - wfrac) / (1 + np.exp(-(T - 130.0) / 9.0))
        dw = np.clip(rate * dt, 0, 1 - wfrac)
        T = T + dt / (rho * c) * (lap + src) - dw * Lw / c
        wfrac = wfrac + dw
    return dict(xs=xs, ys=ys, snaps=snaps, wsnaps=wsnaps, cols=cols, wcols=wcols, dt_snap=every * dt,
                probes={k_: np.array(v) for k_, v in probes.items()}, footprint=footprint, xc=xc, yc=yc, sig=sig, dz=dz)


class GypsumAnimation(Animation):
    key = "gypsum"
    file = "gypsum-fire-response"
    duration = 32.0
    tag = "FIRE SAFETY  |  BUILDING MATERIALS"
    title = "Reading a fire from the wall it heated"
    subtitle = "Three-dimensional heat and mass transfer in gypsum board under localized exposure"
    authors = "M. Hasnain  ·  H. Sezer  ·  S. P. Kozhumal"
    meta_right = "Int. J. Thermal Sciences 221 (2026)"
    footnote = "Illustrative animation inspired by the published study: fields and curves come from a simplified model for presentation, not reported data."
    card_titles = [("Fire scenario", "Localized heat-flux footprint on a wall"),
                   ("Exposed-face temperature", "Live 3D conduction with dehydration"),
                   ("Thermal response", "Temperature at three depths through the board")]
    poster_time = 15.0
    TAU_KEYS = [(0, 0), (1.5, 0), (26.0, 1800), (32, 1800)]
    chapters = [
        (0.0, "A small, local fire does not heat a wall uniformly."),
        (7.5, "Heat spreads through the thickness and along the board; dehydration absorbs much of it."),
        (16.0, "The rear face lags far behind the exposed face, and the calcined footprint records the exposure."),
        (26.5, "Calcination depth becomes a quantitative clue for fire investigators."),
    ]
    captions = [
        (0, 7.5, "A localized fire creates a Gaussian heat-flux footprint on a gypsum wall. Heating is strongly non-uniform."),
        (7.5, 16, "Heat conducts through the 12 millimetre board and along its surface. Dehydration of the gypsum absorbs energy and holds the temperature near 100 to 150 degrees."),
        (16, 26.5, "The rear face lags far behind the exposed face. The calcined footprint grows and records where the exposure was."),
        (26.5, 32, "Calcination depth links the observed damage to the heat-flux history, a quantitative tool for fire investigation."),
    ]

    def setup(self):
        self.sim = simulate_gypsum()

    def tau_of(self, t):
        return sweep(t, self.TAU_KEYS)

    def interp(self, arrs, tau):
        f = tau / self.sim["dt_snap"]
        i = min(int(f), len(arrs) - 2)
        a = f - i
        return arrs[i] * (1 - a) + arrs[i + 1] * a

    def calcination_depth(self, tau):
        w = self.interp(self.sim["wcols"], tau)
        # dehydrated thickness at the footprint centre (fractional, so the readout moves smoothly)
        return min(12.0, float(w.sum()) * self.sim["dz"] * 1000)

    def kpi(self, im, d, t):
        tau = self.tau_of(t)
        rear = float(self.interp(self.sim["cols"], tau)[-1])
        self.kpi_strip(d, "EXPOSURE TIME", f"{tau:,.0f}", "s", (f"{rear:.0f} °C", "rear face now"),
                       (0, 1800, tau, None, "", "0", "1800 s", "LOCALIZED EXPOSURE, PEAK 50 kW/m²"),
                       ("12 mm board", "Gaussian footprint, σ = 75 mm"),
                       ("CALCINATION DEPTH", f"{self.calcination_depth(tau):.1f} mm", "Dehydrated thickness at the footprint centre"))

    def card1(self, im, d, box, t):
        x, y, w, h_box = box
        tau = self.tau_of(t)
        ramp = min(1.0, tau / 90.0)
        # isometric board
        A = np.array([x + 96.0, y + 192.0])
        U = np.array([200.0, -44.0])
        V = np.array([0.0, 174.0])
        D = np.array([26.0, 0.0])
        front = [A, A + U, A + U + V, A + V]
        d.polygon([tuple(p) for p in [A + U, A + U + D, A + U + V + D, A + U + V]], fill="#C3CDD0")
        d.polygon([tuple(p) for p in [A, A + D, A + U + D, A + U]], fill="#E9EAE3")
        d.polygon([tuple(p) for p in front], fill="#F2EEE4", outline="#64747A")
        # footprint on the exposed face (warm patch, low on the wall above the fire)
        cpt = A + U * 0.5 + V * 0.6
        def fn(dd, layer):
            for i, r in enumerate(range(74, 6, -4)):
                a = int(14 + 150 * ramp * (1 - r / 74) ** 1.4)
                col = (236, 150 - int(90 * (1 - r / 74)), 60, a)
                dd.ellipse((cpt[0] - r * 0.85 - x, cpt[1] - r * 0.8 - y, cpt[0] + r * 0.85 - x, cpt[1] + r * 0.8 - y), fill=col)
        overlay(im, (x, y, w, h_box), fn)
        # flames in a tray at the foot of the wall, plume rising into the footprint
        base_y = (A + V)[1] + 8 + (cpt[0] - A[0]) / U[0] * V[0]
        def flames(dd, layer):
            bx, by = cpt[0] - x, base_y - y
            for i in range(7):
                flick = 0.8 + 0.2 * math.sin(t * 9 + i * 1.9)
                hgt = (38 + 12 * math.sin(i * 2.1)) * flick * ramp
                ox = i * 13 - 39
                for s, col in ((1.0, (226, 92, 36, 190)), (0.66, (242, 160, 48, 215)), (0.38, (252, 222, 110, 235))):
                    hh, ww = hgt * s, 8 * s
                    tip = (bx + ox + 3 * math.sin(t * 6 + i), by - hh)
                    dd.polygon([(bx + ox - ww, by), tip, (bx + ox + ww, by), (bx + ox, by + ww * 0.6)], fill=col)
            dd.rounded_rectangle((bx - 54, by - 2, bx + 54, by + 12), 4, fill=(70, 80, 88, 255))
        overlay(im, (x, y, w, h_box), flames)
        # plume heat into the footprint
        for j in range(3):
            if ramp > 0.1:
                motion(d, (cpt[0] - 36 + j * 36, base_y - 44), (cpt[0] - 24 + j * 24, cpt[1] + 24), t, GOLD, 2, 0.3, 2, 9, 3)
        # through-thickness transport on the side face
        motion(d, (A[0] + U[0] + 4, cpt[1] - 46), (A[0] + U[0] + D[0] + 30, cpt[1] - 46), t, MAROON, 2, 0.25, 2, 9, 3)
        T(d, (A[0] + U[0] + D[0] + 6, (A + U + V + D)[1] + 6), "12 mm", 16, MUTED, "semibold")
        T(d, (x + 24, y + 134), "EXPOSED FACE", 17, GOLD, "bold")
        T(d, (x + w - 24, y + 134), "3D CONDUCTION", 15, MAROON, "bold", anchor="ra")
        # footprint profile sparkline
        pl = Plot(d, (x + 70, y + 436, 330, 50), (0, 0.72), (0, 55))
        pl.axes([0, 0.36, 0.72], [0, 50], "", "Incident heat flux across the wall [kW/m²]", xfmt="{:.2f} m")
        xs = np.linspace(0, 0.72, 100)
        q = 50 * np.exp(-((xs - self.sim["xc"]) ** 2) / (2 * self.sim["sig"] ** 2)) * ramp
        pl.curve(xs, q, GOLD, 3)
        def band(dd, layer):
            pts = [pl.px(a, b) for a, b in zip(xs, q)] + [pl.px(0.72, 0), pl.px(0, 0)]
            dd.polygon([(a - pl.x, b - pl.y) for a, b in pts], fill=(184, 134, 43, 50))
        overlay(im, (pl.x, pl.y, pl.w, pl.h), band)

    def card2(self, im, d, box, t):
        x, y, w, h_box = box
        tau = self.tau_of(t)
        s = self.sim
        Ts = self.interp(s["snaps"], tau)
        ws = self.interp(s["wsnaps"], tau)
        fw, fh = 435, 290
        fx, fy = x + 24, y + 148
        img = field_image(Ts, 20, 800, "heat").resize((fw, fh), Image.Resampling.BICUBIC)
        img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        im.alpha_composite(img, dest=(fx, fy))
        sx, sy = fw / 0.72, fh / 0.48
        def fn(dd, layer):
            for seg in contour_lines(s["xs"], s["ys"], ws, 0.5):
                pts = [(a * sx, fh - b * sy) for a, b in seg]
                if len(pts) > 2:
                    dd.line(pts, fill=(255, 255, 255, 240), width=3)
            for seg in contour_lines(s["xs"], s["ys"], Ts, 100.0):
                pts = [(a * sx, fh - b * sy) for a, b in seg]
                if len(pts) > 2:
                    for p0, p1 in zip(pts, pts[1:]):
                        dd.line([p0, p1], fill=(255, 255, 255, 150), width=1)
        overlay(im, (fx, fy, fw, fh), fn)
        d.rectangle((fx, fy, fx + fw, fy + fh), outline="#50606A", width=2)
        T(d, (fx + 10, fy + fh - 26), "white contour: calcined footprint (dehydration complete)", 14, CARD, "semibold")
        # through-thickness column
        col = self.interp(s["cols"], tau)
        cxp, cyp, cw, ch = x + 548, fy, 40, fh
        colimg = field_image(col[:, None], 20, 800, "heat").resize((cw, ch), Image.Resampling.BICUBIC)
        im.alpha_composite(colimg, dest=(cxp, cyp))
        d.rectangle((cxp, cyp, cxp + cw, cyp + ch), outline="#50606A", width=2)
        T(d, (cxp + cw / 2, cyp - 22), "Through thickness", 15, INK2, "medium", anchor="ma")
        for i, lab in ((0, "exposed 0 mm"), (3, "6 mm"), (6, "rear 12 mm")):
            yy = cyp + (i + 0.5) / 7 * ch
            T(d, (cxp + cw + 8, yy), lab, 15, MUTED, anchor="lm")
            T(d, (cxp - 8, yy), f"{col[i]:.0f}°", 15, INK2, anchor="rm")
        colorbar(im, d, (fx, y + 486, 400, 14), "heat", 20, 800, [20, 200, 400, 600, 800], "Exposed-face temperature [°C]")
        T(d, (x + w - 24, y + 484), f"{tau:,.0f} s elapsed", 17, MUTED, "semibold", anchor="ra")

    def card3(self, im, d, box, t):
        x, y, w, h_box = box
        tau = self.tau_of(t)
        s = self.sim
        pl = Plot(d, (x + 84, y + 160, 440, 222), (0, 1800), (0, 800))
        pl.axes([0, 600, 1200, 1800], [0, 200, 400, 600, 800], "Exposure time [s]", "Temperature [°C]")
        taus = np.arange(len(s["probes"][0])) * s["dt_snap"]
        sel = taus <= tau
        for dm, col in ((12, BLUE), (6, GOLD), (0, RED)):
            vals = s["probes"][dm]
            pl.curve(taus, vals, "#E4E8EA", 2)
            if sel.sum() > 1:
                pl.curve(taus[sel], vals[sel], col, 3)
                px, py = pl.px(taus[sel][-1], vals[sel][-1])
                dot(d, px, py, 5, col, CARD, 2)
        # dehydration plateau annotation
        a = pl.px(1800, 135)
        dashed(d, pl.px(0, 110), pl.px(1800, 110), "#B9C2C7", 1, 6, 6)
        dashed(d, pl.px(0, 160), pl.px(1800, 160), "#B9C2C7", 1, 6, 6)
        T(d, (a[0] - 6, a[1] + 2), "dehydration plateau", 15, MUTED, anchor="rm")
        lx = x + 236
        for i, (col, lab) in enumerate(((RED, "Exposed 0 mm"), (GOLD, "Mid 6 mm"), (BLUE, "Rear 12 mm"))):
            line(d, [(lx + i * 108, y + 139), (lx + i * 108 + 20, y + 139)], col, 3)
            T(d, (lx + i * 108 + 26, y + 129), lab, 15, INK2)
        colv = self.interp(s["cols"], tau)
        T(d, (x + 24, y + 444), "Exposed face", 18, MUTED)
        T(d, (x + 24, y + 464), f"{colv[0]:.0f} °C", 32, RED, "bold")
        T(d, (x + 190, y + 444), "Rear face", 18, MUTED)
        T(d, (x + 190, y + 464), f"{colv[-1]:.0f} °C", 32, BLUE, "bold")
        T(d, (x + 356, y + 444), "Calcined thickness", 18, MUTED)
        T(d, (x + 356, y + 464), f"{self.calcination_depth(tau):.1f} / 12 mm", 32, MAROON, "bold")
        T(d, (x + 24, y + 504), "Plateau near 130 °C: dehydration absorbs heat before the board warms further.", 14, MUTED)


# --------------------------------------------------------------------------- #
# ANIMATION 4: Metal-hydride hydrogen storage
# --------------------------------------------------------------------------- #
def simulate_hydride(P_bar, record_fields=True):
    nr, nz = 30, 60
    R, L = 0.03, 0.12
    dr, dz = R / nr, L / nz
    r = (np.arange(nr) + 0.5) * dr
    rf = np.arange(nr + 1) * dr
    Rg = 8.314
    dH, dS = -30478.0, -108.0
    Ca, Ea = 59.2 * 0.55, 21170.0
    rho_c = 1.76e6
    dHvol = 8.97e8
    k = 1.9
    hw = 1500.0
    hend = 500.0
    Tc = 293.0
    T = np.full((nz, nr), Tc)
    F = np.zeros_like(T)
    dt = 0.25
    steps = int(2000 / dt)
    every = int(5 / dt)
    snapsF, snapsT, avg = [], [], []
    for n in range(steps + 1):
        if n % every == 0:
            if record_fields:
                snapsF.append(F.astype(np.float32).copy())
                snapsT.append(T.astype(np.float32).copy())
            avg.append(float((F * r[None, :]).sum() / (r.sum() * nz)))
        Peq = np.exp(dH / (Rg * T) - dS / Rg)
        rate = Ca * np.exp(-Ea / (Rg * T)) * np.log(np.maximum(P_bar / Peq, 1e-9)) * (1 - F)
        rate = np.clip(rate, 0, None)
        dF = np.minimum(rate * dt, 1 - F)
        # radial conduction (axisymmetric, flux form)
        flux_r = np.zeros((nz, nr + 1))
        flux_r[:, 1:-1] = k * (T[:, 1:] - T[:, :-1]) / dr * rf[1:-1]
        flux_r[:, -1] = -hw * (T[:, -1] - Tc) * rf[-1]
        div = (flux_r[:, 1:] - flux_r[:, :-1]) / (r * dr)
        lap_z = np.zeros_like(T)
        lap_z[1:] += k * (T[:-1] - T[1:]) / dz ** 2
        lap_z[:-1] += k * (T[1:] - T[:-1]) / dz ** 2
        # cooled end caps (inlet plate and closed end) give the fields their axial structure
        lap_z[0] -= hend * (T[0] - Tc) / dz
        lap_z[-1] -= hend * (T[-1] - Tc) / dz
        T = T + dt / rho_c * (div + lap_z) + dF * dHvol / rho_c
        F = F + dF
    return dict(r=r, snapsF=snapsF, snapsT=snapsT, avg=np.array(avg), dt_snap=every * dt, R=R, L=L)


class HydrideAnimation(Animation):
    key = "hydride"
    file = "hydrogen-storage"
    duration = 32.0
    tag = "ENERGY STORAGE  |  HYDROGEN"
    title = "Hydrogen storage begins with heat management"
    subtitle = "Coupled heat and mass transfer in a cooled metal-hydride reactor during charging"
    authors = "M. Hasnain  ·  H. Sezer  ·  J. H. Mason"
    meta_right = "Int. J. Hydrogen Energy 71 (2024)"
    footnote = "Illustrative animation inspired by the published study: fields and curves come from a simplified model for presentation, not reported data."
    card_titles = [("Reactor", "Jacketed metal-hydride bed, section view"),
                   ("Reacted fraction & temperature", "Live r–z fields during charging"),
                   ("Charging curves", "Average reacted fraction vs. supply pressure")]
    poster_time = 14.0
    TAU_KEYS = [(0, 0), (1.5, 0), (26.0, 2000), (32, 2000)]
    PRESSURES = (6, 10, 15)
    chapters = [
        (0.0, "Hydrogen is absorbed into a solid bed, and every absorbed molecule releases heat."),
        (7.5, "The bed heats up until absorption stalls; only cooling through the wall lets it continue."),
        (16.0, "Charging proceeds as a front from the cooled wall toward the hot core."),
        (26.5, "Supply pressure and coolant temperature set the charging time, which guides reactor design."),
    ]
    captions = [
        (0, 7.5, "Hydrogen enters a cooled metal-hydride reactor and is absorbed into the solid bed, releasing heat."),
        (7.5, 16, "The bed warms until absorption stalls near its equilibrium temperature. Heat removed through the jacketed wall lets the reaction continue."),
        (16, 26.5, "The reacted fraction advances as a front from the cooled wall toward the hot core of the bed."),
        (26.5, 32, "Supply pressure and coolant temperature set the charging time. These trade-offs guide safer, faster reactor design."),
    ]

    def setup(self):
        self.sim = simulate_hydride(10)
        self.curves = {p: simulate_hydride(p, record_fields=False)["avg"] for p in self.PRESSURES}

    def tau_of(self, t):
        return sweep(t, self.TAU_KEYS)

    def interp(self, arrs, tau):
        f = tau / self.sim["dt_snap"]
        i = min(int(f), len(arrs) - 2)
        a = f - i
        return arrs[i] * (1 - a) + arrs[i + 1] * a

    def t90(self, p):
        c = self.curves[p]
        idx = np.argmax(c >= 0.9)
        return idx * self.sim["dt_snap"] if c.max() >= 0.9 else None

    def kpi(self, im, d, t):
        tau = self.tau_of(t)
        favg = float(self.interp(self.sim["avg"], tau))
        t90 = self.t90(10)
        self.kpi_strip(d, "CHARGING TIME", f"{tau:,.0f}", "s", (f"{favg * 100:.0f}%", "of capacity filled"),
                       (0, 2000, tau, t90, "90% charged", "0", "2000 s", "CHARGING AT 10 bar, COOLANT 293 K"),
                       ("P = 10 bar", "Supply pressure held fixed"),
                       ("AVERAGE REACTED FRACTION", f"{favg:.2f}", "Hydrogen stored relative to bed capacity"))

    def card1(self, im, d, box, t):
        x, y, w, h_box = box
        tau = self.tau_of(t)
        favg = float(self.interp(self.sim["avg"], tau))
        # jacket and bed
        jx, jy, jw, jh = x + 120, y + 190, 200, 272
        d.rounded_rectangle((jx, jy, jx + jw, jy + jh), 22, fill="#DDEFF3", outline=BLUE, width=3)
        bx, by, bw, bh = jx + 30, jy + 26, jw - 60, jh - 52
        d.rounded_rectangle((bx, by, bx + bw, by + bh), 10, fill="#D9DDDA", outline="#526570", width=3)
        # granular bed: particles turn teal as hydrogen is stored (visual proxy for F)
        for iy in range(8):
            for ix in range(6):
                px = bx + 16 + ix * 21 + (iy % 2) * 6
                py = by + 18 + iy * 25
                depth = abs((px - (bx + bw / 2)) / (bw / 2))
                frac = smooth((favg * 1.5 - (1 - depth) * 0.9) / 0.6)
                col = tuple(int(a + (b - a) * frac) for a, b in zip((184, 191, 188), (0, 127, 135)))
                dot(d, px, py, 7, col, "#8F9E9B", 1)
        # inlet
        d.rectangle((bx + bw / 2 - 18, jy - 40, bx + bw / 2 + 18, by + 2), fill="#D9DDDA", outline="#526570", width=3)
        T(d, (bx + bw / 2 - 28, jy - 24), "H₂ inlet", 18, TEAL, "bold", anchor="rm")
        for j in range(2):
            motion(d, (bx + bw / 2 - 7 + j * 14, jy - 36), (bx + bw / 2 - 7 + j * 14, by + 50), t, TEAL, 2, 0.3, 2, 8, 3)
        # coolant up both sides
        for yy in (by + 40, by + 125, by + 210):
            motion(d, (jx + 15, yy + 46), (jx + 15, yy), t, BLUE, 2, 0.4, 2, 8, 3)
            motion(d, (jx + jw - 15, yy + 46), (jx + jw - 15, yy), t, BLUE, 2, 0.4, 2, 8, 3)
        # reaction heat outward
        for yy in (by + 60, by + 145, by + 230):
            motion(d, (bx + bw - 40, yy), (jx + jw + 36, yy), t, GOLD, 2, 0.28, 2, 9, 3)
        # labels
        T(d, (x + 24, jy + 56), "Metal-", 18, INK, "semibold")
        T(d, (x + 24, jy + 78), "hydride", 18, INK, "semibold")
        T(d, (x + 24, jy + 100), "bed", 18, INK, "semibold")
        arrow(d, (x + 96, jy + 96), (bx + 10, jy + 106), MUTED, 1, 7)
        T(d, (x + 24, jy + 190), "Cooling", 18, BLUE, "semibold")
        T(d, (x + 24, jy + 212), "jacket", 18, BLUE, "semibold")
        arrow(d, (x + 96, jy + 205), (jx + 12, jy + 205), MUTED, 1, 7)
        T(d, (jx + jw + 46, by + 44), "Reaction heat", 17, GOLD, "bold")
        T(d, (jx + jw + 46, by + 64), "to coolant", 16, MUTED)
        T(d, (jx + jw + 46, by + 180), "Coolant 293 K", 16, BLUE, "semibold")
        T(d, (jx + jw + 46, by + 200), "counter-flow", 16, MUTED)
        T(d, (x + 24, y + 134), "SECTION VIEW", 17, TEAL, "bold")
        T(d, (x + w - 24, y + 134), "R = 30 mm · L = 120 mm", 17, MUTED, "bold", anchor="ra")
        T(d, (x + w / 2, y + 484), "Absorption is exothermic; the cooled wall is the heat sink.", 16, MUTED, anchor="ma")

    def card2(self, im, d, box, t):
        x, y, w, h_box = box
        tau = self.tau_of(t)
        s = self.sim
        Ff = self.interp(s["snapsF"], tau)
        Tf = self.interp(s["snapsT"], tau)
        pw, ph = 160, 320
        gap = 118
        x0 = x + 70
        for i, (arr, vmin, vmax, cmap, title, ticks, fmt) in enumerate((
                (Ff, 0, 1, "viridis", "Reacted fraction", [0, 0.5, 1], "{:.1f}"),
                (Tf, 293, 350, "heat", "Temperature [K]", [293, 320, 350], "{:.0f}"))):
            px = x0 + i * (pw + gap)
            full = np.concatenate([arr[:, ::-1], arr], axis=1)   # mirror about the axis
            img = field_image(full, vmin, vmax, cmap).resize((pw, ph), Image.Resampling.BICUBIC)
            im.alpha_composite(img, dest=(px, y + 150))
            d.rectangle((px, y + 150, px + pw, y + 150 + ph), outline="#50606A", width=2)
            dashed(d, (px + pw / 2, y + 150), (px + pw / 2, y + 150 + ph), (255, 255, 255, 180), 1, 6, 6)
            T(d, (px + pw / 2, y + 126), title, 19, INK2, "semibold", anchor="ma")
            colorbar(im, d, (px, y + 486, pw, 12), cmap, vmin, vmax, ticks, "", fmt)
            if i == 1:
                def fn(dd, layer):
                    xs_ = np.linspace(0, 1, full.shape[1])
                    ys_ = np.linspace(0, 1, full.shape[0])
                    for seg in contour_lines(xs_, ys_, full, 330.0):
                        pts = [(a * pw, b * ph) for a, b in seg]
                        if len(pts) > 2:
                            dd.line(pts, fill=(255, 255, 255, 220), width=2)
                overlay(im, (px, y + 150, pw, ph), fn)
        # side annotations
        T(d, (x0 + pw + 14, y + 160), "wall", 15, MUTED)
        T(d, (x0 + pw + 14, y + 180), "cooled", 15, BLUE, "semibold")
        T(d, (x0 + pw + 14, y + 300), "axis", 15, MUTED)
        arrow(d, (x0 + pw + 50, y + 308), (x0 + pw / 2 + 4, y + 308), MUTED, 1, 7)
        T(d, (x0 + pw + 14, y + 440), "inlet end ↑", 15, MUTED)
        lx = x + 70 + 2 * pw + gap + 40
        T(d, (lx, y + 150), "ELAPSED", 17, MAROON, "bold")
        T(d, (lx, y + 172), f"{tau:,.0f} s", 40, INK, "bold")
        T(d, (lx, y + 236), "Peak bed temperature", 17, MUTED)
        T(d, (lx, y + 258), f"{Tf.max():.0f} K", 30, MAROON, "bold")
        T(d, (lx, y + 310), "Core reacted fraction", 17, MUTED)
        T(d, (lx, y + 332), f"{Ff[:, 0].mean():.2f}", 30, TEAL, "bold")
        T(d, (lx, y + 384), "Wall reacted fraction", 17, MUTED)
        T(d, (lx, y + 406), f"{Ff[:, -1].mean():.2f}", 30, TEAL, "bold")
        line(d, [(lx, y + 462), (lx + 26, y + 462)], CARD, 2)
        d.rectangle((lx - 1, y + 459, lx + 27, y + 465), outline="#9AA5AB")
        T(d, (lx + 34, y + 452), "330 K isotherm", 15, INK2)

    def card3(self, im, d, box, t):
        x, y, w, h_box = box
        tau = self.tau_of(t)
        s = self.sim
        pl = Plot(d, (x + 84, y + 160, 440, 222), (0, 2000), (0, 1))
        pl.axes([0, 500, 1000, 1500, 2000], [0, 0.25, 0.5, 0.75, 1], "Charging time [s]", "Reacted fraction", yfmt="{:.2f}")
        a, b = pl.px(0, 0.9), pl.px(2000, 0.9)
        dashed(d, a, b, "#9AA5AB", 2, 8, 6)
        T(d, (a[0] + 8, a[1] - 20), "90% charged", 16, MUTED)
        taus = np.arange(len(s["avg"])) * s["dt_snap"]
        sel = taus <= tau
        cols = {6: BLUE, 10: MAROON, 15: GOLD}
        for p in self.PRESSURES:
            c = self.curves[p]
            pl.curve(taus, c, "#E4E8EA", 2)
            if sel.sum() > 1:
                pl.curve(taus[sel], c[sel], cols[p], 4 if p == 10 else 2.5)
                px, py = pl.px(taus[sel][-1], c[sel][-1])
                dot(d, px, py, 6 if p == 10 else 4, cols[p], CARD, 2)
        lx = x + 280
        for i, p in enumerate(self.PRESSURES):
            line(d, [(lx + i * 92, y + 139), (lx + i * 92 + 20, y + 139)], cols[p], 4 if p == 10 else 2)
            T(d, (lx + i * 92 + 26, y + 129), f"{p} bar", 15, INK2, "bold" if p == 10 else "regular")
        T(d, (x + 24, y + 444), "Time to 90% charge", 18, MUTED)
        xx = x + 24
        for p in self.PRESSURES:
            t90 = self.t90(p)
            txt = f"{t90:,.0f} s" if t90 else "> 2000 s"
            T(d, (xx, y + 464), txt, 30, cols[p], "bold")
            T(d, (xx + text_width(txt, 30, "bold") + 8, y + 476), f"@ {p} bar", 15, MUTED)
            xx += 178
        T(d, (x + 24, y + 504), "Higher pressure raises the equilibrium temperature; more heat can leave the bed.", 14, MUTED)


ANIMATIONS = {"bfs": BFSAnimation, "tree": TreeAnimation, "gypsum": GypsumAnimation, "hydride": HydrideAnimation}


# --------------------------------------------------------------------------- #
# Output
# --------------------------------------------------------------------------- #
def write_vtt(animation, path):
    def ts(v):
        return f"{int(v // 3600):02d}:{int(v % 3600 // 60):02d}:{v % 60:06.3f}"
    lines = ["WEBVTT", ""]
    for a, b, s in animation.captions:
        lines += [f"{ts(a)} --> {ts(b)}", s, ""]
    path.write_text("\n".join(lines))


def render(key, out: Path):
    out.mkdir(parents=True, exist_ok=True)
    animation = ANIMATIONS[key]()
    hd = out / f"{animation.file}-1080p.mp4"
    web = out / f"{animation.file}-720p.mp4"
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", "-profile:v", "high",
           "-level", "4.1", "-movflags", "+faststart", "-metadata", f"title={animation.title}", str(hd)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    n = int(animation.duration * FPS)
    for i in range(n):
        p.stdin.write(animation.frame(i / FPS).tobytes())
        if i % 150 == 0:
            print(f"{key}: {i}/{n}", flush=True)
    p.stdin.close()
    if p.wait():
        raise RuntimeError("ffmpeg failed")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(hd), "-an", "-vf", "scale=1280:720:flags=lanczos", "-c:v", "libx264",
                    "-preset", "medium", "-crf", "23", "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.0",
                    "-movflags", "+faststart", str(web)], check=True)
    # posters: full-size jpg and a small thumbnail
    animation.part = None
    animation.last_t = None
    poster = animation.frame(animation.poster_time)
    poster.save(out / f"{animation.file}-poster.jpg", quality=86, optimize=True, progressive=True)
    poster.resize((640, 360), Image.Resampling.LANCZOS).save(out / f"{animation.file}-thumb.jpg", quality=82, optimize=True)
    write_vtt(animation, out / f"{animation.file}.vtt")
    print("done", key, flush=True)


def preview(key, out: Path, times):
    out.mkdir(parents=True, exist_ok=True)
    animation = ANIMATIONS[key]()
    for t in times:
        animation.frame(t).save(out / f"{key}_{t:05.1f}.png")
        print("preview", key, t, flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--animation", choices=list(ANIMATIONS) + ["all"], default="all")
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--render", action="store_true")
    ap.add_argument("--times", default="3,10,17,24,30")
    ap.add_argument("--out", default=str(HERE / "out"))
    args = ap.parse_args()
    keys = list(ANIMATIONS) if args.animation == "all" else [args.animation]
    if args.preview:
        times = [float(v) for v in args.times.split(",")]
        for k in keys:
            preview(k, Path(args.out) / "preview", times)
    if args.render:
        with ProcessPoolExecutor(max_workers=min(4, len(keys))) as ex:
            list(ex.map(render, keys, [Path(args.out)] * len(keys)))
