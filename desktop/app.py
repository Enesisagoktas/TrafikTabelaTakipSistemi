"""Windows uygulaması (ilk sürüm): web kamerası + model (ekran kartı varsa levha.pt GPU'da, yoksa levha.onnx CPU'da)
+ mobil sürümle aynı uyarı kuralları.

Levha kataloğu (cümle + öncelik) mobile/lib/alerts.dart'tan okunur, sesler mobile/assets/sounds/*.wav.
Çalıştırma (proje kökünde):
    ml\\.venv\\Scripts\\python desktop\\app.py           # web kamerası (0)
    ml\\.venv\\Scripts\\python desktop\\app.py yol.mp4   # video, kendi hızında oynar (log: yol.levha.log.csv; ad = model dosyasının adı)
    ml\\.venv\\Scripts\\python desktop\\app.py yol.mp4 diger_model.onnx   # başka bir modelle
    ml\\.venv\\Scripts\\python desktop\\app.py yol.mp4 --sessiz           # ses ve pencere yok, yalnızca log
    ml\\.venv\\Scripts\\python desktop\\app.py --test    # kural öz-testi
Çıkış: q
"""

import ctypes
import os
import re
import sys
import time
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL = Path(__file__).with_name("levha.onnx")
SOUNDS = ROOT / "mobile" / "assets" / "sounds"
_CATALOG = re.findall(r"'(\w+)': \(text: '([^']+)', short: '([^']+)', priority: (\d)\)", (ROOT / "mobile/lib/alerts.dart").read_text("utf-8"))
SIGNS = {n: (text, int(p)) for n, text, _, p in _CATALOG}  # sınıf -> (cümle, öncelik); tek kaynak: alerts.dart
SHORT = {n: short for n, _, short, _ in _CATALOG}  # kısa biçim: arkada başka uyarı beklerken (<sınıf>_kisa.wav)
# Hız levhaları birbirine, pedestrian_info başka mavi levhalara karışıyor (YOL_HARITASI, Hafta 2 sonuçları).
CLASS_MIN_CONF = {"speed30": 0.65, "speed50": 0.65, "speed70": 0.65, "pedestrian_info": 0.7}


class DetectionFilter:
    """Güven eşiği + en küçük kutu + son `window` karenin en az `min_hits`'inde görülme."""

    def __init__(self, window=5, min_hits=3, min_conf=0.5, min_height=0.0, class_min_conf=None):
        self.window, self.min_hits, self.min_conf, self.min_height = window, min_hits, min_conf, min_height
        self.class_min_conf = class_min_conf or {}
        self.frames = []

    def update(self, dets):  # dets: [(sınıf, güven, normalize yükseklik)]
        # Sınıf eşiği bir taban: genel eşikten düşükse genel eşik geçerli (alerts.dart classThresholds ile aynı).
        self.frames.append({n for n, c, h in dets if c >= max(self.class_min_conf.get(n, 0), self.min_conf) and h >= self.min_height})
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


class Rules:
    """Telefondaki zincirin aynısı: filtre -> bekleme -> kuyruk -> aynı anda tek ses (sesin süresi kadar meşgul).
    Video loglarını yeniden oynatan eşik taraması da (ml/scripts/esik_tarama.py) bunu kullanır."""

    def __init__(self, **filter_args):
        self.filt, self.cool, self.queue = DetectionFilter(**filter_args), Cooldown(), AlertQueue()
        self.busy_until, self.confirmed, self.brief = 0.0, set(), False

    def step(self, dets, now):
        """dets: [(sınıf, güven, normalize yükseklik)] -> (yeni onaylanan sınıflar, çalınacak uyarı ya da None).
        Katalogda (alerts.dart) olmayan sınıf yok sayılır: ör. diger_levha, yani tanınan ama uyarısı olmayan levha.
        Uyarı çalınırken arkada başka uyarı bekliyorsa `brief` True olur: kısa biçim (<sınıf>_kisa.wav) çalınır."""
        seen = self.filt.update([d for d in dets if d[0] in SIGNS])
        new, self.confirmed = seen - self.confirmed, seen
        for n in self.cool.update(seen, now):
            self.queue.add(n, SIGNS[n][1], now)
        if now < self.busy_until or not (n := self.queue.next(now)):
            return new, None
        self.brief = bool(self.queue.items)
        with wave.open(str(SOUNDS / f"{n}{'_kisa' if self.brief else ''}.wav")) as w:
            self.busy_until = now + w.getnframes() / w.getframerate()
        return new, n


