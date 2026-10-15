# KẾ HOẠCH TỔNG THỂ DỰ ÁN (PROJECT MASTER PLAN)
## Dự án: Ứng dụng Dịch thuật Đa phương tiện Thời gian thực (Real-time Multimodal Live Translator)
### Trọng tâm cốt lõi: Dịch thuật trực quan thay thế tại chỗ trên màn hình (On-Screen In-Place Seamless Translation) cho Game & Tài liệu – Bảo tồn tối đa tính thẩm mỹ

---

## 1. TỔNG QUAN DỰ ÁN & ĐỊNH HƯỚNG MỚI
* **Định danh dự án:** Ứng dụng Dịch thuật Đa phương tiện Thời gian thực (Nhóm 2 – Chủ đề 5).
* **Mục tiêu cốt lõi:** Xây dựng giải pháp dịch thuật trực quan đa phương thức thời gian thực trên máy tính cá nhân. Trong đó, **tập trung ưu tiên cao nhất vào việc dịch thuật khi chơi game hoặc đọc tài liệu bằng cách nhận diện chữ trên màn hình và tạo một layer để che chữ gốc và thay thế bằng chữ dịch tại chỗ**.
* **Yêu cầu thẩm mỹ đặc biệt:** Hạn chế tối đa việc che khuất màn hình hay làm hỏng tính thẩm mỹ của tựa game / tài liệu:
  * Tuyệt đối không dùng hộp chữ nhật đen xì thô thiển đè lên hình ảnh.
  * Tự động lấy mẫu màu nền cục bộ xung quanh khung chữ (Local Background Color Sampling) để tạo mask tiệp màu nền tự nhiên, bo góc mềm mại và làm mờ biên (Feathering).
  * Tự động co giãn kích thước font chữ (Dynamic Font Auto-scaling) và ngắt dòng thông minh để văn bản tiếng Việt (dài hơn tiếng Anh/Nhật 20% – 35%) luôn nằm vừa vặn 100% trong bounding box của chữ gốc, không tràn viền (No Overflow) và không đè lên các thành phần UI khác (thanh máu, minimap, bảng biểu).
  * Viền nét tương phản (Contrast Text Outline 1.5px & Drop Shadow) giúp chữ dịch luôn sắc nét, dễ đọc trên mọi nền game 3D chuyển động phức tạp.
  * Hoạt động 100% ngoài tiến trình game (Out-of-process Zero-touch Desktop Transparent Overlay), an toàn tuyệt đối trước mọi hệ thống chống gian lận (Anti-cheat: EAC, BattlEye, VAC).
* **Thời gian thực hiện dự kiến:** 12 tuần (3 tháng).
* **Ràng buộc tài nguyên chính:** Tổng mức tiêu thụ VRAM trên GPU duy trì nghiêm ngặt dưới **950MB VRAM** (thực tế ~680MB), đảm bảo giữ vững 60 FPS cho game đồ họa nặng chạy đồng thời; hoạt động 100% On-device không phụ thuộc server đám mây.

---

## 2. CHỈ SỐ MỤC TIÊU & TIÊU CHUẨN ĐO LƯỜNG (KPIs / OKRs)

