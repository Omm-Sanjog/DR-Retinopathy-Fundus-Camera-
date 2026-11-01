# Optical design — indirect ophthalmoscopy with a 20 D lens

```
  eye ──── ~50 mm ──── (20 D lens) ── ~50 mm ── | aerial image | ──── ~110 mm ──── [camera]
                                                (inverted, ~3×)
```

| Quantity | Calculation | Result |
|---|---|---|
| Lens focal length | f = 1 / 20 D | 50 mm |
| Magnification | P_eye / P_lens = 60 / 20 | ≈ 3× |
| Retinal patch (~45° field) | 45° × 0.29 mm/° | ≈ 13 mm |
| Aerial image size | 3 × 13 mm | ≈ 39 mm |
| Angle needed for 1,400 px | 66° × 1400 / 4608 | ≈ 20° |
| Camera ↔ aerial image | 19.5 / tan 10° | ≈ 111 mm |
| Lens ↔ camera | 50 + 111 | ≈ 160 mm |
| Retinal sampling (sensor) | 13 mm / 1400 px | ≈ 9.3 µm/px |
| Retinal sampling (384 px input) | 13 mm / 384 px | ≈ 34 µm/px |

## Capture procedure

1. Dim room so the pupil dilates naturally; IR preview only during alignment.
2. Hold the lens ~5 cm in front of the eye (not against the face).
3. Camera ~16 cm behind the lens, light coaxial with the camera.
4. Find the orange **red reflex**, then refocus until vessels appear.
5. Press capture → white flash ≤ 200 ms.

> Holding the lens against the face images the **front** of the eye (iris/sclera) — the device's fundus gate rejects such images.

Reference design: B. Y. Shen & S. Mukai, *J. Ophthalmol.* 2017, Art. 4526243.
