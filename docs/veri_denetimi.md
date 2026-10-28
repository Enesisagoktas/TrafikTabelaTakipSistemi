# Veri Seti Denetimi

Veri: `ml/data/levha` (Roboflow sürüm 17, augmentasyonsuz)

## 1. Bölmeler

| Bölme | Görsel | Levha (kutu) | Etiketsiz görsel |
|---|---|---|---|
| train | 4422 | 6395 | 0 |
| valid | 553 | 806 | 0 |
| test | 552 | 799 | 0 |

## 2. Sınıf dağılımı (kutu sayısı)

| # | Sınıf | train | valid | test |
|---|---|---|---|---|
| 9 | noentry | 330 | 35 | 35 |
| 10 | nostopping | 329 | 35 | 36 |
| 11 | nouturn | 329 | 34 | 37 |
| 14 | priorityroad | 328 | 40 | 32 |
| 3 | dangerousright | 327 | 34 | 39 |
| 0 | caution | 325 | 34 | 41 |
| 1 | crossroads | 324 | 42 | 34 |
| 4 | donotturnleft | 323 | 39 | 38 |
| 15 | schoolpassing | 323 | 33 | 44 |
| 17 | speed50 | 323 | 42 | 35 |
| 12 | pedestrian_info | 322 | 45 | 33 |
| 13 | pedestrian_risk | 322 | 39 | 39 |
| 16 | speed30 | 321 | 40 | 39 |
| 8 | keepright | 318 | 42 | 40 |
| 19 | stop | 318 | 36 | 46 |
| 5 | donotturnright | 312 | 47 | 41 |
| 7 | keepleft | 310 | 45 | 45 |
| 2 | dangerousleft | 308 | 41 | 51 |
| 18 | speed70 | 305 | 44 | 51 |
| 6 | giveway | 298 | 59 | 43 |

## 3. Levhaların model girişindeki boyutu

Kutunun kısa kenarı, görüntü model girişine küçültüldükten sonra kaç piksel kalıyor?

| Kısa kenar | imgsz=640 | imgsz=320 |
|---|---|---|
| < 8 px | %9.7 | %34.8 |
| 8–16 px | %25.1 | %34.5 |
| 16–32 px | %34.5 | %22.3 |
| 32–64 px | %22.3 | %7.0 |
| ≥ 64 px | %8.3 | %1.3 |

Medyan kısa kenar: imgsz=640'ta 21 px, imgsz=320'de 11 px.

## 4. Veri sızıntısı: valid/test görsellerinin train'deki en yakın eşi

Algısal hash (64 bit) farkı: 0 = aynı görsel, ≤ 8 = neredeyse aynı kare, ≥ 20 = farklı görsel.

| En yakın train eşine uzaklık | valid | test |
|---|---|---|
| 0 (aynı) | 0 | 3 |
| 1–4 | 19 | 8 |
| 5–8 | 57 | 54 |
| 9–12 | 181 | 179 |
| ≥ 13 | 296 | 308 |

Tam liste: `ml/runs/denetim/yakin_kopyalar.csv`

Uzaklığı ≤ 12 olanlar sızıntı sayıldı ve dışarıda bırakıldı. Temiz valid: 296 görsel, temiz test: 308 görsel → `data/levha/data_temiz.yaml` (train aynı; orijinal veri setine dokunulmadı).

## 5. Gözle kontrol

100 rastgele train görselinin kutuları çizildi: `ml/runs/denetim/etiketler/sayfa_1..4.jpg`
