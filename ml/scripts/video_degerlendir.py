"""Uygulama loglarını (desktop/app.py --sessiz) videoların gerçek durumuyla karşılaştırır.

Gerçek durum: ml/degerlendirme/video_gercek_durum.json. Saniyede 1 karede iki bağımsız inceleyicinin (A, B) listesi.
Kabul kuralı: bir sınıf o saniyede ikisi tarafından da "net" (clear) görüldüyse vardır. Aynı sınıfın 2 sn'den kısa
aralıklı saniyeleri tek "olay" (aynı levhaya yaklaşma) sayılır.
- Yakalandı: olay sırasında [başlangıç-1, bitiş+2] aralığında aynı sınıf için uyarı var.
- Zamanında: uyarı, levhanın net görüldüğü son saniyeden (+0,5) önce geldi.
- Yanlış alarm: hiçbir olaya denk gelmeyen uyarı. Neden olarak ±3 sn içinde inceleyicilerin not ettiği
  belirsiz/tartışmalı aynı sınıf ("muhtemelen gerçek, uzak") ya da başka bir levha ("başka levhaya karıştı") yazılır.
Düzeltme: bizim "crossroads" sınıfı bütün ana yol-tali yol kavşak üçgenlerini kapsıyor (T, kademeli, Y birleşme;
train etiketlerinden bakıldı). İnceleyicilere yalnızca "+" anlatılmıştı; notunda kavşak geçen "other" üçgenler
crossroads sayılır.

Çalıştırma (ml/ klasöründe):  .venv\\Scripts\\python scripts\\video_degerlendir.py levha     # log adı: <video>.levha.log.csv
"""

import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ML = Path(__file__).resolve().parents[1]
VID = ML / "data" / "videolar"
TARGET = {
    "stop", "noentry", "giveway", "speed30", "speed50", "speed70", "caution", "crossroads", "dangerousleft",
    "dangerousright", "pedestrian_risk", "schoolpassing", "pedestrian_info", "keepleft", "keepright", "donotturnleft",
    "donotturnright", "nouturn", "nostopping", "priorityroad",
}
JUNCTION = re.compile(r"side.?road|junction|merge|staggered", re.I)
# v9 (30 Ekim): 20 sınıfın dışındaki yeni sesli sınıflar gerçek durumda olay olarak yok (inceleyiciler yalnızca 20
# sınıfı saydı), ama notlarında geçiyor. Böyle bir uyarı, ±3 sn içinde notu eşleşiyorsa "yeni sınıf doğru" sayılır.
NEW_NOTE = {
    "keskin_viraj": r"chevron", "dusen_kaya": r"rock", "sollama_yasak": r"overtak", "durak": r"bus stop|durak",
    "kasis": r"bump|hump|kasis", "devamli_viraj": r"double bend|s-curve|s curve|bends", "hayvan": r"animal|deer|cattle|cow",
    "daralan_yol": r"narrow", "dik_egim": r"slope|gradient|steep|descent|hill|%", "speed40": r"\b40\b", "speed60": r"\b60\b",
    "hiz_sonu": r"end of|limit end|derestrict", "isikli_isaret": r"traffic light|signal", "yol_calismasi": r"roadwork|road work|construction|works",
    "demiryolu": r"rail|train|level crossing", "ada_etrafinda": r"roundabout", "kaygan_yol": r"slipper|skid",
}


def credit_new(cells, extra):
    """Eşleşmeyen uyarılardan yeni sınıfa ait olup notu tutanları ayırır -> (doğru sayılanlar, kalan yanlışlar)."""
    ok, rest = [], []
    for t, c in extra:
        pat = NEW_NOTE.get(c)
        near = " | ".join(n for s, cell in cells.items() if abs(s - t) <= 3 for cc, _, n in cell.get("notes", []) if cc not in TARGET)
        (ok if pat and re.search(pat, near, re.I) else rest).append((t, c))
    return ok, rest


