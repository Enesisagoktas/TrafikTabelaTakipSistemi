"""Wikimedia Commons 'Road signs in Turkey' ağacındaki gerçek fotoğrafları (JPEG/PNG; SVG, çizim, sokak tabelası hariç)
açık lisans koşuluyla indirir, en uzun kenarı 1280 px'e küçültür, atıf listesini yazar.
Çalıştırma: python -X utf8 commons_indir.py <kategori_json> <hedef_klasor>"""
import csv
import io
import json
import re
import sys
import time
from pathlib import Path

import requests
from PIL import Image

API = "https://commons.wikimedia.org/w/api.php"
H = {"User-Agent": "TrafikTabelaTakipSistemi/0.1 (https://github.com/Enesisagoktas/TrafikTabelaTakipSistemi; student project) python-requests/2.32"}
ATLA = re.compile(r"Street signs|SVG|Diagrams|historic|Road markings|Feride|Paris convention", re.I)
LISANS_OK = re.compile(r"^(CC0|CC BY(-SA)?( \d\.\d)?( [a-z]{2})?|Public domain|PD)", re.I)


def get(params):
    for d in range(8):
        try:
            r = requests.get(API, params={"format": "json", **params}, headers=H, timeout=90)
        except Exception as e:  # noqa: BLE001
            print("  ! bağlantı:", str(e)[:80], file=sys.stderr)
            time.sleep(10 * (d + 1))
            continue
        if r.status_code == 200 and r.text.startswith("{"):
            time.sleep(5.0)  # Commons: ~1 istek / 5 sn
            return r.json()
        wait = int(r.headers.get("Retry-After") or 0) or 20 * (d + 1)
        print("  !", r.status_code, " ".join(r.text[:80].split()), "->", wait, "sn", file=sys.stderr)
        time.sleep(wait)
    return {}


def files_of(cat):
    out, cont = [], {}
    while True:
        r = get({"action": "query", "list": "categorymembers", "cmtitle": cat, "cmtype": "file", "cmlimit": 500, **cont})
        out += [m["title"] for m in r.get("query", {}).get("categorymembers", [])]
        if "continue" not in r:
            return out
        cont = r["continue"]
        time.sleep(1.2)


def info(titles):
    r = get({"action": "query", "prop": "imageinfo", "titles": "|".join(titles),
             "iiprop": "url|size|mime|extmetadata", "iiextmetadatafilter": "Artist|LicenseShortName|LicenseUrl|Credit"})
    return list(r.get("query", {}).get("pages", {}).values())


def main(kat_json, hedef):
    rows = json.load(open(kat_json, encoding="utf-8"))
    cats = [c for c, nf, _ in rows if nf and not ATLA.search(c)]
    print(len(cats), "kategori")
    titles = {}
    for c in cats:
        for t in files_of(c):
            titles.setdefault(t, c)
        time.sleep(1.2)
    for t in files_of("Category:Exploring the Soul of Villages in Adana"):  # 1.325 köy fotoğrafı; yalnız yol/levha başlıklıları
        if re.search(r"Yolu|Yol |yolu|Karayolu|Kavşak|Kavsak|Tabela|Levha|D-?\d{3}", t):
            titles.setdefault(t, "Category:Exploring the Soul of Villages in Adana")
    print(len(titles), "dosya adayı")
    hedef = Path(hedef)
    (hedef / "kareler").mkdir(parents=True, exist_ok=True)
    atif = csv.writer(open(hedef / "atif.csv", "w", newline="", encoding="utf-8"))
    atif.writerow(["dosya", "commons_sayfa", "yazar", "lisans", "lisans_url", "kategori"])
    n_ok = n_lis = n_svg = 0
    tl = sorted(titles)
    for i in range(0, len(tl), 40):
        for p in info(tl[i:i + 40]):
            ii = (p.get("imageinfo") or [{}])[0]
            if not ii or not ii.get("mime", "").startswith(("image/jpeg", "image/png")):
                n_svg += 1
                continue
            md = {k: re.sub(r"<[^>]+>", "", v.get("value", "")).strip() for k, v in ii.get("extmetadata", {}).items()}
            lic = md.get("LicenseShortName", "")
            if not LISANS_OK.match(lic):
                n_lis += 1
                print("  lisans dışı:", p["title"], lic, file=sys.stderr)
                continue
            name = re.sub(r"[^\w.-]+", "_", p["title"].replace("File:", ""))[:120]
            name = re.sub(r"\.(png|PNG|jpeg|JPEG|jpg|JPG)$", "", name) + ".jpg"
            dst = hedef / "kareler" / name
            if not dst.exists():
                for d in range(4):
                    try:
                        r = requests.get(ii["url"], headers=H, timeout=120)
                        if r.status_code == 200:
                            im = Image.open(io.BytesIO(r.content)).convert("RGB")
                            im.thumbnail((1280, 1280))
                            im.save(dst, quality=92)
                            break
                        print("  !", r.status_code, ii["url"], file=sys.stderr)
                    except Exception as e:  # noqa: BLE001
                        print("  !", e, file=sys.stderr)
                    time.sleep(3 * (d + 1))
                time.sleep(1.2)
            if dst.exists():
                n_ok += 1
                atif.writerow([name, ii.get("descriptionurl", ""), md.get("Artist", ""), lic, md.get("LicenseUrl", ""), titles[p["title"]]])
        time.sleep(1.2)
    print(f"indirilen {n_ok}, lisans dışı {n_lis}, svg/başka {n_svg}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
