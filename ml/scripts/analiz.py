"""Video loglarını uygulamanın kurallarıyla yeniden oynatıp uyarıları açıklar (ml/data/videolar/<video>.<etiket>.log.csv).

Loglar `desktop/app.py <video> <model> --sessiz` ile üretilir; etiket = model dosyasının adı (ör. levha, v5b, v6).
Çalıştırma (ml/ klasöründe):
  python scripts/analiz.py uyarilar ankara_corum_iskilip [--etiket v5b] [--sure 120] [--yanlis]
      Her uyarı: doğru mu, inceleyiciler o saniyelerde ne gördü, levha ilk ne zaman güvenle (>= 0,7) görüldü,
      boy sınırını (%5) ne zaman geçti. --yanlis: yalnızca yanlış uyarılar.
  python scripts/analiz.py kurallar [--etiket v5b]
      Boy/güven seçenekleri 10 videoda: yakalanan (zamanında) / yanlış uyarı, levha net görününce kaç sn sonra uyardı.
29 Ekim (v5b): Ankara'daki 13 yanlış uyarının 12'si 20 sınıfın dışındaki levhalardan; boy sınırını %3'e indirmek
yanlış uyarıyı 30 FPS'te 18 -> 36 yapıyor (docs/YOL_HARITASI.md, canlı demo).
"""

import argparse
import csv
import statistics as st
import sys
from pathlib import Path

from video_degerlendir import VID, credit_new, events, load_gt, match

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "desktop"))
from app import CLASS_MIN_CONF, Rules  # noqa: E402

TABAN8 = {"speed30", "crossroads", "dangerousleft", "dangerousright", "pedestrian_info", "pedestrian_risk", "schoolpassing", "caution"}
TABAN5 = {"speed30", "crossroads", "dangerousright", "pedestrian_risk", "schoolpassing"}


def frames(log):
    out = []  # [(zaman, [(sınıf, güven, boy)])]
    with open(log, encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter=";"):
            if r["olay"] not in ("tespit", "kare"):
                continue
            t = float(r["zaman_sn"])
            if not out or out[-1][0] != t:
                out.append((t, []))
            if r["olay"] == "tespit":  # sari sütunu 30 Ekim'de eklendi; eski loglarda 0
                out[-1][1].append((r["sinif"], float(r["guven"]), float(r["yukseklik"]), float(r.get("sari") or 0)))
    return out


def replay(fr, keep=None, sari=1.1, **kw):
    """sari: kutudaki sarı oranı bu eşiği geçen tespit yok sayılır (app.py SARI_ESIK); 1.1 = kural kapalı."""
    rules, out = Rules(class_min_conf=CLASS_MIN_CONF, **kw), []
    for t, d in fr:
        _, n = rules.step([x[:3] for x in d if x[3] < sari and (keep is None or keep(*x[:3]))], t)
        if n:
            out.append((t, n))
    return out


def track(fr, t, c):
    """Uyarıdan geriye: aynı sınıfın 1 sn'den uzun ara vermeden görüldüğü kareler -> [(zaman, en yüksek güven, en büyük boy)]"""
    seen = [(ft, max(x[1] for x in d if x[0] == c), max(x[2] for x in d if x[0] == c)) for ft, d in fr if ft <= t and any(x[0] == c for x in d)]
    out = []
    for x in reversed(seen):
        if out and out[-1][0] - x[0] > 1.0:
            break
        out.append(x)
    return out[::-1]


def uyarilar(video, tag, until, only_false):
    gt, fr = load_gt()[video], frames(VID / f"{video}.{tag}.log.csv")
    als = replay(fr, min_conf=0.7, min_height=0.05)
    res, _ = match(events(gt), als)
    ev_of = {t: e for e, t in res if t is not None}
    for t, c in als:
        if t > until:
            break
        e, tr = ev_of.get(t), track(fr, t, c)
        if e and only_false:
            continue
        f07 = next(((ft, h) for ft, p, h in tr if p >= 0.7), None)
        f5 = next((ft for ft, p, h in tr if p >= 0.7 and h >= 0.05), None)
        sari = max((s for ft, d in fr if abs(ft - t) < 0.5 for n, _, _, s in d if n == c), default=0)
        print(f"\n{t:6.1f} sn {c:15s} sarı {sari:.2f}  " + (f"DOĞRU (inceleyiciler {e['start']}-{e['end']}. sn net gördü)" if e else "YANLIŞ"))
        print(f"         ilk tespit {tr[0][0]:.1f} sn (güven {tr[0][1]:.2f}, boy %{tr[0][2] * 100:.1f}); güven >= 0,7: "
              f"{f07[0]:.1f} sn (boy %{f07[1] * 100:.1f}); boy %5'i geçti: {f5:.1f} sn; uyarı {t:.1f} sn")
        for x in sorted({f"{n}: {note[:80]}" if n == "other" else n for s in range(int(t) - 2, int(t) + 3) for n, _, note in gt.get(s, {}).get("notes", [])}):
            print("         inceleyici notu (±2 sn):", x)