def selftest():
    f = DetectionFilter()
    assert [f.update(x) for x in ([("stop", 0.9, 0.1)], [], [("stop", 0.9, 0.1)], [("stop", 0.9, 0.1)])][-1] == {"stop"}
    f = DetectionFilter(min_hits=1, min_conf=0.7, class_min_conf=CLASS_MIN_CONF)
    assert f.update([("speed30", 0.68, 0.1)]) == set()  # taban (0,65) genel eşiği düşürmez
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
    r = Rules()
    assert [r.step([("stop", 0.9, 0.1)], t)[1] for t in (0, 0.1, 0.2)] == [None, None, "stop"]
    assert not r.brief
    r = Rules()
    assert [r.step([("diger_levha", 0.99, 0.2)], t) for t in (0, 0.1, 0.2)][-1] == (set(), None)
    r = Rules()
    # aynı öncelik ve aynı an: kuyruk ada göre sıralar, önce yol ver çalar
    assert [r.step([("stop", 0.9, 0.1), ("giveway", 0.9, 0.1)], t)[1] for t in (0, 0.1, 0.2)][-1] == "giveway"
    assert r.brief  # yol ver çalarken dur bekliyor: kısa biçim
    assert len(SIGNS) == 28 and all(1 <= p <= 3 for _, p in SIGNS.values()) and set(SHORT) == set(SIGNS)
    print("öz-test geçti")


def high_qos():
    """Windows 11 odakta olmayan pencerenin işlemini kısıyor: pencere arkada ya da küçültülmüşken CPU'da çıkarım 27 ms'den
    ~230 ms'ye çıktı (29 Ekim ölçümü). İşlem yalnızca kendi kısılmasını kapatır; sistem ayarı değişmez."""

    class State(ctypes.Structure):
        _fields_ = [("Version", ctypes.c_ulong), ("ControlMask", ctypes.c_ulong), ("StateMask", ctypes.c_ulong)]

    k = ctypes.windll.kernel32
    k.SetProcessInformation.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_ulong]
    # ProcessPowerThrottling (4): yürütme hızı (1) denetlenir, kısma durumu kapalı (0). c_void_p(-1): bu işlem
    return k.SetProcessInformation(ctypes.c_void_p(-1), 4, ctypes.byref(State(1, 1, 0)), ctypes.sizeof(State))


