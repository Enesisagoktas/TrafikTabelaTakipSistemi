"""Windows uygulaması (ilk sürüm): web kamerası + ONNX model (GPU) + mobil sürümle aynı uyarı kuralları.

Levha kataloğu (cümle + öncelik) mobile/lib/alerts.dart'tan okunur, sesler mobile/assets/sounds/*.wav.
Çalıştırma (proje kökünde):
    ml\\.venv\\Scripts\\python desktop\\app.py           # web kamerası (0)
    ml\\.venv\\Scripts\\python desktop\\app.py yol.mp4   # video dosyası (log: yol.log.csv)
    ml\\.venv\\Scripts\\python desktop\\app.py yol.mp4 diger_model.onnx   # başka bir modelle
    ml\\.venv\\Scripts\\python desktop\\app.py --test    # kural öz-testi
Çıkış: q
"""

import os
import re
import sys
import time
import wave
import winsound
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL = Path(__file__).with_name("levha.onnx")
SOUNDS = ROOT / "mobile" / "assets" / "sounds"
SIGNS = {  # sınıf -> (cümle, öncelik); tek kaynak: alerts.dart
    m[1]: (m[2], int(m[3]))
    for m in re.finditer(r"'(\w+)': \(text: '([^']+)', priority: (\d)\)", (ROOT / "mobile/lib/alerts.dart").read_text("utf-8"))
}
# Hız levhaları birbirine, pedestrian_info başka mavi levhalara karışıyor (YOL_HARITASI, Hafta 2 sonuçları).
CLASS_MIN_CONF = {"speed30": 0.65, "speed50": 0.65, "speed70": 0.65, "pedestrian_info": 0.7}


class DetectionFilter:
    """Güven eşiği + en küçük kutu + son `window` karenin en az `min_hits`'inde görülme."""

    def __init__(self, window=5, min_hits=3, min_conf=0.5, min_height=0.0, class_min_conf=None):
        self.window, self.min_hits, self.min_conf, self.min_height = window, min_hits, min_conf, min_height
        self.class_min_conf = class_min_conf or {}
        self.frames = []

    def update(self, dets):  # dets: [(sınıf, güven, normalize yükseklik)]
        self.frames.append({n for n, c, h in dets if c >= self.class_min_conf.get(n, self.min_conf) and h >= self.min_height})
        self.frames = self.frames[-self.window :]
        names = [n for f in self.frames for n in f]
        return {n for n in names if names.count(n) >= self.min_hits}


class Cooldown:
    """En az `min_gap` sn sessizlik ve levha `rearm_after` sn görünmeyip yeniden kurulmalı."""

    def __init__(self, min_gap=5.0, rearm_after=2.0):
        self.min_gap, self.rearm_after = min_gap, rearm_after
        self.last_alert, self.last_seen, self.disarmed = {}, {}, set()

    def update(self, seen, now):
        self.disarmed = {n for n in self.disarmed if n in seen or now - self.last_seen[n] < self.rearm_after}
        out = []
        for n in seen:
            self.last_seen[n] = now
            if n in self.disarmed or now - self.last_alert.get(n, -1e9) < self.min_gap:
                continue
            self.last_alert[n] = now
            self.disarmed.add(n)
            out.append(n)
        return out


class AlertQueue:
    """Öncelik sıralı, en fazla `max_len` uyarı, `max_age` sn'den eskisi atılır."""

    def __init__(self, max_len=2, max_age=3.0):
        self.max_len, self.max_age, self.items = max_len, max_age, []

    def add(self, name, priority, now):
        self.items = sorted([*self.items, (priority, now, name)])[: self.max_len]

    def next(self, now):
        self.items = [i for i in self.items if now - i[1] <= self.max_age]
        return self.items.pop(0)[2] if self.items else None


