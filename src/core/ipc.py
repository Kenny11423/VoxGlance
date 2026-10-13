"""Inter-Process Communication (IPC) schemas and queues for OmniTranslate."""

from dataclasses import dataclass, field
import multiprocessing as mp
from typing import Any, List, Optional
import time


@dataclass
class SubtitleToken:
    """Represents a speech recognition/translation subtitle segment."""
    text: str
    is_partial: bool
    start_time: float = 0.0
    end_time: float = 0.0
    confidence: float = 1.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class VisualBoundingBox:
    """Represents a detected text box on screen with coordinates and translation."""
    x: int
    y: int
    width: int
    height: int
    original_text: str
    translated_text: str
    confidence: float = 1.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class ControlMessage:
    """Command sent between Main Daemon, AI Worker, and UI Overlay."""
    command: str
    payload: Any = None
    timestamp: float = field(default_factory=time.time)


class IPCChannels:
    """Container for queues connecting Daemon, AI Worker, and UI Overlay."""

    def __init__(self):
        # AI Worker -> UI Overlay (Subtitles and OCR boxes)
        self.subtitles_queue: mp.Queue = mp.Queue(maxsize=100)
        self.visual_boxes_queue: mp.Queue = mp.Queue(maxsize=50)

        # Main Daemon <-> AI Worker (Commands and state)
        self.ai_control_queue: mp.Queue = mp.Queue(maxsize=20)
        self.ai_status_queue: mp.Queue = mp.Queue(maxsize=20)

        # Main Daemon <-> UI Overlay (Hotkeys, visibility)
        self.ui_control_queue: mp.Queue = mp.Queue(maxsize=20)
