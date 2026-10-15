"""Aesthetic Blending Engine for In-Place Visual Translation.

Features:
1. Adaptive Local Background Sampling (extracts surrounding background color, no black boxes).
2. Dynamic Font Auto-scaling & Word Reflow (prevents text overflow in Vietnamese/multilingual text).
3. Contrast Text Styling (ensures legibility on complex dynamic 3D game backgrounds).
"""

from typing import Optional, Tuple
import numpy as np


def sample_background_color(
    frame: Optional[np.ndarray],
    bbox: Tuple[int, int, int, int],
    margin: int = 4,
    default_color: Tuple[int, int, int] = (20, 24, 33),
) -> Tuple[int, int, int]:
    """Sample the dominant background color from pixels bordering the text bounding box.

    Args:
        frame: The screen frame as a numpy array of shape (H, W, 3) or (H, W, 4) in RGB/BGR.
        bbox: (x, y, width, height) of the bounding box.
        margin: Thickness in pixels of the surrounding border ring to sample.
        default_color: Fallback color if frame is invalid or coordinates are out of bounds.

    Returns:
        RGB tuple of the sampled background color (r, g, b).
    """
    if frame is None or not isinstance(frame, np.ndarray) or frame.ndim < 3:
        return default_color

    h_img, w_img = frame.shape[:2]
    x, y, w, h = bbox

    # Clamp coordinates to valid image bounds
    x1 = max(0, x)
    y1 = max(0, y)
    x2 = min(w_img, x + w)
    y2 = min(h_img, y + h)

    if x2 <= x1 or y2 <= y1:
        return default_color

    # Border coordinates including margin
    outer_x1 = max(0, x1 - margin)
    outer_y1 = max(0, y1 - margin)
    outer_x2 = min(w_img, x2 + margin)
    outer_y2 = min(h_img, y2 + margin)

    border_pixels = []

    # Top border strip
    if outer_y1 < y1:
        border_pixels.append(frame[outer_y1:y1, outer_x1:outer_x2])
    # Bottom border strip
    if y2 < outer_y2:
        border_pixels.append(frame[y2:outer_y2, outer_x1:outer_x2])
    # Left border strip
    if outer_x1 < x1:
        border_pixels.append(frame[y1:y2, outer_x1:x1])
    # Right border strip
    if x2 < outer_x2:
        border_pixels.append(frame[y1:y2, x2:outer_x2])

    if not border_pixels:
        # Fallback to sampling inside corners
        corner_pixels = [
            frame[y1, x1],
            frame[y1, max(0, x2 - 1)],
            frame[max(0, y2 - 1), x1],
            frame[max(0, y2 - 1), max(0, x2 - 1)],
        ]
        sampled = np.mean(corner_pixels, axis=0)[:3]
        return int(sampled[0]), int(sampled[1]), int(sampled[2])

    # Flatten collected border strips
    flattened = []
    for strip in border_pixels:
        if strip.size > 0:
            flattened.append(strip.reshape(-1, frame.shape[2])[:, :3])

    if not flattened:
        return default_color

    all_border = np.vstack(flattened)
    if all_border.shape[0] == 0:
        return default_color

    # Use median to resist noise/text edges
    median_color = np.median(all_border, axis=0)
    return int(median_color[0]), int(median_color[1]), int(median_color[2])


def estimate_original_font_size(line_height: float) -> int:
    """Estimate the original typographic font size (in pt) based on line height in pixels."""
    if line_height <= 0:
        return 12
    pt = int(round(line_height * 0.62))
    return max(8, min(36, pt))


def get_contrast_text_color(
    bg_color: Tuple[int, int, int],
) -> Tuple[Tuple[int, int, int], Tuple[int, int, int]]:
    """Determine optimal text color and contrast outline color based on background luminance.

    Formula: W3C Relative Luminance L = 0.299*R + 0.587*G + 0.114*B

    Returns:
        ((text_r, text_g, text_b), (outline_r, outline_g, outline_b))
    """
    r, g, b = bg_color[:3]
    luminance = 0.299 * r + 0.587 * g + 0.114 * b

    if luminance < 160:
        # Dark background -> Crisp white text, subtle dark outline/shadow
        text_color = (255, 255, 255)
        outline_color = (10, 10, 15)
    else:
        # Light background (documents/web novels) -> Sharp dark slate text, bright outline
        text_color = (15, 23, 42)
        outline_color = (255, 255, 255)

    return text_color, outline_color


