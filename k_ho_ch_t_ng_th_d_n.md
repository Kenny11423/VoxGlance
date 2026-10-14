# KẾ HOẠCH TỔNG THỂ DỰ ÁN (PROJECT MASTER PLAN)
## Dự án: VoxGlance – Real-time Multimodal Live Translator

---

## 1. TỔNG QUAN DỰ ÁN
* **Tên mã dự án:** `VoxGlance`
* **Mục tiêu cốt lõi:** Xây dựng giải pháp dịch thuật trực quan đa phương thức thời gian thực, đồng thời tiếp nhận và dịch cả luồng hiển thị (Visual OCR) lẫn âm thanh hệ thống (Speech-to-Subtitles), tối ưu hóa trải nghiệm tương tự YouTube Live Caption với độ trễ cực thấp.
* **Thời gian thực hiện dự kiến:** 12 tuần (3 tháng).
* **Ràng buộc tài nguyên chính:** Tổng mức tiêu thụ VRAM trên GPU duy trì nghiêm ngặt dưới **1GB VRAM**, độ trễ tổng thể $\le 800\text{ms}$.

---

## 2. CHỈ SỐ MỤC TIÊU & TIÊU CHUẨN ĐO LƯỜNG (KPIs / OKRs)

| Hạng mục | Baseline thông thường | Chỉ số mục tiêu | Phương pháp đo lường |
| :--- | :--- | :--- | :--- |
| **Độ trễ âm thanh $\rightarrow$ Phụ đề** | 2.500ms – 4.000ms | **$\le 800\text{ms}$** | Timestamp từ audio chunk đến lúc ký tự xuất hiện trên overlay |
| **Độ trễ màn hình $\rightarrow$ Text dịch** | 1.000ms – 1.500ms | **$\le 400\text{ms}$** | Benchmark thời gian bắt khung hình, OCR và render overlay |
| **Chiếm dụng VRAM GPU** | > 2.500MB VRAM | **$\le 950\text{MB}$** | `nvidia-smi` / `cudaMemGetInfo` ghi log định kỳ |
| **Chiếm dụng CPU hệ thống** | 35% – 50% CPU load | **$\le 15\%$** | Windows Performance Monitor / Task Manager |
| **Thao tác người dùng** | 4 – 6 bước bấm chuột | **1 Hotkey / 0-click** | Đánh giá qua user journey testing |
| **Chất lượng âm thanh (WER)** | 12% – 15% | **$\le 8\%$** | Đánh giá trên tập dữ liệu kiểm thử chuẩn (LibriSpeech/Custom) |

---

## 3. KIẾN TRÚC HỆ THỐNG TỔNG THỂ

```
                                  [USER SYSTEM]
               ┌─────────────────────────┴─────────────────────────┐
               ▼                                                   ▼
     [System Audio Output]                               [Display Frame Buffer]
  (WASAPI Loopback / PipeWire)                          (DXGI / Desktop Duplication)
               │                                                   │
  ┌────────────┴────────────┐                        ┌─────────────┴─────────────┐
  │  AUDIO PIPELINE         │                        │  VISUAL OCR PIPELINE      │
  │  - Silero VAD (Chunking)│                        │  - Frame Differencing     │
  │  - Faster-Whisper INT8  │                        │  - DBNet TensorRT (Det)   │
  │  - Stream-and-Revise MT │                        │  - CRNN/SVTR INT8 (Rec)   │
  └────────────┬────────────┘                        └─────────────┬─────────────┘
               │                                                   │
               └─────────────────────────┬─────────────────────────┘
                                         ▼
                   [CORE ORCHESTRATOR & MEMORY CONTROLLER]
                   - Shared CUDA Stream & VRAM Cap (< 1GB)
                   - LRU Cache (Tránh dịch lại từ lặp)
                   - Collision Resolver (Tránh sub đè lên chữ OCR)
                                         │
                                         ▼
                       [FRONTEND UI / OVERLAY LAYER]
                       - Frameless Transparent Window
                       - Click-through & Global Hotkeys
                       - Smooth Word-by-word Roll-up Subtitles
```

---

## 4. LỘ TRÌNH TRIỂN KHAI 12 TUẦN (4 GIAI ĐOẠN)