def selftest():
    f = DetectionFilter()
    assert [f.update(x) for x in ([("stop", 0.9, 0.1)], [], [("stop", 0.9, 0.1)], [("stop", 0.9, 0.1)])][-1] == {"stop"}
    c = Cooldown()
    assert c.update({"stop"}, 0) == ["stop"] and c.update({"stop"}, 1) == []
    c.update(set(), 2.5)  # yalnızca 1,5 sn görünmedi: yeniden kurulmaz
    assert c.update({"stop"}, 6) == []
    c = Cooldown()
    c.update({"stop"}, 0)
    c.update(set(), 2.5)  # 2,5 sn görünmedi: yeniden kurulur, ama 5 sn dolmadan uyarmaz
    assert c.update({"stop"}, 3) == [] and c.update({"stop"}, 5) == ["stop"]
    q = AlertQueue()
    for n, p in (("speed50", 2), ("priorityroad", 3), ("noentry", 1)):
        q.add(n, p, 0)
    assert (q.next(0), q.next(0), q.next(0)) == ("noentry", "speed50", None)
    q.add("stop", 1, 0)
    assert q.next(3.5) is None
    assert len(SIGNS) == 20 and all(1 <= p <= 3 for _, p in SIGNS.values())
    print("öz-test geçti")


def main(source, model_path=MODEL):
    import cv2
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    from ultralytics import YOLO

    font = ImageFont.truetype("arial.ttf", 44)
    model = YOLO(str(model_path), task="detect")
    filt, cool, queue = DetectionFilter(class_min_conf=CLASS_MIN_CONF), Cooldown(), AlertQueue()
    busy_until, banner, t_prev = 0.0, "", time.perf_counter()
    # Video dosyasında saat videonun kendi zamanıdır (kurallar gerçek sürüşteki gibi işler) ve her şey loglanır.
    video = isinstance(source, str)
    fps = cv2.VideoCapture(source).get(cv2.CAP_PROP_FPS) if video else 0
    log = open(Path(source).with_suffix(f".{Path(model_path).stem}.log.csv") if video else os.devnull, "w", encoding="utf-8")
    log.write("zaman_sn;olay;sinif;guven\n")
    # CPU: i7-12700H'de çıkarım ~22 ms, uçtan uca ~33 FPS (29 Ekim). onnxruntime-gpu 1.31 CUDA 13 istiyor,
    # GPU sürücüsü (566) en fazla CUDA 12.7 destekliyor; gerek de yok.
    for i, r in enumerate(model.predict(source=source, stream=True, imgsz=640, conf=0.4, device="cpu", verbose=False)):
        now = i / fps if video else time.monotonic()
        dets = [(r.names[int(k)], float(p), float(b[3])) for k, p, b in zip(r.boxes.cls, r.boxes.conf, r.boxes.xywhn)]
        log.writelines(f"{now:.2f};tespit;{n};{p:.2f}\n" for n, p, _ in dets)
        for n in cool.update(filt.update(dets), now):
            queue.add(n, SIGNS[n][1], now)
        if now >= busy_until and (n := queue.next(now)):  # aynı anda tek ses
            wav = SOUNDS / f"{n}.wav"
            with wave.open(str(wav)) as w:
                busy_until = now + w.getnframes() / w.getframerate()
            winsound.PlaySound(str(wav), winsound.SND_FILENAME | winsound.SND_ASYNC)
            banner = SIGNS[n][0]
            log.write(f"{now:.2f};uyari;{n};\n")
            print(f"{now:6.1f} sn  uyarı: {banner}", flush=True)
        frame = r.plot()
        t = time.perf_counter()
        cv2.putText(frame, f"{1 / max(t - t_prev, 1e-6):.0f} FPS", (10, frame.shape[0] - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        t_prev = t
        if banner:  # OpenCV yazı tipi Türkçe karakter çizemiyor; Pillow + Arial
            im = Image.fromarray(frame[..., ::-1])
            ImageDraw.Draw(im).text((10, 5), banner, font=font, fill=(255, 40, 40), stroke_width=3, stroke_fill=(0, 0, 0))
            frame = np.ascontiguousarray(np.asarray(im)[..., ::-1])
        cv2.imshow("Trafik Asistani (q: cikis)", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    log.close()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "0"
    selftest() if arg == "--test" else main(int(arg) if arg.isdigit() else arg, *sys.argv[2:3])
