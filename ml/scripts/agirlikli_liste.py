"""Zayıf sınıfları çoğaltan eğitim listesi (oversampling): data/levha640/train_agirlikli.txt + data_v3.yaml.

Zayıf sınıfların geçtiği train görselleri listeye ek kez yazılır; model onları her epoch daha sık görür.
Seçim Hafta 2 elden geçirmesinden (temiz test AP50): pedestrian_info, speed70, speed30, giveway.

Çalıştırma (ml/ klasöründe):  .venv\\Scripts\\python scripts\\agirlikli_liste.py
"""

from pathlib import Path

import yaml

ZAYIF = {"pedestrian_info", "speed70", "speed30", "giveway"}
EK = 1  # zayıf sınıf içeren görsel kaç kez daha eklensin

DATA = Path(__file__).resolve().parents[1] / "data" / "levha640"

if __name__ == "__main__":
    cfg = yaml.safe_load((DATA / "data_temiz.yaml").read_text(encoding="utf-8"))
    zayif_id = {i for i, n in enumerate(cfg["names"]) if n in ZAYIF}
    lines, ekstra = [], 0
    for img in sorted((DATA / "train" / "images").glob("*.jpg")):
        lbl = DATA / "train" / "labels" / f"{img.stem}.txt"
        sinif = {int(r.split()[0]) for r in lbl.read_text().splitlines() if r.strip()}
        kopya = 1 + (EK if sinif & zayif_id else 0)
        lines += [f"./train/images/{img.name}"] * kopya
        ekstra += kopya - 1
    (DATA / "train_agirlikli.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    cfg["train"] = "train_agirlikli.txt"
    (DATA / "data_v3.yaml").write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"{len(lines)} satır ({ekstra} ek kopya) -> {DATA / 'train_agirlikli.txt'}")
