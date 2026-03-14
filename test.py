"""
Voice-to-Text Test Tool
========================
Bolo aur dekho ki ASR kya sun raha hai.

Controls:
  Enter       → Record & transcribe
  d <seconds> → Duration change (e.g. "d 8" for 8 seconds)
  h           → Show history
  c           → Clear history
  q           → Quit
"""

import time
import numpy as np
import sounddevice as sd



from voice.asr import WhisperASR
from telemetry.logger import TelemetryLogger

# ── Config ───────────────────────────────────────────────────────────────────
SAMPLE_RATE = 16000
DEFAULT_DURATION = 5   # seconds
MODEL_SIZE = "small.en"
# ─────────────────────────────────────────────────────────────────────────────


def volume_bar(rms: float, width: int = 30) -> str:
    """Return a visual volume bar for the given RMS level."""
    filled = int(min(rms * width * 10, width))
    bar = "█" * filled + "░" * (width - filled)
    label = "LOW " if rms < 0.01 else ("OK  " if rms < 0.05 else "HIGH")
    return f"[{bar}] {label} ({rms:.4f})"


def record_with_stats(duration: int) -> tuple:
    """Record audio and return (audio_array, stats_dict)."""
    print(f"\n[🎙️  RECORDING] Bol do! ({duration}s baki hain...)")
    audio = sd.rec(
        int(duration * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
    )
    sd.wait()
    audio = np.squeeze(audio)

    rms = float(np.sqrt(np.mean(audio ** 2)))
    peak = float(np.abs(audio).max())
    silence_ratio = float(np.mean(np.abs(audio) < 0.01))

    stats = {
        "rms": rms,
        "peak": peak,
        "silence_ratio": silence_ratio,
        "samples": len(audio),
        "duration_sec": len(audio) / SAMPLE_RATE,
    }
    return audio, stats


def print_stats(stats: dict):
    print(f"  Volume  : {volume_bar(stats['rms'])}")
    print(f"  Peak    : {stats['peak']:.4f}")
    print(f"  Silence : {stats['silence_ratio']*100:.1f}% of audio is near-silent")
    if stats["silence_ratio"] > 0.9:
        print("  ⚠️  Mic se almost koi awaaz nahi aayi — mic check karo!")
    elif stats["rms"] < 0.005:
        print("  ⚠️  Volume bahut kam hai — mic ke paas bolo ya gain badhao.")


def main():
    logger = TelemetryLogger()
    print("[INIT] Whisper model load ho raha hai...")
    asr = WhisperASR(logger=logger, model_size=MODEL_SIZE,
                     sample_rate=SAMPLE_RATE, duration=DEFAULT_DURATION)

    duration = DEFAULT_DURATION
    history = []
    count = 0

    print("\n" + "═" * 60)
    print("  VOICE-TO-TEXT TESTER  |  Enter dabao aur bolo")
    print("═" * 60)
    print("  Commands: [Enter]=record  [d N]=duration  [h]=history  [q]=quit")
    print("═" * 60 + "\n")

    while True:
        try:
            raw = input("▶  Command (Enter to record): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n[EXIT] Bye!")
            break

        # ── Quit ──────────────────────────────────────────────────────────
        if raw == "q":
            print("[EXIT] Bye!")
            break

        # ── Show history ──────────────────────────────────────────────────
        if raw == "h":
            if not history:
                print("  (history empty)")
            else:
                print("\n── HISTORY ──────────────────────────")
                for i, h in enumerate(history, 1):
                    status = "✓" if h["text"] else "✗ (nothing heard)"
                    print(f"  {i:2}. [{h['duration']}s | {h['time_taken']:.1f}s] {status}  → {h['text'] or '—'}")
                print("─────────────────────────────────────\n")
            continue

        # ── Clear history ─────────────────────────────────────────────────
        if raw == "c":
            history.clear()
            count = 0
            print("  [History cleared]")
            continue

        # ── Change duration ───────────────────────────────────────────────
        if raw.startswith("d "):
            parts = raw.split()
            if len(parts) == 2 and parts[1].isdigit():
                duration = max(1, min(30, int(parts[1])))
                print(f"  [Duration set to {duration}s]")
            else:
                print("  Usage: d <seconds>  (e.g. d 8)")
            continue

        # ── Record & transcribe ───────────────────────────────────────────
        count += 1
        print(f"\n{'─'*60}")
        print(f"  Test #{count}  |  Duration: {duration}s")
        print(f"{'─'*60}")

        try:
            audio, stats = record_with_stats(duration)

            print("\n[📊 AUDIO STATS]")
            print_stats(stats)

            print("\n[🔄 TRANSCRIBING] Processing...")
            t0 = time.perf_counter()
            text = asr.transcribe_from_array(audio)
            elapsed = time.perf_counter() - t0

            print(f"\n[⏱  Time taken] {elapsed:.2f}s")
            print("─" * 60)
            if text:
                print(f"  ✅ SUNA  : \"{text}\"")
            else:
                print("  ❌ Kuch nahi suna (silent audio ya hallucination filter ne hata diya)")
            print("─" * 60 + "\n")

            history.append({
                "text": text,
                "duration": duration,
                "time_taken": elapsed,
                "rms": stats["rms"],
            })

        except Exception as e:
            print(f"\n  ❌ Error: {e}\n")


if __name__ == "__main__":
    main()

