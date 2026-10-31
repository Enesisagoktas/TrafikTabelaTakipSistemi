"""Yeni karelerin 10 test videosuyla çakışma denetimi (aynı klip eğitime girmesin).
1) python test_benzerlik.py hazirla            -> test videolarının 1 kare/sn 16x16 gri imzaları (test_imza.npz)
2) python test_benzerlik.py kontrol <kare_klasoru> -> klip başına en yakın test karesi (MSE) ve eşik altı kare sayısı"""
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(r"C:\Projeler\TrafikTabelaTakipSistemi")
IMZA = Path(__file__).with_name("test_imza.npz")


def imza(img):
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    g = cv2.resize(g, (16, 16), interpolation=cv2.INTER_AREA).astype(np.float32)
    return (g - g.mean()) / (g.std() + 1e-6)


def hazirla():
    sigs, names = [], []
    for v in sorted((ROOT / "ml/data/videolar/kucuk").glob("*.avi")):
        cap = cv2.VideoCapture(str(v))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        i = 0
        while True:
            ok, fr = cap.read()
            if not ok:
                break
            if i % int(round(fps)) == 0:
                sigs.append(imza(fr))
                names.append(f"{v.stem}@{i / fps:.0f}s")
            i += 1
        print(v.stem, len([n for n in names if n.startswith(v.stem)]), "imza")
    np.savez_compressed(IMZA, sigs=np.stack(sigs), names=np.array(names))


def kontrol(klasor):
    d = np.load(IMZA)
    S, N = d["sigs"].reshape(len(d["names"]), -1), d["names"]
    by_clip = {}
    for p in sorted(Path(klasor).glob("*.jpg")):
        clip = p.stem.rsplit("_", 1)[0]
        img = cv2.imread(str(p))
        if img is None:
            continue
        q = imza(img).reshape(1, -1)
        mse = ((S - q) ** 2).mean(axis=1)
        j = int(mse.argmin())
        by_clip.setdefault(clip, []).append((float(mse[j]), N[j], p.name))
    for clip, lst in by_clip.items():
        lst.sort()
        yakin = sum(m < 0.15 for m, _, _ in lst)
        print(f"{clip:22s} kare {len(lst):5d}  en yakın MSE {lst[0][0]:.3f} ({lst[0][1]}, {lst[0][2]})  MSE<0,15: {yakin}")


if __name__ == "__main__":
    hazirla() if sys.argv[1] == "hazirla" else kontrol(sys.argv[2])
