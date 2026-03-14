"""
voice/config.py
───────────────
Voice system configuration for easy parameter tuning.

Edit these values to improve voice input performance:
- Lower aggressiveness for better wake word detection sensitivity
- Adjust VAD thresholds for your environment  
- Modify ASR settings for different microphones/conditions
"""

from dataclasses import dataclass, field
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class VADConfig:
    """Voice Activity Detection settings."""
    # 0-3: 0 = least filtering (catch more), 3 = most filtering (strict)
    # Lower = more sensitive to voice, but may pick up background noise
    aggressiveness: int = 1
    
    # Frame size (ms): 10, 20, or 30
    frame_duration_ms: int = 30
    
    # Silence padding after speech detection (ms)
    padding_duration_ms: int = 500
    
    # Minimum speech segment length (ms) before sending upstream
    # Lower = catch short commands, Higher = filter out noise
    min_segment_ms: int = 350
    
    # Ratio of voiced frames to trigger recording start (0.0-1.0)
    # Lower = starts recording sooner, Higher = waits for more confident speech
    start_trigger_ratio: float = 0.5
    
    # Ratio of unvoiced frames to end recording (0.0-1.0)
    # Lower = stops quicker, Higher = waits longer for pauses
    end_trigger_ratio: float = 0.7
    
    # Enable noise suppression (removes low-amplitude audio)
    enable_noise_suppression: bool = True


@dataclass(frozen=True)
class ASRConfig:
    """Automatic Speech Recognition settings."""
    # Model size: tiny.en, base.en, small.en, medium.en
    # Larger = better accuracy but slower & uses more memory
    model_size: str = "base.en"
    
    # Language: en, es, fr, de, it, pt, ja, zh, etc.
    language: str = "en"
    
    # Number of transcription retry attempts on failure
    retry_attempts: int = 2
    
    # Sample rate (should be 16000 for Whisper)
    sample_rate: int = 16000
    
    # Duration of fixed recording (for standalone mode)
    duration: int = 5


@dataclass(frozen=True)
class WakeWordConfig:
    """Wake word detection settings."""
    # Built-in keywords: jarvis, alexa, hey google, hey siri, ok google, etc.
    # Or custom keyword path for .ppn files
    keyword: str = "jarvis"
    keyword_path: Optional[str] = None
    
    # Sensitivity (0.0-1.0): 0 = conservative, 1.0 = aggressive
    # Higher = more false positives, Lower = misses wake words
    sensitivity: float = 0.65
    
    # Cooldown between wake word detections (seconds)
    # Prevents rapid multiple detections of single utterance
    detection_cooldown_sec: float = 0.8


@dataclass(frozen=True)
class PipelineConfig:
    """Full pipeline settings."""
    vad: VADConfig = field(default_factory=VADConfig)
    asr: ASRConfig = field(default_factory=ASRConfig)
    wake_word: WakeWordConfig = field(default_factory=WakeWordConfig)
    
    # Overall sample rate (must be 16000 for compatibility)
    sample_rate: int = 16000
    
    # Follow-up command window (seconds)
    # Time to wait for follow-up commands after first command
    followup_window_sec: int = 20
    
    # Enable debug logging
    debug: bool = False


# ──── PRESET CONFIGURATIONS ────────────────────────────────────────────────

@dataclass(frozen=True)
class SensitiveConfig(PipelineConfig):
    """
    Sensitive mode: catch more, filter less.
    Use when voice input misses commands or you have a quiet voice.
    """
    vad: VADConfig = field(default_factory=lambda: VADConfig(
        aggressiveness=0,  # Least filtering
        start_trigger_ratio=0.3,  # Start sooner
        end_trigger_ratio=0.6,  # End sooner
        min_segment_ms=200,  # Accept shorter segments
    ))
    wake_word: WakeWordConfig = field(default_factory=lambda: WakeWordConfig(
        sensitivity=0.75,  # More sensitive
    ))


@dataclass(frozen=True)
class RobustConfig(PipelineConfig):
    """
    Robust mode: filter more, reduce noise.
    Use when you have background noise or false positives.
    """
    vad: VADConfig = field(default_factory=lambda: VADConfig(
        aggressiveness=2,  # More filtering
        start_trigger_ratio=0.7,  # Wait for confident speech
        end_trigger_ratio=0.8,  # Wait longer for pauses
        min_segment_ms=500,  # Longer minimum segments
    ))
    wake_word: WakeWordConfig = field(default_factory=lambda: WakeWordConfig(
        sensitivity=0.55,  # Less sensitive
    ))


@dataclass(frozen=True)
class FastConfig(PipelineConfig):
    """
    Fast mode: smaller model, faster recognition.
    Use for lower latency, though accuracy may suffer.
    """
    asr: ASRConfig = field(default_factory=lambda: ASRConfig(
        model_size="tiny.en",  # Fastest
    ))


# ──── ENVIRONMENT-BASED CONFIG ─────────────────────────────────────────────

def get_config() -> PipelineConfig:
    """
    Get configuration based on environment variable or return default.
    
    Set VOICE_CONFIG environment variable to:
    - "sensitive" for sensitive mode
    - "robust" for robust mode
    - "fast" for fast mode
    - default PipelineConfig if not set
    """
    mode = os.getenv("VOICE_CONFIG", "default").lower()
    
    if mode == "sensitive":
        return SensitiveConfig()
    elif mode == "robust":
        return RobustConfig()
    elif mode == "fast":
        return FastConfig()
    else:
        return PipelineConfig()


# Global singleton
voice_config = get_config()
