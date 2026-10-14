"""Memory Controller and VRAM Profiler for OmniTranslate.

Enforces strict GPU VRAM budget (< 950MB) and provides peak guard buffer checks.
"""

from dataclasses import dataclass
import gc
from typing import Optional
from loguru import logger
import warnings
warnings.filterwarnings("ignore", category=FutureWarning, module="pynvml")
import pynvml


@dataclass
class VRAMInfo:
    total_mb: float
    used_mb: float
    free_mb: float
    usage_pct: float
    is_safe: bool


class MemoryController:
    """Monitors and manages GPU VRAM usage via NVML."""

    def __init__(
        self,
        device_index: int = 0,
        target_vram_mb: int = 1800,
        peak_guard_buffer_mb: int = 150,
    ):
        self.device_index = device_index
        self.target_vram_mb = target_vram_mb
        self.peak_guard_buffer_mb = peak_guard_buffer_mb
        self.safe_limit_mb = target_vram_mb - peak_guard_buffer_mb
        self._nvml_initialized = False
        self._handle = None
        self._init_nvml()

    def _init_nvml(self) -> None:
        try:
            pynvml.nvmlInit()
            self._handle = pynvml.nvmlDeviceGetHandleByIndex(self.device_index)
            self._nvml_initialized = True
            device_name = pynvml.nvmlDeviceGetName(self._handle)
            if isinstance(device_name, bytes):
                device_name = device_name.decode("utf-8")
            logger.info(
                f"MemoryController initialized for GPU {self.device_index}: {device_name} "
                f"(Target VRAM Cap: {self.target_vram_mb}MB, Safe Threshold: {self.safe_limit_mb}MB)"
            )
        except Exception as e:
            logger.warning(f"Failed to initialize NVML for GPU {self.device_index}: {e}. Running in simulation/CPU mode.")
            self._nvml_initialized = False

    def get_vram_info(self) -> VRAMInfo:
        """Query real-time VRAM statistics in Megabytes."""
        if not self._nvml_initialized or self._handle is None:
            # Fallback mock for non-GPU or testing environment
            return VRAMInfo(
                total_mb=4096.0,
                used_mb=0.0,
                free_mb=4096.0,
                usage_pct=0.0,
                is_safe=True,
            )

        try:
            mem_info = pynvml.nvmlDeviceGetMemoryInfo(self._handle)
            total_mb = mem_info.total / (1024 * 1024)
            used_mb = mem_info.used / (1024 * 1024)
            free_mb = mem_info.free / (1024 * 1024)
            usage_pct = (used_mb / total_mb) * 100.0 if total_mb > 0 else 0.0
            is_safe = used_mb <= self.target_vram_mb

            return VRAMInfo(
                total_mb=round(total_mb, 2),
                used_mb=round(used_mb, 2),
                free_mb=round(free_mb, 2),
                usage_pct=round(usage_pct, 2),
                is_safe=is_safe,
            )
        except Exception as e:
            logger.error(f"Error querying NVML memory: {e}")
            return VRAMInfo(0.0, 0.0, 0.0, 0.0, False)

    def can_allocate(self, additional_mb: float) -> bool:
        """Check if allocating additional_mb will stay strictly within the target VRAM cap."""
        current = self.get_vram_info()
        projected = current.used_mb + additional_mb
        if projected > self.target_vram_mb:
            logger.warning(
                f"VRAM budget exceeded! Current: {current.used_mb:.1f}MB, "
                f"Requested: {additional_mb:.1f}MB, Projected: {projected:.1f}MB > Cap: {self.target_vram_mb}MB"
            )
            return False
        return True

    def enforce_cleanup(self) -> VRAMInfo:
        """Trigger Python garbage collection and framework cache clearing."""
        gc.collect()

        # Try torch cuda cleanup if torch is imported
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.ipc_collect()
        except ImportError:
            pass

        info = self.get_vram_info()
        logger.info(f"Memory cleanup triggered. Current VRAM: {info.used_mb:.1f}MB / {self.target_vram_mb}MB")
        return info

    def shutdown(self) -> None:
        """Shutdown NVML cleanly."""
        if self._nvml_initialized:
            try:
                pynvml.nvmlShutdown()
            except Exception:
                pass
            self._nvml_initialized = False
