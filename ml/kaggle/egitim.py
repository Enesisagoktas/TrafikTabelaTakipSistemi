# %% [markdown]
# # Trafik levhası v14 eğitimi (Kaggle)
#
# 46 sınıf: v13'ün 38 sınıfı + speed20, park_yasak, park_yeri, ileri_mecburi, saga_mecburi, sola_mecburi, ileri_saga, ileri_sola.
# Başlangıç ağırlığı v13. Ayrıntı: `docs/kaggle_egitimi.md`.
#
# **Hazırlık (bir kez):**
# 1. Kaggle → Datasets → New Dataset: `trafik_levha_v14_kaggle.zip` dosyasını yükle, **Private** bırak.
# 2. Bu defteri içe aktar (File → Import Notebook → `egitim.ipynb`).
# 3. Sağ panel → Input → Add Input: kendi veri setin + `nezahatkk/traffic-signs-in-turkiye`.
# 4. Settings → Accelerator: **GPU P100** (ya da T4), Internet: **açık** (pip ve Roboflow için; telefon doğrulaması gerekir).
# 5. İsteğe bağlı Roboflow setleri: Add-ons → Secrets → `ROBOFLOW_API_KEY` (anahtar yalnız sende kalır).
# 6. Save Version → **Save & Run All (Commit)**. Arka planda en çok 12 saat çalışır; sonuç Output sekmesinde `cikti.zip`.

# %%
import json
import os
import random
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

TEST = os.environ.get("YEREL_TEST") == "1"  # bilgisayarda küçük deneme: 1 epoch, küçük görsel
EPOCH, BATCH, LR0, IMGSZ = (1, 4, 3e-4, 160) if TEST else (60, 32, 3e-4, 640)
SURE_SAAT = 10.5  # Kaggle oturumu 12 saat; son değerlendirme ve kayıt için pay bırakıldı
ROBOFLOW = [  # (çalışma alanı, proje, sürüm); daha önce kullanılan Türk setleri burada yok
    ("hootbu", "traffic-signs-recognition-v5m56", 2),   # 17 sınıf, 7.479 kare (3x çoğaltılmış sürüm)
    ("hootbu", "traffic-sign-recognition-2-jqrwu", 3),  # 42 sınıf, 1.563 araç kamerası karesi
    ("etu-veri-kumesi", "etu-trafik-levhalari-veri-kumesi", 1),  # TOBB ETÜ, 33 KGM sınıfı
]
KAGGLE = Path("/kaggle/input").exists()
GIRDI = Path("/kaggle/input") if KAGGLE else Path(os.environ["YEREL_GIRDI"])
IS = Path("/kaggle/working") if KAGGLE else Path(os.environ["YEREL_CALISMA"])
IS.mkdir(parents=True, exist_ok=True)
# Bizim paket: tam olarak .../ml/data/levha640/data_v14.yaml. Paketin betikleri ve ağırlığı çalıştırılacağı için başka bir
# girdi setinde aynı yapı varsa durulur (yanlış kodu yüklememek için).
adaylar = [p for p in GIRDI.rglob("data_v14.yaml") if p.parent.name == "levha640" and p.parents[2].name == "ml"]
if len(adaylar) != 1:
    raise SystemExit(f"bizim paket tek olmalı, bulunan: {adaylar}")
PAKET = adaylar[0].parents[2]  # .../ml
print("paket:", PAKET)

# %%
if KAGGLE:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "ultralytics==8.4.191", "imagehash", "roboflow"], check=True)
import imagehash
import numpy as np
import yaml
from PIL import Image, ImageDraw


def bagla(src, dst):
    """Girdi salt okunur; kopyalamak yerine bağlantı. Windows'ta bağlantı izni yoksa kopya (yalnız yerel deneme)."""
    try:
        os.symlink(src, dst, target_is_directory=src.is_dir())
    except OSError:
        (shutil.copytree if src.is_dir() else shutil.copy)(src, dst)


# Çalışma ağacı: ek_veri.py ek/<ad> altına yazar, gerisi girdiye bağlantı
ML = IS / "ml"
L = ML / "data" / "levha640"
(L / "ek").mkdir(parents=True, exist_ok=True)
for p in (PAKET / "data" / "levha640").iterdir():
    if not (L / p.name).exists() and p.name != "ek":
        bagla(p, L / p.name)
