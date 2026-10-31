"""Wikimedia Commons: Category:Road signs in Turkey ağacını (derinlik 3) dolaşır, alt kategori başına dosya sayısını yazar.
Ayrıca Türkiye'de sürüş videosu kategorilerini dener. Giriş yok, yalnız okuma API'si."""
import json
import sys
import time

import requests

API = "https://commons.wikimedia.org/w/api.php"
H = {"User-Agent": "TrafikTabelaTakipSistemi/0.1 (student project; contact via GitHub Enesisagoktas)"}


def members(cat, cmtype):
    out, cont = [], {}
    while True:
        for deneme in range(5):
            resp = requests.get(API, params={"action": "query", "list": "categorymembers", "cmtitle": cat, "cmtype": cmtype,
                                             "cmlimit": 500, "format": "json", **cont}, headers=H, timeout=60)
            if resp.status_code == 200 and resp.text.startswith("{"):
                r = resp.json()
                break
            print("  !", resp.status_code, " ".join(resp.text[:120].split()), file=sys.stderr)
            time.sleep(3 * (deneme + 1))
        else:
            return out
        out += [m["title"] for m in r["query"]["categorymembers"]]
        if "continue" not in r:
            return out
        cont = r["continue"]
        time.sleep(0.5)


def walk(cat, depth, seen, rows):
    if cat in seen or depth < 0:
        return
    seen.add(cat)
    time.sleep(0.5)
    files = members(cat, "file")
    subs = members(cat, "subcat")
    rows.append((cat, len(files), len(subs)))
    for s in subs:
        walk(s, depth - 1, seen, rows)


if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else "Category:Road signs in Turkey"
    rows, seen = [], set()
    walk(root, 3, seen, rows)
    tot = 0
    for cat, nf, ns in rows:
        tot += nf
        print(f"{nf:4d} dosya {ns:3d} altkat  {cat}")
    print("TOPLAM dosya:", tot, "kategori:", len(rows))
    json.dump(rows, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False) if len(sys.argv) > 2 else None
