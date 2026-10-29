"""Eşik taraması: video loglarını (desktop/app.py --sessiz; her kare yazılı) farklı kural ayarlarıyla yeniden oynatır
ve gerçek durumla karşılaştırır. Model yeniden çalışmaz; yalnızca kurallar değişir (güven eşiği, en küçük kutu, oylama).
Kurallar telefondakinin aynısı (desktop/app.py Rules).

Çalıştırma (ml/ klasöründe):  .venv\\Scripts\\python scripts\\esik_tarama.py <log_etiketi> [kare_adımı=1]
kare_adımı 3: 30 FPS videonun her 3. karesi, yani telefonun ~10 FPS'i (oylama penceresi zamanda daha uzun sürer).
Dikkat: bu 10 video aynı zamanda test; eşik buna göre seçilirse sonuç iyimser olur. Kaba adımlarla seç.
"""

import csv
import itertools
import sys
from collections import defaultdict
from pathlib import Path

from video_degerlendir import VID, events, load_gt, match

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "desktop"))
from app import CLASS_MIN_CONF, Rules  # noqa: E402


def frames(log):
    out = defaultdict(list)
    with open(log, encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter=";"):
            if r["olay"] == "tespit":
                out[float(r["zaman_sn"])].append((r["sinif"], float(r["guven"]), float(r["yukseklik"])))
            elif r["olay"] == "kare":
                out[float(r["zaman_sn"])] = []
    return sorted(out.items())


def replay(fr, **kw):
    rules = Rules(**kw)
    return [(t, a) for t, d in fr if (a := rules.step(d, t)[1])]


if __name__ == "__main__":
    tag, step = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 1
    gt = load_gt()
    vids = {v: (events(gt[v]), frames(VID / f"{v}.{tag}.log.csv")[::step]) for v in sorted(gt) if (VID / f"{v}.{tag}.log.csv").exists()}
    print(f"{len(vids)} video, {sum(len(e) for e, _ in vids.values())} gerçek levha olayı, model: {tag}, kare adımı {step}")
    print("güven  sınıf_tabanı  en_küçük_kutu  oylama | yakalanan zamanında kaçan yanlış_alarm")
    rows = []
    for conf, floors, h, (win, hits) in itertools.product((0.4, 0.5, 0.6, 0.7), (True, False), (0.02, 0.025, 0.035, 0.05), ((5, 3), (5, 4), (7, 5))):
        cmc = {k: max(v, conf) for k, v in CLASS_MIN_CONF.items()} if floors else {}
        caught = timely = fa = 0
        for evs, fr in vids.values():
            res, extra = match(evs, replay(fr, window=win, min_hits=hits, min_conf=conf, min_height=h, class_min_conf=cmc))
            caught += sum(t is not None for _, t in res)
            timely += sum(t is not None and t <= e["end"] + 0.5 for e, t in res)
            fa += len(extra)
        rows.append((conf, floors, h, f"{hits}/{win}", caught, timely, sum(len(e) for e, _ in vids.values()) - caught, fa))
    for r in sorted(rows, key=lambda r: (r[7], -r[4])):
        print(f"{r[0]:.2f}   {'evet' if r[1] else 'hayır':5s}        {r[2]:.3f}          {r[3]:4s}  | {r[4]:4d} {r[5]:4d} {r[6]:4d} {r[7]:4d}")
