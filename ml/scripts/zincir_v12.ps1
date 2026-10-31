# v12 zinciri (31 Ekim gece): v9 verisi + Commons/Pexels Turk kareleri (ajan denetimi) + resmi KGM cizimlerinden sentetik kopyala-yapistir (ek/sentetik, 1397 gorsel)
# -> v8 den yeniden 38 sinifli egitim -> temiz test -> 10 video -> kapi (yeni kural: v9 32/11/4) -> sevk.
# ASCII: PS 5.1 BOM'suz .ps1'i ANSI okur.
$ErrorActionPreference = 'Continue'
$SC = 'C:\Users\06Ene\AppData\Local\Temp\claude\C--Projeler-TrafikTabelaTakipSistemi\a51b9072-0689-4a97-bd05-329bd93dc8fb\scratchpad'
$KOK = 'C:\Projeler\TrafikTabelaTakipSistemi'
$env:PYTHONIOENCODING = 'utf-8'
$ozet = "$SC\zincir_v12_ozet.txt"
function Not($m) { $line = "$(Get-Date -Format 'HH:mm') $m"; $line | Out-File -Encoding utf8 -Append $ozet; Write-Output $line }
Add-Type -Name P -Namespace W -MemberDefinition '[DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint f);'
[W.P]::SetThreadExecutionState([uint32]"0x80000003") | Out-Null
Not "v12 zinciri basladi"

Set-Location "$KOK\ml"
$py = ".venv\Scripts\python.exe"; $yolo = ".venv\Scripts\yolo.exe"

# 1) Egitim: v9'dan, ayni 38 sinif (bas korunur), kisa ince ayar
& $yolo train model=runs/detect/v8/weights/best.pt data=data/levha640/data_v12.yaml imgsz=640 batch=16 workers=3 optimizer=AdamW lr0=0.0003 lrf=0.05 warmup_epochs=1 warmup_bias_lr=0 epochs=60 patience=60 close_mosaic=10 fliplr=0 mixup=0 cache=False name=v12 exist_ok=True 2>&1 | Out-File -Encoding utf8 "$SC\zincir_v12_egitim.log"
if (-not (Test-Path runs\detect\v12\weights\best.pt)) {
    Not "egitim kesildi; last.pt'den surduruluyor"
    & $yolo train resume model=runs/detect/v12/weights/last.pt 2>&1 | Out-File -Encoding utf8 -Append "$SC\zincir_v12_egitim.log"
}
if (-not (Test-Path runs\detect\v12\weights\best.pt)) { Not "best.pt yok, zincir durdu"; exit 1 }
$res = @(Import-Csv runs\detect\v12\results.csv)
$best = $res | Sort-Object { [double](($_.PSObject.Properties | Where-Object Name -match 'mAP50-95').Value) } -Descending | Select-Object -First 1
Not ("egitim bitti: {0} epoch, en iyi epoch {1}: val mAP50 {2:N3} / mAP50-95 {3:N3}" -f $res.Count, ($best.PSObject.Properties | Where-Object Name -match 'epoch').Value.Trim(), [double]($best.PSObject.Properties | Where-Object Name -match 'mAP50\(B\)').Value, [double]($best.PSObject.Properties | Where-Object Name -match 'mAP50-95').Value)

# 2) Temiz test
& $yolo val model=runs/detect/v12/weights/best.pt data=data/levha640/data_v12.yaml split=test imgsz=640 batch=16 plots=False name=v12_test exist_ok=True 2>&1 | Out-File -Encoding utf8 "$SC\zincir_v12_test.log"
$txt = (Get-Content "$SC\zincir_v12_test.log" -Raw) -replace '\x1b\[[0-9;]*m', ''
Not ("temiz test .pt: " + (($txt -split "`r|`n" | Where-Object { $_ -match '^\s+all\s+\d' } | Select-Object -Last 1) -replace '\s+', ' '))

