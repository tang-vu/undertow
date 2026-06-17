"""Neural narration via edge-tts (Microsoft Edge online voices — free, no API key).

Male voice with deliberate pacing: each scene is split into phrases, each phrase synthesized at a
chosen rate, then concatenated with timed silences for emphasis ("nhấn nhá"). Outputs the same
video/audio/line_XX.wav files that build_video.py consumes.

    python video/make_narration_edge.py
"""
from __future__ import annotations
import os, asyncio, subprocess, tempfile
import edge_tts

ROOT = os.path.dirname(os.path.abspath(__file__))
AUD = os.path.join(ROOT, "audio")
VOICE = "en-US-AndrewNeural"          # warm, confident; swap to GuyNeural/ChristopherNeural if preferred

# scene -> list of (phrase, rate, pause_after_ms). Slower + longer pauses = more dramatic.
SCENES = [
    [("Undertow.", "-8%", 600),
     ("A CoinMarketCap agent skill that trades the gap between what the crowd feels", "-4%", 250),
     ("and how it's positioned.", "-9%", 200)],

    [("On the surface — Fear and Greed, social hype.", "-4%", 450),
     ("Underneath — crowded leverage, and price stretched from trend.", "-4%", 450),
     ("When they diverge, conditioned on regime,", "-6%", 320),
     ("the tide turns.", "-14%", 200)],

    [("Undertow reads both layers into a single positioning-stress score, and a market regime.", "-4%", 350),
     ("Then it emits a full strategy spec — stance, sizing, and risk — as JSON.", "-4%", 200)],

    [("Backtested out of sample, on five majors, since twenty nineteen.", "-4%", 300),
     ("Trading costs, and slippage — modeled.", "-8%", 200)],

    [("The result?", "-10%", 500),
     ("Bitcoin-like returns,", "-5%", 250),
     ("with less than half the drawdown.", "-9%", 450),
     ("Nearly double the Sharpe over the full cycle.", "-4%", 350),
     ("And it laps the naive Fear and Greed baseline.", "-4%", 200)],

    [("And it's agent-native.", "-5%", 400),
     ("Live data over M C P.", "-4%", 300),
     ("Pay-per-request over x four-oh-two — with a real four-oh-two challenge.", "-4%", 350),
     ("And it orchestrates CoinMarketCap's own Skill Hub services.", "-4%", 200)],

    [("Reproducible.", "-10%", 480),
     ("Honest.", "-10%", 480),
     ("Agent-native.", "-10%", 560),
     ("Undertow.", "-13%", 200)],
]


async def synth(text: str, rate: str, path: str, tries: int = 5):
    """edge-tts occasionally returns NoAudioReceived transiently — retry with backoff."""
    for attempt in range(tries):
        try:
            await edge_tts.Communicate(text, VOICE, rate=rate).save(path)
            if os.path.getsize(path) > 800:
                return
        except Exception as e:
            if attempt == tries - 1:
                raise
        await asyncio.sleep(1.0 + attempt)
    raise RuntimeError(f"no audio for: {text!r}")


def concat_scene(pieces: list[tuple[str, int]], out_wav: str):
    """pieces = [(mp3_path, pause_after_ms), ...] -> single wav with timed silences between."""
    inputs, labels, idx = [], [], 0
    for mp3, pause in pieces:
        inputs += ["-i", mp3]; labels.append(f"[{idx}:a]"); idx += 1
        if pause > 0:
            inputs += ["-f", "lavfi", "-t", f"{pause/1000:.3f}", "-i", "anullsrc=r=44100:cl=stereo"]
            labels.append(f"[{idx}:a]"); idx += 1
    flt = "".join(labels) + f"concat=n={idx}:v=0:a=1[a]"
    subprocess.run(["ffmpeg", "-y", *inputs, "-filter_complex", flt, "-map", "[a]",
                    "-ar", "44100", "-ac", "2", out_wav],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


async def main():
    os.makedirs(AUD, exist_ok=True)
    tmp = tempfile.mkdtemp()
    for si, scene in enumerate(SCENES, 1):
        pieces = []
        for pi, (text, rate, pause) in enumerate(scene):
            mp3 = os.path.join(tmp, f"s{si}_{pi}.mp3")
            await synth(text, rate, mp3)
            pieces.append((mp3, pause))
            await asyncio.sleep(0.3)
        out = os.path.join(AUD, f"line_{si:02d}.wav")
        concat_scene(pieces, out)
        print(f"  scene {si}: {len(scene)} phrases -> {os.path.basename(out)}")


if __name__ == "__main__":
    asyncio.run(main())
    print(f"voice = {VOICE}")
