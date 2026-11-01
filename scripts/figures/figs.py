import json, sys, time
import numpy as np, cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle, Ellipse, Rectangle, Polygon, FancyArrowPatch, Arc
from fundus_synth import make_fundus

OUT = "/home/claude/rep/figs/"
BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN, VIOLET, RED = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"
INK, INK2, MUTED, GRID = "#1b1b1b", "#52514e", "#8a8984", "#e5e4df"
NAVY = "#1f3864"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 14, "axes.edgecolor": "#bdbcb6", "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "axes.titleweight": "bold", "axes.titlesize": 15,
    "axes.titlecolor": INK, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
    "savefig.dpi": 220, "savefig.bbox": "tight", "savefig.facecolor": "white",
})


def save(fig, name):
    fig.savefig(OUT + name); plt.close(fig); print("saved", name)


def rbar(ax, x, h, w, color, horiz=False, **kw):
    if horiz:
        return ax.barh(x, h, height=w, color=color, edgecolor="white", linewidth=1.5, **kw)
    return ax.bar(x, h, width=w, color=color, edgecolor="white", linewidth=1.5, **kw)


# 1. Disease burden ---------------------------------------------------------
def f_burden():
    fig, ax = plt.subplots(1, 2, figsize=(10, 4.6))
    yrs = ["2020", "2045 (projected)"]
    dr, vt = [103.12, 160.50], [28.54, 44.82]
    x = np.arange(2); w = 0.36
    rbar(ax[0], x - w / 2, dr, w, BLUE, label="Any diabetic retinopathy")
    rbar(ax[0], x + w / 2, vt, w, ORANGE, label="Vision-threatening DR")
    for i in range(2):
        ax[0].text(x[i] - w / 2, dr[i] + 3, f"{dr[i]:.1f} M", ha="center", fontsize=13.0, color=INK)
        ax[0].text(x[i] + w / 2, vt[i] + 3, f"{vt[i]:.1f} M", ha="center", fontsize=13.0, color=INK)
    ax[0].set_xticks(x, yrs); ax[0].set_ylabel("People affected (millions)"); ax[0].set_ylim(0, 215)
    ax[0].set_title("(a) Global, 2020 vs 2045", loc="left")
    ax[0].legend(frameon=False, fontsize=11.5, loc="upper left"); ax[0].grid(axis="x", visible=False)
    cats = ["Known diabetes", "Undiagnosed diabetes"]
    a, b = [15.5, 8.0], [5.3, 2.4]
    rbar(ax[1], x - w / 2, a, w, BLUE, label="Any DR")
    rbar(ax[1], x + w / 2, b, w, ORANGE, label="Vision-threatening DR")
    for i in range(2):
        ax[1].text(x[i] - w / 2, a[i] + 0.3, f"{a[i]}%", ha="center", fontsize=13.0)
        ax[1].text(x[i] + w / 2, b[i] + 0.3, f"{b[i]}%", ha="center", fontsize=13.0)
    ax[1].set_xticks(x, cats); ax[1].set_ylabel("Prevalence (%)"); ax[1].set_ylim(0, 22)
    ax[1].set_title("(b) India (SMART India study)", loc="left")
    ax[1].legend(frameon=False, fontsize=11.5, loc="upper right"); ax[1].grid(axis="x", visible=False)
    fig.tight_layout(); save(fig, "f_burden.png")


