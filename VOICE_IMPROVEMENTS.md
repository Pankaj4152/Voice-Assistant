# 🎙️ Voice Input Improvements Guide

## What's Been Improved

Your voice assistant's listening system has been significantly improved to handle real-world conditions better:

### 1. **Enhanced VAD (Voice Activity Detection)**
- **Better default sensitivity** (aggressiveness lowered to 1 from 2)
- **Noise floor calibration** - automatically adapts to your environment on startup
- **Noise suppression** - filters out low-amplitude background noise
- **Improved thresholds** - better balance between catching speech and filtering noise

### 2. **Better ASR (Speech Recognition)**
- **Audio preprocessing** - removes DC offset and emphasizes speech frequencies
- **Retry logic** - automatically retries transcription on failures
- **Better error handling** - provides clearer error messages
- **GPU fallback** - gracefully handles GPU errors

### 3. **New Tools & Configuration**

#### Audio Debugging Tool
Test and diagnose your microphone setup:

```bash
# List all available microphones
python -m voice.debug_audio list

# Test microphone input (5 seconds)
python -m voice.debug_audio test

# Calibrate noise floor
python -m voice.debug_audio calibrate
```

#### Voice Configuration
Customize voice settings in `voice/config.py` or set environment variables:

```bash
# Use sensitive mode (catches more, filters less)
set VOICE_CONFIG=sensitive

# Use robust mode (filters more, cleaner)
set VOICE_CONFIG=robust

# Use fast mode (lower latency)
set VOICE_CONFIG=fast
```

### Preset Modes

**Sensitive Mode** - Use if:
- Commands are missed
- You have a quiet voice
- In a quiet environment
```
aggressiveness: 0 (minimal filtering)
wake_word_sensitivity: 0.75 (higher)
```

**Robust Mode** - Use if:
- Too many false activations
- Background noise is present
- You want cleaner input
```
aggressiveness: 2 (more filtering)
wake_word_sensitivity: 0.55 (lower)
```

**Fast Mode** - Use if:
- You want lower latency
- You have a slower machine
```
model: tiny.en (smallest/fastest)
```

## Quick Start

### 1. **Test Your Microphone Setup**

```bash
# First, see what microphones are available
python -m voice.debug_audio list

# Test the default microphone
python -m voice.debug_audio test

# Check for excessive background noise
python -m voice.debug_audio calibrate
```

### 2. **Run the Voice Assistant**

```bash
# Default settings
python voice_server.py

# With sensitive mode for better detection
set VOICE_CONFIG=sensitive
python voice_server.py
```

### 3. **Configuration Tuning**

Edit `voice/config.py` to customize:
- **aggressiveness**: 0-3 (lower = more sensitive)
- **wake_sensitivity**: 0.0-1.0 (higher = more sensitive)
- **min_segment_ms**: minimum audio length before processing
- **start_trigger_ratio**: how quickly to start listening

## Troubleshooting

### "Not listening properly" / Commands are missed

**Try:**
```bash
# Test microphone first
python -m voice.debug_audio test

# Use sensitive mode
set VOICE_CONFIG=sensitive
python voice_server.py
```

**If still not working:**
- Lower `aggressiveness` to 0 in config
- Increase `wake_word_sensitivity` to 0.75
- Check if microphone is working: `python -m voice.debug_audio test`

### False activations / Too many wrong detections

**Try:**
```bash
# Use robust mode
set VOICE_CONFIG=robust
python voice_server.py
```

**If still noisy:**
- Increase `aggressiveness` to 2-3
- Lower `wake_word_sensitivity` to 0.55
- Reduce background noise in your environment

### Low audio level / Sound not being picked up

**Try:**
1. Check microphone: `python -m voice.debug_audio test`
2. Look at RMS level - should be > 0.05
3. If low:
   - Check microphone connection
   - Increase system volume
   - Check microphone default device
   - Try `python -m voice.debug_audio list` to select different device

### Slow/Delayed responses

**Try:**
```bash
# Use fast mode
set VOICE_CONFIG=fast
python voice_server.py
```

**Or manually in config:**
- Set ASR `model_size: "tiny.en"` for w
- Set ASR `model_size: "small.en"` for balanced
- Test with smaller model first

## Architecture

```
┌─────────────┐
│ Microphone  │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────┐
│ ⏐ VAD (Voice Activity)      │  ← Detects speech vs silence
│   - Noise suppression       │    using WebRTC VAD
│   - Noise floor calibration │
└──────┬──────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│ 🎙️ Wake Word Detector        │  ← Detects "jarvis" keyword
│   - Porcupine (offline)      │    using Picovoice
└──────┬───────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│ 🧠 ASR (Speech -> Text)      │  ← Transcribes speech
│   - Whisper (offline)        │    using OpenAI Whisper
│   - Preprocessing            │
│   - Audio fallback           │
└──────┬───────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│ 🔤 Intent Classifier         │  ← Determines what to do
│   - Rule-based + Gemini LLM  │
└──────┬───────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│ ⚙️ Action Engine             │  ← Executes the action
│   - OS commands, browser,etc │
└──────────────────────────────┘
```

## File Locations

- **VAD**: `voice/vad.py` - Voice activation detection
- **ASR**: `voice/asr.py` - Speech recognition
- **Wake Word**: `voice/wake_word.py` - Keyword detection
- **Config**: `voice/config.py` - Tunable settings
- **Debug Tool**: `voice/debug_audio.py` - Testing tool
- **Pipeline**: `voice_server.py` - Main orchestration

## Parameters Reference

### VAD Parameters

```python
aggressiveness: 0-3           # 0=sensitive, 3=strict filtering
start_trigger_ratio: 0.0-1.0 # How quick to start listening (lower=quicker)
end_trigger_ratio: 0.0-1.0   # How quick to stop listening (lower=quicker)
min_segment_ms: int          # Minimum audio segment length
enable_noise_suppression: bool
```

### Wake Word Parameters

```python
sensitivity: 0.0-1.0         # 0=conservative, 1.0=aggressive
detection_cooldown_sec: float # Min time between detections
```

### ASR Parameters

```python
model_size: "tiny.en" | "base.en" | "small.en" | "medium.en"
             # tiny = fast, medium = accurate but slower
retry_attempts: int          # How many times to retry on failure
```

## Tips for Best Performance

1. **Use in quiet environment** first to get baseline
2. **Test microphone** before adjusting software settings
3. **Start with default**, then tweak based on results
4. **Use sensitive mode** if commands are missed often
5. **Use robust mode** if getting false activations
6. **Monitor the console** output for clues on what's happening

## Next Steps

- Try different microphones with `debug_audio.py`
- Adjust `VOICE_CONFIG` mode based on your environment
- Fine-tune individual parameters in `voice/config.py`
- Check logs for specific error messages

Need help? Check the console output for detailed timing and error messages!