### Giai đoạn 1: Nghiên cứu lõi AI & Tối ưu hóa Bộ nhớ (Tuần 1 – Tuần 3)
* **Tuần 1: Khởi tạo & Benchmark Baseline**
  * Thiết lập môi trường kỹ thuật chuẩn: CUDA 12.x, TensorRT 10.x, cuDNN 9.x, CTranslate2, ONNX Runtime.
  * Xây dựng công cụ profiling VRAM chuyên biệt (phân tách giữa cấp phát thực tế và cache buffer).
  * Thu thập tập dữ liệu kiểm thử chuẩn cho âm thanh và giao diện game/ứng dụng.
* **Tuần 2: Nén và Tối ưu hóa Whisper (ASR Engine)**
  * Chuyển đổi mô hình Whisper-Small sang `int8_float16` bằng CTranslate2.
  * Tích hợp Silero VAD streaming (cửa sổ 30ms – 50ms) để loại bỏ âm lặng trước khi gửi dữ liệu đến decoder.
  * Giới hạn trần VRAM của module ASR dưới **400MB**.
* **Tuần 3: Tối ưu hóa PaddleOCR sang TensorRT**
  * Export mô hình Text Detection (DBNet) và Text Recognition (SVTR/CRNN) sang ONNX.
  * Xây dựng engine TensorRT với dynamic shapes hẹp và bật FP16/INT8 Calibration.
  * Cấu hình `trt_max_workspace_size = 256MB`, chốt trần VRAM OCR dưới **300MB**.

---

### Giai đoạn 2: Xây dựng Pipeline Thời gian thực (Tuần 4 – Tuần 6)
* **Tuần 4: Pipeline Âm thanh Streaming (Low Latency)**
  * Lập trình bộ thu âm hệ thống trực tiếp qua WASAPI Loopback (Windows) và PipeWire (Linux).
  * Cài đặt cơ chế **Stream-and-Revise**: đẩy partial tokens ra màn hình sau mỗi 250ms và chốt hạ (commit) khi dứt câu.
  * Triển khai thuật toán dịch đồng thời Wait-$k$ kết hợp CTranslate2 Opus-MT / NLLB-200.
* **Tuần 5: Pipeline Quét màn hình & Typography**
  * Xây dựng bộ trích xuất khung hình hiệu năng cao bằng DXGI Desktop Duplication API.
  * Áp dụng thuật toán so sánh khung hình (Frame Differencing): chỉ kích hoạt OCR khi màn hình có thay đổi ký tự $> 5\%$.
  * Tự động căn chỉnh kích thước font và viền tương phản (Stroke/Shadow) dựa theo kích thước Bounding Box.
* **Tuần 6: Điều phối Bộ nhớ & Tránh Phân mảnh VRAM**
  * Tích hợp bộ nhớ đệm nội bộ (LRU In-memory Cache) để trả kết quả tức thì cho các nhãn UI lặp lại.
  * Chia sẻ CUDA Stream giữa ASR và OCR để triệt tiêu hiện tượng khởi tạo nhiều context gây tốn thêm VRAM.

---

### Giai đoạn 3: Phát triển Giao diện & Trải nghiệm Người dùng (Tuần 7 – Tuần 9)
* **Tuần 7: Transparent Overlay & Click-Through**
  * Xây dựng cửa sổ không viền trong suốt bằng PyQt6 kết hợp Win32 API (`WS_EX_TRANSPARENT | WS_EX_LAYERED`).
  * Đảm bảo chuột click xuyên qua overlay vào game/ứng dụng phía sau mà không gây gián đoạn focus.
* **Tuần 8: Smooth Subtitle Animation & Tránh Che khuất**
  * Xây dựng hiệu ứng chữ xuất hiện mượt mà (Word-by-word fade-in) theo timestamps của Whisper.
  * Cơ chế né va chạm (Collision Detection): nếu phía dưới màn hình có chữ OCR, phụ đề âm thanh tự động dời lên phía trên.
* **Tuần 9: Floating Widget & Phím tắt Toàn cục**
  * Thiết kế thanh điều khiển mini dạng Floating Widget neo ở góc màn hình, tự động ẩn sau 3 giây không tương tác.
  * Cài đặt Global Hotkeys (`Alt + T` bật/tắt dịch nhanh, `Alt + S` chọn vùng quét, `Alt + M` tắt/mở âm thanh).
  * Tự động lưu và kích hoạt profile theo ứng dụng (App Profiles: YouTube, Discord, game cụ thể).

