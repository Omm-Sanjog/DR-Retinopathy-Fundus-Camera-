
import cv2
import numpy as np

def crop_fundus(img_rgb, tol=7):
    """Remove the black border around the circular fundus."""
    gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
    mask = gray > tol
    if mask.sum() < 0.05 * mask.size:      # almost entirely dark: leave unchanged
        return img_rgb
    rows = np.where(mask.any(axis=1))[0]
    cols = np.where(mask.any(axis=0))[0]
    return img_rgb[rows[0]:rows[-1] + 1, cols[0]:cols[-1] + 1]

def pad_to_square(img):
    h, w = img.shape[:2]
    s = max(h, w)
    out = np.zeros((s, s, 3), dtype=img.dtype)
    y, x = (s - h) // 2, (s - w) // 2
    out[y:y + h, x:x + w] = img
    return out

def preprocess_fundus(img_rgb, size=384, ben_graham=True):
    """RGB uint8 image in -> RGB uint8 (size x size) out. Used for training AND on the Pi."""
    img = pad_to_square(crop_fundus(img_rgb))
    img = cv2.resize(img, (size, size), interpolation=cv2.INTER_AREA)
    if ben_graham:   # local contrast / lighting normalisation (Ben Graham, Kaggle DR 2015)
        blur = cv2.GaussianBlur(img, (0, 0), sigmaX=size / 30)
        img = cv2.addWeighted(img, 4, blur, -4, 128)
    mask = np.zeros((size, size), np.uint8)
    cv2.circle(mask, (size // 2, size // 2), int(size * 0.47), 1, -1)
    img = img * mask[:, :, None] + 128 * (1 - mask[:, :, None])
    return img.astype(np.uint8)

def quality_metrics(img_rgb):
    """Simple image-quality numbers: brightness and sharpness of the fundus (green channel)."""
    img = pad_to_square(crop_fundus(img_rgb))
    img = cv2.resize(img, (512, 512), interpolation=cv2.INTER_AREA)
    g = img[:, :, 1]
    mask = np.zeros((512, 512), np.uint8)
    cv2.circle(mask, (256, 256), 230, 1, -1)
    inside = mask == 1
    lap = cv2.Laplacian(g, cv2.CV_64F)
    return {"brightness": float(g[inside].mean()), "sharpness": float(lap[inside].var())}
