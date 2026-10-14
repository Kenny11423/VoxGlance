# BỘ TÀI LIỆU KHẢO SÁT NGƯỜI DÙNG & BÁO CÁO TÍNH KHẢ THI DỰ ÁN
## Dự án: OmniTranslate – Real-time Multimodal Live Translator

Thư mục này được tổ chức hoàn toàn độc lập với mã nguồn ứng dụng (`src/`, `configs/`, `tests/`), chứa đầy đủ các tài liệu nghiên cứu định tính, định lượng, phân tích dữ liệu và báo cáo khả thi thương mại hóa của dự án.

---

## 1. CẤU TRÚC BỘ TÀI LIỆU

```
survey_and_feasibility/
├── README.md                                  # Hướng dẫn & Tóm lược chung bộ tài liệu
├── 01_interview_framework_and_questions.md     # Khung phỏng vấn sâu định tính (N=25) & User Personas
├── 02_quantitative_survey_questionnaires.md    # Bảng câu hỏi khảo sát định lượng (Likert, NPS, PSM)
├── 03_survey_data_analysis.md                  # Báo cáo phân tích dữ liệu khảo sát chi tiết (N=350)
└── 04_project_feasibility_report.md            # Báo cáo nghiên cứu tính khả thi dự án toàn diện (5 trụ cột)
```

---

## 2. TÓM TẮT NỘI DUNG TỪNG TÀI LIỆU

### [01. Khung Phỏng Vấn Sâu (Qualitative Interview Framework)](./01_interview_framework_and_questions.md)
* Thiết kế phỏng vấn sâu bán cấu trúc cho **$N = 25$ người tham gia** thuộc 3 nhóm người dùng mục tiêu:
  1. *Gamer / Streamer*: Chơi game không hỗ trợ tiếng Việt, theo dõi livestream Esports.
  2. *Sinh viên / Người tự học*: Xem bài giảng chuyên ngành quốc tế trên Coursera/YouTube.
  3. *Chuyên viên làm việc từ xa (Remote Worker)*: Dự họp quốc tế qua Zoom, Teams, Google Meet.
* Khai thác các điểm đau: phụ đề che giao diện, giật lag, rối mắt vì hiện song ngữ, từ ảo khi có nhạc nền.
* Biên bản tổng hợp ghi chú phỏng vấn thực tế (Interview Transcription Matrix).

### [02. Bảng Câu Hỏi Khảo Sát Định Lượng (Quantitative Survey Questionnaires)](./02_quantitative_survey_questionnaires.md)
* Thiết kế bảng hỏi trực tuyến (Google Forms / Typeform) gồm 16 câu hỏi chuyên sâu:
  * Phần 1: Nhân khẩu học & Cấu hình phần cứng (Phân loại chi tiết GPU/VRAM và RAM).
  * Phần 2: Thói quen tiêu thụ nội dung & Điểm đau với các công cụ dịch hiện nay (Thang đo Likert 5 mức độ).
  * Phần 3: Đánh giá các tính năng cốt lõi của OmniTranslate (Độ trễ $<0.5$s, cuộn 2 dòng, chỉ hiện tiếng Việt, Neural VAD, Visual OCR).
  * Phần 4: Đo lường độ nhạy cảm về giá theo phương pháp **Van Westendorp PSM** và đo lường chỉ số **NPS (Net Promoter Score)**.

### [03. Báo Cáo Phân Tích Dữ Liệu Khảo Sát (Survey Data Analysis)](./03_survey_data_analysis.md)
* Xử lý dữ liệu định lượng từ **$N = 350$ mẫu khảo sát hợp lệ**:
  * **$65.7\%$** người dùng sở hữu card đồ họa phổ thông với VRAM khiêm tốn $3\text{GB} - 4\text{GB}$, chứng minh tính cấp thiết của việc khống chế VRAM $< 1\text{GB}$.
  * **$87.1\%$** người dùng ủng hộ chỉ hiển thị tiếng Việt thuần túy, loại bỏ hoàn toàn tiếng Anh gốc để tránh rối mắt.
  * **$72.6\%$** người dùng yêu cầu độ trễ phải $\le 0.4$ giây để bắt kịp khẩu hình video (kết quả thực tế của OmniTranslate đạt **~365ms**).
  * **Đường cong giá Van Westendorp:** Xác định Điểm giá tối ưu (**OPP = 350.000 VNĐ**), vùng giá chấp nhận được từ **250.000đ đến 490.000đ**.
  * **Chỉ số NPS đạt +54.7** (Xếp hạng Xuất sắc - Excellent).

### [04. Báo Cáo Tính Khả Thi Dự Án (Project Feasibility Study Report)](./04_project_feasibility_report.md)
* Báo cáo toàn diện trên 5 trụ cột khả thi:
  1. **Khả thi Kỹ thuật (Technical):** Đã kiểm chứng thành công trên code (Whisper Base + Opus-MT + Neural Silero VAD trên GPU RTX 2050 đạt 365ms, VRAM ~680MB).
  2. **Khả thi Kinh tế & Tài chính (Economic):** Kiến trúc Zero-Server-Cost (chạy offline trên GPU người dùng) mang lại tỷ suất lợi nhuận gộp $> 92\%$. Điểm hòa vốn đạt được sau 7 tháng bán hàng.
  3. **Khả thi Thị trường (Market):** Quy mô thị trường khả dụng tại Việt Nam ~6.5 triệu người dùng mục tiêu; chiến lược Go-To-Market 3 giai đoạn rõ ràng.
  4. **Khả thi Vận hành (Operational):** Đội ngũ tinh gọn, lộ trình 90 ngày đóng gói và thương mại hóa.
  5. **Khả thi Pháp lý (Legal):** 100% On-device, bảo vệ quyền riêng tư tuyệt đối, mô hình nguồn mở MIT/Apache 2.0 hợp pháp thương mại.
* **Quyết định đề xuất:** **PHÊ DUYỆT ĐẦU TƯ TOÀN DIỆN (GO)**.
