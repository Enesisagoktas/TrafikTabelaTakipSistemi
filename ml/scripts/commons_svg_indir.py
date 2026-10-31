"""Commons'taki resmi Türk levha çizimlerini (SVG) 256 px PNG olarak indirir (Commons'ın kendi küçük resmi; yerel SVG çizici gerekmez)
ve başlıklı bir pafta yazar (sınıf eşlemesini gözle yapmak için). Çalıştırma: python -X utf8 commons_svg_indir.py <hedef>"""
import csv
import io
import re
import sys
import time
from pathlib import Path

import requests
from PIL import Image, ImageDraw

API = "https://commons.wikimedia.org/w/api.php"
H = {"User-Agent": "TrafikTabelaTakipSistemi/0.1 (https://github.com/Enesisagoktas/TrafikTabelaTakipSistemi; student project) python-requests/2.32"}
CATS = ["Category:Diagrams of warning road signs of Turkey", "Category:Diagrams of prohibitory road signs of Turkey",
        "Category:Diagrams of mandatory road signs of Turkey", "Category:Diagrams of priority road signs of Turkey",
        "Category:Diagrams of information road signs of Turkey", "Category:Diagrams of temporary road signs of Turkey",
        "Category:Diagrams of regulatory road signs of Turkey"]


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


def main(hedef):
    hedef = Path(hedef)
    (hedef / "png").mkdir(parents=True, exist_ok=True)
    w = csv.writer(open(hedef / "liste.csv", "w", newline="", encoding="utf-8"))
    w.writerow(["dosya", "baslik", "kategori", "lisans", "yazar", "sayfa"])
    items = []
    def members(cat, cmtype):
        out, cont = [], {}
        while True:
            r = get({"action": "query", "list": "categorymembers", "cmtitle": cat, "cmtype": cmtype, "cmlimit": 500, **cont})
            out += [m["title"] for m in r.get("query", {}).get("categorymembers", [])]
            if "continue" not in r:
                return out
            cont = r["continue"]

    gorulen = set()
    for cat in CATS:
        titles = []
        for c in [cat] + members(cat, "subcat"):  # çizimler sayı bazlı alt kategorilerde (Road sign TT-29 (Turkey) ...)
            for c2 in [c] + (members(c, "subcat") if c != cat else []):
                if c2 in gorulen:
                    continue
                gorulen.add(c2)
                titles += members(c2, "file")
        titles = sorted(set(titles))
        print(cat, len(titles), "dosya", file=sys.stderr)
        for i in range(0, len(titles), 40):
            r = get({"action": "query", "prop": "imageinfo", "titles": "|".join(titles[i:i + 40]), "iiprop": "url|mime|extmetadata",
                     "iiurlwidth": 256, "iiextmetadatafilter": "Artist|LicenseShortName"})
            for p in r.get("query", {}).get("pages", {}).values():
                ii = (p.get("imageinfo") or [{}])[0]
                if not ii.get("thumburl"):
                    continue
                md = {k: re.sub(r"<[^>]+>", "", v.get("value", "")).strip() for k, v in ii.get("extmetadata", {}).items()}
                name = re.sub(r"[^\w.-]+", "_", p["title"].replace("File:", ""))[:100] + ".png"
                dst = hedef / "png" / name
                if not dst.exists():
                    try:
                        rr = requests.get(ii["thumburl"], headers=H, timeout=90)
                        if rr.status_code == 200:
                            Image.open(io.BytesIO(rr.content)).convert("RGBA").save(dst)
                    except Exception as e:  # noqa: BLE001
                        print("  !", e, file=sys.stderr)
                    time.sleep(1.2)
                if dst.exists():
                    items.append((name, p["title"].replace("File:", ""), cat.split("of ")[1].split(" road")[0]))
                    w.writerow([name, p["title"], cat, md.get("LicenseShortName", ""), md.get("Artist", ""), ii.get("descriptionurl", "")])
            time.sleep(1.2)
    # pafta: 8 sütun, hücre 150 px + başlık
    S, C = 150, 8
    for si in range(0, len(items), C * 8):
        chunk = items[si:si + C * 8]
        sheet = Image.new("RGB", (C * S, -(-len(chunk) // C) * (S + 30)), "white")
        d = ImageDraw.Draw(sheet)
        for i, (name, title, cat) in enumerate(chunk):
            im = Image.open(hedef / "png" / name).convert("RGBA")
            im.thumbnail((S - 10, S - 10))
            bg = Image.new("RGB", im.size, "white")
            bg.paste(im, mask=im.split()[3])
            px, py = (i % C) * S + 5, (i // C) * (S + 30) + 5
            sheet.paste(bg, (px, py))
            d.text((px, py + S - 2), f"{si + i + 1}", fill="red")
            d.text((px, py + S + 10), title[:28], fill="black")
        sheet.save(hedef / f"pafta_svg_{si // (C * 8) + 1}.jpg", quality=88)
    print(len(items), "çizim indirildi; paftalar:", len(list(hedef.glob("pafta_svg_*.jpg"))))


if __name__ == "__main__":
    main(sys.argv[1])
