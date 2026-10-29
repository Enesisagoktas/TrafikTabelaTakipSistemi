"""Test videolarından saniyede 1 kare çıkarır (gerçek durum incelemesi için): data/videolar/kareler/<video>/t0000.jpg

Çalıştırma (ml/ klasöründe):  .venv\\Scripts\\python scripts\\kare_cikar.py [genislik=960]
"""

import sys
from pathlib import Path

import cv2

VID = Path(__file__).resolve().parents[1] / "data" / "videolar"

if __name__ == "__main__":
    width = int(sys.argv[1]) if len(sys.argv) > 1 else 960
    for v in sorted(p for p in VID.iterdir() if p.suffix in {".mp4", ".webm"}):
        out = VID / "kareler" / v.stem
        out.mkdir(parents=True, exist_ok=True)
        cap = cv2.VideoCapture(str(v))
        fps = cap.get(cv2.CAP_PROP_FPS)
        i = saved = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if i % round(fps) == 0:  # her saniyenin ilk karesi
                h, w = frame.shape[:2]
                s = width / max(w, h)
                frame = cv2.resize(frame, (round(w * s), round(h * s)), interpolation=cv2.INTER_AREA)
                cv2.imwrite(str(out / f"t{i / fps:04.0f}.jpg"), frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
                saved += 1
            i += 1
        print(f"{v.name:36s} {fps:5.2f} fps, {i} kare, {saved} kaydedildi")
