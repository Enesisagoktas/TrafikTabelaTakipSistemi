# Uyarı seslerini Windows'un çevrimdışı Türkçe sesiyle (Microsoft Tolga) üretir: assets/sounds/<sınıf>.wav (cümle)
# ve <sınıf>_kisa.wav (kısa biçim; arkada başka uyarı beklerken çalınır).
# Cümleler lib/alerts.dart içindeki `signs` kataloğundan okunur. Kendi sesini kaydedersen aynı adla üzerine yaz.
# Çalıştırma (mobile/ klasöründe):  .\tool\sesleri_uret.ps1
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
[void][Windows.Media.SpeechSynthesis.SpeechSynthesizer, Windows.Media.SpeechSynthesis, ContentType = WindowsRuntime]
[void][Windows.Storage.Streams.DataReader, Windows.Storage.Streams, ContentType = WindowsRuntime]
$asTask = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' } | Select-Object -First 1
function Await($op, [type]$t) { $task = $asTask.MakeGenericMethod($t).Invoke($null, @($op)); $task.Wait(); $task.Result }

$root = Split-Path $PSScriptRoot -Parent
$out = Join-Path $root 'assets\sounds'
New-Item -ItemType Directory -Force $out | Out-Null
$synth = [Windows.Media.SpeechSynthesis.SpeechSynthesizer]::new()
$synth.Voice = [Windows.Media.SpeechSynthesis.SpeechSynthesizer]::AllVoices | Where-Object Language -eq 'tr-TR' | Select-Object -First 1
if (-not $synth.Voice) { throw 'Türkçe ses (tr-TR) kurulu değil.' }

$catalog = Get-Content (Join-Path $root 'lib\alerts.dart') -Raw -Encoding UTF8
foreach ($m in [regex]::Matches($catalog, "'(\w+)': \(text: '([^']+)', short: '([^']+)'")) {
    foreach ($pair in @(@("$($m.Groups[1].Value).wav", $m.Groups[2].Value), @("$($m.Groups[1].Value)_kisa.wav", $m.Groups[3].Value))) {
        $stream = Await ($synth.SynthesizeTextToStreamAsync($pair[1])) ([Windows.Media.SpeechSynthesis.SpeechSynthesisStream])
        $reader = [Windows.Storage.Streams.DataReader]::new($stream.GetInputStreamAt(0))
        [void](Await ($reader.LoadAsync([uint32]$stream.Size)) ([uint32]))
        $bytes = New-Object byte[] $stream.Size
        $reader.ReadBytes($bytes)
        [IO.File]::WriteAllBytes((Join-Path $out $pair[0]), $bytes)
        "$($pair[0])  <- $($pair[1])"
    }
}
