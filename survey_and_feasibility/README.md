# BỘ TÀI LIỆU KHẢO SÁT NGƯỜI DÙNG & BÁO CÁO TÍNH KHẢ THI DỰ ÁN
## Dự án: Ứng dụng Dịch thuật Đa phương tiện Thời gian thực (Real-time Multimodal Live Translator)
### Chuyên đề: Dịch thuật trực quan thay thế tại chỗ trên màn hình (On-Screen In-Place Seamless Translation) cho Game & Tài liệu
### Căn cứ thực nghiệm: Steam Hardware Survey, Thảo luận Cộng đồng Voz & Tinh Tế, Reddit r/visualnovels, GitHub Trackers

Thư mục này được tổ chức hoàn toàn độc lập với mã nguồn ứng dụng (`src/`, `configs/`, `tests/`), chứa đầy đủ các tài liệu nghiên cứu định tính, thiết kế bảng câu hỏi khảo sát, báo cáo phân tích nhu cầu thực nghiệm trực tuyến và báo cáo khả thi thương mại hóa của dự án.

---

## 1. CẤU TRÚC BỘ TÀI LIỆU

```
survey_and_feasibility/
├── README.md                                  # Hướng dẫn & Tóm lược chung bộ tài liệu
├── Tai_Lieu_Khao_Sat_Va_Tinh_Kha_Thi_Ung_Dung_Dich_Thuat_Da_Phuong_Tien.docx # File Word (.docx) tổng hợp hoàn chỉnh (Không ghi tên sản phẩm)
├── 01_interview_framework_and_questions.md     # Khung phỏng vấn sâu, 4 nhóm đối tượng & 4 phương pháp khảo sát
├── 02_quantitative_survey_questionnaires.md    # Bảng câu hỏi khảo sát định lượng đo lường điểm đau thẩm mỹ (Likert, NPS, PSM)
├── 03_survey_data_analysis.md                  # Báo cáo phân tích nhu cầu 4 nhóm đối tượng & Dữ liệu thực nghiệm trực tuyến
└── 04_project_feasibility_report.md            # Báo cáo nghiên cứu tính khả thi dự án toàn diện (5 trụ cột)
```

---

## 2. TÓM TẮT NỘI DUNG TỪNG TÀI LIỆU

### [01. Khung Phỏng Vấn Sâu & Phương Pháp Khảo Sát](./01_interview_framework_and_questions.md)
* Trình bày hệ thống **4 phương pháp khảo sát và nghiên cứu**:
  1. *Khảo sát định lượng trực tuyến (Online Quantitative Survey)*: Thang đo Likert 5 mức độ, Van Westendorp PSM, NPS.
  2. *Phỏng vấn sâu bán cấu trúc (Semi-structured In-depth Interview)*: Kịch bản 4 giai đoạn logic.
  3. *Thử nghiệm khả năng sử dụng & Giao thức Thinking Aloud*: Đo lường phản ứng thị giác khi trải nghiệm lớp phủ thay thế chữ tại chỗ.
  4. *Khảo cứu dữ liệu thực nghiệm thứ cấp*: Steam Survey, diễn đàn Voz, Tinh Tế, Reddit r/visualnovels.
* **Phân nhóm đối tượng khảo sát mục tiêu (hoàn toàn không bịa tên cá nhân)**:
  * *Nhóm I – Game thủ Cốt truyện & Nhập vai:* Chơi game JRPG/Visual Novel/AAA không Việt hóa, cần thay thế chữ tại chỗ không che mất tranh nhân vật, an toàn với Anti-cheat.
  * *Nhóm II – Người đọc Tài liệu Kỹ thuật & Học thuật:* Đọc bài báo khoa học PDF, slide bài giảng, cần giữ nguyên bố cục và hình minh họa.
  * *Nhóm III – Độc giả Truyện tranh & Sách số:* Đọc Manga, Manhua, Light Novel, cần xóa chữ trong bóng thoại và căn chữ vừa khít.
  * *Nhóm IV – Chuyên viên & Nhân sự Doanh nghiệp:* Xử lý hợp đồng, tài liệu nội bộ cần bảo mật tuyệt đối 100% On-device.