def load_gt():
    gt = defaultdict(lambda: defaultdict(dict))  # video -> saniye -> {"A": Counter, "B": Counter, "notes": [...]}
    for chunk in json.loads((ML / "degerlendirme" / "video_gercek_durum.json").read_text(encoding="utf-8")):
        for who, frames in zip("AB", chunk["reviewers"]):
            for fr in frames or []:
                signs = [(x["cls"], x["clear"], x["note"]) for x in fr["signs"]]
                signs = [("crossroads" if c == "other" and "triangle" in n.lower() and JUNCTION.search(n) else c, cl, n)
                         for c, cl, n in signs]
                cell = gt[chunk["video"]][int(fr["frame"][1:5])]
                cell.setdefault("notes", [])
                cell[who] = Counter(c for c, clear, _ in signs if clear and c in TARGET)
                cell["notes"] += signs
    return gt


def events(cells):
    present = defaultdict(list)
    for s, cell in sorted(cells.items()):
        a, b = cell.get("A", Counter()), cell.get("B", Counter())
        for c in set(a) & set(b):
            present[c].append(s)
    out = []
    for c, secs in present.items():
        start = prev = secs[0]
        for s in secs[1:] + [None]:
            if s is None or s - prev > 2:
                out.append({"cls": c, "start": start, "end": prev})
                if s is not None:
                    start = s
            if s is not None:
                prev = s
    return sorted(out, key=lambda e: e["start"])


def alerts(log):
    with open(log, encoding="utf-8") as f:
        return [(float(r["zaman_sn"]), r["sinif"]) for r in csv.DictReader(f, delimiter=";") if r["olay"] == "uyari"]


def match(evs, als):
    """-> ([(olay, uyarı zamanı ya da None)], eşleşmeyen uyarılar)"""
    used, res = set(), []
    for e in evs:
        hit = next((i for i, (t, c) in enumerate(als) if c == e["cls"] and i not in used and e["start"] - 1 <= t <= e["end"] + 2), None)
        if hit is not None:
            used.add(hit)
        res.append((e, None if hit is None else als[hit][0]))
    return res, [a for i, a in enumerate(als) if i not in used]


def explain(cells, t, cls):
    near = [n for s, cell in cells.items() if abs(s - t) <= 3 for n in cell.get("notes", [])]
    if any(c == cls for c, _, _ in near):
        return "muhtemelen gerçek (inceleyicilerden biri/belirsiz gördü)"
    other = [note for c, clear, note in near if c == "other" or c not in TARGET]
    return f"başka levhaya karıştı: {other[0][:60]}" if other else "boş yerde"


if __name__ == "__main__":
    tag = sys.argv[1] if len(sys.argv) > 1 else "levha"
    gt = load_gt()
    tot = Counter()
    for video in sorted(gt):
        log = VID / f"{video}.{tag}.log.csv"
        if not log.exists():
            print(f"\n## {video}: log yok ({log.name})")
            continue
        evs, als = events(gt[video]), alerts(log)
        print(f"\n## {video}  ({len(evs)} gerçek levha olayı, {len(als)} uyarı)")
        res, extra = match(evs, als)
        for e, t in res:
            tot["olay"] += 1
            if t is None:
                tot["kacirma"] += 1
                print(f"  KAÇIRDI   {e['cls']:15s} görünür {e['start']}-{e['end']} sn")
                continue
            timely = t <= e["end"] + 0.5
            tot["yakalandi"] += 1
            tot["zamaninda"] += timely
            print(f"  YAKALADI  {e['cls']:15s} görünür {e['start']}-{e['end']} sn, uyarı {t:.1f} sn {'(zamanında)' if timely else '(GEÇ)'}")
        ok_new, extra = credit_new(gt[video], extra)
        for t, c in ok_new:
            tot["yeni_ok"] += 1
            print(f"  YENİ OK   {c:15s} uyarı {t:.1f} sn (inceleyici notu tutuyor)")
        for t, c in extra:
            why = explain(gt[video], t, c)
            tot["yanlis_alarm"] += 1
            tot["muhtemelen_gercek"] += why.startswith("muhtemelen")
            print(f"  FAZLA     {c:15s} uyarı {t:.1f} sn -> {why}")
    print(f"\nTOPLAM: {tot['olay']} gerçek levha | yakalanan {tot['yakalandi']} (zamanında {tot['zamaninda']}) | "
          f"kaçırılan {tot['kacirma']} | eşleşmeyen uyarı {tot['yanlis_alarm']} "
          f"(bunların {tot['muhtemelen_gercek']}'i muhtemelen gerçek uzak levha) | yeni sınıf doğru {tot['yeni_ok']}")
