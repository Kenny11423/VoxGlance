# BỘ TÀI LIỆU KHẢO SÁT NGƯỜI DÙNG & BÁO CÁO TÍNH KHẢ THI DỰ ÁN
## Dự án: VoxGlance – Real-time Multimodal Live Translator
### Căn cứ thực nghiệm: Steam Hardware Survey, Windows 11 Docs, DeepL Pro, Whisper Tracker, Voz & Tinh Tế

Thư mục này được tổ chức hoàn toàn độc lập với mã nguồn ứng dụng (`src/`, `configs/`, `tests/`), chứa đầy đủ các tài liệu nghiên cứu định tính, thiết kế bảng câu hỏi khảo sát, báo cáo phân tích nhu cầu thực nghiệm trực tuyến và báo cáo khả thi thương mại hóa của dự án.

---

## 1. CẤU TRÚC BỘ TÀI LIỆU

```
survey_and_feasibility/
├── README.md                                  # Hướng dẫn & Tóm lược chung bộ tài liệu
├── 01_interview_framework_and_questions.md     # Khung phỏng vấn sâu định tính & User Personas
├── 02_quantitative_survey_questionnaires.md    # Bảng câu hỏi khảo sát định lượng (Likert, NPS, PSM)
├── 03_survey_data_analysis.md                  # Báo cáo phân tích nhu cầu & Dữ liệu thực nghiệm trực tuyến
└── 04_project_feasibility_report.md            # Báo cáo nghiên cứu tính khả thi dự án toàn diện (5 trụ cột)
```

---

## 2. TÓM TẮT NỘI DUNG TỪNG TÀI LIỆU

### [01. Khung Phỏng Vấn Sâu (Qualitative Interview Framework)](./01_interview_framework_and_questions.md)
* Thiết kế phỏng vấn sâu bán cấu trúc cho người dùng thuộc 3 nhóm đối tượng mục tiêu:
  1. *Gamer / Streamer*: Chơi game không hỗ trợ tiếng Việt, theo dõi livestream Esports.
  2. *Sinh viên / Người tự học*: Xem bài giảng chuyên ngành quốc tế trên Coursera/YouTube.
  3. *Chuyên viên làm việc từ xa (Remote Worker)*: Dự họp quốc tế qua Zoom, Teams, Google Meet.
* Đào sâu các điểm đau với công cụ thực tế: Translumo (điếc âm thanh), LunaTranslator (nguy cơ bị Anti-cheat cấm tài khoản), YouTube Captions (trễ 2–4s, dịch bậy khi có nhạc).
* Kịch bản phỏng vấn Thinking Aloud kết hợp biên bản thực nghiệm.

### [02. Bảng Câu Hỏi Khảo Sát Định Lượng (Quantitative Survey Questionnaires)](./02_quantitative_survey_questionnaires.md)
* Thiết kế bảng hỏi trực tuyến chuẩn hóa phân phối trên các diễn đàn công nghệ (Voz, Tinh Tế) và cộng đồng game thủ:
  * Phần 1: Phân loại nhân khẩu học & Chi tiết GPU/VRAM máy tính.
  * Phần 2: Thói quen tiêu thụ nội dung & Điểm đau với các công cụ dịch hiện nay (Thang đo Likert 5 mức độ).
  * Phần 3: Đánh giá các tính năng cốt lõi của VoxGlance (Độ trễ $<0.5$s, cuộn 2 dòng, chỉ hiện tiếng Việt, Neural Silero VAD, Visual OCR).
  * Phần 4: Đo lường độ nhạy cảm về giá theo phương pháp **Van Westendorp PSM** và đo lường chỉ số **NPS (Net Promoter Score)**.

### [03. Báo Cáo Phân Tích Nhu Cầu & Dữ Liệu Thực Nghiệm Trực Tuyến (Online Empirical Analysis)](./03_survey_data_analysis.md)
* Loại bỏ hoàn toàn số liệu giả lập, tổng hợp căn cứ từ **5 nguồn trực tuyến có thẩm quyền**:
  * **Valve Steam Hardware Survey:** Hơn $28.5\%$ người dùng sử dụng GPU phổ thông 4GB VRAM (GTX 1650, RTX 2050/3050). Khi game chiếm 2.5GB–3.5GB, phần mềm dịch nền bắt buộc phải ăn VRAM $< 1\text{GB}$ (VoxGlance tiêu thụ thực tế **~680MB**).
  * **Cộng đồng Voz, Tinh Tế, GameVN:** Phân tích điểm nghẽn của các giải pháp hiện tại: Translumo/MORT chỉ OCR hình ảnh và điếc âm thanh; phụ thuộc Cloud API dễ dính lỗi Rate Limit 429; LunaTranslator hook RAM dễ bị cấm nick vĩnh viễn.
  * **OpenAI Whisper GitHub Issues #679, #928:** Xác thực hiện tượng decoder lặp từ ma khi có nhạc nền và giải pháp Silero VAD + `condition_on_previous_text=False`.
  * **Microsoft Windows 11 Docs:** Windows Live Translation đòi hỏi Copilot+ PC trang bị NPU $\ge 40$ TOPS đắt tiền và **hoàn toàn không hỗ trợ Tiếng Việt**.
  * **Chi phí DeepL Pro:** \$8.74/tháng (~2.6 triệu/năm) vượt quá túi tiền học sinh/game thủ; khẳng định tính khả thi của mô hình Freemium + Bản quyền Trọn đời 299k–399k VNĐ.

### [04. Báo Cáo Tính Khả Thi Dự Án (Project Feasibility Study Report)](./04_project_feasibility_report.md)
* Báo cáo toàn diện trên 5 trụ cột khả thi:
  1. **Khả thi Kỹ thuật (Technical):** Đã kiểm chứng thành công trên code (Whisper Base + Opus-MT + Neural Silero VAD trên GPU RTX 2050 đạt ~365ms, VRAM ~680MB).
  2. **Khả thi Kinh tế & Tài chính (Economic):** Kiến trúc Zero-Server-Cost (chạy offline trên GPU người dùng) mang lại tỷ suất lợi nhuận gộp $> 92\%$. Điểm hòa vốn chỉ cần ~579 bản quyền Pro.
  3. **Khả thi Thị trường (Market):** Lấp đầy khoảng trống mà Windows 11 và DeepL Pro bỏ ngỏ tại Việt Nam; chiến lược Go-To-Market 3 giai đoạn rõ ràng.
  4. **Khả thi Vận hành (Operational):** Đội ngũ tinh gọn, kế hoạch quản trị rủi ro chủ động.
  5. **Khả thi Pháp lý (Legal):** 100% On-device, bảo vệ quyền riêng tư tuyệt đối, mô hình nguồn mở MIT/Apache 2.0 hợp pháp thương mại.
* **Quyết định đề xuất:** **PHÊ DUYỆT ĐẦU TƯ TOÀN DIỆN (GO)**.
