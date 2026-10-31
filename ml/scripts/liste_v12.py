"""train_v12.txt = train_v11.txt + ek/<yeni>/ satırları (train_birlesik.txt'den); data_v12.yaml: train_v12 / val_v11."""
import sys
from pathlib import Path
L = Path(r"C:\Projeler\TrafikTabelaTakipSistemi\ml\data\levha640")
yeni = sys.argv[1:]  # ek klasör adları
eski = L.joinpath("train_v11.txt").read_text(encoding="utf-8").splitlines()
bir = L.joinpath("train_birlesik.txt").read_text(encoding="utf-8").splitlines()
ek = []
for a in yeni:
    sat = [l for l in bir if f"ek/{a}/" in l] or [f"./ek/{a}/images/{q.name}" for q in sorted((L / "ek" / a / "images").glob("*.jpg"))]
    ek += sat
L.joinpath("train_v12.txt").write_text("\n".join(eski + ek) + "\n", encoding="utf-8")
y = L.joinpath("data_v12.yaml").read_text(encoding="utf-8")
y = y.replace("train: train_birlesik.txt", "train: train_v12.txt").replace("val: val_temiz.txt", "val: val_v11.txt")
L.joinpath("data_v12.yaml").write_text(y, encoding="utf-8")
print(len(eski), "+", len(ek), "=", len(eski) + len(ek), "train;", {a: sum(f"ek/{a}/" in l for l in ek) for a in yeni})
print(y[:120])
