"""Test videolarının 1280 px genişlikte MJPG kopyalarını üretir: data/videolar/kucuk/<video>.avi

Model kareyi zaten 640 px'e indiriyor; 4K videoyu her model için yeniden çözmek CPU'da ~25 dk sürüyordu,
küçük kopyayla birkaç dakika. Zaman damgaları (kare no / fps) aynı kalır, gerçek durum dosyası geçerli.

Çalıştırma (ml/ klasöründe):  .venv\\Scripts\\python scripts\\video_kucult.py
"""

from pathlib import Path

import cv2

VID = Path(__file__).resolve().parents[1] / "data" / "videolar"
WIDTH = 1280

if __name__ == "__main__":
    (VID / "kucuk").mkdir(exist_ok=True)
    for v in sorted(p for p in VID.iterdir() if p.suffix in {".mp4", ".webm"}):
        dst = VID / "kucuk" / f"{v.stem}.avi"
        if dst.exists():
            continue
        cap = cv2.VideoCapture(str(v))
        fps = cap.get(cv2.CAP_PROP_FPS)
        out, n = None, 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            h, w = frame.shape[:2]
            if w > WIDTH:
                frame = cv2.resize(frame, (WIDTH, round(h * WIDTH / w)), interpolation=cv2.INTER_AREA)
            if out is None:
                size = frame.shape[1::-1]
                out = cv2.VideoWriter(str(dst), cv2.VideoWriter_fourcc(*"MJPG"), fps, size)
                out.set(cv2.VIDEOWRITER_PROP_QUALITY, 95)
            out.write(frame)
            n += 1
        out.release()
        print(f"{v.name:36s} {fps:5.2f} fps, {n} kare -> {size[0]}x{size[1]}", flush=True)
