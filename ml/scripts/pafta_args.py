"""pafta_denetim.js akışı için args JSON'u üretir: python pafta_args.py <ad>  (data/dis/<ad>_sozde)"""
import json
import re
import sys
from pathlib import Path

import yaml

ad = sys.argv[1]
d = Path(r"C:\Projeler\TrafikTabelaTakipSistemi\ml\data\dis") / f"{ad}_sozde"
names = yaml.safe_load((d / "data.yaml").read_text(encoding="utf-8"))["names"]
sheets = []
for p in sorted(d.glob("pafta_*.jpg")):
    m = re.match(r"pafta_(.+)_(\d+)\.jpg$", p.name)
    sheets.append({"file": p.name, "sinif": m.group(1)})
important = [n for n in names if n not in ("diger_levha",)]  # yeni 17 + temel 20: hepsi çift denetim; diger tek
out = {"dir": str(d), "sheets": sheets, "important": important, "names": names}
Path(sys.argv[2]).write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8") if len(sys.argv) > 2 else None
print(len(sheets), "pafta;", json.dumps({s: sum(1 for x in sheets if x["sinif"] == s) for s in sorted({x["sinif"] for x in sheets})}, ensure_ascii=False))