# 2. Eye anatomy + fundus landmarks ------------------------------------------
def f_eye():
    fig, ax = plt.subplots(1, 2, figsize=(10.5, 4.6), gridspec_kw=dict(width_ratios=[1.15, 1]))
    a = ax[0]; a.set_aspect("equal"); a.axis("off"); a.set_xlim(-1.9, 1.75); a.set_ylim(-1.35, 1.35)
    a.add_patch(Circle((0, 0), 1.0, fc="#fbf3ec", ec="#b9a99a", lw=2))
    a.add_patch(Arc((0, 0), 1.9, 1.9, theta1=-140, theta2=140, color=RED, lw=4))   # retina
    a.add_patch(Arc((0, 0), 2.0, 2.0, theta1=-140, theta2=140, color="#8c5a3c", lw=2.5))  # choroid
    a.add_patch(Arc((-0.93, 0), 0.75, 0.9, theta1=110, theta2=250, color=BLUE, lw=2.5))  # cornea
    a.add_patch(Ellipse((-0.62, 0), 0.22, 0.62, fc="#cfe3f7", ec=BLUE, lw=1.5))  # lens
    a.plot([-0.72, -0.72], [0.36, 0.55], color="#6b4f3a", lw=4); a.plot([-0.72, -0.72], [-0.36, -0.55], color="#6b4f3a", lw=4)
    a.add_patch(Rectangle((0.93, -0.32), 0.7, 0.22, fc="#f4d58d", ec="#b08a30"))  # optic nerve
    a.plot([0.95], [-0.21], "o", ms=9, color="#f2c94c", mec="#b08a30")
    a.plot([0.975], [0.06], "o", ms=7, color="#8c2f1c")
    for x0, y0, x1, y1 in [(-1.85, 0.12, -1.0, 0.1), (-1.85, -0.12, -1.0, -0.1)]:
        a.annotate("", xy=(x1, y1), xytext=(x0, y0), arrowprops=dict(arrowstyle="->", color=YELLOW, lw=1.8))
    a.plot([-1.0, 0.975], [0.1, 0.06], color=YELLOW, lw=1, ls="--"); a.plot([-1.0, 0.975], [-0.1, 0.06], color=YELLOW, lw=1, ls="--")
    lab = [("Cornea", (-1.25, 0.55), (-1.05, 0.3)), ("Pupil / iris", (-1.0, 0.95), (-0.72, 0.5)),
           ("Lens", (-0.45, -1.05), (-0.62, -0.3)), ("Vitreous", (0.25, -0.3), None),
           ("Retina", (0.55, 1.15), (0.6, 0.72)), ("Choroid", (1.15, 0.85), (0.8, 0.6)),
           ("Macula / fovea", (1.2, 0.33), (0.99, 0.08)), ("Optic disc", (1.25, -0.6), (0.97, -0.25)),
           ("Optic nerve", (1.25, -1.0), (1.4, -0.32)), ("Light path", (-1.85, -0.38), None)]
    for t, p, q in lab:
        if q: a.annotate(t, xy=q, xytext=p, fontsize=12.3, color=INK, ha="center",
                         arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
        else: a.text(*p, t, fontsize=12.3, color=INK2 if t != "Light path" else "#9a7000", ha="center", style="italic")
    a.set_title("(a) Cross-section of the human eye", loc="left")
    b = ax[1]; img = make_fundus(0, 520, seed=11, border=False)
    b.imshow(img); b.axis("off"); b.set_title("(b) Fundus landmarks (schematic)", loc="left")
    H = img.shape[0]; c = H / 2; r = H * 0.47
    for t, p, q in [("Optic disc", (c + 0.42 * r, c - 0.05 * r), (c + 0.55 * r, c - 0.62 * r)),
                    ("Macula / fovea", (c - 0.12 * r, c + 0.03 * r), (c - 0.55 * r, c - 0.7 * r)),
                    ("Retinal arteries\n& veins", (c + 0.1 * r, c + 0.55 * r), (c - 0.15 * r, c + 0.95 * r))]:
        b.annotate(t, xy=p, xytext=q, color="white", fontsize=13.0, ha="center", fontweight="bold",
                   arrowprops=dict(arrowstyle="->", color="white", lw=1.2))
    fig.tight_layout(); save(fig, "f_eye.png")


# 3. ICDR stages ------------------------------------------------------------
def f_icdr():
    names = ["Grade 0\nNo DR", "Grade 1\nMild NPDR", "Grade 2\nModerate NPDR", "Grade 3\nSevere NPDR", "Grade 4\nProliferative DR"]
    notes = ["No abnormalities", "Microaneurysms\nonly", "More than MAs:\nhaemorrhages,\nexudates", "4-2-1 rule:\nextensive bleeds,\nIRMA, beading", "Neovascularisation,\nvitreous /\npre-retinal bleed"]
    cols = [AQUA, "#7fbf3f", YELLOW, ORANGE, RED]
    fig, ax = plt.subplots(1, 5, figsize=(11, 3.6))
    for g in range(5):
        ax[g].imshow(make_fundus(g, 420, seed=20 + g, border=False)); ax[g].axis("off")
        ax[g].set_title(names[g], fontsize=13.8, color=INK)
        ax[g].text(0.5, -0.06, notes[g], transform=ax[g].transAxes, ha="center", va="top", fontsize=11.9, color=INK2)
        ax[g].add_patch(Rectangle((0, 1.0), 1, 0.035, transform=ax[g].transAxes, color=cols[g], clip_on=False))
    fig.text(0.5, 1.02, "Increasing severity  →   referable DR = grade 2 and above", ha="center", fontsize=14.5, color=INK2)
    fig.tight_layout(); save(fig, "f_icdr.png")


# 4. Dataset sizes -----------------------------------------------------------
def f_datasets():
    d = [("IDRiD (India)", 516), ("Messidor-2 (France)", 1748), ("APTOS 2019 train (India)", 3662), ("DDR (China)", 13673), ("EyePACS / Kaggle 2015 (USA)", 88702)]
    fig, ax = plt.subplots(figsize=(8.5, 3.0))
    y = np.arange(len(d))
    cols = [MUTED, MUTED, BLUE, MUTED, MUTED]
    rbar(ax, y, [v for _, v in d], 0.6, cols, horiz=True)
    ax.set_yticks(y, [n for n, _ in d]); ax.set_xscale("log"); ax.set_xlim(300, 300000)
    for i, (_, v) in enumerate(d):
        ax.text(v * 1.12, i, f"{v:,}", va="center", fontsize=13.0, color=INK)
    ax.set_xlabel("Number of graded fundus images (log scale)"); ax.grid(axis="y", visible=False)
    ax.set_title("Public DR grading datasets (APTOS 2019 used for training in Project-I)", loc="left")
    save(fig, "f_datasets.png")


# 5. Optical layout -----------------------------------------------------------
def f_optics():
    fig, ax = plt.subplots(figsize=(10.5, 4.8)); ax.axis("off"); ax.set_aspect("equal")
    ax.set_xlim(-3, 48); ax.set_ylim(-10, 7.5)
    ax.add_patch(Circle((0, 0), 1.2, fc="#fbf3ec", ec="#b9a99a", lw=1.5)); ax.add_patch(Arc((0, 0), 2.3, 2.3, theta1=-130, theta2=130, color=RED, lw=3))
    ax.text(0, -1.7, "Eye", ha="center", va="top", fontsize=13.0)
    lx = -1.2 - 5.0
    lx = 6.0
    ax.add_patch(Ellipse((lx, 0), 0.7, 7.0, fc="#cfe3f7", ec=BLUE, lw=1.5))
    ax.text(lx, 4.0, "20 D lens\nf = 50 mm", ha="center", va="bottom", fontsize=13.0)
    ax.annotate("", xy=(lx, -4.3), xytext=(-1.2, -4.3), arrowprops=dict(arrowstyle="<->", color=INK2))
    ax.text((lx - 1.2) / 2, -5.6, "≈ 50 mm", ha="center", fontsize=12.3, color=INK2)
    ix = 12.0
    ax.plot([ix, ix], [-2.4, 2.4], color=VIOLET, lw=2, ls="--"); ax.text(ix + 0.5, 2.6, "Aerial image\n(inverted)", ha="left", va="bottom", fontsize=12.3, color=VIOLET)
    for y0 in [-0.6, 0, 0.6]:
        ax.plot([-0.9, lx], [y0 * 0.5, y0 * 4], color=YELLOW, lw=1.2); ax.plot([lx, ix], [y0 * 4, -y0 * 3.3], color=YELLOW, lw=1.2)
        ax.plot([ix, 34], [-y0 * 3.3, -y0 * 0.6], color=YELLOW, lw=1.0, alpha=0.8)
    cx = 34
    ax.add_patch(FancyBboxPatch((cx, -1.8), 10, 3.6, boxstyle="round,pad=0.2", fc="#e8eef8", ec=NAVY, lw=1.5))
    ax.add_patch(Rectangle((cx - 0.8, -0.7), 0.8, 1.4, fc="#9fb3d1", ec=NAVY))
    ax.text(cx + 5.0, 0, "Pi Camera\nModule 3 NoIR", ha="center", va="center", fontsize=12.3, color=NAVY)
    ax.add_patch(Rectangle((cx - 1.3, 1.9), 0.9, 0.7, fc=RED, ec="none")); ax.text(cx - 0.85, 2.9, "IR 850 nm + white LED", ha="center", fontsize=11.6)
    ax.annotate("", xy=(lx + 0.6, 1.2), xytext=(cx - 1.3, 2.2), arrowprops=dict(arrowstyle="->", color=RED, lw=1.2, ls="--"))
    ax.annotate("", xy=(cx, -7.6), xytext=(lx, -7.6), arrowprops=dict(arrowstyle="<->", color=INK2))
    ax.text((lx + cx) / 2, -9.6, "Lens-to-camera ≈ 160–180 mm (camera ≈ 110 mm behind aerial image)", ha="center", fontsize=12.3, color=INK2)
    ax.text(47, 6.6, "Not to scale", ha="right", fontsize=11.6, color=MUTED, style="italic")
    save(fig, "f_optics.png")


# 6. Interfacing schematic ---------------------------------------------------
def box(ax, x, y, w, h, t, fc="#e8eef8", ec=NAVY, fs=9, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.12", fc=fc, ec=ec, lw=1.4))
    ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontsize=fs, color=INK, fontweight="bold" if bold else "normal")


def f_circuit():
    fig, ax = plt.subplots(figsize=(10.5, 5.6)); ax.axis("off"); ax.set_xlim(0, 21); ax.set_ylim(-0.6, 11)
    box(ax, 7.5, 3.0, 6.3, 5.2, "", fc="#eef6ff")
    ax.text(10.65, 7.75, "Raspberry Pi 5 (8 GB)", ha="center", fontsize=15.2, fontweight="bold", color=NAVY)
    ax.text(10.65, 7.25, "BCM2712 · 4× Cortex-A76 @ 2.4 GHz", ha="center", fontsize=12.3, color=INK2)
    pins = [("CSI-0 (22-pin FPC)", 6.5), ("GPIO18 (PWM0)", 5.7), ("GPIO19 (PWM1)", 4.9), ("GPIO17 (in, pull-up)", 4.1), ("DSI-1 / HDMI-0", 3.4)]
    for t, y in pins:
        ax.text(7.7, y, t, fontsize=12.3, va="center", color=INK)
    box(ax, 0.3, 8.6, 5.0, 1.6, "Camera Module 3 NoIR\nSony IMX708, 12 MP, AF", fc="#fff3e8", ec=ORANGE)
    ax.plot([5.3, 6.4, 6.4, 7.5], [9.4, 9.4, 6.5, 6.5], color=ORANGE, lw=2)
    # IR LED driver
    box(ax, 0.3, 5.9, 4.0, 1.5, "IR LED string\n4 × 850 nm, 50 mA", fc="#fde8e8", ec=RED)
    box(ax, 4.8, 5.3, 2.0, 1.0, "N-MOSFET\nAO3400", fc="white", fs=8)
    ax.plot([7.5, 6.8], [5.7, 5.7], color=INK2, lw=1.5); ax.plot([4.3, 4.8], [6.6, 5.9], color=INK2, lw=1.5)
    ax.text(1.0, 5.55, "R = 68 Ω, 0.25 W per LED", fontsize=11.6, color=INK2)
    box(ax, 0.3, 3.2, 4.0, 1.5, "White LED (flash)\n2 × 3000 K, 20 mA", fc="#fff8e1", ec=YELLOW)
    box(ax, 4.8, 3.9, 2.0, 1.0, "N-MOSFET\nAO3400", fc="white", fs=8)
    ax.plot([7.5, 6.8], [4.9, 4.4], color=INK2, lw=1.5); ax.plot([4.3, 4.8], [3.95, 4.3], color=INK2, lw=1.5)
    ax.text(1.0, 2.85, "R = 100 Ω, 0.25 W per LED", fontsize=11.6, color=INK2)
    box(ax, 0.3, 0.6, 4.0, 1.4, "Capture push-button\n(to GND, 10 kΩ pull-up)", fc="#e9f7f1", ec=AQUA)
    ax.plot([4.3, 7.0, 7.0, 7.5], [1.3, 1.3, 4.1, 4.1], color=AQUA, lw=1.8)
    box(ax, 15.0, 6.8, 5.6, 1.6, "7″ touch display\n1024 × 600 (HDMI)", fc="#efeafc", ec=VIOLET)
    ax.plot([13.8, 14.4, 14.4, 15.0], [3.4, 3.4, 7.6, 7.6], color=VIOLET, lw=1.8)
    box(ax, 15.0, 4.2, 5.6, 1.6, "USB-C PD supply\n5.1 V / 5 A (27 W)\nor 10 000 mAh PD bank", fc="#f2f2f0", ec=MUTED, fs=8.5)
    ax.plot([13.8, 15.0], [5.0, 5.0], color=MUTED, lw=2.2)
    box(ax, 15.0, 1.6, 5.6, 1.6, "Active cooler (fan header)\n+ microSD 32 GB (OS, model)", fc="#f2f2f0", ec=MUTED, fs=8.5)
    ax.plot([13.8, 14.1, 14.1, 15.0], [4.4, 4.4, 2.4, 2.4], color=MUTED, lw=1.5)
    ax.text(10.5, -0.35, "5 V rail feeds both LED strings; GPIO only drives MOSFET gates (≤ 16 mA per pin limit respected)", ha="center", fontsize=12.3, color=INK2, style="italic")
    save(fig, "f_circuit.png")


# 7. Preprocessing stages -----------------------------------------------------
sys.path.insert(0, "/home/claude/rep/src")
PRE = open("/home/claude/rep/src/preproc_code.py").read(); exec(PRE)


def f_preproc():
    raw = make_fundus(2, 700, seed=5, border=True, uneven=True)
    raw = cv2.copyMakeBorder(raw, 40, 40, 120, 120, cv2.BORDER_CONSTANT, value=0)
    s1 = crop_fundus(raw); s2 = pad_to_square(s1); s3 = cv2.resize(s2, (384, 384), interpolation=cv2.INTER_AREA)
    blur = cv2.GaussianBlur(s3, (0, 0), 384 / 30); s4 = cv2.addWeighted(s3, 4, blur, -4, 128)
    s5 = preprocess_fundus(raw, 384)
    imgs = [raw, s2, s3, s4, s5]
    tt = ["① Raw capture", "② Crop + pad", "③ Resize 384²", "④ Ben Graham", "⑤ Mask → input"]
    fig, ax = plt.subplots(1, 5, figsize=(12, 3.0))
    for i in range(5):
        ax[i].imshow(imgs[i]); ax[i].axis("off"); ax[i].set_title(tt[i], fontsize=13.0)
    save(fig, "f_preproc.png")


# 8. EfficientNet-B0 stages ---------------------------------------------------
def f_effnet():
    st = [("Stem\nConv3×3", 32, 192, 1, "#cfd8e6"), ("MBConv1\nk3", 16, 192, 1, BLUE), ("MBConv6\nk3", 24, 96, 2, BLUE), ("MBConv6\nk5", 40, 48, 2, AQUA),
          ("MBConv6\nk3", 80, 24, 3, BLUE), ("MBConv6\nk5", 112, 24, 3, AQUA), ("MBConv6\nk5", 192, 12, 4, AQUA), ("MBConv6\nk3", 320, 12, 1, BLUE),
          ("Head\nConv1×1", 1280, 12, 1, "#cfd8e6"), ("GAP +\nDrop 0.3", 1280, 1, 1, "#f2f2f0"), ("FC → 1\nscore", 1, 1, 1, ORANGE)]
    fig, ax = plt.subplots(figsize=(12, 3.6)); ax.axis("off"); ax.set_xlim(-0.5, 11 * 1.1 + 0.6); ax.set_ylim(-1.8, 3.4)
    for i, (n, ch, res, L, c) in enumerate(st):
        x = i * 1.1; h = 0.7 + 2.2 * np.sqrt(res / 192)
        ax.add_patch(FancyBboxPatch((x, 1.5 - h / 2), 0.85, h, boxstyle="round,pad=0.02,rounding_size=0.08", fc=c, ec="white", lw=1.5, alpha=0.9))
        ax.text(x + 0.425, 1.5, n, ha="center", va="center", fontsize=11.3, color="white" if c in (BLUE, AQUA, ORANGE) else INK, fontweight="bold")
        ax.text(x + 0.425, -0.35, f"{res}×{res}" if res > 1 else "1×1", ha="center", fontsize=10.9, color=INK2)
        ax.text(x + 0.425, -0.75, f"{ch} ch", ha="center", fontsize=10.9, color=INK2)
        ax.text(x + 0.425, -1.15, f"×{L}" if i not in (0, 8, 9, 10) else "", ha="center", fontsize=10.9, color=INK2)
        if i < len(st) - 1:
            ax.annotate("", xy=(x + 1.1, 1.5), xytext=(x + 0.85, 1.5), arrowprops=dict(arrowstyle="->", color=MUTED, lw=1))
    ax.text(-0.45, -0.35, "res.", fontsize=10.9, color=MUTED); ax.text(-0.45, -0.75, "width", fontsize=10.9, color=MUTED); ax.text(-0.45, -1.15, "layers", fontsize=10.9, color=MUTED)
    ax.text(-0.4, 3.15, "Input 3 × 384 × 384  →  EfficientNet-B0 backbone (4.0 M parameters, 1.13 GMACs)  →  continuous severity score", fontsize=13.8, color=INK, fontweight="bold")
    save(fig, "f_effnet.png")


# 9. Threshold mapping -------------------------------------------------------
def f_thresholds():
    fig, ax = plt.subplots(figsize=(10, 2.9)); ax.axis("off"); ax.set_xlim(-0.6, 4.6); ax.set_ylim(-1.2, 1.55)
    edges = [-0.6, 0.5, 1.5, 2.5, 3.5, 4.6]; cols = [AQUA, "#7fbf3f", YELLOW, ORANGE, RED]
    names = ["0\nNo DR", "1\nMild", "2\nModerate", "3\nSevere", "4\nProliferative"]
    for i in range(5):
        ax.add_patch(Rectangle((edges[i], -0.1), edges[i + 1] - edges[i] - 0.02, 0.75, fc=cols[i], ec="white"))
        ax.text((edges[i] + edges[i + 1]) / 2, 0.27, names[i], ha="center", va="center", fontsize=13.0, color="white", fontweight="bold")
    for t, lab in zip([0.5, 1.5, 2.5, 3.5], ["t₁", "t₂", "t₃", "t₄"]):
        ax.plot([t, t], [-0.15, 0.8], color=INK, lw=1.2); ax.text(t, 0.88, f"{lab} = {t}", ha="center", fontsize=12.3)
    ax.annotate("", xy=(4.6, -0.3), xytext=(-0.6, -0.3), arrowprops=dict(arrowstyle="->", color=INK2))
    for v in range(5): ax.text(v, -0.55, str(v), ha="center", fontsize=12.3, color=INK2)
    ax.text(2.0, -1.0, "Model output ŷ (continuous score) → grade = number of thresholds below ŷ", ha="center", fontsize=12.8, color=INK2)
    
    ax.text(3.55, 1.33, "Referable DR (grade ≥ 2)", ha="center", fontsize=13.0, color=RED, fontweight="bold")
    ax.plot([1.5, 4.6], [1.22, 1.22], color=RED, lw=2)
    save(fig, "f_thresholds.png")


# 10. Enclosure concept -------------------------------------------------------
def f_enclosure():
    fig, ax = plt.subplots(figsize=(10, 5.2)); ax.axis("off"); ax.set_aspect("equal"); ax.set_xlim(0, 58); ax.set_ylim(-4, 20)
    ax.add_patch(FancyBboxPatch((1, 6), 6, 7, boxstyle="round,pad=0.3", fc="#3d3d3d", ec="none")); ax.text(4, 14.0, "Rubber eyecup /\nforehead rest", ha="center", fontsize=12.3)
    ax.add_patch(Rectangle((7, 7.5), 6, 4, fc="#d9d9d6", ec="#8a8984")); ax.text(10, 7.0, "Lens holder\n(20 D, sliding)", ha="center", va="top", fontsize=12.3)
    ax.add_patch(Ellipse((10, 9.5), 0.8, 5.5, fc="#cfe3f7", ec=BLUE, lw=1.5))
    ax.add_patch(Rectangle((13, 8.6), 20, 1.8, fc="#efefec", ec="#8a8984")); ax.text(23, 7.9, "Light-tight tube\n(matte black PLA)", ha="center", va="top", fontsize=12.3)
    ax.add_patch(FancyBboxPatch((33, 4), 22, 11, boxstyle="round,pad=0.4", fc="#e8eef8", ec=NAVY, lw=1.5))
    ax.text(44, 13.4, "Main housing", ha="center", fontsize=13.8, fontweight="bold", color=NAVY)
    ax.text(44, 11.4, "Camera + LED ring", ha="center", fontsize=12.3); ax.text(44, 9.7, "Raspberry Pi 5 + cooler", ha="center", fontsize=12.3); ax.text(44, 8.0, "7″ touch display (rear)", ha="center", fontsize=12.3)
    ax.add_patch(Rectangle((38, -1.5), 5, 5.5, fc="#c9c9c4", ec="#8a8984")); ax.text(44, 0.5, "Handle with\nPD power bank", fontsize=12.3)
    ax.add_patch(Circle((50.5, 15.6), 0.8, fc=AQUA, ec="none")); ax.text(52, 16.8, "Capture button", fontsize=12.3)
    ax.annotate("", xy=(33, 1.0), xytext=(1, 1.0), arrowprops=dict(arrowstyle="<->", color=INK2)); ax.text(17, -0.6, "≈ 230 mm eye-to-camera path (adjustable)", ha="center", fontsize=12.3, color=INK2)
    ax.text(57, -3.8, "Concept sketch — not to scale", fontsize=11.6, color=MUTED, style="italic", ha="right")
    save(fig, "f_enclosure.png")


# 11. Class distribution ------------------------------------------------------
def f_classdist():
    n = [1805, 370, 999, 193, 295]; names = ["0 No DR", "1 Mild", "2 Moderate", "3 Severe", "4 Proliferative"]
    cols = [AQUA, "#7fbf3f", YELLOW, ORANGE, RED]
    fig, ax = plt.subplots(figsize=(8.5, 3.4))
    rbar(ax, np.arange(5), n, 0.6, cols)
    for i, v in enumerate(n): ax.text(i, v + 25, f"{v}  ({100 * v / sum(n):.1f}%)", ha="center", fontsize=13.0)
    ax.set_xticks(range(5), names); ax.set_ylabel("Images"); ax.set_ylim(0, 2250); ax.grid(axis="x", visible=False)
    ax.set_title("APTOS 2019 training set — class distribution (n = 3,662)", loc="left")
    save(fig, "f_classdist.png")


def f_split():
    tr = [1263, 259, 699, 135, 207]; va = [271, 55, 150, 29, 44]; te = [271, 56, 150, 29, 44]
    fig, ax = plt.subplots(figsize=(8.5, 3.4)); x = np.arange(5); w = 0.26
    for k, (d, c, l) in enumerate([(tr, BLUE, "Train (2,563)"), (va, ORANGE, "Validation (549)"), (te, AQUA, "Test (550)")]):
        rbar(ax, x + (k - 1) * w, d, w, c, label=l)
    ax.set_xticks(x, ["0 No DR", "1 Mild", "2 Moderate", "3 Severe", "4 Proliferative"]); ax.set_ylabel("Images")
    ax.legend(frameon=False); ax.grid(axis="x", visible=False)
    ax.set_title("Stratified 70 / 15 / 15 split (random seed 42)", loc="left")
    save(fig, "f_split.png")


# 12. Augmentation ------------------------------------------------------------
def f_augment():
    import torch, torchvision.transforms as T
    torch.manual_seed(3)
    base = preprocess_fundus(make_fundus(2, 500, seed=8, border=False, uneven=False), 384)
    tf = T.Compose([T.ToPILImage(), T.RandomHorizontalFlip(), T.RandomVerticalFlip(), T.RandomRotation(180, fill=128),
                    T.RandomResizedCrop(384, scale=(0.85, 1.0), ratio=(0.95, 1.05)),
                    T.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.1, hue=0.02), T.RandomApply([T.GaussianBlur(3)], p=0.2)])
    fig, ax = plt.subplots(1, 6, figsize=(12, 2.4))
    ax[0].imshow(base); ax[0].set_title("Input", fontsize=13.0)
    for i in range(1, 6):
        ax[i].imshow(np.array(tf(base))); ax[i].set_title(f"Aug. {i}", fontsize=13.0)
    for a in ax: a.axis("off")
    save(fig, "f_augment.png")


