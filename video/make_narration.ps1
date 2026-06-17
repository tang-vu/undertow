# Generate per-scene narration WAVs with Windows SAPI (offline, no API). Voice: Zira (en-US).
Add-Type -AssemblyName System.Speech
$lines = @(
  "Undertow. A CoinMarketCap agent skill that trades the gap between what the crowd feels, and how it is positioned.",
  "On the surface, Fear and Greed, and social hype. Underneath, crowded leverage, and price stretched from trend. When they diverge, conditioned on market regime, the tide turns.",
  "Undertow reads both layers into a positioning stress score and a market regime, then emits a full strategy spec. Stance, sizing, and risk, as J SON.",
  "Backtested out of sample on five majors since twenty nineteen, with trading costs and slippage modeled.",
  "The result. Bitcoin like returns, with less than half the drawdown. Nearly double the Sharpe over the full cycle. And it laps the naive Fear and Greed baseline.",
  "And it is agent native. Live data over M C P. Pay per request over x four oh two, with a real four oh two challenge. And it orchestrates CoinMarketCap's own Skill Hub services.",
  "Reproducible. Honest. Agent native. Undertow."
)
$dir = Join-Path $PSScriptRoot "audio"
New-Item -ItemType Directory -Force -Path $dir | Out-Null
for ($i = 0; $i -lt $lines.Count; $i++) {
  $s = New-Object System.Speech.Synthesis.SpeechSynthesizer
  $s.SelectVoice("Microsoft Zira Desktop")
  $s.Rate = -1
  $s.Volume = 100
  $out = Join-Path $dir ("line_{0:00}.wav" -f ($i + 1))
  $s.SetOutputToWaveFile($out)
  $s.Speak($lines[$i])
  $s.Dispose()
  Write-Output ("wrote " + $out)
}
