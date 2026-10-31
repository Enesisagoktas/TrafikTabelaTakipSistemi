"""Eğitim listesindeki sınıf başına kutu sayısı (sentetik.py ağırlığı için). python scripts/sinif_sayim.py train_v11.txt sinif_sayim.json"""
import collections
import json
import sys
from pathlib import Path

L = Path(__file__).resolve().parent.parent / "data" / "levha640"
names = [l.strip("- \n") for l in (L / "data_v11.yaml").read_text(encoding="utf-8").splitlines() if l.startswith("- ")]
c = collections.Counter()
for l in (L / sys.argv[1]).read_text(encoding="utf-8").splitlines():
    p = Path(l.replace("./", ""))
    t = L / p.parent.parent / "labels" / (p.stem + ".txt")  # stem: Hootbu adlarında nokta var, with_suffix yanlış keser
    if t.exists():
        for sat in t.read_text().splitlines():
            if sat.strip():
                c[names[int(sat.split()[0])]] += 1
d = {n: c[n] for n in names}
json.dump(d, open(sys.argv[2], "w"), indent=0)
print(d)