| Hạng mục đo lường | Baseline công cụ cũ (Translumo/MORT) | Chỉ số mục tiêu của dự án | Phương pháp & Công cụ kiểm chứng |
| :--- | :--- | :--- | :--- |
| **Độ trễ màn hình $\rightarrow$ Chữ dịch tại chỗ** | 1.200ms – 2.000ms | **$\le 300\text{ms}$** | Benchmark trích xuất DXGI, OCR TensorRT, CTranslate2 MT và render overlay |
| **Độ trễ âm thanh $\rightarrow$ Phụ đề** | 2.500ms – 4.000ms | **$\le 500\text{ms}$** | Timestamp từ audio chunk (Silero VAD) đến lúc ký tự xuất hiện trên overlay |
| **Độ chính xác bao phủ Bounding Box** | Lệch 10 – 20px, đè lấn UI | **Sai số $\le 2\text{px}$ ($\text{Fit Ratio} > 98\%$)** | Đo lường tỷ lệ IoU giữa bounding box gốc và mask che phủ |
| **Mức độ tiệp màu nền (Aesthetic Blend)** | Hộp đen thô thiển ($\Delta E > 50$) | **Tiệp màu tự nhiên ($\Delta E \le 2.5$ CIEDE2000)** | So màu giữa mask che và vùng nền lân cận của game/tài liệu |
| **Tỷ lệ tràn viền font tiếng Việt (Overflow)** | 35% – 50% câu bị tràn/cắt cụt | **$0\%$ câu bị tràn viền** | Thuật toán Dynamic Font Auto-scaling tự động tính toán cỡ font vừa khít |
| **Mức độ tụt khung hình game (FPS Drop)** | Drop 15% – 25% FPS | **Tụt FPS $\le 3\%$ (duy trì 58–60 FPS)** | MSI Afterburner / NVIDIA FrameView khi chơi Cyberpunk 2077 / Persona |
| **Chiếm dụng VRAM GPU** | > 2.500MB VRAM | **$\le 850\text{MB}$ (thực tế ~680MB)** | `nvidia-smi` / `cudaMemGetInfo` ghi log định kỳ |
| **An toàn trước Anti-Cheat** | Nguy cơ ban nick (nếu hook RAM) | **An toàn 100% (Zero ban risk)** | Kiến trúc Zero-touch Desktop Overlay, 0% memory injection |
| **Chi phí hạ tầng Server** | 50 – 200 triệu đ/tháng | **$0$ VNĐ (100% On-device)** | Không sử dụng GPU Cloud, người dùng tự xử lý trên máy cá nhân |

---

## 3. KIẾN TRÚC HỆ THỐNG TỔNG THỂ

```
                                      [HỆ THỐNG NGƯỜI DÙNG (USER PC)]
                     ┌───────────────────────────────┴───────────────────────────────┐
                     ▼                                                               ▼
        [Màn hình Game / Tài liệu PDF]                                     [Âm thanh Hệ thống Game/Video]
          (DXGI Desktop Duplication)                                         (WASAPI Loopback / PipeWire)
                     │                                                               │
        ┌────────────┴────────────┐                                     ┌────────────┴────────────┐
        │ VISUAL IN-PLACE ENGINE  │                                     │ AUDIO SUBTITLE ENGINE   │
        │ - Frame Differencing    │                                     │ - Silero VAD (Chunking) │
        │ - DBNet Detection ONNX  │                                     │ - Faster-Whisper INT8   │
        │ - CRNN/SVTR Recognition │                                     │ - Roll-up Subtitles     │
        └────────────┬────────────┘                                     └────────────┬────────────┘
                     │                                                               │
                     └───────────────────────────────┬───────────────────────────────┘
                                                     ▼
                                      [CORE ORCHESTRATOR & LOCAL NMT]
                                      - CTranslate2 INT8 Opus-MT / NLLB-200 (15ms)
                                      - Shared CUDA Stream & VRAM Limiter (< 850MB)
                                      - LRU In-memory Cache (Cache cụm từ lặp lại)
                                                     │
                                                     ▼
                                  [AESTHETIC IN-PLACE BLENDING ENGINE]
         ┌───────────────────────────────────────────┴───────────────────────────────────────────┐
         ▼                                           ▼                                           ▼
[Local Background Sampling]              [Dynamic Font Auto-scaling]                 [Contrast Text Styling]
- Trích xuất pixel viền ngoài            - Tính tỷ lệ S_font = f(W, H, L_vi)         - Outline nét viền 1.5px
- Alpha blending (85% - 95%)             - Word reflow & tự động ngắt dòng           - Drop shadow tương phản
- Feathering viền mềm, không hộp đen     - Vừa vặn 100% bounding box                - Nổi bật trên mọi đồ họa động
         └───────────────────────────────────────────┬───────────────────────────────────────────┘
                                                     ▼
                                 [ZERO-TOUCH TRANSPARENT OVERLAY (PyQt6)]
                                 - WS_EX_LAYERED | WS_EX_TRANSPARENT Click-through
                                 - Top-level OS Window (Không hook RAM, 100% Anti-cheat Safe)
                                 - Hardware Acceleration Render 60 FPS
```

---

## 4. LỘ TRÌNH TRIỂN KHAI 12 TUẦN (4 GIAI ĐOẠN)

