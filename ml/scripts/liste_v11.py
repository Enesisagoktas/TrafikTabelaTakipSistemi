"""v11 listeleri: val/test 17 yeni sınıfı hiç görmüyordu (val_temiz/test_temiz yalnızca 20 temel sınıf), bu yüzden best.pt
seçimi ve erken durma yeni sınıfları ölçmüyordu. Yeni sınıf içeren DFG görsellerinin %10'u val'e alınır (eğitimden çıkar).
Çıktı: data/levha640/train_v11.txt, val_v11.txt (val_temiz + ayrılan DFG), data_v11.yaml (adlar data_v10 ile aynı).
Çalıştırma (ml/): .venv\\Scripts\\python scripts\\liste_v11.py
"""

import random
from pathlib import Path

import yaml

D = Path(__file__).resolve().parents[1] / "data" / "levha640"
NEW = set(range(20, 37))  # data_v10.yaml: 20 temel + 17 yeni (20..36) + diger_levha 37


def classes(line):
    lbl = D / line.strip()[2:].replace("/images/", "/labels/").rsplit(".", 1)[0]
    lbl = lbl.with_suffix(".txt")
    if not lbl.exists():
        return set()
    return {int(r.split()[0]) for r in lbl.read_text(encoding="utf-8").splitlines() if r.strip()}


def main():
    random.seed(0)
    train = [l for l in (D / "train_birlesik.txt").read_text(encoding="utf-8").splitlines() if l.strip()]
    dfg_new = [l for l in train if "/ek/dfg/" in l and classes(l) & NEW]
    hold = set(random.sample(dfg_new, len(dfg_new) // 10))
    train_v11 = [l for l in train if l not in hold]
    val = [l for l in (D / "val_temiz.txt").read_text(encoding="utf-8").splitlines() if l.strip()] + sorted(hold)
    (D / "train_v11.txt").write_text("\n".join(train_v11) + "\n", encoding="utf-8")
    (D / "val_v11.txt").write_text("\n".join(val) + "\n", encoding="utf-8")
    cfg = yaml.safe_load((D / "data_v10.yaml").read_text(encoding="utf-8"))
    cfg.update(train="train_v11.txt", val="val_v11.txt")
    (D / "data_v11.yaml").write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False), encoding="utf-8")
    per = {}
    for l in hold:
        for c in classes(l) & NEW:
            per[cfg["names"][c]] = per.get(cfg["names"][c], 0) + 1
    print(f"DFG'de yeni sınıflı görsel {len(dfg_new)}, val'e ayrılan {len(hold)}; train_v11 {len(train_v11)}, val_v11 {len(val)}")
    print("val'deki yeni sınıf görselleri:", dict(sorted(per.items())))
    assert not hold & set(train_v11) and len(train_v11) + len(hold) == len(train)


if __name__ == "__main__":
    main()