---

### Giai đoạn 4: Kiểm thử Chịu tải, Đóng gói & Phát hành (Tuần 10 – Tuần 12)
* **Tuần 10: Kiểm thử Ổn định & Đo FPS Game**
  * Chạy thử nghiệm liên tục trong 8 giờ để giám sát rò rỉ bộ nhớ (Memory Leak).
  * Đo đạc mức tụt FPS trên các tựa game đồ họa nặng chạy đồng thời với ứng dụng dịch.
* **Tuần 11: Tối ưu Đa chế độ (Offline & Hybrid Cloud)**
  * Hỗ trợ chuyển đổi mượt mà giữa chế độ Offline (mô hình nội bộ) và Hybrid Cloud (gọi API DeepL/Groq khi có mạng).
  * Xây dựng module tự động kiểm tra phần cứng (Hardware Check) để cấu hình số luồng tính toán tối ưu.
* **Tuần 12: Đóng gói Installer & Phát hành Thử nghiệm**
  * Đóng gói bản cài đặt độc lập (Inno Setup / MSIX) bao gồm các runtime tối thiểu, không yêu cầu cài Python rời.
  * Phát hành phiên bản Closed Beta và thu thập phản hồi từ người dùng đầu tiên.

---

## 5. PHÂN BỔ NHÂN SỰ & TRÁCH NHIỆM (RACI MATRIX)

| Vị trí nhân sự | Trách nhiệm chính | Giai đoạn tập trung |
| :--- | :--- | :--- |
| **Lead AI/ML Engineer** | Quantize mô hình Whisper/OCR, build TensorRT engine, kiểm soát VRAM | Tuần 1 – Tuần 6 |
| **Systems/Backend Engineer** | Lập trình WASAPI Loopback, DXGI Capture, streaming pipeline, memory pool | Tuần 2 – Tuần 8 |
| **Frontend/UI Engineer** | Phát triển Overlay trong suốt, Click-through, PyQt6, animation, hotkeys | Tuần 5 – Tuần 10 |
| **QA / Performance Tester** | Đo đạc độ trễ, kiểm tra rò rỉ bộ nhớ, benchmark FPS và độ chính xác dịch thuật | Tuần 1 – Tuần 12 |

---

## 6. QUẢN LÝ RỦI RO & PHƯƠNG ÁN DỰ PHÒNG

| Rủi ro kỹ thuật | Khả năng | Ảnh hưởng | Phương án xử lý dự phòng |
| :--- | :---: | :---: | :--- |
| **VRAM vượt quá trần 1GB khi chạy đồng thời** | Trung bình | Nghiêm trọng | Ép OCR chạy trên CPU đa luồng; chuyển Whisper sang bản Tiny thay vì Small. |
| **Phụ đề nhấp nháy do mô hình ASR liên tục sửa từ** | Cao | Trung bình | Đặt vùng đệm trễ cố định 250ms – 300ms trước khi hiển thị token lên màn hình. |
| **Phần mềm chống gian lận (Anti-cheat) chặn Overlay** | Trung bình | Cao | Sử dụng Top-level Window tiêu chuẩn của hệ điều hành, tuyệt đối không can thiệp hook vào DirectX của game. |
| **Giọng nói bị lẫn tạp âm hoặc nhiều người nói đè** | Trung bình | Trung bình | Bổ sung bộ lọc Decibel trong Silero VAD, chỉ lấy luồng âm thanh có cường độ vượt ngưỡng xác định. |

---

## 7. TIÊU CHÍ NGHIỆM THU DỰ ÁN (ACCEPTANCE CHECKLIST)

- [ ] Tổng mức sử dụng VRAM hiển thị trên `nvidia-smi` duy trì dưới **950MB** khi chạy đồng thời cả ASR và OCR.
- [ ] Độ trễ phụ đề âm thanh không vượt quá **800ms** so với tiếng phát ra từ loa.
- [ ] Chuột click xuyên qua vùng phụ đề mượt mà, không làm mất tiêu điểm (focus) của cửa sổ game hoặc video.
- [ ] Không xuất hiện hiện tượng rò rỉ bộ nhớ (VRAM và RAM ổn định sau 6 giờ chạy liên tục).
- [ ] Bản đóng gói cài đặt hoạt động độc lập, không yêu cầu người dùng tự cài đặt thêm Python hay CUDA Toolkit.