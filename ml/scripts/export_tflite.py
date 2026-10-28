"""Telefon için .tflite dışa aktarma (Windows).

Ultralytics'in Windows'ta çalışan yolu format=saved_model (ONNX -> onnx2tf). Bu sürümde (8.4.191) o yol kutu
koordinatlarını piksel (0..imgsz) olarak veriyor, oysa .tflite okuyucuları (Ultralytics LiteRT arka ucu,
Flutter eklentisi) 0..1 arası normalize koordinat bekliyor; sonuç: mAP 0. Bu betik ONNX çıkışına
"xywh / imgsz" çarpımı ekleyip Ultralytics'in kendi onnx2tf fonksiyonuyla yeniden çevirir ve sınıf
isimlerini taşıyan metadata.json'ı yeni dosyalara ekler.

Çalıştırma (ml/ klasöründe):  .venv\\Scripts\\python scripts\\export_tflite.py runs/detect/v2/weights/best.pt
Çıktı: <weights>/best_tflite/best_float32.tflite ve best_float16.tflite
"""

import sys
import zipfile
from pathlib import Path

import numpy as np
import onnx
from onnx import helper, numpy_helper
from ultralytics import YOLO
from ultralytics.utils.export.tensorflow import onnx2saved_model


def main(pt: str, imgsz: int = 640):
    pt = Path(pt)
    saved = Path(YOLO(pt).export(format="saved_model", imgsz=imgsz))  # .onnx + piksel koordinatlı .tflite + metadata
    meta = zipfile.ZipFile(next(saved.glob("*_float32.tflite"))).read("metadata.json")

    m = onnx.load(pt.with_suffix(".onnx"))
    out = m.graph.output[0]
    rows = out.type.tensor_type.shape.dim[1].dim_value  # 4 + sınıf sayısı
    scale = np.ones((1, rows, 1), np.float32)
    scale[0, :4] = 1 / imgsz
    m.graph.initializer.append(numpy_helper.from_array(scale, "xywh_scale"))
    m.graph.node.append(helper.make_node("Mul", [out.name, "xywh_scale"], [out.name + "_norm"]))
    out.name += "_norm"
    norm_onnx = pt.with_name(f"{pt.stem}_norm.onnx")
    onnx.save(m, norm_onnx)

    out_dir = pt.parent / f"{pt.stem}_tflite"
    onnx2saved_model(str(norm_onnx), out_dir)
    for f in out_dir.glob("*.tflite"):
        f = f.rename(out_dir / f.name.replace("_norm", ""))
        with zipfile.ZipFile(f, "a") as z:
            z.writestr("metadata.json", meta)
        print("->", f)
    for f in saved.glob("*.tflite"):  # piksel koordinatlı, yanlış ölçekli dosyalar karışmasın
        f.unlink()


if __name__ == "__main__":
    main(sys.argv[1])
