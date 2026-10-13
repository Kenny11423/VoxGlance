#!/usr/bin/env python3
"""Real-time GPU VRAM and System Profiler for OmniTranslate."""

import argparse
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.config import load_config
from src.core.memory import MemoryController


def profile_loop(interval: float = 0.5, duration: float = 10.0, target_mb: int = 950) -> int:
    config = load_config()
    target_mb = target_mb or config.system.target_vram_mb
    controller = MemoryController(target_vram_mb=target_mb)

    print("=" * 70)
    print(f" OmniTranslate VRAM Profiler | Target Cap: {target_mb} MB")
    print("=" * 70)
    print(f"{'Time':<10} | {'Used (MB)':<12} | {'Free (MB)':<12} | {'Total (MB)':<12} | {'Status':<10}")
    print("-" * 70)

    start_time = time.time()
    max_used = 0.0
    violation_count = 0

    try:
        while True:
            elapsed = time.time() - start_time
            if duration > 0 and elapsed >= duration:
                break

            info = controller.get_vram_info()
            if info.used_mb > max_used:
                max_used = info.used_mb

            status = "SAFE" if info.is_safe else "EXCEEDED!"
            if not info.is_safe:
                violation_count += 1

            time_str = f"{elapsed:05.1f}s"
            print(f"{time_str:<10} | {info.used_mb:<12.1f} | {info.free_mb:<12.1f} | {info.total_mb:<12.1f} | {status:<10}")

            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nProfiling stopped by user.")
    finally:
        controller.shutdown()

    print("=" * 70)
    print(f" Summary: Peak VRAM: {max_used:.1f} MB / Cap: {target_mb} MB")
    print(f" Cap Violations: {violation_count}")
    print("=" * 70)

    return 0 if violation_count == 0 else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Profile GPU VRAM in real-time.")
    parser.add_argument("--interval", type=float, default=0.5, help="Sampling interval in seconds")
    parser.add_argument("--duration", type=float, default=5.0, help="Total duration in seconds (0 for indefinite)")
    parser.add_argument("--target-mb", type=int, default=950, help="Target VRAM ceiling in MB")
    args = parser.parse_args()

    sys.exit(profile_loop(args.interval, args.duration, args.target_mb))
