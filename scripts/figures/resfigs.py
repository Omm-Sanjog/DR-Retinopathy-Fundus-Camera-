"""Result figures regenerated from the user's Colab run (values logged in the executed notebook)."""
import numpy as np, shutil
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image

NB = "/home/claude/rep/nb/"; R = "/home/claude/rep/figs/"; P = "/home/claude/rep/figs/paper/"
BLUE, ORANGE, AQUA, RED, INK2, GRID, NAVY = "#2a78d6", "#eb6834", "#1baf7a", "#e34948", "#52514e", "#e5e4df", "#1f3864"
ep = np.arange(1, 21)
tr = [3.8505, 2.2857, 1.4590, 1.1885, 0.8173, 0.6155, 0.4707, 0.4054, 0.3152, 0.3028, 0.2637, 0.2547, 0.2264, 0.2212, 0.1997, 0.1977, 0.1873, 0.1791, 0.1859, 0.1882]
vl = [1.9815, 1.2275, 0.8968, 0.7584, 0.6941, 0.3713, 0.3899, 0.2670, 0.4114, 0.3638, 0.2242, 0.2068, 0.3661, 0.2117, 0.2119, 0.2191, 0.1989, 0.1952, 0.1947, 0.1986]
vq = [0.2592, 0.2138, 0.3243, 0.3188, 0.4465, 0.6901, 0.6422, 0.7276, 0.6498, 0.6529, 0.7812, 0.7892, 0.6697, 0.7949, 0.7889, 0.7814, 0.8140, 0.8189, 0.8137, 0.8181]
va = [0.355, 0.366, 0.341, 0.373, 0.514, 0.474, 0.612, 0.630, 0.603, 0.596, 0.674, 0.659, 0.616, 0.698, 0.690, 0.696, 0.696, 0.730, 0.698, 0.712]
CM = np.array([[250, 20, 1, 0, 0], [6, 21, 26, 3, 0], [3, 7, 82, 53, 5], [0, 2, 1, 13, 13], [0, 2, 5, 19, 18]])
G = ["No DR", "Mild", "Moderate", "Severe", "PDR"]


def style(fs):
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": fs, "axes.spines.top": False, "axes.spines.right": False,
                         "axes.edgecolor": "#bdbcb6", "axes.grid": True, "grid.color": GRID, "axes.axisbelow": True,
                         "axes.titleweight": "bold", "axes.titlesize": fs + 1, "savefig.bbox": "tight", "savefig.facecolor": "white",
                         "xtick.color": INK2, "ytick.color": INK2, "axes.labelcolor": INK2})


def curves(path, size, fs, dpi, small=False):
    style(fs); fig, ax = plt.subplots(1, 2, figsize=size)
    ax[0].plot(ep, tr, color=BLUE, lw=1.8, marker="o", ms=3, label="Training"); ax[0].plot(ep, vl, color=ORANGE, lw=1.8, marker="o", ms=3, label="Validation")
    ax[0].set_xlabel("Epoch"); ax[0].set_ylabel("Smooth-L1 loss"); ax[0].set_title("(a) Loss", loc="left"); ax[0].legend(frameon=False); ax[0].set_xticks([1, 5, 10, 15, 20])
    ax[1].plot(ep, vq, color=BLUE, lw=1.8, marker="o", ms=3, label="Validation QWK"); ax[1].plot(ep, va, color=ORANGE, lw=1.8, marker="o", ms=3, label="Validation accuracy")
    b = int(np.argmax(vq)); ax[1].scatter([ep[b]], [vq[b]], s=60, facecolor="none", edgecolor=RED, lw=1.5, zorder=5)
    if not small: ax[1].annotate(f"best QWK {vq[b]:.3f}\n(epoch {ep[b]})", xy=(ep[b], vq[b]), xytext=(ep[b] - 9, 0.45), fontsize=fs - 0.5, arrowprops=dict(arrowstyle="->", color=INK2, lw=0.8))
    ax[1].set_xlabel("Epoch"); ax[1].set_ylim(-0.1 if small else 0.15, 0.9); ax[1].set_title("(b) Validation metrics", loc="left"); ax[1].legend(frameon=False, loc="lower right", fontsize=fs - (2 if small else 0), handlelength=1.2, markerscale=0.6); ax[1].set_xticks([1, 5, 10, 15, 20])
    fig.tight_layout(); fig.savefig(path, dpi=dpi); plt.close(fig)


