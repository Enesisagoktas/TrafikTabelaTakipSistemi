"""Açık lisanslı Türk sürüş videolarını indirir (Commons: lisans API'den doğrulanır; Pexels: Pexels lisansı), atıf yazar,
ffmpeg ile kare çıkarır. Çalıştırma: python -X utf8 video_indir.py <hedef_klasor>"""
import csv
import re
import subprocess
import sys
import time
from pathlib import Path

import requests

API = "https://commons.wikimedia.org/w/api.php"
H = {"User-Agent": "TrafikTabelaTakipSistemi/0.1 (https://github.com/Enesisagoktas/TrafikTabelaTakipSistemi; student project) python-requests/2.32"}
LISANS_OK = re.compile(r"^(CC0|CC BY(-SA)?( \d\.\d)?|Public domain|PD)", re.I)
COMMONS = {  # kısa ad -> dosya başlığı (arama sorgusu ile bulunur)
    "corum_merkez": "ÇORUM ŞEHİR MERKEZİ.webm",
    "canakkale_1915": "Çanakkale 1915 Bridge.webm",
}
COMMONS_ARA = {"e80_pegasus": "Pegasus uçak kazası E80"}  # başlığı tam bilinmeyen: list=search
PEXELS = {"ist_buyukdere": 11914938, "ist_otoyol": 31660095, "ist_bogaz_koprusu": 38740040, "bayrak_otoyol": 39278559}
FPS = {"corum_merkez": 1, "canakkale_1915": 1}  # ötekiler 2 kare/sn (kısa klipler)


def get(params):
    for d in range(8):
        try:
            r = requests.get(API, params={"format": "json", **params}, headers=H, timeout=90)
        except Exception as e:  # noqa: BLE001
            print("  ! bağlantı:", str(e)[:80], file=sys.stderr)
            time.sleep(10 * (d + 1))
            continue
        if r.status_code == 200 and r.text.startswith("{"):
            time.sleep(5.0)
            return r.json()
        wait = int(r.headers.get("Retry-After") or 0) or 20 * (d + 1)
        print("  !", r.status_code, "->", wait, "sn", file=sys.stderr)
        time.sleep(wait)
    return {}


def indir(url, dst, headers=None):
    tmp = dst.with_suffix(dst.suffix + ".part")
    for d in range(80):  # baglanti ~30 MB'da kopuyor: Range ile kaldigi yerden surdur
        have = tmp.stat().st_size if tmp.exists() else 0
        h = {**(headers or H), **({"Range": f"bytes={have}-"} if have else {})}
        try:
            with requests.get(url, headers=h, timeout=180, stream=True, allow_redirects=True) as r:
                if r.status_code == 416:
                    tmp.rename(dst)
                    return True
                if r.status_code not in (200, 206) or not r.headers.get("Content-Type", "").startswith(("video", "application/octet")):
                    wait = int(r.headers.get("Retry-After") or 0) or 60 * (d + 1)
                    print("  !", r.status_code, r.headers.get("Content-Type"), url[:90], "->", wait, "sn", file=sys.stderr)
                    time.sleep(wait)
                    continue
                total = (have if r.status_code == 206 else 0) + int(r.headers.get("Content-Length") or 0)
                with open(tmp, "ab" if r.status_code == 206 else "wb") as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk)
                if total and tmp.stat().st_size < total:
                    continue
                tmp.rename(dst)
                return True
        except Exception as e:  # noqa: BLE001
            print("  !", str(e)[:100], f"({tmp.stat().st_size if tmp.exists() else 0} B)", file=sys.stderr)
            time.sleep(15)
    return False


def kareler(video, out, fps):
    out.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(video), "-vf", f"fps={fps}", "-q:v", "2",
                    str(out / f"{video.stem}_%05d.jpg")], check=False)
    return len(list(out.glob(f"{video.stem}_*.jpg")))


def main(hedef, only=()):
    hedef = Path(hedef)
    (hedef / "video").mkdir(parents=True, exist_ok=True)
    w = csv.writer(open(hedef / "atif.csv", "a", newline="", encoding="utf-8"))
    titles = dict(COMMONS)
    for ad, q in COMMONS_ARA.items():
        if only and ad not in only:
            continue
        r = get({"action": "query", "list": "search", "srsearch": q, "srnamespace": 6, "srlimit": 5})
        hits = [h["title"] for h in r.get("query", {}).get("search", []) if h["title"].lower().endswith((".webm", ".ogv", ".mp4"))]
        print(ad, "arama:", hits)
        if hits:
            titles[ad] = hits[0].replace("File:", "")
    for ad, t in titles.items():
        if only and ad not in only:
            continue
        r = get({"action": "query", "prop": "imageinfo", "titles": "File:" + t, "iiprop": "url|size|mime|extmetadata",
                 "iiextmetadatafilter": "Artist|LicenseShortName|LicenseUrl"})
        pages = list(r.get("query", {}).get("pages", {}).values())
        ii = (pages[0].get("imageinfo") or [{}])[0] if pages else {}
        if not ii:
            print(ad, "bulunamadı", file=sys.stderr)
            continue
        md = {k: re.sub(r"<[^>]+>", "", v.get("value", "")).strip() for k, v in ii.get("extmetadata", {}).items()}
        lic = md.get("LicenseShortName", "")
        print(ad, t, ii.get("mime"), round(ii.get("size", 0) / 1e6), "MB", lic, "|", md.get("Artist", "")[:60])
        if not LISANS_OK.match(lic):
            print("  lisans uygun değil, atlandı", file=sys.stderr)
            continue
        dst = hedef / "video" / (ad + Path(t).suffix.lower())
        if not dst.exists() and not indir(ii["url"], dst):
            continue
        n = kareler(dst, hedef / "kareler", FPS.get(ad, 2))
        w.writerow([ad, dst.name, ii.get("descriptionurl", ""), md.get("Artist", ""), lic, md.get("LicenseUrl", ""), n])
        print("  kare:", n)
    for ad, pid in PEXELS.items():
        if only and ad not in only:
            continue
        dst = hedef / "video" / f"{ad}.mp4"
        if not dst.exists() and not indir(f"https://www.pexels.com/download/video/{pid}/", dst,
                                          headers=H):
            continue
        n = kareler(dst, hedef / "kareler", FPS.get(ad, 2))
        w.writerow([ad, dst.name, f"https://www.pexels.com/video/{pid}/", "Pexels", "Pexels License", "https://www.pexels.com/license/", n])
        print(ad, "kare:", n)
    print("toplam kare:", len(list((hedef / "kareler").glob("*.jpg"))))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2].split(",") if len(sys.argv) > 2 else ())
