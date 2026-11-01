"""Column-width (3.5 in) figures for the IEEE paper."""
import json, subprocess
import numpy as np, cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Ellipse, Rectangle, FancyBboxPatch, Arc
from fundus_synth import make_fundus
exec(open("/home/claude/rep/src/preproc_code.py").read())

OUT = "/home/claude/rep/figs/paper/"
import os; os.makedirs(OUT, exist_ok=True)
BLUE, ORANGE, AQUA, RED, VIOLET, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#e34948", "#6250d6", "#eda100"
INK2, MUTED, GRID, NAVY = "#3a3a38", "#8a8984", "#e5e4df", "#1f3864"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 7, "axes.titlesize": 7.5, "axes.titleweight": "bold",
    "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": "#bdbcb6", "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.6, "axes.axisbelow": True, "xtick.color": INK2, "ytick.color": INK2, "axes.labelcolor": INK2,
    "savefig.dpi": 400, "savefig.bbox": "tight", "savefig.pad_inches": 0.02, "savefig.facecolor": "white"})
W = 3.45


def save(fig, n): fig.savefig(OUT + n); plt.close(fig); print("saved", n)


# Fig: optical layout
def optics():
    fig, ax = plt.subplots(figsize=(W, 1.25)); ax.axis("off"); ax.set_aspect("equal"); ax.set_xlim(-2, 31.5); ax.set_ylim(-5.6, 4.6)
    ax.add_patch(Circle((0, 0), 1.2, fc="#fbf3ec", ec="#b9a99a", lw=1)); ax.add_patch(Arc((0, 0), 2.3, 2.3, theta1=-130, theta2=130, color=RED, lw=2))
    lx, ix, cx = 5.0, 10.0, 22.0
    ax.add_patch(Ellipse((lx, 0), 0.6, 6.5, fc="#cfe3f7", ec=BLUE, lw=1))
    ax.plot([ix, ix], [-2.2, 2.2], color=VIOLET, lw=1.2, ls="--")
    for y0 in [-0.6, 0, 0.6]:
        ax.plot([-0.9, lx], [y0 * 0.5, y0 * 4], color=YELLOW, lw=0.7); ax.plot([lx, ix], [y0 * 4, -y0 * 3.3], color=YELLOW, lw=0.7)
        ax.plot([ix, cx], [-y0 * 3.3, -y0 * 0.5], color=YELLOW, lw=0.6)
    ax.add_patch(FancyBboxPatch((cx, -1.9), 8.6, 3.8, boxstyle="round,pad=0.15", fc="#e8eef8", ec=NAVY, lw=1))
    ax.text(cx + 4.3, 0, "Camera\nModule 3\nNoIR", ha="center", va="center", fontsize=6, color=NAVY)
    ax.add_patch(Rectangle((cx - 1.0, 1.9), 0.8, 0.6, fc=RED, ec="none")); ax.text(cx - 0.6, 2.8, "IR + white LED", ha="center", fontsize=6)
    ax.text(0, -1.6, "eye", ha="center", va="top", fontsize=6); ax.text(lx, 3.6, "20 D lens", ha="center", fontsize=6)
    ax.text(ix, 2.5, "aerial\nimage", ha="center", fontsize=6, color=VIOLET)
    for a, b, y, t in [(-1.2, lx, -4.0, "≈ 50 mm"), (ix, cx, -4.0, "≈ 110 mm")]:
        ax.annotate("", xy=(b, y), xytext=(a, y), arrowprops=dict(arrowstyle="<->", color=INK2, lw=0.7)); ax.text((a + b) / 2, y - 1.4, t, ha="center", fontsize=6, color=INK2)
    save(fig, "p_optics.png")


# Fig: preprocessing
def preproc():
    raw = make_fundus(2, 700, seed=5, border=True, uneven=True); raw = cv2.copyMakeBorder(raw, 40, 40, 120, 120, cv2.BORDER_CONSTANT, value=0)
    s2 = pad_to_square(crop_fundus(raw)); s3 = cv2.resize(s2, (384, 384), interpolation=cv2.INTER_AREA)
    s4 = cv2.addWeighted(s3, 4, cv2.GaussianBlur(s3, (0, 0), 12.8), -4, 128); s5 = preprocess_fundus(raw, 384)
    fig, ax = plt.subplots(1, 4, figsize=(W, 1.05))
    for a, im, t in zip(ax, [raw, s3, s4, s5], ["(a) raw", "(b) crop+resize", "(c) Ben Graham", "(d) masked input"]):
        a.imshow(im); a.axis("off"); a.set_title(t, fontsize=6, fontweight="normal")
    save(fig, "p_preproc.png")