for p in sorted((PAKET / "data" / "levha640" / "ek").glob("*")):
    if not (L / "ek" / p.name).exists():
        bagla(p, L / "ek" / p.name)
shutil.copytree(PAKET / "scripts", ML / "scripts", dirs_exist_ok=True)
sys.path.insert(0, str(ML / "scripts"))
from oto_esleme import norm, oto_esleme  # noqa: E402

SINIF = yaml.safe_load((L / "data_v14.yaml").read_text(encoding="utf-8"))["names"]
CIKTI = IS / "cikti"
CIKTI.mkdir(exist_ok=True)
print(len(SINIF), "sınıf")

# %% [markdown]
# ## Yeni veri setleri: bul, sınıflarını eşle, ek_veri.py ile ekle
# Eşleme kuralla yapılır (`scripts/oto_esleme.py`); tanınmayan sınıfı içeren görsel alınmaz. ek_veri.py bizim valid/test'e
# benzeyen görselleri atar (sızıntı olmasın). Her set için sınıf paftası `cikti/pafta_<ad>.jpg`: eşleme gözle denetlenir.

# %%
RESIM = {".jpg", ".jpeg", ".png", ".bmp"}


def ad_listesi(kok):
    for y in sorted(kok.rglob("*.yaml")):
        try:
            d = yaml.safe_load(y.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(d, dict) and "names" in d:
            n = d["names"]
            return n if isinstance(n, list) else [n[k] for k in sorted(n)]
    for c in sorted(kok.rglob("classes.txt")):
        return [s.strip() for s in c.read_text(encoding="utf-8").splitlines() if s.strip()]
    return None


def sarmala(kok, ad):
    """Her düzeni (images/train/..., train/images/...) ek_veri.py'nin istediği düz images/ + labels/ hâline getirir."""
    S = IS / "kaynak" / ad
    shutil.rmtree(S, ignore_errors=True)
    (S / "images").mkdir(parents=True)
    (S / "labels").mkdir()
    n = 0
    for img in sorted(p for p in kok.rglob("*") if p.suffix.lower() in RESIM):
        s = img.as_posix()
        i = s.rfind("/images/")
        lbl = Path(s[:i] + "/labels/" + s[i + 8:]).with_suffix(".txt") if i >= 0 else None
        if lbl is None or not lbl.exists():
            continue
        yeni = f"{n:06d}_{img.stem}"
        bagla(img, S / "images" / f"{yeni}{img.suffix.lower()}")
        shutil.copy(lbl, S / "labels" / f"{yeni}.txt")
        n += 1
    return S, n


def pafta(ad, adet=8, k=72):
    """Eklenen her sınıftan rastgele kırpıntılar: eşleme doğru mu, gözle bakılır."""
    kutular = {}
    for t in sorted((L / "ek" / ad / "labels").glob("*.txt")):
        for r in t.read_text().split("\n"):
            if r.strip():
                c, x, y, w, h = r.split()
                kutular.setdefault(int(c), []).append((t.stem, float(x), float(y), float(w), float(h)))
    if not kutular:
        return
    random.seed(0)
    sh = Image.new("RGB", (150 + adet * k, len(kutular) * k), "white")
    d = ImageDraw.Draw(sh)
    for row, c in enumerate(sorted(kutular)):
        d.text((4, row * k + k // 2 - 6), f"{SINIF[c]} ({len(kutular[c])})", fill="black")
        for j, (stem, x, y, w, h) in enumerate(random.sample(kutular[c], min(adet, len(kutular[c])))):
            im = Image.open(L / "ek" / ad / "images" / f"{stem}.jpg")
            W, H = im.size
            kr = im.crop((int((x - w / 2) * W), int((y - h / 2) * H), int((x + w / 2) * W), int((y + h / 2) * H)))
            sh.paste(kr.convert("RGB").resize((k - 2, k - 2)), (150 + j * k, row * k))
    sh.save(CIKTI / f"pafta_{ad}.jpg", quality=85)


KAYNAKLAR = [(norm(k.name)[:40], k) for k in sorted(GIRDI.iterdir()) if k.is_dir() and not PAKET.is_relative_to(k)]
try:
    from kaggle_secrets import UserSecretsClient
    RF_KEY = UserSecretsClient().get_secret("ROBOFLOW_API_KEY")
except Exception:
    RF_KEY = os.environ.get("ROBOFLOW_API_KEY")
if RF_KEY:
    from roboflow import Roboflow
    rf = Roboflow(api_key=RF_KEY)
    for ws, proj, ver in ROBOFLOW:
        try:
            ds = rf.workspace(ws).project(proj).version(ver).download("yolov11", location=str(IS / "rf" / proj))
            KAYNAKLAR.append((norm(proj)[:40], Path(ds.location)))
        except Exception as e:  # hata metni adres içerebilir: anahtar maskelenir
            msj = re.sub(r"api_key=[^&\s'\"]+", "api_key=***", str(e).replace(RF_KEY, "***"))
            print("Roboflow indirilemedi:", proj, type(e).__name__, msj[:200])
else:
    print("ROBOFLOW_API_KEY yok: Roboflow setleri atlandı")

RAPOR = {}
for ad, kok in KAYNAKLAR:
    adlar = ad_listesi(kok)
    if not adlar:
        print(f"== {ad}: sınıf listesi bulunamadı, atlandı")
        continue
    esleme, at, atla = oto_esleme(adlar, SINIF)
    S, n = sarmala(kok, ad)
    (S / "data.yaml").write_text(yaml.safe_dump({"names": adlar}, allow_unicode=True), encoding="utf-8")
    ej = IS / f"esleme_{ad}.json"
    ej.write_text(json.dumps(esleme, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"== {ad}: {n} etiketli görsel, {len(adlar)} sınıf")
    for a in adlar:
        print(f"   {a!r:45} -> {esleme.get(a, 'kutu atılır' if a in at else 'görsel alınmaz')}")
    komut = [sys.executable, str(ML / "scripts" / "ek_veri.py"), str(S), ad, str(ej), "--siniflar", "data_v14.yaml"]
    if at:
        komut += ["--at", ",".join(at)]
    if atla:
        komut += ["--atla", ",".join(atla)]
    r = subprocess.run(komut, capture_output=True, text=True, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    print(r.stdout[-2000:], r.stderr[-2000:])
    RAPOR[ad] = {"gorsel": n, "esleme": esleme, "kutu_atilan": at, "gorsel_alinmayan": atla, "ek_veri": r.stdout.strip()[-1500:]}
    if r.returncode == 0:
        pafta(ad)
(CIKTI / "esleme_raporu.json").write_text(json.dumps(RAPOR, ensure_ascii=False, indent=1), encoding="utf-8")

# %% [markdown]
# ## Eğitim listesi
# Bizim train_v14 (v13 verisi; DFG ve Erzurum seti v14 sınıflarıyla yeniden etiketli, TTSD eklendi) + yeni setler.
# Yeni setlerden bizim train'deki bir görsele çok benzeyen (phash <= 4) görsel atılır: aynı kare iki kez sayılmasın.

# %%
def ph(p):
    with Image.open(p) as im:
        im.draft("L", (256, 256))
        return int(str(imagehash.phash(im)), 16)


bizim = [L / s.strip()[2:] for s in (L / "train_v14.txt").read_text(encoding="utf-8").splitlines() if s.strip()]
hb = np.array([ph(p) for p in bizim], dtype=np.uint64)
yeni, kopya = [], 0
for ad in RAPOR:
    for p in sorted((L / "ek" / ad / "images").glob("*.jpg")):
        x = np.bitwise_xor(hb, np.uint64(ph(p)))
        if np.unpackbits(x.view(np.uint8).reshape(-1, 8), axis=1).sum(axis=1).min() <= 4:
            kopya += 1
            continue
        yeni.append(p)
        hb = np.append(hb, np.uint64(ph(p)))  # yeni setler birbirinin kopyasını da getirmesin
print(f"bizim train {len(bizim)}, yeni {len(yeni)}, bizimkine kopya olduğu için atılan {kopya}")


def liste(ad, yollar):
    (IS / ad).write_text("\n".join(p.as_posix() for p in yollar) + "\n", encoding="utf-8")
    return str(IS / ad)


def okunan(dosya):
    return [L / s.strip()[2:] for s in (L / dosya).read_text(encoding="utf-8").splitlines() if s.strip()]


cfg = {"path": L.as_posix(), "train": liste("train_kaggle.txt", bizim + yeni), "val": liste("val_kaggle.txt", okunan("val_v14.txt")),
       "test": liste("test_kaggle.txt", okunan("test_temiz.txt")), "nc": len(SINIF), "names": SINIF}
(IS / "data_kaggle.yaml").write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False), encoding="utf-8")
say = {}
for p in bizim + yeni:
    t = Path(str(p).replace(f"{os.sep}images{os.sep}", f"{os.sep}labels{os.sep}").replace("/images/", "/labels/")).with_suffix(".txt")
    for r in (t.read_text().split("\n") if t.exists() else []):
        if r.strip():
            say[SINIF[int(r.split()[0])]] = say.get(SINIF[int(r.split()[0])], 0) + 1
print("sınıf başına kutu:", json.dumps({c: say.get(c, 0) for c in SINIF}, ensure_ascii=False))
(CIKTI / "sinif_sayim.json").write_text(json.dumps({c: say.get(c, 0) for c in SINIF}, ensure_ascii=False, indent=0), encoding="utf-8")

# %% [markdown]
# ## Eğitim (v13'ten 46 sınıfa, v9 tarifi)

# %%
from ultralytics import YOLO  # noqa: E402

model = YOLO(str(PAKET / "agirlik" / "v13.pt"))
t0 = time.time()


def sure_siniri(tr):
    if time.time() - t0 > SURE_SAAT * 3600:
        tr.stop = True
        print(f"{SURE_SAAT} saat doldu: eğitim bu epoch'ta bitiriliyor")


model.add_callback("on_fit_epoch_end", sure_siniri)
model.train(data=str(IS / "data_kaggle.yaml"), imgsz=IMGSZ, epochs=EPOCH, batch=BATCH, workers=0 if TEST else 4,
            optimizer="AdamW", lr0=LR0, lrf=0.05, warmup_epochs=1, warmup_bias_lr=0, patience=EPOCH, close_mosaic=10,
            fliplr=0, mixup=0, cache=False, project=str(IS / "runs"), name="v14", exist_ok=True, plots=True,
            device="cpu" if TEST else 0)

# %% [markdown]
# ## Değerlendirme ve çıktı (`cikti.zip`: v14.pt, sonuçlar, paftalar, eşleme raporu)

# %%
best = IS / "runs" / "v14" / "weights" / "best.pt"
m = YOLO(str(best))
sonuc = {}
for split in ("val", "test"):
    r = m.val(data=str(IS / "data_kaggle.yaml"), split=split, imgsz=IMGSZ, batch=BATCH, project=str(IS / "runs"),
              name=f"deger_{split}", exist_ok=True, device="cpu" if TEST else 0)
    sonuc[split] = {"mAP50": round(float(r.box.map50), 4), "mAP50-95": round(float(r.box.map), 4),
                    "sinif_AP50": {SINIF[int(c)]: round(float(a), 3) for c, a in zip(r.box.ap_class_index, r.box.ap50)}}
    print(split, sonuc[split]["mAP50"], sonuc[split]["mAP50-95"])
(CIKTI / "sonuc.json").write_text(json.dumps(sonuc, ensure_ascii=False, indent=1), encoding="utf-8")
shutil.copy(best, CIKTI / "v14.pt")
for f in ("results.csv", "results.png", "confusion_matrix_normalized.png", "args.yaml"):
    if (IS / "runs" / "v14" / f).exists():
        shutil.copy(IS / "runs" / "v14" / f, CIKTI / f)
shutil.make_archive(str(IS / "cikti"), "zip", CIKTI)
print("hazır:", IS / "cikti.zip", f"({(IS / 'cikti.zip').stat().st_size / 1e6:.1f} MB)")
