"""DFG levha veri setini (Slovenya, ViCoS; CC BY-NC-SA 4.0) YOLO düzenine çevirir, sonra ek_veri.py ile eklenir.

Kaynak: Tabernik & Skočaj 2019, IEEE T-ITS, doi 10.1109/TITS.2019.2913588. https://www.vicos.si/resources/dfg/
Bütün levhalar (200 sınıf) etiketli olduğu için bizim 20 sınıfa girmeyenler (şerit levhaları, yükseklik/ağırlık
sınırı, başka uyarı üçgenleri, hız sonu...) modele "uyarı verme" diye öğretilir: yanlış alarmın ana kaynağı bunlar.

Görüntü arşivi (JPEGImages.tar.bz2, 7,5 GB) data/dis/dfg/parcalar/p000, p001, ... diye 64 MB'lık parçalarla
iner; baştan kesintisiz tam parçalar tek akış olarak okunur, böylece arşivin yalnızca inmiş kısmı da kullanılabilir.
Yalnızca gerçek görüntüler (no <= 7489) alınır; sentetik (yapıştırılmış) olanlar alınmaz. Etiketler:
train-difficult.json (gerçek görüntülerde 30 px altı levhalar "ignore" kutusu olarak var) + test.json.
Küçük levhalar da etiket olarak yazılır (bizim veride de küçük levhalar etiketli).

Çalıştırma (ml/ klasöründe):
  .venv\\Scripts\\python scripts\\dfg_hazirla.py
  .venv\\Scripts\\python scripts\\ek_veri.py data\\dis\\dfg\\stage dfg scripts\\esleme_dfg.json --atla III-29-30,III-29-40,III-30-30 --arka-plan
--atla: "CONA 30/40" bölge levhaları bizim hız levhasıyla aynı daireyi taşıyor; ne levha ne arka plan sayılsın.
"""

import io
import json
import shutil
import tarfile
from pathlib import Path

import yaml

DFG = Path(__file__).resolve().parents[1] / "data" / "dis" / "dfg"
CHUNK, TOTAL, LAST_REAL = 64 * 1024 * 1024, 7491490842, 7489


class Prefix(io.RawIOBase):
    """parcalar/p000, p001, ... dosyalarını, tamamı inmiş olanlar bitene kadar tek akış gibi okur."""

    def __init__(self, folder):
        self.files, self.cur, i = [], None, 0
        while (f := folder / f"p{i:03d}").exists() and f.stat().st_size == min(CHUNK, TOTAL - i * CHUNK):
            self.files.append(f)
            i += 1
        print(f"{i} tam parça ({i * CHUNK / 1e9:.2f} GB)")

    def readable(self):
        return True

    def readinto(self, b):
        while True:
            if self.cur is None:
                if not self.files:
                    return 0
                self.cur = open(self.files.pop(0), "rb")
            if n := self.cur.readinto(b):
                return n
            self.cur.close()
            self.cur = None


def main():
    per_img, names = {}, None
    for js in ("train-difficult.json", "test.json"):
        d = json.loads((DFG / "annot" / js).read_text())
        cats = sorted(d["categories"], key=lambda c: c["id"])
        assert [c["id"] for c in cats] == list(range(len(cats)))
        assert names in (None, [c["name"] for c in cats])
        names = [c["name"] for c in cats]
        ims = {im["id"]: im for im in d["images"] if int(Path(im["file_name"]).stem) <= LAST_REAL}
        for im in ims.values():
            per_img[im["file_name"]] = (im["width"], im["height"], [])
        for a in d["annotations"]:
            if a["image_id"] in ims:
                per_img[ims[a["image_id"]]["file_name"]][2].append((a["category_id"], a["bbox"]))

    out = DFG / "stage"
    shutil.rmtree(out, ignore_errors=True)
    (out / "images").mkdir(parents=True)
    (out / "labels").mkdir()
    (out / "data.yaml").write_text(yaml.safe_dump({"names": names}), encoding="utf-8")
    n = boxes = 0
    try:
        with tarfile.open(fileobj=io.BufferedReader(Prefix(DFG / "parcalar"), 1 << 20), mode="r|bz2") as tf:
            for m in tf:
                name = Path(m.name).name
                if name not in per_img:  # sentetik görüntü
                    continue
                data = tf.extractfile(m).read()
                W, H, anns = per_img[name]
                lines = []
                for c, (x, y, w, h) in anns:
                    x1, y1, x2, y2 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
                    if x2 - x1 >= 2 and y2 - y1 >= 2:
                        lines.append(f"{c} {(x1 + x2) / 2 / W:.6f} {(y1 + y2) / 2 / H:.6f} {(x2 - x1) / W:.6f} {(y2 - y1) / H:.6f}\n")
                (out / "images" / name).write_bytes(data)
                (out / "labels" / f"{Path(name).stem}.txt").write_text("".join(lines))
                n += 1
                boxes += len(lines)
    except (EOFError, tarfile.ReadError) as e:  # arşivin inmemiş kısmı
        print("arşiv önekinin sonu:", e)
    print(f"{n} gerçek görüntü, {boxes} kutu -> {out}")


if __name__ == "__main__":
    main()