# 3) 10 video
Copy-Item runs\detect\v12\weights\best.pt runs\detect\v12\weights\v12.pt -Force
Set-Location $KOK
Get-ChildItem ml\data\videolar\kucuk\*.avi | ForEach-Object { & ml\.venv\Scripts\python.exe desktop\app.py $_.FullName ml\runs\detect\v12\weights\v12.pt --sessiz 2>&1 | Out-Null }
Move-Item ml\data\videolar\kucuk\*.v12.log.csv ml\data\videolar\ -Force
Set-Location "$KOK\ml"
& $py scripts\video_degerlendir.py v12 2>&1 | Out-File -Encoding utf8 "$SC\zincir_v12_video.txt"
& $py scripts\analiz.py kurallar --etiket v12 2>&1 | Out-File -Encoding utf8 -Append "$SC\zincir_v12_video.txt"
$g = Get-Content "$SC\zincir_v12_video.txt" -Encoding UTF8 | Where-Object { $_ -match '^GATE30 ' } | Select-Object -First 1
Not ("video 30 FPS: " + $g)
$g5 = Get-Content "$SC\zincir_v12_video.txt" -Encoding UTF8 | Where-Object { $_ -match '^GATE30T5' } | Select-Object -First 1
Not ("video 30 FPS, 5 sinifta taban 0.8: " + $g5)
$m = [regex]::Match([string]$g, 'caught=(\d+) timely=(\d+) false=(\d+) newok=(\d+)')
$yak = [int]$m.Groups[1].Value; $yan = [int]$m.Groups[3].Value; $yeni = [int]$m.Groups[4].Value
$iyi = $m.Success -and ($yak -ge 31) -and ($yan -le 11) -and ($yeni -ge 4)   # v9 + taban: 32 (27) / 11 / 4 @30 FPS
Not ("karar: 30 FPS'te $yak yakalanan / $yan yanlis uyari / $yeni yeni sinif dogru -> " + $(if ($iyi) { 'v9''dan kotu degil, uygulamaya aliniyor' } else { 'v9''dan kotu, uygulama v9''da kaliyor' }))

# 4) Disa aktarma + uygulamalar + APK + commit (yalnizca iyiyse)
if ($iyi) {
    & $py scripts\export_tflite.py runs/detect/v12/weights/best.pt 2>&1 | Out-File -Encoding utf8 "$SC\zincir_v12_export.log"
    & $yolo val model=runs/detect/v12/weights/best_tflite/best_float16.tflite data=data/levha640/data_v12.yaml split=test imgsz=640 batch=16 plots=False name=v12_tflite_test exist_ok=True 2>&1 | Out-File -Encoding utf8 -Append "$SC\zincir_v12_export.log"
    $txt = (Get-Content "$SC\zincir_v12_export.log" -Raw) -replace '\x1b\[[0-9;]*m', ''
    Not ("temiz test tflite: " + (($txt -split "`r|`n" | Where-Object { $_ -match '^\s+all\s+\d' } | Select-Object -Last 1) -replace '\s+', ' '))
    Set-Location $KOK
    if (Test-Path ml\runs\detect\v12\weights\best_tflite\best_float16.tflite) {
        Copy-Item ml\runs\detect\v12\weights\best_tflite\best_float16.tflite mobile\assets\models\levha.tflite -Force
        Copy-Item ml\runs\detect\v12\weights\best.pt desktop\levha.pt -Force
        if (Test-Path ml\runs\detect\v12\weights\best.onnx) { Copy-Item ml\runs\detect\v12\weights\best.onnx desktop\levha.onnx -Force } else { Not "best.onnx yok" }
        & ml\.venv\Scripts\python.exe -X utf8 "$SC\model_adi.py" v12 38 2>&1 | ForEach-Object { Not "$_" }
        Set-Location "$KOK\mobile"
        flutter build apk --release --split-per-abi 2>&1 | Out-File -Encoding utf8 "$SC\zincir_v12_apk.log"
        .\android\gradlew.bat --stop 2>&1 | Out-Null
        Set-Location $KOK
        $apk = 'mobile\build\app\outputs\flutter-apk\app-arm64-v8a-release.apk'
        if ((Get-Item $apk).LastWriteTime -gt (Get-Date).AddMinutes(-30)) { Not ("APK {0:N1} MB derlendi" -f ((Get-Item $apk).Length/1MB)) } else { Not "APK derlenemedi (zincir_v12_apk.log)" }
        git add desktop/levha.pt desktop/levha.onnx mobile/assets/models/levha.tflite mobile/lib/main.dart 2>&1 | Out-Null
        git commit -q -F "$SC\commit_v12.txt" 2>&1 | Out-Null
        Not ("commit: " + (git log --oneline -1))
    } else { Not "TFLite uretilemedi" }
}
Not "zincir bitti"