# 13. Capture trial analysis ---------------------------------------------------
def rg_ratio(rgb):
    img = cv2.resize(rgb, (256, 256)).astype(np.float32); lit = img.mean(2) >= 20
    return float(np.median(img[..., 0][lit] / (img[..., 1][lit] + 1)))


def f_capture():
    u = cv2.cvtColor(cv2.imread("/home/claude/rep/src/capture_trial.png"), cv2.COLOR_BGR2RGB)
    crop = u[620:1230, 30:660]
    syn = make_fundus(1, 500, seed=31, border=True)
    r_u, r_s = rg_ratio(u), rg_ratio(syn)
    fig, ax = plt.subplots(1, 3, figsize=(11.5, 3.6), gridspec_kw=dict(width_ratios=[1, 1.2, 1.3]))
    ax[0].imshow(crop); ax[0].axis("off"); ax[0].set_title("(a) Capture trial 1 — lens held\nagainst the face", fontsize=13.8)
    ax[1].imshow(syn); ax[1].axis("off"); ax[1].set_title("(b) Target: fundus view\n(schematic)", fontsize=13.8)
    a = ax[2]; rbar(a, [0, 1], [r_u, r_s], 0.55, [MUTED, RED])
    a.axhline(1.6, color=INK, lw=1.2, ls="--"); a.text(-0.3, 1.68, "gate threshold 1.6", ha="left", fontsize=12.3)
    for i, v in enumerate([r_u, r_s]): a.text(i, v + 0.05, f"{v:.2f}", ha="center", fontsize=13.8, fontweight="bold")
    a.set_xticks([0, 1], ["Trial 1\n(rejected)", "Fundus\n(accepted)"]); a.set_ylabel("Median red / green ratio"); a.set_ylim(0, max(r_u, r_s) * 1.25)
    a.set_title("(c) Fundus-image gate", fontsize=13.8); a.grid(axis="x", visible=False)
    fig.tight_layout(); save(fig, "f_capture.png")
    return r_u, r_s


