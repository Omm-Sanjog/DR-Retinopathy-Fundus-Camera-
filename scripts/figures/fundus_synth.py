"""Synthetic (schematic) fundus images for illustration figures. Not patient data."""
import numpy as np, cv2


def _vessels(img, rng, disc, scale):
    h, w = img.shape[:2]
    def branch(p, ang, length, thick, depth):
        if depth == 0 or thick < 1:
            return
        pts = [p]
        x, y = p
        for _ in range(int(length / 6)):
            ang += rng.normal(0, 0.12)
            x += 6 * scale * np.cos(ang); y += 6 * scale * np.sin(ang)
            pts.append((x, y))
        pts_i = np.array(pts, np.int32)
        cv2.polylines(img, [pts_i], False, (115, 25, 20), int(thick), cv2.LINE_AA)
        for k in (len(pts) // 3, 2 * len(pts) // 3):
            if rng.random() < 0.85:
                branch(pts[k], ang + rng.choice([-1, 1]) * rng.uniform(0.4, 0.8),
                       length * 0.6, thick * 0.7, depth - 1)
        branch(pts[-1], ang + rng.normal(0, 0.3), length * 0.55, thick * 0.75, depth - 1)
    for a in [-2.2, -1.2, 1.2, 2.2, -2.7, 2.7, 0.2]:
        branch(disc, a, 220, 7 * scale, 4)


def make_fundus(grade=0, size=600, seed=0, border=True, uneven=True):
    rng = np.random.default_rng(seed)
    s = size / 600
    H, W = (int(size * 0.85), size) if border else (size, size)
    img = np.zeros((H, W, 3), np.float32)
    c = (W // 2, H // 2); r = int(min(H, W) * 0.47)
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.sqrt((xx - c[0]) ** 2 + (yy - c[1]) ** 2) / r
    base = np.stack([200 - 60 * d ** 2, 85 - 35 * d ** 2, 35 - 15 * d ** 2], -1)
    if uneven:
        base *= (1.05 + 0.25 * (xx - c[0]) / r)[..., None]
    img[:] = base
    tex = cv2.GaussianBlur(rng.normal(0, 8, (H, W)).astype(np.float32), (0, 0), 3 * s)
    img += tex[..., None]
    disc = (int(c[0] + 0.42 * r), int(c[1] - 0.05 * r))
    cv2.circle(img, disc, int(0.15 * r), (245, 215, 150), -1, cv2.LINE_AA)
    cv2.circle(img, disc, int(0.07 * r), (255, 240, 200), -1, cv2.LINE_AA)
    mac = (int(c[0] - 0.12 * r), int(c[1] + 0.03 * r))
    m = np.exp(-(((xx - mac[0]) ** 2 + (yy - mac[1]) ** 2) / (2 * (0.13 * r) ** 2)))
    img *= (1 - 0.35 * m)[..., None]
    v = np.zeros_like(img)
    _vessels(v, rng, disc, s)
    mask_v = v.sum(-1) > 0
    img[mask_v] = img[mask_v] * 0.45 + v[mask_v] * 0.55
    img = cv2.GaussianBlur(img, (0, 0), 1.0 * s)

    def rpt():
        while True:
            a = rng.uniform(0, 2 * np.pi); rr = r * np.sqrt(rng.uniform(0.02, 0.7))
            p = (int(c[0] + rr * np.cos(a)), int(c[1] + rr * np.sin(a)))
            if np.hypot(p[0] - disc[0], p[1] - disc[1]) > 0.2 * r:
                return p
    n_ma = [0, 10, 22, 35, 30][grade]
    for _ in range(n_ma):
        cv2.circle(img, rpt(), max(2, int(3 * s)), (110, 10, 10), -1, cv2.LINE_AA)
    n_hem = [0, 0, 6, 20, 18][grade]
    for _ in range(n_hem):
        p = rpt(); ax = (int(rng.uniform(5, 13) * s), int(rng.uniform(4, 9) * s))
        cv2.ellipse(img, p, ax, rng.uniform(0, 180), 0, 360, (120, 15, 10), -1, cv2.LINE_AA)
    n_ex = [0, 0, 12, 25, 25][grade]
    for _ in range(n_ex):
        p = rpt()
        for _ in range(rng.integers(1, 4)):
            q = (p[0] + int(rng.normal(0, 6 * s)), p[1] + int(rng.normal(0, 6 * s)))
            cv2.circle(img, q, max(2, int(rng.uniform(2, 5) * s)), (250, 225, 90), -1, cv2.LINE_AA)
    n_cws = [0, 0, 1, 4, 4][grade]
    for _ in range(n_cws):
        p = rpt(); mk = np.zeros(img.shape[:2], np.float32)
        cv2.ellipse(mk, p, (int(14 * s), int(9 * s)), rng.uniform(0, 180), 0, 360, 1.0, -1, cv2.LINE_AA)
        mk = cv2.GaussianBlur(mk, (0, 0), 3 * s)[..., None] * 0.8
        img = img * (1 - mk) + np.array([235, 215, 195], np.float32) * mk
    if grade == 4:
        for _ in range(14):
            a = rng.uniform(0, 2 * np.pi)
            pts = [(disc[0] + int(18 * s * np.cos(a)), disc[1] + int(18 * s * np.sin(a)))]
            for _ in range(10):
                a += rng.normal(0, 0.9)
                pts.append((pts[-1][0] + int(7 * s * np.cos(a)), pts[-1][1] + int(7 * s * np.sin(a))))
            cv2.polylines(img, [np.array(pts, np.int32)], False, (150, 20, 25), max(1, int(2 * s)), cv2.LINE_AA)
        p = (int(c[0] - 0.1 * r), int(c[1] + 0.45 * r))
        cv2.ellipse(img, p, (int(55 * s), int(30 * s)), 15, 0, 360, (100, 10, 10), -1, cv2.LINE_AA)
    img = cv2.GaussianBlur(img, (0, 0), 0.7 * s)
    img[d > 1] = 0
    return np.clip(img, 0, 255).astype(np.uint8)