def kurallar(tag):
    variants = {
        "şimdiki: güven 0,7 ve boy >= %5": (None, dict(min_conf=0.7, min_height=0.05)),
        "güven 0,7 ve boy >= %3": (None, dict(min_conf=0.7, min_height=0.03)),
        "güven 0,7 ve boy >= %2,5": (None, dict(min_conf=0.7, min_height=0.025)),
        "kademeli: %5'te 0,7; %3'te 0,85": (lambda n, p, h: (h >= 0.05 and p >= 0.7) or (h >= 0.03 and p >= 0.85), dict(min_conf=0, min_height=0)),
        "kademeli: %5'te 0,7; %3'te 0,9": (lambda n, p, h: (h >= 0.05 and p >= 0.7) or (h >= 0.03 and p >= 0.9), dict(min_conf=0, min_height=0)),
        "kademeli: %5'te 0,7; %2,5'te 0,9": (lambda n, p, h: (h >= 0.05 and p >= 0.7) or (h >= 0.025 and p >= 0.9), dict(min_conf=0, min_height=0)),
        "şimdiki + sarı zemin >= 0,2 yok say": (None, dict(min_conf=0.7, min_height=0.05, sari=0.2)),
        "şimdiki + sarı zemin >= 0,3 yok say": (None, dict(min_conf=0.7, min_height=0.05, sari=0.3)),
        "şimdiki + sarı zemin >= 0,4 yok say": (None, dict(min_conf=0.7, min_height=0.05, sari=0.4)),
        # 30 Ekim gece: yanlış uyarı üreten sınıflara 0,8 güven tabanı (TABAN8: ajan taramasının 8 sınıfı; TABAN5: taramada
        # gerçekten yanlış uyarı silen 5'i; caution/dangerousleft/pedestrian_info tabanı hiçbir yanlış uyarıyı silmedi).
        "şimdiki + 8 sınıfta güven >= 0,8": (lambda n, p, h: h >= 0.05 and p >= (0.8 if n in TABAN8 else 0.7), dict(min_conf=0, min_height=0)),
        "şimdiki + 5 sınıfta güven >= 0,8": (lambda n, p, h: h >= 0.05 and p >= (0.8 if n in TABAN5 else 0.7), dict(min_conf=0, min_height=0)),
    }
    gt = load_gt()
    logs = {v: frames(VID / f"{v}.{tag}.log.csv") for v in gt}
    for step, label in ((1, "30 FPS (her kare)"), (3, "~10 FPS (her 3. kare)")):
        print(f"\n### {label}")
        for name, (keep, kw) in variants.items():
            caught = timely = false = newok = 0
            delay = []
            for v, fr in logs.items():
                res, extra = match(events(gt[v]), replay(fr[::step], keep, **kw))
                for e, t in res:
                    if t is not None:
                        caught, timely = caught + 1, timely + (t <= e["end"] + 0.5)
                        delay.append(t - e["start"])
                ok_new, extra = credit_new(gt[v], extra)
                newok += len(ok_new)
                false += len(extra)
            print(f"{name:36s} yakalanan {caught:2d} (zamanında {timely:2d}) / yanlış uyarı {false:2d}; "
                  f"levha net görününce medyan {st.median(delay):+.1f} sn sonra uyardı; yeni sınıf doğru {newok}")
            if step == 1 and name.startswith("şimdiki:"):  # zincir betikleri için ASCII satır (PS 5.1 Türkçe regex'i okuyamıyor)
                print(f"GATE30 caught={caught} timely={timely} false={false} newok={newok}")
            if step == 1 and "5 sınıfta" in name:
                print(f"GATE30T5 caught={caught} timely={timely} false={false} newok={newok}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("kip", choices=["uyarilar", "kurallar"])
    ap.add_argument("video", nargs="?", default="ankara_corum_iskilip")
    ap.add_argument("--etiket", default="v5b")
    ap.add_argument("--sure", type=float, default=1e9)
    ap.add_argument("--yanlis", action="store_true")
    a = ap.parse_args()
    if a.kip == "uyarilar":
        uyarilar(a.video, a.etiket, a.sure, a.yanlis)
    else:
        kurallar(a.etiket)
