# Kế hoạch Triển khai: OmniTranslate – Giai đoạn 1 (Lõi AI, Quản lý Bộ nhớ & Nền tảng Đa tiến trình)

## Goal Description
Xây dựng nền móng kỹ thuật và khung mã nguồn (codebase) cho dự án **OmniTranslate** theo lộ trình [k_ho_ch_t_ng_th_d_n.md](file:///home/kennysk/omni-traslator/k_ho_ch_t_ng_th_d_n.md) và thiết kế kiến trúc [ki_n_tr_c_h_th_ng_d_ch_thu_t_tr_c_quan_qua_s_mermaid.md](file:///home/kennysk/omni-traslator/ki_n_tr_c_h_th_ng_d_ch_thu_t_tr_c_quan_qua_s_mermaid.md).

Mục tiêu giai đoạn 1 tập trung vào:
1. Thiết lập cấu trúc thư mục chuẩn mô-đun hóa và môi trường runtime tối ưu cho **NVIDIA RTX 2050 (4GB VRAM)** trên hệ điều hành **Arch Linux (Wayland/PipeWire)**, đồng thời giữ khả năng tương thích chéo với Windows.
2. Xây dựng **Memory Controller & VRAM Profiler** độc lập để theo dõi và khóa trần VRAM $\le 950\text{MB}$.
3. Triển khai **Audio Pipeline Streaming**: Silero VAD (cắt khoảng lặng) $\rightarrow$ Faster-Whisper `int8_float16` qua CTranslate2 (VRAM mục tiêu $< 400\text{MB}$).
4. Triển khai **Visual Pipeline Foundation**: Frame Differencing (bỏ qua khung hình không đổi $> 5\%$) và mô-đun trích xuất OCR.
5. Thiết lập cơ chế **IPC & Shared Memory** đa tiến trình để chống nghẽn Python GIL.

---

## User Review Required

> [!IMPORTANT]
> **Phiên bản Python & Quản lý Môi trường:**
> Hệ thống hiện tại đang chạy **Python 3.14.7** trên Arch Linux. Các thư viện AI cốt lõi (PyTorch CUDA, CTranslate2, TensorRT, onnxruntime-gpu) hiện tại chỉ tương thích và có pre-built binary wheels ổn định trên **Python 3.11 hoặc 3.12**.
> **Giải pháp đề xuất:** Sử dụng công cụ `uv` (Astral) để cài đặt tự động môi trường Python 3.11/3.12 cô lập mà không can thiệp hay ảnh hưởng đến Python 3.14 của hệ thống.

> [!WARNING]
> **Hỗ trợ Cross-Platform (Linux PipeWire/Wayland vs Windows WASAPI/DXGI):**
> Tài liệu thiết kế ban đầu tập trung vào Windows API (WASAPI Loopback, DXGI Desktop Duplication, Win32 HWND). Máy trạm hiện tại là **Arch Linux (Wayland)**.
> Chúng tôi đề xuất thiết kế **Lớp trừu tượng phần cứng (Hardware Abstraction Layer - HAL)**:
> - Luồng Audio: Hỗ trợ backend `pipewire` / `pulseaudio` (Linux) và `wasapi` (Windows).
> - Luồng Screen Capture: Hỗ trợ backend `pipewire_portal` / `mss` / `x11` (Linux) và `dxgi` (Windows).
> Điều này đảm bảo dự án chạy và benchmark trực tiếp được ngay trên máy tính của bạn, đồng thời sẵn sàng đóng gói cho Windows.

---

## Open Questions

1. **Backend Dịch thuật trong giai đoạn đầu:**
   Bạn muốn giai đoạn 1 thử nghiệm dịch đồng thời cục bộ hoàn toàn bằng mô hình **CTranslate2 (Opus-MT / NLLB-200 INT8)** hay kết hợp thử nghiệm **Cloud API (Groq / DeepL / OpenAI)** trước để đo lường độ trễ mạng?
2. **Khu vực hiển thị Overlay:**
   Trên Wayland, các cửa sổ transparent click-through cần cấu hình thông qua `layer-shell` (hoặc chạy qua XWayland). Bạn muốn phát triển và test UI trên XWayland hay native Wayland Layer Shell?

---

## Proposed Changes

```
omni-translate/
├── configs/
│   └── default_config.yaml       # [NEW] Cấu hình trần VRAM, audio backend, OCR thresholds
├── pyproject.toml                # [NEW] Định nghĩa package, dependencies và scripts
├── scripts/
│   ├── vram_profiler.py          # [NEW] Công cụ ghi log và kiểm tra trần VRAM thời gian thực
│   └── benchmark_asr.py          # [NEW] Script benchmark Whisper INT8 + Silero VAD latency
├── src/
│   ├── __init__.py               # [NEW]
│   ├── core/
│   │   ├── __init__.py           # [NEW]
│   │   ├── config.py             # [NEW] Model Pydantic nạp cấu hình hệ thống
│   │   ├── memory.py             # [NEW] Memory Controller, VRAM Tracker, Peak Guard
│   │   ├── cache.py              # [NEW] In-memory LRU Cache cho từ vựng UI trùng lặp
│   │   └── ipc.py                # [NEW] Message passing & POSIX Shared Memory abstraction
│   ├── audio/
│   │   ├── __init__.py           # [NEW]
│   │   ├── capture.py            # [NEW] Audio Capture (PipeWire / WASAPI loopback)
│   │   ├── vad.py                # [NEW] Silero VAD streaming 30ms frame filter
│   │   └── asr.py                # [NEW] Faster-Whisper INT8 streaming engine (CTranslate2)
│   └── visual/
│       ├── __init__.py           # [NEW]
│       ├── capture.py            # [NEW] Screen grabber abstraction (PipeWire / MSS / DXGI)
│       ├── diff.py               # [NEW] Frame Differencing & SSIM filter (> 5% motion)
│       └── ocr.py                # [NEW] PaddleOCR / TensorRT engine wrapper
└── tests/
    ├── test_memory.py            # [NEW] Test giới hạn VRAM và giải phóng bộ nhớ
    ├── test_vad.py               # [NEW] Test Silero VAD lọc âm lặng
    └── test_diff.py              # [NEW] Test thuật toán so sánh khung hình
```

---

### Component 1: Cấu hình & Quản lý Môi trường

#### [NEW] `pyproject.toml`
- Quản lý cấu hình dự án chuẩn PEP 621.
- Định nghĩa dependencies: `ctranslate2`, `faster-whisper`, `torch`, `torchaudio`, `numpy`, `sounddevice`, `pynvml`, `pydantic`, `pyyaml`, `loguru`, `pytest`.

#### [NEW] `configs/default_config.yaml`
```yaml
system:
  device: "cuda:0"
  target_vram_mb: 950
  peak_guard_buffer_mb: 150

audio:
  sample_rate: 16000
  chunk_duration_ms: 250
  vad:
    threshold: 0.5
    min_silence_duration_ms: 200
  asr:
    model_size: "small"
    compute_type: "int8_float16"
    beam_size: 1
    max_vram_mb: 400

visual:
  frame_diff_threshold: 0.05
  fps_limit: 10
  ocr:
    max_vram_mb: 300
```

---

### Component 2: Core Memory Controller & VRAM Profiler

#### [NEW] `src/core/memory.py`
- Giám sát VRAM thông qua `pynvml` (`nvmlDeviceGetMemoryInfo`) hoặc PyTorch CUDA API.
- Hàm `check_vram_budget(budget_mb: int) -> bool` ngăn chặn cấp phát thêm nếu VRAM tổng chạm ngưỡng 950MB.
- Cơ chế buộc gọi Garbage Collection & CUDA Cache cleanup (`torch.cuda.empty_cache()`) khi vượt quá trần.

#### [NEW] `scripts/vram_profiler.py`
- Chạy nền ghi log theo chu kỳ (mỗi 500ms): VRAM Used, VRAM Free, VRAM Reserved, CPU Load.
- Định dạng bảng màu hoặc xuất file CSV để vẽ đồ thị báo cáo kiểm thử.

#### [NEW] `src/core/cache.py`
- Bộ nhớ đệm Thread-safe LRU Cache với giới hạn số lượng mục (`maxsize=2000`).
- Lưu trữ cặp `(text_hash, original_text) -> translated_text` giúp phản hồi tức thì với các nhãn giao diện lặp lại.

---

### Component 3: Audio Streaming Pipeline (VAD & Faster-Whisper INT8)

#### [NEW] `src/audio/vad.py`
- Tích hợp Silero VAD chạy ONNX / Torchscript siêu nhẹ (< 30MB VRAM / CPU).
- Tiếp nhận từng chunk 30ms–50ms PCM 16kHz, trả về cờ `is_speech: bool`.
- Tự động bỏ qua các khối âm thanh im lặng để giải phóng tải tính toán cho GPU.

#### [NEW] `src/audio/asr.py`
- Wrapper của `faster_whisper.WhisperModel` cấu hình với `device="cuda"`, `compute_type="int8_float16"`.
- Thực thi cơ chế streaming partial transcript: xuất tokens tạm thời mỗi 250ms và chốt hạ khi dứt câu.

---

### Component 4: Visual Pipeline (Frame Differencing & Capture)

#### [NEW] `src/visual/diff.py`
- So sánh sự thay đổi giữa 2 khung hình liên tiếp bằng thuật toán trừ ma trận pixel (Absolute Difference) và chuẩn hóa.
- Nếu tỷ lệ thay đổi $< 5\%$, lập tức bỏ qua (Skip Frame) không gọi Text Detection để tiết kiệm GPU.

#### [NEW] `src/visual/capture.py`
- Cung cấp lớp trừu tượng `ScreenCapture` với backend linh hoạt (hỗ trợ `mss`/`X11` trên Linux và sẵn sàng hook `DXGI` trên Windows).

---

## Verification Plan

### Automated Tests
1. **Kiểm tra Môi trường & GPU VRAM Profiler:**
   ```bash
   python scripts/vram_profiler.py --interval 0.5 --duration 5
   ```
   *Kỳ vọng:* Đo đạc chính xác mức sử dụng VRAM của card RTX 2050 hiện tại.

2. **Unit Tests cho Bộ nhớ & Cache:**
   ```bash
   pytest tests/test_memory.py tests/test_diff.py -v
   ```
   *Kỳ vọng:* LRU cache xử lý đúng giới hạn kích thước, thuật toán frame diff phát hiện đúng biến thiên $> 5\%$.

3. **Benchmark Audio Whisper INT8:**
   ```bash
   python scripts/benchmark_asr.py
   ```
   *Kỳ vọng:* VRAM sử dụng của Whisper-Small INT8 không vượt quá 400MB; độ trễ xử lý chunk âm thanh 1s dưới 300ms.

### Manual Verification
- Chạy script test thu âm / audio synthetic và quan sát log phụ đề thời gian thực được đẩy ra màn hình console.
- Kiểm tra `nvidia-smi` xác nhận mức VRAM tổng thể của tiến trình kiểm thử luôn duy trì trong khoảng an toàn $\le 950\text{MB}$.
