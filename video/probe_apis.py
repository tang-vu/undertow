"""Probe the MiMo TTS and Qwen image APIs (keys read from env; never hardcoded).

Run:  MIMO_API_KEY=... MIMO_BASE=... QWEN_API_KEY=... QWEN_BASE=... python video/probe_apis.py
"""
import os, json, requests

OUT = os.path.dirname(os.path.abspath(__file__))


def probe_mimo_tts():
    base, key = os.environ.get("MIMO_BASE"), os.environ.get("MIMO_API_KEY")
    if not key:
        print("MiMo: no key"); return
    url = base.rstrip("/") + "/audio/speech"
    body = {"model": "mimo-v2.5-tts", "input": "Undertow trades the gap between sentiment and positioning.",
            "voice": "default", "response_format": "mp3"}
    try:
        r = requests.post(url, headers={"Authorization": f"Bearer {key}"}, json=body, timeout=60)
        ct = r.headers.get("Content-Type", "")
        print(f"MiMo TTS {url} -> {r.status_code} ct={ct} len={len(r.content)}")
        if r.status_code == 200 and ("audio" in ct or len(r.content) > 2000):
            open(os.path.join(OUT, "audio", "_probe.mp3"), "wb").write(r.content)
            print("  saved audio/_probe.mp3 OK")
        else:
            print("  body:", r.text[:500])
    except Exception as e:
        print("MiMo TTS error:", e)


def probe_qwen_image():
    base, key = os.environ.get("QWEN_BASE"), os.environ.get("QWEN_API_KEY")
    if not key:
        print("Qwen: no key"); return
    url = base.rstrip("/") + "/images/generations"
    body = {"model": "qwen-image-2.0", "prompt": "deep dark ocean undercurrent, abstract teal waves, cinematic",
            "size": "1024x1024", "n": 1}
    try:
        r = requests.post(url, headers={"Authorization": f"Bearer {key}"}, json=body, timeout=120)
        print(f"Qwen image {url} -> {r.status_code} len={len(r.content)}")
        if r.status_code == 200:
            d = r.json()
            print("  keys:", list(d.keys()))
            print("  sample:", json.dumps(d)[:300])
        else:
            print("  body:", r.text[:500])
    except Exception as e:
        print("Qwen image error:", e)


if __name__ == "__main__":
    probe_mimo_tts()
    print("-" * 50)
    probe_qwen_image()