### Giai đoạn 1: Lõi Thị Giác & Công Nghệ Thẩm Mỹ Thay Thế Chữ Tại Chỗ (Tuần 1 – Tuần 3)
* **Tuần 1: Khởi tạo Hạ tầng Kỹ thuật & Bắt Khung hình Hiệu năng cao**
  * Thiết lập môi trường kỹ thuật chuẩn: Python 3.12, CUDA 12.x, TensorRT 10.x, ONNX Runtime-GPU, CTranslate2, PyQt6.
  * Lập trình module trích xuất khung hình siêu tốc bằng Windows DXGI Desktop Duplication API (tốc độ $< 10\text{ms}$ ở độ phân giải 2K/4K).
  * Tích hợp thuật toán so sánh khung hình (Frame Differencing): chỉ kích hoạt tiến trình OCR khi phát hiện vùng văn bản có chuyển động hoặc thay đổi ký tự $> 5\%$, giúp tiết kiệm 70% tài nguyên tính toán khi cảnh tĩnh.
* **Tuần 2: Tối ưu hóa Mô hình Phát hiện Chữ (Text Detection) & Nhận diện (OCR)**
  * Chuyển đổi mô hình phát hiện văn bản DBNet sang ONNX Runtime / TensorRT với độ chính xác cao đối với font chữ game và văn bản tài liệu PDF.
  * Tối ưu hóa mô hình nhận diện chữ CRNN/SVTR sang INT8/FP16, kiểm soát trần VRAM của toàn bộ module OCR dưới **300MB**.
  * Hỗ trợ trích xuất chính xác tọa độ Bounding Box đa giác (Polygon/Rotated Rectangle) cho cả chữ ngang và chữ dọc (Manga).
* **Tuần 3: Nghiên cứu & Hoàn thiện Thuật toán Thẩm mỹ (Aesthetic Blending)**
  * Phát triển thuật toán **Adaptive Local Background Sampling**: Lấy mẫu màu viền xung quanh Bounding Box để nội suy màu nền, phủ lớp mask tiệp màu có độ mờ biên (Feathering), triệt tiêu hoàn toàn hộp đen thô thiển.
  * Xây dựng công thức **Dynamic Font Auto-scaling**: Tự động tính toán kích thước font và ngắt dòng (Word Reflow) vừa khít bounding box của chữ gốc theo tỷ lệ mở rộng 20% – 35% của tiếng Việt.

---

### Giai đoạn 2: In-place Translation Pipeline & Tối Ưu Thời Gian Thực (Tuần 4 – Tuần 6)
* **Tuần 4: Pipeline Dịch thuật Ngoại tuyến Tốc độ cao (Low-Latency Local NMT)**
  * Triển khai CTranslate2 với mô hình Helsinki-NLP Opus-MT (En-Vi, Ja-Vi, Zh-Vi) lượng tử hóa INT8.
  * Tối ưu hóa tốc độ suy luận dịch thuật xuống dưới **15ms** cho mỗi đoạn hội thoại.
  * Tích hợp bộ nhớ đệm thông minh (LRU In-memory Cache) để trả kết quả dịch ngay lập tức (0ms) cho các thuật ngữ giao diện game lặp lại (như "Inventory", "Attack", "Settings").
* **Tuần 5: Pipeline Thay thế Chữ tại chỗ Hoàn chỉnh (End-to-End Visual In-place Pipeline)**
  * Kết nối đồng bộ: Bắt khung hình DXGI $\rightarrow$ Frame Diff $\rightarrow$ DBNet $\rightarrow$ CTranslate2 MT $\rightarrow$ Aesthetic Blending $\rightarrow$ Render Overlay.
  * Đo đạc và tinh chỉnh độ trễ toàn trình đạt mục tiêu $\le 300\text{ms}$.
  * Kiểm soát bộ nhớ chia sẻ qua Shared CUDA Stream, khóa trần tổng VRAM dưới **850MB**.
* **Tuần 6: Tích hợp Module Âm thanh Phụ trợ (Audio Subtitle Pipeline)**
  * Tích hợp mạng Silero VAD để lọc sạch tạp âm và nhạc nền game, loại bỏ 100% hiện tượng tự sinh chữ rác (hallucination).
  * Kết nối Whisper-Base INT8 để hiển thị phụ đề cuộn mượt mà (Roll-up Subtitles) cho các đoạn phim cutscenes không có phụ đề chữ trên màn hình.

---