# Fig: backbones
def backbones():
    b = json.load(open("/home/claude/rep/src/backbones.json"))
    keys = ["mobilenetv3_large_100", "efficientnet_b0", "efficientnet_b2", "densenet121", "resnet50"]
    lab = ["MobileNetV3-L", "EfficientNet-B0", "EfficientNet-B2", "DenseNet-121", "ResNet-50"]
    fig, ax = plt.subplots(1, 2, figsize=(W, 1.45))
    for k, (m, t, f) in enumerate([("gmacs", "GMACs @ 384 px", "{:.2f}"), ("lat_ms", "CPU latency (ms)", "{:.0f}")]):
        v = [b[x][m] for x in keys]; c = [BLUE if x == "efficientnet_b0" else "#b8c7dc" for x in keys]
        ax[k].barh(range(5), v, color=c, height=0.62); ax[k].invert_yaxis()
        ax[k].set_yticks(range(5), lab if k == 0 else [""] * 5); ax[k].set_title(t, loc="left")
        for i, val in enumerate(v): ax[k].text(val + max(v) * 0.03, i, f.format(val), va="center", fontsize=5.8)
        ax[k].set_xlim(0, max(v) * 1.3); ax[k].grid(axis="y", visible=False); ax[k].tick_params(labelsize=6)
    fig.tight_layout(w_pad=0.4); save(fig, "p_backbones.png")


# Fig: gate
def rg(rgb):
    img = cv2.resize(rgb, (256, 256)).astype(np.float32); lit = img.mean(2) >= 20
    return float(np.median(img[..., 0][lit] / (img[..., 1][lit] + 1)))


def gate():
    u = cv2.cvtColor(cv2.imread("/home/claude/rep/src/capture_trial.png"), cv2.COLOR_BGR2RGB); crop = u[620:1230, 30:660]
    syn = make_fundus(1, 500, seed=31, border=True)
    fig, ax = plt.subplots(1, 3, figsize=(W, 1.3), gridspec_kw=dict(width_ratios=[1, 1.15, 1.25]))
    ax[0].imshow(crop); ax[0].axis("off"); ax[0].set_title("(a) trial capture", fontsize=6.3, fontweight="normal")
    ax[1].imshow(syn); ax[1].axis("off"); ax[1].set_title("(b) fundus (schematic)", fontsize=6.3, fontweight="normal")
    v = [rg(u), rg(syn)]; ax[2].bar([0, 1], v, color=[MUTED, RED], width=0.55)
    ax[2].axhline(1.6, color="k", lw=0.8, ls="--"); ax[2].text(-0.38, 1.7, "threshold 1.6", fontsize=5.6)
    for i, x in enumerate(v): ax[2].text(i, x / 2, f"{x:.2f}", ha="center", va="center", fontsize=6.5, fontweight="bold", color="white")
    ax[2].set_xticks([0, 1], ["(a) reject", "(b) accept"], fontsize=6); ax[2].set_ylabel("median R/G", fontsize=6); ax[2].set_ylim(0, 3.2)
    ax[2].tick_params(labelsize=6); ax[2].grid(axis="x", visible=False); ax[2].set_title("(c) gate statistic", fontsize=6.3, fontweight="normal")
    fig.tight_layout(w_pad=0.3); save(fig, "p_gate.png")


# Fig: system pipeline (graphviz, column width)
def pipeline():
    dot = '''digraph G { rankdir=TB; nodesep=0.12; ranksep=0.14;
graph [fontname="DejaVu Sans", pad=0.02];
node [fontname="DejaVu Sans", fontsize=8.5, shape=box, style="rounded,filled", margin="0.08,0.03", height=0.3, penwidth=0.9];
edge [arrowsize=0.5, penwidth=0.8, color="#52514e", fontname="DejaVu Sans", fontsize=7];
a [label="Eye + 20 D lens + IR/white LEDs", fillcolor="#fdeadf", color="#d9541f"];
b [label="Camera Module 3 NoIR → Raspberry Pi 5", fillcolor="#e3eefc", color="#2a78d6"];
c [label="Quality gate (sharpness, brightness)\\n+ fundus gate (median R/G ≥ 1.6)", fillcolor="#fdf3d6", color="#b88200"];
r [label="Retake\\nprompt", fillcolor="#fbe3e3", color="#c43c3b"];
d [label="Crop → 384 px → Ben Graham → mask", fillcolor="#dff5ec", color="#14936a"];
e [label="EfficientNet-B0 (ONNX, FP32/INT8) → score ŷ", fillcolor="#1f3864", color="#1f3864", fontcolor="white"];
f [label="Thresholds → ICDR grade 0–4 + referral flag", fillcolor="#ebe8fb", color="#6250d6"];
a -> b -> c; c -> d [label=" pass"]; c -> r [label=" fail"]; d -> e -> f; {rank=same; c; r}
}'''
    open("/home/claude/rep/src/p_pipe.dot", "w").write(dot)
    subprocess.run(["dot", "-Tpng", "-Gdpi=400", "/home/claude/rep/src/p_pipe.dot", "-o", OUT + "p_pipeline.png"], check=True); print("saved p_pipeline.png")


optics(); preproc(); backbones(); gate(); pipeline()
