"""Tests for FrameDifferencer."""

import numpy as np
from src.visual.diff import FrameDifferencer


def test_frame_differencer_first_frame():
    diff = FrameDifferencer(threshold=0.05)
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    
    # First frame must always be processed
    result = diff.compare(frame)
    assert result.should_process is True
    assert result.diff_ratio == 1.0


def test_frame_differencer_identical_frames():
    diff = FrameDifferencer(threshold=0.05)
    frame = np.ones((100, 100, 3), dtype=np.uint8) * 128

    # First frame
    diff.compare(frame)

    # Identical frame -> should skip
    result = diff.compare(frame)
    assert result.should_process is False
    assert result.diff_ratio == 0.0


def test_frame_differencer_small_change():
    diff = FrameDifferencer(threshold=0.05)
    frame1 = np.zeros((100, 100, 3), dtype=np.uint8)
    diff.compare(frame1)

    # Modify only 2% of the pixels (200 pixels out of 10,000)
    frame2 = frame1.copy()
    frame2[:2, :, :] = 255  # 2 rows * 100 cols = 200 pixels = 2%

    result = diff.compare(frame2)
    assert result.should_process is False
    assert result.diff_ratio < 0.05


def test_frame_differencer_large_change():
    diff = FrameDifferencer(threshold=0.05)
    frame1 = np.zeros((100, 100, 3), dtype=np.uint8)
    diff.compare(frame1)

    # Modify 20% of the pixels
    frame2 = frame1.copy()
    frame2[:20, :, :] = 255  # 20 rows * 100 cols = 2000 pixels = 20%

    result = diff.compare(frame2)
    assert result.should_process is True
    assert result.diff_ratio >= 0.05