# 14. Backbone comparison ------------------------------------------------------
def f_backbones():
    b = json.load(open("/home/claude/rep/src/backbones.json"))
    keys = ["mobilenetv3_large_100", "efficientnet_b0", "efficientnet_b2", "densenet121", "resnet50"]
    lab = ["MobileNetV3-L", "EfficientNet-B0", "EfficientNet-B2", "DenseNet-121", "ResNet-50"]
    fig, ax = plt.subplots(1, 3, figsize=(12, 3.4))
    for k, (m, t, f) in enumerate([("params_M", "Parameters (millions)", "{:.1f}"), ("gmacs", "Compute @384 px (GMACs)", "{:.2f}"), ("lat_ms", "ONNX CPU latency (ms)*", "{:.0f}")]):
        v = [b[x][m] for x in keys]; cols = [BLUE if x == "efficientnet_b0" else "#b8c7dc" for x in keys]
        rbar(ax[k], np.arange(5), v, 0.6, cols, horiz=True); ax[k].invert_yaxis()
        ax[k].set_yticks(range(5), lab if k == 0 else [""] * 5); ax[k].set_title(t, fontsize=14.5, loc="left")
        for i, val in enumerate(v): ax[k].text(val * 1.02 + max(v) * 0.01, i, f.format(val), va="center", fontsize=12.3)
        ax[k].set_xlim(0, max(v) * 1.25); ax[k].grid(axis="y", visible=False)
    fig.text(0.01, -0.03, "* Measured on the development PC (2 CPU threads, ONNX Runtime 1.29, batch 1, median of 15 runs). Raspberry Pi 5 figures are measured in Project-II.", fontsize=11.6, color=INK2)
    fig.tight_layout(); save(fig, "f_backbones.png")


