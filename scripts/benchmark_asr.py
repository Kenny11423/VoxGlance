#!/usr/bin/env python3
"""Benchmark script for Faster-Whisper INT8 latency and VRAM usage."""

import argparse
import sys
import time
from pathlib import Path
import numpy as np

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.config import load_config
from src.core.memory import MemoryController
from src.audio.asr import FasterWhisperEngine


def run_benchmark(model_size: str = "tiny", device: str = "cuda", compute_type: str = "int8_float16", rounds: int = 5):
    print("=" * 65)
    print(f" Faster-Whisper Benchmark | Model: {model_size} | Device: {device} | Type: {compute_type}")
    print("=" * 65)

    controller = MemoryController()
    initial_vram = controller.get_vram_info()
    print(f"Initial VRAM Used: {initial_vram.used_mb:.1f} MB (Cap: {controller.target_vram_mb} MB)")

    # Load model
    start_load = time.time()
    engine = FasterWhisperEngine(
        model_size=model_size,
        device=device,
        compute_type=compute_type,
        memory_controller=controller,
    )
    load_duration = time.time() - start_load
    after_load_vram = controller.get_vram_info()
    model_vram = after_load_vram.used_mb - initial_vram.used_mb

    print(f"Model Load Time: {load_duration:.2f}s")
    print(f"Post-load VRAM Used: {after_load_vram.used_mb:.1f} MB (Delta: +{model_vram:.1f} MB)")
    print("-" * 65)

    # Synthetic 2-second audio (16kHz float32 mono)
    sample_rate = 16000
    duration_sec = 2.0
    t = np.linspace(0, duration_sec, int(sample_rate * duration_sec), endpoint=False)
    synthetic_audio = 0.3 * np.sin(2 * np.pi * 440 * t).astype(np.float32)

    latencies = []
    for r in range(rounds):
        t0 = time.time()
        tokens = engine.transcribe(synthetic_audio)
        dt_ms = (time.time() - t0) * 1000.0
        latencies.append(dt_ms)
        token_count = len(tokens)
        print(f"Round {r + 1}/{rounds} | Latency: {dt_ms:.1f}ms | Tokens: {token_count}")

    avg_latency = np.mean(latencies)
    peak_vram = controller.get_vram_info()

    print("=" * 65)
    print(f"Results Summary:")
    print(f"  Average Inference Latency (2s audio): {avg_latency:.1f} ms")
    print(f"  Peak VRAM: {peak_vram.used_mb:.1f} MB / {controller.target_vram_mb} MB")
    print(f"  VRAM Safe: {'PASSED' if peak_vram.is_safe else 'FAILED'}")
    print("=" * 65)

    controller.shutdown()
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark Faster-Whisper ASR engine.")
    parser.add_argument("--model-size", default="tiny", help="Whisper model size (tiny, base, small)")
    parser.add_argument("--device", default="cpu", help="Device (cpu, cuda)")
    parser.add_argument("--compute-type", default="int8", help="Compute type (int8, int8_float16, float16)")
    parser.add_argument("--rounds", type=int, default=3, help="Number of test rounds")
    args = parser.parse_args()

    sys.exit(run_benchmark(args.model_size, args.device, args.compute_type, args.rounds))