def calculate_optimal_font_size(
    text: str,
    box_w: int,
    box_h: int,
    original_line_height: Optional[float] = None,
    target_lines: Optional[int] = None,
    min_size: int = 8,
    max_size: int = 24,
    padding: int = 4,
) -> int:
    """Calculate the optimal font size (in pt) that guarantees text fits inside bounding box.

    Strictly anchors to original font size: translation font will NEVER exceed original text size.
    Auto-shrinks if Vietnamese/target language expansion requires tighter fit.
    """
    clean_text = text.strip()
    if not clean_text:
        return 12

    # Anchor upper limit to original font size if available
    if original_line_height and original_line_height > 0:
        orig_pt = estimate_original_font_size(original_line_height)
        max_size = min(max_size, orig_pt)

    usable_w = max(20, box_w - padding * 2)
    usable_h = max(14, box_h - padding * 2)

    words = clean_text.split()
    total_chars = len(clean_text)

    for font_size in range(max_size, min_size - 1, -1):
        char_w = font_size * 0.55
        line_h = font_size * 1.35

        # Single line check
        if (target_lines == 1 or len(words) <= 3) and (total_chars * char_w) <= usable_w and line_h <= usable_h:
            return font_size

        # Multi-line simulation
        chars_per_line = max(1, int(usable_w / char_w))
        max_possible_lines = max(1, int(usable_h / line_h))
        if target_lines and target_lines > 0:
            max_possible_lines = max(max_possible_lines, target_lines)

        lines_needed = 0
        current_line_chars = 0
        fit = True

        for word in words:
            word_len = len(word)
            if word_len > chars_per_line:
                fit = False
                break
            if current_line_chars + word_len + (1 if current_line_chars > 0 else 0) <= chars_per_line:
                current_line_chars += word_len + (1 if current_line_chars > 0 else 0)
            else:
                lines_needed += 1
                current_line_chars = word_len
                if lines_needed > max_possible_lines:
                    fit = False
                    break

        if current_line_chars > 0:
            lines_needed += 1

        if fit and lines_needed <= max_possible_lines:
            return font_size

    return min_size


def apply_aesthetic_styling(
    box,
    frame: Optional[np.ndarray] = None,
    padding: int = 4,
):
    """Enrich a VisualBoundingBox with adaptive background, contrast colors, alignment, and auto-scaled font."""
    bbox = (box.x, box.y, box.width, box.height)
    
    # 1. Sample Background Color
    bg = sample_background_color(frame, bbox)
    box.bg_color = bg

    # 2. Derive Contrast Text and Outline Colors
    text_c, outline_c = get_contrast_text_color(bg)
    box.text_color = text_c
    box.outline_color = outline_c

    # 3. Estimate Original Font Size and Typography Properties
    line_count = max(1, getattr(box, "line_count", 1))
    orig_line_h = getattr(box, "original_line_height", 0.0) or (box.height / line_count)
    box.original_line_height = orig_line_h
    box.original_font_size = estimate_original_font_size(orig_line_h)

    # 4. Text Alignment and Font Weight
    display_text = box.translated_text or box.original_text
    words = display_text.strip().split()
    if box.width >= 120 or len(display_text) >= 25 or len(words) >= 4:
        box.alignment = "left"
        box.font_weight = "medium"
    else:
        box.alignment = "center"
        box.font_weight = "bold"

    # 5. Calculate Optimal Font Size Anchored to Original Size
    box.font_size = calculate_optimal_font_size(
        display_text,
        box.width,
        box.height,
        original_line_height=orig_line_h,
        target_lines=line_count,
        padding=padding,
    )

    return box
