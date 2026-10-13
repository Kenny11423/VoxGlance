"""Tests for AudioRingBuffer and SileroVAD."""

import numpy as np
from src.audio.capture import AudioRingBuffer
from src.audio.vad import SileroVAD


def test_audio_ring_buffer():
    buf = AudioRingBuffer(sample_rate=16000, buffer_duration_sec=1.0)
    assert len(buf) == 0

    # Append 8000 samples (0.5s)
    samples = np.ones(8000, dtype=np.float32) * 0.5
    buf.append(samples)
    assert len(buf) == 8000

    # Append another 12000 samples (total 20000 > max 16000)
    samples2 = np.ones(12000, dtype=np.float32) * 0.8
    buf.append(samples2)
    # Length capped at 16000
    assert len(buf) == 16000

    # Get latest 4000 samples
    latest = buf.get_latest(4000)
    assert len(latest) == 4000
    assert np.allclose(latest, 0.8)

    buf.clear()
    assert len(buf) == 0


def test_vad_silence_detection():
    vad = SileroVAD()

    # Pure silence (all zeros)
    silence = np.zeros(1600, dtype=np.float32)  # 100ms at 16kHz
    result = vad.is_speech_chunk(silence)
    assert result.is_speech is False
    assert result.rms_energy == 0.0


def test_vad_speech_detection():
    vad = SileroVAD()

    # Generate synthetic speech-like signal (sine wave at 300Hz with audible amplitude)
    t = np.linspace(0, 0.1, 1600, endpoint=False)
    synthetic_speech = 0.2 * np.sin(2 * np.pi * 300 * t).astype(np.float32)

    result = vad.is_speech_chunk(synthetic_speech)
    assert result.is_speech is True
    assert result.confidence > 0.5
    assert result.rms_energy > 0.015