def f_int8():
    q = json.load(open("/home/claude/rep/src/int8.json")); f, i8 = q["efficientnet_b0.onnx"], q["b0_int8.onnx"]
    fig, ax = plt.subplots(1, 2, figsize=(9, 2.8))
    for k, (m, t, u) in enumerate([("MB", "Model file size", "MB"), ("lat", "Latency on development PC", "ms")]):
        v = [f[m], i8[m]]; rbar(ax[k], [0, 1], v, 0.55, [BLUE, ORANGE], horiz=True); ax[k].invert_yaxis()
        ax[k].set_yticks([0, 1], ["FP32 ONNX", "INT8 ONNX (QDQ)"] if k == 0 else ["", ""])
        for j, val in enumerate(v): ax[k].text(val + max(v) * 0.02, j, f"{val:.1f} {u}", va="center", fontsize=13.0)
        ax[k].set_xlim(0, max(v) * 1.3); ax[k].set_title(t, loc="left", fontsize=14.5); ax[k].grid(axis="y", visible=False)
    fig.tight_layout(); save(fig, "f_int8.png")


def f_preproc_time():
    raw = make_fundus(2, 2000, seed=4, border=True); raw = cv2.copyMakeBorder(raw, 100, 100, 300, 300, cv2.BORDER_CONSTANT, value=0)
    steps = {}
    def tm(name, fn, n=10):
        t = []
        for _ in range(n):
            t0 = time.perf_counter(); r = fn(); t.append((time.perf_counter() - t0) * 1000)
        steps[name] = float(np.median(t)); return r
    c = tm("Crop black border", lambda: crop_fundus(raw)); sq = tm("Pad to square", lambda: pad_to_square(c))
    rs = tm("Resize to 384²", lambda: cv2.resize(sq, (384, 384), interpolation=cv2.INTER_AREA))
    tm("Ben Graham filter", lambda: cv2.addWeighted(rs, 4, cv2.GaussianBlur(rs, (0, 0), 12.8), -4, 128))
    tm("Quality metrics", lambda: quality_metrics(raw))
    fig, ax = plt.subplots(figsize=(8.5, 2.6)); n = list(steps); v = [steps[k] for k in n]
    rbar(ax, np.arange(len(n)), v, 0.6, BLUE, horiz=True); ax.invert_yaxis(); ax.set_yticks(range(len(n)), n)
    for i, val in enumerate(v): ax.text(val + max(v) * 0.02, i, f"{val:.1f} ms", va="center", fontsize=13.0)
    ax.set_xlim(0, max(v) * 1.25); ax.set_xlabel("Median time per image (ms)"); ax.grid(axis="y", visible=False)
    ax.set_title(f"Pre-processing cost for a {raw.shape[1]}×{raw.shape[0]} capture (development PC)", loc="left")
    save(fig, "f_preproc_time.png"); return steps, raw.shape


