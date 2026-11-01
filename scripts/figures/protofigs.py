import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image
import numpy as np

PH = "/home/claude/rep/photos/"; R = "/home/claude/rep/figs/"; P = R + "paper/"
plt.rcParams.update({"font.family": "DejaVu Sans", "savefig.bbox": "tight", "savefig.facecolor": "white"})
NAVY = "#1f3864"
ld = lambda f: np.array(Image.open(PH + f).convert("RGB"))

# exterior composite
fig = plt.figure(figsize=(10, 8.6))
gs = fig.add_gridspec(2, 2, height_ratios=[1.25, 1], hspace=0.12, wspace=0.04)
ax = fig.add_subplot(gs[0, :]); ax.imshow(ld("p_34.jpg")[60:900, 250:1600]); ax.axis("off"); ax.set_title("(a) Prototype v1 — three-quarter view", fontsize=14, loc="left")
ax = fig.add_subplot(gs[1, 0]); ax.imshow(ld("p_front.jpg")[0:900, 150:1450]); ax.axis("off"); ax.set_title("(b) Front panel: lens port and controls", fontsize=13, loc="left")
ax = fig.add_subplot(gs[1, 1]); ax.imshow(ld("p_side.jpg")[0:900, 250:1450]); ax.axis("off"); ax.set_title("(c) Side display and input devices", fontsize=13, loc="left")
fig.savefig(R + "r_proto_ext.png", dpi=160); plt.close(fig)

# annotated interior
img = ld("p_int.jpg")
fig, ax = plt.subplots(figsize=(10, 11.5)); ax.imshow(img); ax.axis("off")
ax.set_xlim(-900, 1800); ax.set_ylim(1600, 120)
L = [  # (label, point, text_xy, side)
    ("Touch display\n+ driver board", (205, 520), (-860, 520)),
    ("USB / HDMI to display", (165, 760), (-860, 790)),
    ("Side focus lever\n(through slot)", (215, 1240), (-860, 1210)),
    ("3D-printed corner\nbrackets", (110, 1420), (-860, 1450)),
    ("Raspberry Pi 5\n+ active cooler", (400, 530), (1000, 430)),
    ("Arduino Nano on perfboard\n(USB link to Pi)", (470, 715), (1000, 700)),
    ("Wiring harness to\nfront-panel LEDs / controls", (595, 930), (1000, 940)),
    ("Twin steel guide rails", (510, 1060), (1000, 1110)),
    ("Sliding camera carriage\n(Lenovo USB webcam)", (470, 1300), (1000, 1300)),
    ("Lens / eyepiece port", (430, 1455), (1000, 1490)),
]
for t, p, q in L:
    ax.annotate(t, xy=p, xytext=q, fontsize=15, color=NAVY, va="center", ha="left" if q[0] > 0 else "left",
                arrowprops=dict(arrowstyle="-|>", color="#d9541f", lw=1.6, shrinkA=4, shrinkB=2))
    ax.plot(*p, "o", ms=7, mfc="#d9541f", mec="white", mew=1.2)
fig.savefig(R + "r_proto_int.png", dpi=230); plt.close(fig)

# paper: column-width two panels
a = ld("p_34.jpg")[100:900, 480:1600]; b = ld("p_int.jpg")[180:1560, 120:690]
fig, ax = plt.subplots(1, 2, figsize=(3.45, 1.95), gridspec_kw=dict(width_ratios=[a.shape[1] / a.shape[0], b.shape[1] / b.shape[0]], wspace=0.03))
ax[0].imshow(a); ax[1].imshow(b)
for x, t in zip(ax, ["(a) exterior", "(b) interior"]): x.axis("off"); x.set_title(t, fontsize=6.5)
fig.savefig(P + "p_proto.png", dpi=400, pad_inches=0.02); plt.close(fig)
print("ok")
