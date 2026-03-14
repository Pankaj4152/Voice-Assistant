"""
voice/debug_audio.py
────────────────────
Audio debugging tool to diagnose microphone and audio issues.

Usage:
    python -m voice.debug_audio list           # List available microphones
    python -m voice.debug_audio test           # Test current microphone
    python -m voice.debug_audio calibrate      # Calibrate noise floor
"""

import sounddevice as sd
import numpy as np
import sys
import time


def list_devices():
    """List all available audio input devices."""
    print("\n" + "="*70)
    print("📻 AVAILABLE AUDIO INPUT DEVICES")
    print("="*70)
    devices = sd.query_devices()
    
    if isinstance(devices, dict):
        # Single device
        devices = [devices]
    
    input_devices = [d for d in devices if d['max_input_channels'] > 0]
    
    if not input_devices:
        print("❌ No input devices found!")
        return
    
    for i, device in enumerate(input_devices):
        is_default = " ← DEFAULT" if device['name'] == sd.query_devices(kind='input')['name'] else ""
        print(f"\n  [{i}] {device['name']}{is_default}")
        print(f"      Sample Rate: {device['default_samplerate']} Hz")
        print(f"      Input Channels: {device['max_input_channels']}")
        print(f"      Latency: {device['default_low_input_latency']*1000:.1f}ms (low)")


def test_microphone(duration=5, device=None):
    """Test microphone input and display audio levels."""
    print("\n" + "="*70)
    print(f"🎙️ MICROPHONE TEST ({duration}s)")
    print("="*70)
    
    try:
        sample_rate = 16000
        print(f"\nRecording at {sample_rate}Hz...")
        print("Speak normally or make noise to test...\n")
        
        audio = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype="float32",
            device=device
        )
        
        # Show recording progress
        for i in range(duration):
            time.sleep(1)
            samples_recorded = min((i + 1) * sample_rate, len(audio))
            progress = (samples_recorded / len(audio)) * 20
            bar = "█" * int(progress) + "░" * (20 - int(progress))
            print(f"  [{bar}] {samples_recorded // sample_rate}s")
        
        sd.wait()
        audio = np.squeeze(audio)
        
        # Analyze
        rms = np.sqrt(np.mean(audio ** 2))
        peak = np.abs(audio).max()
        
        print(f"\n✓ Recording complete!")
        print(f"  RMS Level: {rms:.4f} ({rms*100:.1f}%)")
        print(f"  Peak Level: {peak:.4f} ({peak*100:.1f}%)")
        
        if rms < 0.01:
            print("    WARNING: Very low audio level - check microphone connection or volume")
        elif rms < 0.05:
            print("    WARNING: Low audio level - may cause recognition issues")
        elif rms > 0.9:
            print("    WARNING: Audio very loud - may be clipping")
        else:
            print("  ✓ Audio level looks good!")
        
        # Energy distribution
        energy_recent = np.sqrt(np.mean(audio[-2000:] ** 2))
        print(f"  Recent energy (last 0.125s): {energy_recent:.4f}")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def calibrate_noise_floor(duration=3):
    """Calibrate noise floor by analyzing silent audio."""
    print("\n" + "="*70)
    print(f"🔊 NOISE FLOOR CALIBRATION ({duration}s)")
    print("="*70)
    
    try:
        sample_rate = 16000
        frame_size = 480  # 30ms at 16kHz
        
        print(f"\nKeep quiet while we measure background noise...")
        print(f"Recording {duration}s of silence...\n")
        
        audio = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype="float32"
        )
        
        # Monitor in real time
        for i in range(duration):
            time.sleep(1)
            print(f"  {'.' * (i+1)}", end='\r')
        
        sd.wait()
        audio = np.squeeze(audio)
        
        # Analyze frames
        rms_values = []
        for i in range(0, len(audio) - frame_size, frame_size):
            frame = audio[i:i+frame_size]
            rms = np.sqrt(np.mean(frame ** 2))
            rms_values.append(rms)
        
        noise_floor = np.percentile(rms_values, 75)
        
        print(f"\n✓ Calibration complete!")
        print(f"  Noise Floor (75th percentile): {noise_floor:.4f}")
        print(f"  Recommended threshold: {noise_floor * 1.5:.4f}")
        print(f"  Frame RMS range: {min(rms_values):.4f} - {max(rms_values):.4f}")
        
        if noise_floor > 0.05:
            print(f"    High background noise detected")
            print(f"     Consider: Reducing background noise, using a better microphone")
        
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python debug_audio.py [list|test|calibrate]")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "list":
        list_devices()
    elif command == "test":
        device = int(sys.argv[2]) if len(sys.argv) > 2 else None
        test_microphone(device=device)
    elif command == "calibrate":
        calibrate_noise_floor()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