def main(source, model_path=None, quiet=False):
    import cv2
    import numpy as np
    import torch
    from PIL import Image, ImageDraw, ImageFont
    from ultralytics import YOLO

    # --sessiz (yalnızca log) kipi Linux'ta da çalışır, ör. Colab'da video testi: ses, pencere, yazı tipi ve QoS Windows'a özgü
    if os.name == "nt":
        high_qos()
    if not quiet:
        import winsound
    font = None if quiet else ImageFont.truetype("arial.ttf", 44)
    # Ekran kartı varsa PyTorch modeli (levha.pt, levha.onnx ile aynı v5b ağırlıkları) GPU'da çalışır. ONNX yalnızca CPU'da:
    # onnxruntime-gpu 1.31 CUDA 13 istiyor, sürücü (566) en fazla 12.7 destekliyor; PyTorch kendi CUDA'sını (12.6) getiriyor.
    gpu = torch.cuda.is_available()
    model_path = model_path or MODEL.with_suffix(".pt" if gpu else ".onnx")
    device = 0 if gpu and Path(model_path).suffix == ".pt" else "cpu"
    model = YOLO(str(model_path), task="detect")

    def render(text, width):
        """Uyarı yazısı uyarı başına bir kez çizilir (her karede çizmek ~23 ms tutuyordu). OpenCV Türkçe karakter
        çizemiyor: Pillow + Arial. Dönüş: (BGR yama, yazı maskesi)."""
        im, mask = Image.new("RGB", (width, 64)), Image.new("L", (width, 64))
        ImageDraw.Draw(im).text((10, 5), text, font=font, fill=(255, 40, 40), stroke_width=3, stroke_fill=(0, 0, 0))
        ImageDraw.Draw(mask).text((10, 5), text, font=font, fill=255, stroke_width=3, stroke_fill=255)
        return np.asarray(im)[..., ::-1], np.asarray(mask) > 0

    # Telefon uygulamasının varsayılanlarıyla aynı: güven 0,7, küçük kutu eşiği %5 (uzak levhalar yanlış alarmın ana
    # kaynağı; 10 test videosunda ml/scripts/esik_tarama.py ile seçildi). Oylama hep 5 karenin 3'ü: bilgisayar en az ~21 FPS
    # çalışıyor; telefondaki "8 FPS altında 3 karenin 2'si" kuralı (alerts.dart votingFor) burada hiç devreye girmez.
    rules = Rules(class_min_conf=CLASS_MIN_CONF, min_conf=0.7, min_height=0.05)
    banner, t_prev = None, time.perf_counter()
    # Video dosyasında saat videonun kendi zamanıdır (kurallar gerçek sürüşteki gibi işler) ve her şey loglanır.
    # Boş kareler de yazılır: eşik taraması logu kare kare yeniden oynatır (5 karenin 3'ü kuralı boş kareyi sayar).
    video = isinstance(source, str)
    fps = cv2.VideoCapture(source).get(cv2.CAP_PROP_FPS) if video else 0
    log = open(Path(source).with_suffix(f".{Path(model_path).stem}.log.csv") if video else os.devnull, "w", encoding="utf-8")
    log.write("zaman_sn;olay;sinif;guven;yukseklik\n")
    # Pencereyle kare başına (29 Ekim, 1280 px video): CPU/ONNX ~40 ms (25 FPS; çıkarım ~27 ms), GPU ~16 ms (~63 FPS).
    # conf=0.25 ve sınıftan bağımsız NMS: telefondaki eklentinin (ultralytics_yolo) ayarlarıyla aynı.
    for i, r in enumerate(model.predict(source=source, stream=True, imgsz=640, conf=0.25, agnostic_nms=True, device=device, verbose=False)):
        now = i / fps if video else time.monotonic()
        dets = [(r.names[int(k)], float(p), float(b[3])) for k, p, b in zip(r.boxes.cls, r.boxes.conf, r.boxes.xywhn)]
        log.writelines(f"{now:.2f};tespit;{n};{p:.3f};{h:.4f}\n" for n, p, h in dets)
        if not dets:
            log.write(f"{now:.2f};kare;;;\n")
        new, n = rules.step(dets, now)
        log.writelines(f"{now:.2f};onay;{c};;\n" for c in new)  # 5 karenin 3'üne yeni giren
        if n:
            text = SHORT[n] if rules.brief else SIGNS[n][0]
            if not quiet:
                winsound.PlaySound(str(SOUNDS / f"{n}{'_kisa' if rules.brief else ''}.wav"), winsound.SND_FILENAME | winsound.SND_ASYNC)
                banner = render(text, r.orig_shape[1])
            log.write(f"{now:.2f};uyari;{n};;\n")
            print(f"{now:6.1f} sn  uyarı: {text}", flush=True)
        if quiet:
            continue
        frame = r.plot()
        t = time.perf_counter()
        cv2.putText(frame, f"{1 / max(t - t_prev, 1e-6):.0f} FPS", (10, frame.shape[0] - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        t_prev = t
        if banner:
            patch, mask = banner
            top = frame[:64]
            top[mask] = patch[mask]
        cv2.imshow("Trafik Asistani (q: cikis)", frame)
        # Video kendi hızında oynar, uyarı sesi görüntüyle aynı anda duyulur; model geride kalırsa (60 FPS video) beklenmez.
        if i == 0:
            t0 = t
        wait = round((t0 + now - time.perf_counter()) * 1000) if video else 1
        if cv2.waitKey(max(wait, 1)) & 0xFF == ord("q"):
            break
    log.close()
    if not quiet:
        cv2.destroyAllWindows()


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--sessiz"]  # --sessiz: ses ve pencere yok, yalnızca log (toplu test)
    arg = args[0] if args else "0"
    if arg == "--test":
        selftest()
    else:
        main(int(arg) if arg.isdigit() else arg, *args[1:2], quiet=len(args) < len(sys.argv) - 1)
