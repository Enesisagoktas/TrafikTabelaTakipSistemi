"""Resmî Türk levha çizimlerinden (Commons SVG -> PNG) sentetik eğitim görselleri: levhasız Türk yol karelerine rastgele
ölçek / perspektif / bulanıklık / renk ile yapıştırır, YOLO etiketi yazar (kopyala-yapıştır artırma; az örnekli yeni sınıflar için).
python sentetik.py <esleme.json> <png_klasoru> <arka_plan_klasorleri(virgül)> <cikti> <adet> [tohum] [sinif_sayim.json]
esleme.json: {"dosya.png": "sinif"}  ->  cikti/{images,labels,data.yaml} (ek_veri.py ile eğitime eklenir)"""
import json
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

NAMES = ["caution", "crossroads", "dangerousleft", "dangerousright", "donotturnleft", "donotturnright", "giveway", "keepleft", "keepright",
         "noentry", "nostopping", "nouturn", "pedestrian_info", "pedestrian_risk", "priorityroad", "schoolpassing", "speed30", "speed50",
         "speed70", "stop", "kasis", "durak", "demiryolu", "ada_etrafinda", "isikli_isaret", "keskin_viraj", "devamli_viraj", "sollama_yasak",
         "dusen_kaya", "hayvan", "daralan_yol", "dik_egim", "speed40", "speed60", "hiz_sonu", "yol_calismasi", "kaygan_yol", "diger_levha"]
YENI = set(NAMES[20:37])  # 17 yeni sesli sınıf: ağırlık 3; temel 20: 1; diger_levha: 1


def levha_hazirla(png, h_hedef):
    im = Image.open(png).convert("RGBA")
    im = im.crop(im.getchannel("A").getbbox())
    im = im.resize((max(8, round(im.width * h_hedef / im.height)), h_hedef), Image.LANCZOS)
    w, h = im.size
    j = 0.12  # perspektif: köşeleri rastgele oynat (QUAD: sol-üst, sol-alt, sağ-alt, sağ-üst kaynak köşeleri)
    q = [random.uniform(-j, j) * w, random.uniform(-j, j) * h, random.uniform(-j, j) * w, h + random.uniform(-j, j) * h,
         w + random.uniform(-j, j) * w, h + random.uniform(-j, j) * h, w + random.uniform(-j, j) * w, random.uniform(-j, j) * h]
    im = im.transform((w, h), Image.QUAD, q, Image.BICUBIC)
    im = im.rotate(random.uniform(-7, 7), Image.BICUBIC, expand=True)
    rgb = im.convert("RGB")
    rgb = ImageEnhance.Brightness(rgb).enhance(random.uniform(0.55, 1.1))
    rgb = ImageEnhance.Contrast(rgb).enhance(random.uniform(0.7, 1.1))
    rgb = ImageEnhance.Color(rgb).enhance(random.uniform(0.6, 1.0))
    im = Image.merge("RGBA", (*rgb.split(), im.getchannel("A")))
    if random.random() < 0.15:  # geçici (yol çalışması) levha: sarı kare zemin
        kenar = round(max(im.size) * 0.12); sari = Image.new("RGBA", (im.width + 2 * kenar, im.height + 2 * kenar), (247, 208, 40, 255))
        sari.paste(im, (kenar, kenar), im); im = sari
    im = im.filter(ImageFilter.GaussianBlur(random.uniform(0.2, 0.3 + 0.012 * h)))
    bb = im.getchannel("A").getbbox()
    return im.crop(bb) if bb else im