# 15. Risk matrix --------------------------------------------------------------
RISKS = [("R1", "Retinal light exposure", 2, 5), ("R2", "Wrong grade / missed referable DR", 3, 5), ("R3", "Ungradable images", 4, 3),
         ("R4", "Patient data leak", 2, 4), ("R5", "Domain shift (own camera)", 4, 4), ("R6", "Pi overheating", 2, 2),
         ("R7", "Electrical shock / burn", 1, 3), ("R8", "Component delivery delay", 3, 2), ("R9", "Colab GPU unavailable", 4, 2)]


def f_risk(after=None):
    fig, ax = plt.subplots(figsize=(7.2, 5.6))
    M = np.array([[l * s for l in range(1, 6)] for s in range(1, 6)])
    from matplotlib.colors import ListedColormap, BoundaryNorm
    cmap = ListedColormap(["#d7efe3", "#fbeec9", "#fbd5c2", "#f4b0ae"]); norm = BoundaryNorm([0, 5, 10, 15, 26], 4)
    ax.imshow(M, origin="lower", cmap=cmap, norm=norm, extent=(0.5, 5.5, 0.5, 5.5))
    ax.set_xticks(range(1, 6)); ax.set_yticks(range(1, 6)); ax.grid(False); ax.set_xlim(0.5, 5.5); ax.set_ylim(0.5, 5.5)
    ax.set_xlabel("Likelihood (L)"); ax.set_ylabel("Severity (S)")
    for l in range(1, 6):
        for s in range(1, 6): ax.text(l + 0.38, s - 0.38, l * s, fontsize=10.2, color=MUTED, ha="right", va="bottom")
    from collections import defaultdict
    cell = defaultdict(list)
    for rid, _, l, s in RISKS: cell[(l, s)].append(rid)
    for (l, s), ids in cell.items():
        for j, rid in enumerate(ids):
            ax.add_patch(Circle((l - 0.18 + 0.36 * (j % 2), s + 0.12 - 0.3 * (j // 2)), 0.17, fc=NAVY, ec="white", lw=1.5))
            ax.text(l - 0.18 + 0.36 * (j % 2), s + 0.12 - 0.3 * (j // 2), rid, color="white", fontsize=10.9, ha="center", va="center", fontweight="bold")
    for t, c in [("Low (1–4)", "#d7efe3"), ("Medium (5–9)", "#fbeec9"), ("High (10–14)", "#fbd5c2"), ("Critical (15–25)", "#f4b0ae")]:
        ax.bar(0, 0, color=c, label=t)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=4, frameon=False, fontsize=12.3)
    ax.set_title("Risk heat map before mitigation (Risk = L × S)", loc="left")
    save(fig, "f_risk.png")


# 16. Cost ---------------------------------------------------------------------
BOM = [("Raspberry Pi 5 (8 GB)", 8248), ("20 D condensing lens", 5000), ("7″ touch display", 4450), ("Camera Module 3 NoIR", 3379),
       ("USB webcam (v1)", 2500), ("Acrylic enclosure", 2500), ("USB-C PD power bank", 2500), ("BT keyboard + mouse", 1800),
       ("Shipping & consumables", 1500), ("3D-printed parts", 1500), ("Linear rods & bearings", 1200), ("27 W USB-C supply", 1094),
       ("microSD 64 GB", 900), ("Cables", 900), ("LED driver parts", 600), ("Active cooler", 469), ("Arduino Nano", 450), ("Fasteners", 400)]


def f_cost():
    fig, ax = plt.subplots(figsize=(8.5, 5.6)); n = [b[0] for b in BOM]; v = [b[1] for b in BOM]; tot = sum(v)
    cols = [BLUE] * 4 + ["#9fbbe0"] * (len(BOM) - 4)
    rbar(ax, np.arange(len(n)), v, 0.65, cols, horiz=True); ax.invert_yaxis(); ax.set_yticks(range(len(n)), n)
    for i, val in enumerate(v): ax.text(val + 80, i, f"₹{val:,}  ({100 * val / tot:.0f}%)", va="center", fontsize=12.3)
    ax.set_xlim(0, 11000); ax.set_xlabel("Estimated cost (₹)"); ax.grid(axis="y", visible=False)
    ax.set_title(f"Prototype bill of materials — total ₹{tot:,}", loc="left")
    save(fig, "f_cost.png")


# 17. Gantt ---------------------------------------------------------------------
def f_gantt():
    import datetime as dt
    D = lambda s: dt.date.fromisoformat(s)
    T = [("PROJECT-I  (7th semester)", None, None, None),
         ("Problem identification & literature survey", "2026-07-15", "2026-08-20", "done"),
         ("Dataset survey & selection (APTOS, IDRiD, Messidor)", "2026-08-05", "2026-08-31", "done"),
         ("Requirements, constraints & system design", "2026-08-25", "2026-09-25", "done"),
         ("Optical-head design (20 D indirect ophthalmoscopy)", "2026-09-15", "2026-10-20", "done"),
         ("Colab training pipeline (EfficientNet-B0)", "2026-09-28", "2026-10-31", "done"),
         ("Edge export: ONNX FP32/INT8 + Pi inference script", "2026-10-15", "2026-10-31", "done"),
         ("Prototype v1: acrylic enclosure, rails, assembly", "2026-10-01", "2026-10-31", "done"),
         ("Capture trials & fundus-image gate", "2026-10-25", "2026-11-15", "prog"),
         ("Report, presentation & mid-term review", "2026-10-25", "2026-11-25", "prog"),
         ("PROJECT-II  (8th semester)", None, None, None),
         ("Optical head v2 + 3D-printed enclosure", "2027-01-05", "2027-02-05", "plan"),
         ("Pi 5 benchmarking & touch-screen application", "2027-01-15", "2027-02-20", "plan"),
         ("Ethics approval & own-device image collection", "2027-01-10", "2027-03-15", "plan"),
         ("Fine-tuning / domain adaptation on own images", "2027-02-20", "2027-03-25", "plan"),
         ("Validation vs. ophthalmologist grading", "2027-03-10", "2027-04-05", "plan"),
         ("Final testing, paper submission & thesis", "2027-03-25", "2027-04-30", "plan")]
    col = {"done": BLUE, "prog": ORANGE, "plan": "#b8c7dc"}
    fig, ax = plt.subplots(figsize=(11.5, 6.2)); y = 0; ticks = []
    for name, s, e, st in T:
        if s is None:
            ax.text(D("2026-07-02").toordinal(), y, name, fontweight="bold", fontsize=13.8, color=NAVY, va="center"); ticks.append(("", y)); y += 1; continue
        ax.barh(y, D(e).toordinal() - D(s).toordinal(), left=D(s).toordinal(), height=0.6, color=col[st], edgecolor="white")
        ticks.append((name, y)); y += 1
    ax.set_yticks([t[1] for t in ticks], [t[0] for t in ticks], fontsize=12.8); ax.invert_yaxis(); ax.tick_params(axis="y", length=0)
    months = [D(f"{yy}-{mm:02d}-01") for yy, mm in [(2026, 7), (2026, 8), (2026, 9), (2026, 10), (2026, 11), (2026, 12), (2027, 1), (2027, 2), (2027, 3), (2027, 4), (2027, 5)]]
    ax.set_xticks([m.toordinal() for m in months], [m.strftime("%b\n%Y") if m.month in (7, 1) else m.strftime("%b") for m in months])
    ax.set_xlim(D("2026-07-01").toordinal(), D("2027-05-01").toordinal()); ax.grid(axis="y", visible=False)
    ax.axvspan(D("2026-12-01").toordinal(), D("2027-01-01").toordinal(), color="#f2f2f0", zorder=0)
    ax.text(D("2026-12-16").toordinal(), 8.5, "End-sem\nexams /\nbreak", ha="center", fontsize=11.6, color=MUTED)
    today = D("2026-10-31").toordinal(); ax.axvline(today, color=RED, lw=1.5, ls="--"); ax.text(today + 2, -0.6, "Report date", color=RED, fontsize=12.3)
    for t, c in [("Completed", BLUE), ("In progress", ORANGE), ("Planned", "#b8c7dc")]: ax.barh(0, 0, color=c, label=t)
    ax.legend(loc="lower left", frameon=False, ncol=3, fontsize=13.0)
    ax.set_title("Project schedule — Project-I (Jul–Nov 2026) and Project-II (Jan–Apr 2027)", loc="left")
    fig.tight_layout(); save(fig, "f_gantt.png")


if __name__ == "__main__":
    f_burden(); f_eye(); f_icdr(); f_datasets(); f_optics(); f_circuit(); f_preproc(); f_effnet(); f_thresholds(); f_enclosure()
    f_classdist(); f_split(); f_augment(); r = f_capture(); f_backbones(); f_int8(); st = f_preproc_time(); f_risk(); f_cost(); f_gantt()
    json.dump({"rg": r, "preproc": st}, open("/home/claude/rep/src/figmeas.json", "w"), indent=1)
    print(r, st)