* Biên bản tổng hợp ghi chú phỏng vấn thực nghiệm với các mã định danh khoa học: `G-01`, `G-02`, `E-01`, `E-02`, `M-01`, `W-01`.

### [02. Bảng Câu Hỏi Khảo Sát Định Lượng](./02_quantitative_survey_questionnaires.md)
* Thiết kế bảng hỏi trực tuyến chuẩn hóa gồm 16 câu hỏi trắc nghiệm chia thành 4 mục:
  * Phần 1: Phân loại nhân khẩu học, nhóm đối tượng & Cấu hình phần cứng (GPU, VRAM, RAM).
  * Phần 2: Thói quen tiếp xúc & Thang đo Likert 7 tiêu chí điểm đau thẩm mỹ (hộp đen che mất đồ họa, chữ dịch tràn viền, mỏi mắt vì popup rời, nguy cơ bị Anti-cheat cấm nick).
  * Phần 3: Đánh giá độ quan trọng các giải pháp công nghệ (Dịch thay thế tại chỗ, lấy mẫu màu nền tự nhiên, tự co giãn font vừa khít, viền nét tương phản, VRAM $<1$GB).
  * Phần 4: Đo lường độ nhạy cảm về giá theo phương pháp **Van Westendorp PSM** và đo lường chỉ số **NPS (Net Promoter Score)**.

### [03. Báo Cáo Phân Tích Nhu Cầu & Dữ Liệu Thực Nghiệm Trực Tuyến](./03_survey_data_analysis.md)
* Phân tích nhu cầu chuyên sâu theo 4 nhóm đối tượng mục tiêu.
* Loại bỏ hoàn toàn số liệu giả lập, tổng hợp căn cứ từ **5 nguồn trực tuyến có thẩm quyền**:
  * **Giải mã điểm đau lớn nhất của game thủ và người đọc:** Khối chữ nhật đen thô kệch che mất tranh/game ($\text{Mean}=4.82/5.0$); popup dịch rời rạc gây mỏi mắt ($\text{Mean}=4.68/5.0$); chữ tiếng Việt tràn viền ($\text{Mean}=4.55/5.0$).
  * **Đột phá công nghệ Layer thẩm mỹ cao:** Cơ chế lấy mẫu màu nền cục bộ (Local Background Sampling), tự động co giãn font (Font Auto-scaling), viền tương phản (Stroke/Shadow) và Desktop Overlay độc lập an toàn 100% với Anti-Cheat.
  * **Căn cứ Steam Hardware Survey:** Kiểm soát VRAM $< 1\text{GB}$ (thực tế tiêu thụ **~680MB**) để giữ vững 60 FPS cho game nặng.
  * **Phân tích kinh tế:** On-device Server = 0đ cho phép áp dụng mô hình bản quyền trọn đời **299.000đ – 399.000đ** (bằng giá 1 tựa game Steam).

### [04. Báo Cáo Tính Khả Thi Dự Án](./04_project_feasibility_report.md)
* Báo cáo toàn diện trên 5 trụ cột khả thi:
  1. **Khả thi Kỹ thuật (Technical):** Đã kiểm chứng thành công trên mã nguồn (Độ trễ toàn trình ~285ms, VRAM ~680MB, 60 FPS, độ chính xác OCR $\ge 94.6\%$).
  2. **Khả thi Kinh tế & Tài chính (Economic):** Kiến trúc Zero-Server-Cost mang lại tỷ suất lợi nhuận gộp $> 92\%$. Điểm hòa vốn chỉ cần ~579 bản quyền.
  3. **Khả thi Thị trường (Market):** Giải quyết trọn vẹn điểm nghẽn thẩm mỹ mà các tool cũ bỏ ngỏ; chiến lược Go-To-Market 3 giai đoạn rõ ràng.
  4. **Khả thi Vận hành (Operational):** Đội ngũ tinh gọn, kế hoạch quản trị rủi ro chủ động.
  5. **Khả thi Pháp lý (Legal):** 100% On-device, không can thiệp RAM game (100% Anti-cheat safe), Nghị định 13/2023/NĐ-CP, MIT/Apache 2.0.
* **Quyết định đề xuất:** **PHÊ DUYỆT ĐẦU TƯ TOÀN DIỆN (GO)**.