def main(esleme, png_dir, bg_dirs, out, adet, tohum=0, sayim_json=None):
    random.seed(tohum); np.random.seed(tohum)
    es = json.load(open(esleme, encoding="utf-8"))
    sinif_png = {}
    for f, c in es.items():
        if c in NAMES and (Path(png_dir) / f).exists():
            sinif_png.setdefault(c, []).append(Path(png_dir) / f)
    siniflar = sorted(sinif_png)
    sayim = json.load(open(sayim_json, encoding="utf-8")) if sayim_json else {}
    agirlik = [600 if c == "diger_levha" else (max(30, 300 - sayim.get(c, 0)) if sayim else (3 if c in YENI else 1)) for c in siniflar]
    print("ağırlık:", dict(zip(siniflar, agirlik)))
    bgs = [p for d in bg_dirs.split(",") for p in Path(d).glob("*.jpg")]
    out = Path(out); (out / "images").mkdir(parents=True, exist_ok=True); (out / "labels").mkdir(exist_ok=True)
    print(len(bgs), "arka plan;", {c: len(v) for c, v in sinif_png.items()})
    sayac = {}
    sayac_bg = {}
    for i in range(adet):
        bg_p = random.choice(bgs)
        bg = Image.open(bg_p).convert("RGB")
        if bg.width > 1280:
            bg = bg.resize((1280, round(bg.height * 1280 / bg.width)), Image.LANCZOS)
        if bg.width < 400 or bg.height < 300:
            continue
        W, H = bg.size
        kutular = []  # (x, y, w, h, sınıf)
        et = bg_p.parent.parent / "labels" / (bg_p.stem + ".txt")  # etiketli arka plan: kendi kutuları korunur
        if et.exists():
            for sat in et.read_text().splitlines():
                if sat.strip():
                    ci, cx, cy, bw, bh = sat.split()[:5]
                    kutular.append((round((float(cx) - float(bw) / 2) * W), round((float(cy) - float(bh) / 2) * H), round(float(bw) * W), round(float(bh) * H), NAMES[int(ci)]))
        n_eski = len(kutular)
        for _ in range(random.choices([1, 2, 3], [0.5, 0.35, 0.15])[0]):
            c = random.choices(siniflar, agirlik)[0]
            lv = levha_hazirla(random.choice(sinif_png[c]), round(H * random.uniform(0.04, 0.16)))
            w, h = lv.size
            if w >= W or h >= H:
                continue
            for _d in range(10):
                lo, hi = 0, W - w
                if random.random() < 0.7:  # yol kenarı: sol ya da sağ üçte bir (sığmazsa her yer)
                    lo, hi = (0, round(0.3 * W) - w) if random.random() < 0.5 else (round(0.68 * W), W - w)
                    if hi < lo:
                        lo, hi = 0, W - w
                x = random.randint(lo, hi)
                y = random.randint(round(0.08 * H), max(round(0.08 * H), round(0.6 * H) - h))
                if all(x + w < bx or bx + bw < x or y + h < by or by + bh < y for bx, by, bw, bh, _c in kutular):
                    # direk: levhanın altından aşağı ince gri çubuk (gerçek levhalar havada durmaz)
                    dw = max(2, round(h * 0.07)); dh = round(h * random.uniform(1.0, 2.6)); g = random.randint(70, 150)
                    bg.paste((g, g, g), (x + w // 2 - dw // 2, y + h - 2, x + w // 2 - dw // 2 + dw, min(H, y + h + dh)))
                    # hafif gölge + arka plan rengine çekme (ışık uyumu)
                    bolge = np.asarray(bg.crop((x, y, x + w, y + h))).reshape(-1, 3).mean(0)
                    ton = Image.new("RGBA", lv.size, tuple(int(v) for v in bolge) + (0,))
                    ton.putalpha(lv.getchannel("A").point(lambda a: int(a * random.uniform(0.0, 0.18))))
                    bg.paste(lv, (x, y), lv)
                    bg.paste(ton, (x, y), ton)
                    kutular.append((x, y, w, h, c)); sayac[c] = sayac.get(c, 0) + 1
                    break
        if len(kutular) == n_eski:
            continue
        arr = np.asarray(bg).astype(np.float32) + np.random.normal(0, random.uniform(0, 4), (H, W, 3))
        bg = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
        sayac_bg[bg_p.parent.parent.name] = sayac_bg.get(bg_p.parent.parent.name, 0) + 1
        ad = f"sentetik_{tohum}_{i:05d}"
        if max(bg.size) > 640:
            bg = bg.resize((round(bg.width * 640 / max(bg.size)), round(bg.height * 640 / max(bg.size))), Image.LANCZOS)
        bg.save(out / "images" / f"{ad}.jpg", quality=random.randint(60, 92))
        with open(out / "labels" / f"{ad}.txt", "w") as f:
            for x, y, w, h, c in kutular:
                f.write(f"{NAMES.index(c)} {(x + w / 2) / W:.6f} {(y + h / 2) / H:.6f} {w / W:.6f} {h / H:.6f}\n")
    (out / "data.yaml").write_text("names:\n" + "".join(f"- {n}\n" for n in NAMES) + f"nc: {len(NAMES)}\n", encoding="utf-8")
    print(len(list((out / "images").glob("*.jpg"))), "görsel; arka plan:", sayac_bg, "; yapıştırılan kutu/sınıf:", dict(sorted(sayac.items(), key=lambda kv: -kv[1])))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5]), int(sys.argv[6]) if len(sys.argv) > 6 else 0, sys.argv[7] if len(sys.argv) > 7 else None)