### Giai đoạn 3: Giao Diện Người Dùng & Trải Nghiệm Thẩm Mỹ (Tuần 7 – Tuần 9)
* **Tuần 7: Cửa Sổ Trong Suốt Zero-Touch & Click-Through**
  * Xây dựng giao diện Overlay trong suốt toàn màn hình bằng PyQt6 kết hợp Win32 API (`WS_EX_LAYERED | WS_EX_TRANSPARENT`).
  * Đảm bảo mọi thao tác chuột và phím xuyên qua overlay vào game / tài liệu phía sau 100%, không gây mất tiêu điểm (focus).
  * Kiểm tra tính an toàn: Xác nhận overlay là tiến trình đồ họa độc lập, tuyệt đối không chèn mã (DLL Injection) hay can thiệp RAM game, đạt độ an toàn 100% với Easy Anti-Cheat và BattlEye.
* **Tuần 8: Tinh Chỉnh Typography & Chống Va Chạm Giao Diện (Collision Avoidance)**
  * Áp dụng hiệu ứng viền tương phản (Stroke 1.5px) và bóng đổ nhẹ (Drop shadow) cho chữ dịch tiếng Việt, giúp chữ luôn nổi bật trên nền đồ họa 3D phức tạp.
  * Triển khai cơ chế né va chạm giao diện: Tự động phát hiện các vùng nhạy cảm của game (Minimap, thanh máu HP/MP) và tài liệu (sơ đồ, bảng biểu) để điều chỉnh vị trí hiển thị, tuyệt đối không che khuất thông tin quan trọng.
* **Tuần 9: Thanh Điều Khiển Nổi (Floating Widget) & Hồ Sơ Ứng Dụng (App Profiles)**
  * Thiết kế thanh điều khiển mini dạng Floating Widget neo ở góc màn hình, tự động thu nhỏ sau 3 giây không tương tác.
  * Cài đặt hệ thống phím tắt toàn cục (Global Hotkeys): `Alt + T` (Bật/tắt dịch nhanh), `Alt + S` (Chọn vùng quét tùy chỉnh), `Alt + D` (Chuyển chế độ Game / Tài liệu).
  * Hỗ trợ lưu cấu hình riêng cho từng tựa game và ứng dụng đọc tài liệu (Game Profiles & PDF Reader Profiles).

---

