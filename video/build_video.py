"""Assemble the Undertow demo MP4 from scene PNGs + SAPI narration, with a soft ocean ambience bed.

Pipeline (all local, ffmpeg only):
  1. per scene: still image for (narration + pad)s, fade in/out, narration delayed 0.4s.
  2. concat scenes -> core (video + voice).
  3. mix a brown-noise "ocean" bed (lowpassed + slow tremolo) low under the voice; loudnorm.
  -> video/undertow_demo.mp4

    python video/build_video.py
"""
from __future__ import annotations
import os, subprocess, json

ROOT = os.path.dirname(os.path.abspath(__file__))
SCN = os.path.join(ROOT, "scenes")
AUD = os.path.join(ROOT, "audio")
TMP = os.path.join(ROOT, "_tmp")
OUT = os.path.join(ROOT, "undertow_demo.mp4")
PAD = 1.0           # extra seconds per scene (0.4 lead + 0.6 tail)
FPS = 30
N = 7


def dur(path: str) -> float:
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path])
    return float(out.strip())


def run(args: list):
    subprocess.run(args, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main():
    os.makedirs(TMP, exist_ok=True)
    total = 0.0
    clips = []
    for i in range(1, N + 1):
        scene = os.path.join(SCN, f"scene_{i:02d}.png")
        voice = os.path.join(AUD, f"line_{i:02d}.wav")
        d = round(dur(voice) + PAD, 3)
        total += d
        clip = os.path.join(TMP, f"clip_{i:02d}.mp4")
        vf = (f"scale=1920:1080:force_original_aspect_ratio=decrease,"
              f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2,format=yuv420p,setsar=1,"
              f"fade=t=in:st=0:d=0.4,fade=t=out:st={d-0.4:.3f}:d=0.4")
        af = "adelay=400:all=1,apad"
        run(["ffmpeg", "-y", "-loop", "1", "-i", scene, "-i", voice,
             "-filter_complex", f"[0:v]{vf}[v];[1:a]{af}[a]",
             "-map", "[v]", "-map", "[a]", "-t", f"{d:.3f}", "-r", str(FPS),
             "-c:v", "libx264", "-preset", "medium", "-crf", "20",
             "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "44100", "-b:a", "192k", clip])
        clips.append(clip)
        print(f"  scene {i}: {d:.2f}s")

    listf = os.path.join(TMP, "concat.txt")
    with open(listf, "w") as f:
        for c in clips:
            f.write(f"file '{c.replace(os.sep, '/')}'\n")
    core = os.path.join(TMP, "core.mp4")
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", listf, "-c", "copy", core])

    # Ocean ambience bed: brown noise -> band-limited rush + slow swell, low under the voice.
    bed = (f"anoisesrc=color=brown:amplitude=0.9:duration={total:.3f}:sample_rate=44100,"
           f"lowpass=f=620,highpass=f=90,tremolo=f=0.1:d=0.75,volume=0.06")
    run(["ffmpeg", "-y", "-i", core, "-filter_complex",
         f"{bed}[bed];[0:a][bed]amix=inputs=2:duration=first:weights=1 0.5,"
         f"loudnorm=I=-16:TP=-1.5:LRA=11[a]",
         "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", OUT])

    print(f"\nTOTAL {total:.1f}s -> {OUT} ({os.path.getsize(OUT)//1024} KB)")


if __name__ == "__main__":
    main()