def confusion(path, size, fs, dpi, ticks=G):
    style(fs); fig, ax = plt.subplots(figsize=size)
    rown = CM / CM.sum(1, keepdims=True)
    ax.imshow(rown, cmap="Blues", vmin=0, vmax=1); ax.grid(False)
    for i in range(5):
        for j in range(5):
            ax.text(j, i, f"{CM[i, j]}", ha="center", va="center", fontsize=fs, color="white" if rown[i, j] > 0.55 else "#1b1b1b", fontweight="bold" if i == j else "normal")
    ax.set_xticks(range(5), ticks, rotation=30, ha="right"); ax.set_yticks(range(5), ticks)
    ax.set_xlabel("Predicted grade"); ax.set_ylabel("True grade")
    ax.add_patch(plt.Rectangle((1.5, 1.5), 3, 3, fill=False, ec=RED, lw=1.4, ls="--")); ax.add_patch(plt.Rectangle((-0.5, -0.5), 2, 2, fill=False, ec=AQUA, lw=1.4, ls="--"))
    for s in ax.spines.values(): s.set_visible(False)
    fig.tight_layout(); fig.savefig(path, dpi=dpi); plt.close(fig)


def int8(path):
    style(13); fig, ax = plt.subplots(1, 3, figsize=(11, 3.0))
    data = [([16.0, 4.83], "Model file size (MB)", "{:.1f}"), ([0.877, 0.570], "Test QWK (training run)", "{:.3f}"), ([36.4, 60.9], "Latency, dev. PC (ms)", "{:.1f}")]
    for k, (v, t, f) in enumerate(data):
        ax[k].barh([0, 1], v, color=[BLUE, ORANGE], height=0.55, edgecolor="white"); ax[k].invert_yaxis()
        ax[k].set_yticks([0, 1], ["FP32", "INT8"] if k == 0 else ["", ""])
        for j, val in enumerate(v): ax[k].text(val + max(v) * 0.03, j, f.format(val), va="center", fontsize=12)
        ax[k].set_xlim(0, max(v) * 1.35); ax[k].set_title(t, loc="left", fontsize=13); ax[k].grid(axis="y", visible=False)
    fig.tight_layout(); fig.savefig(path, dpi=220); plt.close(fig)


def perclass(path):
    style(13); rec = [0.923, 0.375, 0.547, 0.448, 0.409]; pre = [0.965, 0.404, 0.713, 0.148, 0.500]
    fig, ax = plt.subplots(figsize=(8.5, 3.2)); x = np.arange(5); w = 0.36
    ax.bar(x - w / 2, pre, w, color=BLUE, label="Precision", edgecolor="white"); ax.bar(x + w / 2, rec, w, color=ORANGE, label="Recall", edgecolor="white")
    for i in range(5):
        ax.text(x[i] - w / 2, pre[i] + 0.02, f"{pre[i]:.2f}", ha="center", fontsize=10); ax.text(x[i] + w / 2, rec[i] + 0.02, f"{rec[i]:.2f}", ha="center", fontsize=10)
    ax.set_xticks(x, ["0 No DR (271)", "1 Mild (56)", "2 Moderate (150)", "3 Severe (29)", "4 PDR (44)"]); ax.set_ylim(0, 1.12); ax.legend(frameon=False, ncol=2, loc="upper right")
    ax.grid(axis="x", visible=False); ax.set_title("Per-grade precision and recall on the test set (support in brackets)", loc="left")
    fig.tight_layout(); fig.savefig(path, dpi=220); plt.close(fig)


curves(R + "r_curves.png", (10, 3.6), 12, 220)
confusion(R + "r_confusion.png", (5.2, 4.4), 12, 220, ["0 No DR", "1 Mild", "2 Moderate", "3 Severe", "4 PDR"])
int8(R + "r_int8.png"); perclass(R + "r_perclass.png")
# ROC panel cropped from the notebook's own plot; Grad-CAM and sample grid used as produced
im = Image.open(NB + "img_c7_3.png"); w, h = im.size; im.crop((int(w * 0.47), 0, w, h)).save(R + "r_roc.png")
shutil.copy(NB + "img_c8_4.png", R + "r_gradcam.png"); shutil.copy(NB + "img_c4_1.png", R + "r_samples.png")
# paper versions (3.45 in column)
curves(P + "p_curves.png", (3.45, 1.55), 6.5, 400, small=True)
confusion(P + "p_confusion.png", (2.5, 2.2), 7, 400)
print("done")