### Giai đoạn 4: Kiểm Thử Chịu Tải, Đồ Họa Game & Đóng Gói (Tuần 10 – Tuần 12)
* **Tuần 10: Thử Nghiệm Tương Thích Game 3D & Kiểm Soát Tụt Khung Hình (FPS Drop)**
  * Đo đạc hiệu năng thực tế trên các tựa game đồ họa nặng (Cyberpunk 2077, Baldur's Gate 3, Persona 3 Reload) chạy đồng thời với ứng dụng.
  * Bảo đảm mức tụt khung hình duy trì dưới **3%** (từ 60 FPS xuống không thấp hơn 58.2 FPS).
  * Chạy thử nghiệm liên tục trong 8 giờ để giám sát rò rỉ bộ nhớ (VRAM và RAM duy trì ổn định không tăng).
* **Tuần 11: Đa Chế Độ Hoạt Động (Offline & Hybrid Cloud)**
  * Cung cấp tùy chọn chuyển đổi linh hoạt: Chế độ Offline (mô hình nội bộ CTranslate2, bảo mật 100%) và Chế độ Hybrid Cloud (kết nối DeepL / Groq API khi người dùng có kết nối mạng và muốn độ chuẩn xác văn phong tối đa).
  * Xây dựng bộ tự động phát hiện phần cứng (Hardware Detector) để tinh chỉnh số luồng CPU / cấu hình GPU phù hợp nhất với máy người dùng.
* **Tuần 12: Đóng Gói Bộ Cài Đặt Độc Lập & Phát Hành Thử Nghiệm**
  * Đóng gói bản cài đặt độc lập (.msi / Inno Setup) tích hợp sẵn các runtime tối thiểu, không bắt buộc người dùng cài Python rời hay thiết lập CUDA phức tạp.
  * Phát hành bản Closed Beta đến cộng đồng game thủ JRPG và sinh viên kỹ thuật; thu thập phản hồi tinh chỉnh giao diện lần cuối.

---

## 5. PHÂN BỔ NHÂN SỰ & TRÁCH NHIỆM (RACI MATRIX)

| Vị trí nhân sự | Trách nhiệm chính trong dự án | Giai đoạn tập trung cao độ |
| :--- | :--- | :--- |
| **Lead AI/Vision Engineer** | Xây dựng pipeline OCR (DBNet + CRNN TensorRT), mô hình CTranslate2 INT8, thuật toán Background Sampling | Tuần 1 – Tuần 6 |
| **Systems / Graphics Engineer** | Lập trình DXGI Desktop Duplication, Win32 Transparent Overlay, Memory pool, Kiểm soát VRAM $< 850\text{MB}$ | Tuần 1 – Tuần 8 |
| **Frontend / UX Engineer** | Phát triển Typography, Font Auto-scaling, Click-through Overlay, Floating Widget, Profile Manager | Tuần 5 – Tuần 10 |
| **QA / Game Benchmark Tester** | Kiểm thử FPS game 3D, đo độ trễ toàn trình, kiểm tra rò rỉ bộ nhớ, kiểm chứng an toàn Anti-cheat | Tuần 4 – Tuần 12 |

---

## 6. QUẢN LÝ RỦI RO & PHƯƠNG ÁN DỰ PHÒNG

| Rủi ro kỹ thuật / vận hành | Khả năng | Ảnh hưởng | Phương án xử lý dự phòng đã thiết kế |
| :--- | :---: | :---: | :--- |
| **Văn bản tiếng Việt quá dài gây tràn viền bounding box** | Cao | Cao | Kích hoạt thuật toán Dynamic Font Auto-scaling: Tự động giảm kích thước font theo từng nấc 1pt kết hợp ngắt dòng theo từ, đảm bảo chữ luôn nằm gọn trong khung. |
| **Nền game là cảnh 3D chuyển động phức tạp làm mask bị lộ viền** | Trung bình | Trung bình | Áp dụng thuật toán làm mờ biên (Feathering) từ 2px – 4px kết hợp độ trong suốt linh hoạt (Alpha blending 85% – 95%), giúp mask tiệp tự nhiên vào đồ họa xung quanh. |
| **Hệ thống Anti-cheat nghi ngờ ứng dụng là phần mềm gian lận** | Thấp | Nghiêm trọng | Sử dụng 100% cơ chế Top-level Transparent Window tiêu chuẩn của Windows; tuyệt đối không hook DirectX, không đọc ghi bộ nhớ game, đảm bảo an toàn 100%. |
| **Máy người dùng chỉ có card đồ họa tích hợp Intel onboard** | Trung bình | Trung bình | Tự động chuyển pipeline OCR và MT sang chế độ ONNX INT8 đa luồng CPU; giới hạn vùng quét chủ động để duy trì tốc độ phản hồi $\le 500\text{ms}$. |

---

## 7. TIÊU CHÍ NGHIỆM THU DỰ ÁN (ACCEPTANCE CHECKLIST)

- [ ] **Tiêu chí thẩm mỹ:** Lớp che (mask) tiệp màu tự nhiên với nền game/tài liệu, không xuất hiện khối hộp chữ nhật đen xì thô thiển; sai số màu sắc $\Delta E \le 2.5$.
- [ ] **Tiêu chí không tràn viền:** $100\%$ các đoạn văn bản dịch tiếng Việt tự động co giãn kích thước vừa khít trong bounding box gốc, không bị đè lấn ra ngoài hay che mất các thành phần UI khác.
- [ ] **Tiêu chí thời gian thực:** Độ trễ từ khi khung hình thay đổi đến khi chữ dịch hiển thị tại chỗ trên overlay không vượt quá **300ms**.
- [ ] **Tiêu chí tài nguyên phần cứng:** Tổng mức chiếm dụng VRAM hiển thị trên `nvidia-smi` duy trì dưới **850MB** khi chạy đồng thời cả module hình ảnh và âm thanh.
- [ ] **Tiêu chí đồ họa game:** Mức sụt giảm khung hình (FPS Drop) khi chơi game 3D chạy song song với ứng dụng duy trì dưới **3%** (đảm bảo trải nghiệm 60 FPS mượt mà).
- [ ] **Tiêu chí an toàn Anti-cheat:** Hoạt động độc lập ngoài tiến trình game, không bị phát hiện hay cấm bởi các hệ thống chống gian lận tiêu chuẩn.
- [ ] **Tiêu chí đóng gói:** Bộ cài đặt độc lập (.exe/.msi), tự động nhận diện phần cứng và hoạt động ngay sau khi cài mà không yêu cầu cấu hình môi trường phức tạp.