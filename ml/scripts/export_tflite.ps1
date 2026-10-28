# .pt -> .tflite (LiteRT) dışa aktarma.
# Ultralytics LiteRT dışa aktarması yalnızca Linux/macOS'ta destekleniyor; bu betik işi WSL'deki Ubuntu'ya yaptırır.
# Yollar ml/ klasörüne göredir. Örnekler:
#   .\scripts\export_tflite.ps1 -Model models\yolo11n.pt -ImgSz 320
#   .\scripts\export_tflite.ps1 -Model runs\detect\train\weights\best.pt -Quantize w8a32
#   .\scripts\export_tflite.ps1 -Model runs\detect\train\weights\best.pt -Quantize 8 -Data data\levha.yaml
param(
    [Parameter(Mandatory)] [string] $Model,
    [int] $ImgSz = 640,
    [string] $Quantize = "",  # "" = FP32, "w8a32" = dinamik INT8, "8" = statik INT8 (Data gerekir), "w8a16"
    [string] $Data = ""
)

$ml = Split-Path $PSScriptRoot -Parent
$wslMl = "/mnt/" + $ml.Substring(0, 1).ToLower() + ($ml.Substring(2) -replace '\\', '/')

# nms=None: NMS modele gömülmez, eklenti Android tarafında yapar (bkz. docs/YOL_HARITASI.md #22)
$cmd = "yolo export model=$($Model -replace '\\', '/') format=litert nms=None imgsz=$ImgSz"
if ($Quantize) { $cmd += " quantize=$Quantize" }
if ($Data) { $cmd += " data=$($Data -replace '\\', '/')" }

wsl.exe -d Ubuntu-24.04 -u root -- bash -lc "source /root/venvs/export/bin/activate && cd '$wslMl' && $cmd"
