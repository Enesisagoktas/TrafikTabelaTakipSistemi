"""Kaggle'a yüklenecek veri paketini yapar: yalnız train_v14 / val_v14 / test_temiz listelerindeki görseller ve etiketleri,
data_v14.yaml, ek_veri.py + oto_esleme.py, başlangıç ağırlığı v13.pt. JPEG zaten sıkışık: zip sıkıştırmasız (hızlı).

  python ml/kaggle/paket_yap.py [cikti.zip] [N]   (varsayılan ml/data/kaggle_yukle/trafik_levha_v14_kaggle.zip;
                                                 N: her listeden ilk N görsel, yalnız deneme paketi için)
"""
import sys
import zipfile
from pathlib import Path

M = Path(__file__).resolve().parents[1]
L = M / "data" / "levha640"
out = Path(sys.argv[1]) if len(sys.argv) > 1 else M / "data" / "kaggle_yukle" / "trafik_levha_v14_kaggle.zip"
out.parent.mkdir(parents=True, exist_ok=True)
N = int(sys.argv[2]) if len(sys.argv) > 2 else None

LISTE = ("train_v14.txt", "val_v14.txt", "test_temiz.txt")
satirlar = {f: [s for s in (L / f).read_text(encoding="utf-8").splitlines() if s.strip()][:N] for f in LISTE}
dosyalar = {L / "data_v14.yaml"}
for liste in LISTE:
    for s in satirlar[liste]:
        img = L / s.strip()[2:]
        lbl = img.parent.parent / "labels" / f"{img.stem}.txt"
        dosyalar.add(img)
        if lbl.exists():
            dosyalar.add(lbl)
eksik = [p for p in dosyalar if not p.exists()]
assert not eksik, eksik[:5]

with zipfile.ZipFile(out, "w", zipfile.ZIP_STORED) as z:
    for p in sorted(dosyalar):
        z.write(p, ("ml" / p.relative_to(M)).as_posix())
    for f in LISTE:  # N ile kısaltılmış olabilir
        z.writestr(f"ml/data/levha640/{f}", "\n".join(satirlar[f]) + "\n")
    for f in ("ek_veri.py", "oto_esleme.py"):
        z.write(M / "scripts" / f, f"ml/scripts/{f}")
    z.write(M / "runs" / "detect" / "v13" / "weights" / "best.pt", "ml/agirlik/v13.pt")
print(f"{len(dosyalar)} dosya -> {out} ({out.stat().st_size / 1e9:.2f} GB)")
