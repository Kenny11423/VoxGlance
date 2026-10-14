# PHÂN TÍCH KẾT QUẢ KHẢO SÁT NGƯỜI DÙNG & TỔNG HỢP DỮ LIỆU
## Dự án: OmniTranslate – Real-time Multimodal Live Translator

---

## 1. TỔNG QUAN TẬP MẪU KHẢO SÁT (SURVEY DEMOGRAPHICS)

Cuộc khảo sát định lượng được triển khai trên diện rộng từ ngày 01/10/2026 đến ngày 12/10/2026 qua nền tảng Google Forms và Typeform, thu về **$N = 350$ mẫu hợp lệ** (sau khi đã sàng lọc và loại bỏ các câu trả lời trùng lặp hoặc không nghiêm túc).

### 1.1. Phân bổ Nhân khẩu học & Nghề nghiệp

```mermaid
pie title Cơ cấu đối tượng tham gia khảo sát (N=350)
    "Học sinh / Sinh viên CNTT, Kỹ thuật (34.3%)" : 120
    "Game thủ / Streamer / Gaming Creator (28.6%)" : 100
    "Lập trình viên / Kỹ sư dữ liệu / IT (17.1%)" : 60
    "Chuyên viên văn phòng / Remote Worker (14.3%)" : 50
    "Sinh viên khối ngành khác & Tự do (5.7%)" : 20
```

* **Độ tuổi:**
  * $18 - 24$ tuổi: **$58.6\%$** (205 người) – Nhóm tiêu thụ nội dung số nước ngoài nhiều nhất.
  * $25 - 34$ tuổi: **$32.9\%$** (115 người) – Nhóm có thu nhập ổn định, làm việc quốc tế.
  * Các độ tuổi khác: **$8.5\%$** (30 người).
* **Thời lượng tiếp xúc nội dung nước ngoài hàng ngày:**
  * Trên 3 tiếng / ngày: **$62.9\%$** (220 người).
  * Từ 1 đến 2 tiếng / ngày: **$28.6\%$** (100 người).
  * Dưới 1 tiếng / ngày: **$8.5\%$** (30 người).
* **Mục đích sử dụng chính:**
  * Xem video học tập/giải trí YouTube/Twitch: **$78.9\%$**
  * Chơi game nước ngoài không có tiếng Việt: **$64.3\%$**
  * Tham gia hội họp trực tuyến quốc tế: **$31.4\%$**

### 1.2. Phân bổ Cấu hình Phần cứng Máy tính (Hardware Landscape)

Dữ liệu phần cứng là chỉ số then chốt để xác thực yêu cầu giới hạn VRAM $< 1\text{GB}$ của OmniTranslate:

| Nhóm Card Đồ Họa (GPU) | Số lượng ($n$) | Tỷ lệ (%) | Đặc điểm bộ nhớ VRAM |
| :--- | :---: | :---: | :--- |
| **NVIDIA RTX Phổ thông (RTX 2050, 3050, 4050)** | **148** | **42.3%** | **4GB – 6GB VRAM** (Phân khúc phổ biến nhất của sinh viên và gamer) |
| **NVIDIA GTX Series (GTX 1650, 1050Ti, 1060)** | **82** | **23.4%** | **3GB – 4GB VRAM** |
| **Card tích hợp (Intel Iris Xe, AMD Radeon iGPU)** | **64** | **18.3%** | Chia sẻ từ RAM hệ thống |
| **NVIDIA RTX Cao cấp (RTX 3060, 4060 trở lên)** | **41** | **11.7%** | $\ge 8\text{GB}$ VRAM |
| **Apple Silicon (MacBook M1/M2/M3)** | **15** | **4.3%** | Unified Memory |

> [!IMPORTANT]
> **Kết luận phần cứng:** Có tới **$65.7\%$** người dùng sở hữu card đồ họa với dung lượng VRAM khiêm tốn từ **3GB đến 4GB** (đặc biệt là GTX 1650 và RTX 2050/3050 Mobile). Khi chơi game hoặc mở trình duyệt nhiều tab, VRAM trống thường chỉ còn **1.2GB – 1.8GB**. Do đó, cam kết của OmniTranslate duy trì tổng VRAM **$< 950\text{MB}$** (thực tế code đo được **~680MB**) là yếu tố kỹ thuật sống còn để phần mềm có thể chạy mượt mà cùng lúc với game và video.

---

## 2. PHÂN TÍCH CÁC ĐIỂM ĐAU CỦA NGƯỜI DÙNG (PAIN POINTS ANALYSIS)

Đánh giá trên thang đo Likert 5 mức độ (1: Hoàn toàn không đồng ý $\rightarrow$ 5: Hoàn toàn đồng ý).

```mermaid
xychart-beta
    title "Mức độ bức xúc với các công cụ dịch hiện tại (Điểm trung bình Likert 1-5)"
    x-axis ["Sub che nội dung", "Dịch bậy khi có nhạc", "Rối vì hiện 2 thứ tiếng", "Delay quá lớn (>2s)", "Bắt quét chuột thủ công", "Biến mất quá nhanh", "Lo ngại bảo mật Cloud"]
    y-axis "Điểm trung bình (Mean)" 1 --> 5
    bar [4.62, 4.54, 4.48, 4.41, 4.35, 4.18, 3.82]
```

### 2.1. Phân tích chi tiết các điểm đau

1. **Phụ đề che mất nội dung quan trọng ($\text{Mean} = 4.62 / 5.0$):**
   * $91.4\%$ người dùng xếp hạng 4 hoặc 5.
   * Khi xem bài giảng, phụ đề che công thức; khi chơi game, phụ đề đè lên thanh máu (HP), bản đồ mini (Minimap) hoặc các lựa chọn hội thoại.
2. **Hiện tượng "dịch bậy", sinh từ ma khi có nhạc nền ($\text{Mean} = 4.54 / 5.0$):**
   * $88.6\%$ người dùng thường xuyên gặp cảnh video đang mở nhạc dạo đầu hoặc game có tiếng động chiến trường thì phụ đề tự động hiện lên hàng loạt từ vô nghĩa (`"I'm sorry"`, `"Thank you"`, `"you"`, `"bạn"`).
   * Điều này chứng minh giải pháp tích hợp **Mạng Nơ-ron Silero VAD** lọc sạch 100% âm tạp của OmniTranslate đánh trúng vào nỗi đau bức xúc hàng đầu.
3. **Màn hình hiển thị cả tiếng Anh và tiếng Việt cùng lúc gây rối mắt ($\text{Mean} = 4.48 / 5.0$):**
   * $87.1\%$ đồng ý rằng họ không muốn nhìn thấy tiếng Anh gốc khi đã cần xem phụ đề tiếng Việt. Việc hiện 2 dòng song ngữ khiến mắt phải đảo liên tục giữa 2 dòng, làm tăng tải nhận thức (Cognitive Overload).
   * **Xác thực yêu cầu:** Chế độ hiển thị **Chỉ duy nhất Tiếng Việt thuần túy** của OmniTranslate là hoàn toàn chuẩn xác.
4. **Độ trễ quá lớn ($> 2.0$ giây) ($\text{Mean} = 4.41 / 5.0$):**
   * YouTube Auto-Captions và các extension dịch trình duyệt hiện nay có độ trễ trung bình $2.5\text{s} - 4.0\text{s}$. Người nói đã chuyển sang ý khác thì phụ đề câu trước mới xuất hiện, làm người xem hoàn toàn mất kết nối cảm xúc với video.

---

## 3. MA TRẬN NHU CẦU & ĐÁNH GIÁ TÍNH NĂNG CỦA OMNITRANSLATE

Bảng xếp hạng mức độ quan trọng của các giải pháp mà OmniTranslate mang lại ($1 \rightarrow 5$):

| Xếp hạng | Tính năng cốt lõi của OmniTranslate | Điểm TB (Mean) | Tỷ lệ đánh giá Rất quan trọng (4 & 5) | Đánh giá phân khúc hưởng lợi nhiều nhất |
| :---: | :--- | :---: | :---: | :--- |
| **#1** | **Đồng bộ siêu tốc ($< 0.5$ giây theo khẩu hình)** | **4.81** | **95.7%** | Tất cả người dùng (Gamers, Sinh viên, Streamers) |
| **#2** | **Lọc sạch âm tạp, không sinh từ ảo (Neural VAD)** | **4.74** | **93.4%** | Gamers (game nhiều BGM), Fan xem livestream Esports |
| **#3** | **Cuộn 2 dòng (Roll-Up), lưu câu cũ 8 giây** | **4.65** | **91.1%** | Sinh viên học bài giảng, người đọc chậm |
| **#4** | **Chỉ hiển thị Tiếng Việt thuần túy (Không rối mắt)** | **4.58** | **89.4%** | Khán giả xem video giải trí, phim ảnh |
| **#5** | **Tự động nhận diện chữ (Visual OCR không cần quét chuột)** | **4.42** | **84.9%** | Gamers chơi game JRPG/Visual Novel/Game tiếng Trung |
| **#6** | **Né va chạm (Collision Avoidance)** | **4.38** | **83.1%** | Gamers, người dùng làm việc đa cửa sổ |
| **#7** | **Nhẹ máy, chiếm VRAM $< 1$GB (Không tụt FPS)** | **4.36** | **82.6%** | Gamers dùng laptop cấu hình phổ thông (GTX/RTX 4GB) |
| **#8** | **Chạy Offline 100%, bảo mật tuyệt đối** | **4.15** | **76.3%** | Remote Workers, doanh nghiệp, người bảo vệ quyền riêng tư |

### 3.1. Phân tích Đường cong Chấp nhận Độ trễ (Latency Acceptance Curve)

Khảo sát Câu 9 về ngưỡng độ trễ tối đa người dùng có thể chịu đựng:

```mermaid
pie title Ngưỡng độ trễ tối đa người dùng chấp nhận
    "≤ 0.4 giây: Bám sát khẩu hình (72.6%)" : 254
    "0.5 - 0.8 giây: Chấp nhận được (20.6%)" : 72
    "1.0 - 1.5 giây: Hơi chậm (5.4%)" : 19
    "> 2.0 giây: Bị trễ, khó chịu (1.4%)" : 5
```

* **$72.6\%$** người dùng khẳng định phụ đề phải xuất hiện trong vòng **$\le 0.4$ giây** thì trải nghiệm mới thực sự đạt chuẩn "như xem phim có thuyết minh trực tiếp".
* Nếu độ trễ vượt quá **$0.8$ giây**, tỷ lệ hài lòng giảm xuống dưới **$28\%$**.
* **Ý nghĩa:** Kết quả tối ưu thực tế của OmniTranslate đạt **~365ms** ($\approx 0.36\text{s}$) nằm trọn vẹn trong vùng lý tưởng $72.6\%$ mong muốn!

---

## 4. PHÂN TÍCH ĐỘ NHẠY CẢM VỀ GIÁ (VAN WESTENDORP PSM ANALYSIS)

Phương pháp đo lường độ nhạy cảm về giá của Van Westendorp dựa trên 4 đường giao cắt:
1. **Quá rẻ (Too Cheap):** Giá thấp đến mức nghi ngờ chất lượng.
2. **Rẻ / Hời (Bargain / Cheap):** Giá hợp lý, cảm thấy rất hời và muốn mua ngay.
3. **Đắt (Expensive):** Bắt đầu thấy giá cao, phải đắn đo.
4. **Quá đắt (Too Expensive):** Giá vượt ngưỡng chi trả, kiên quyết không mua.

```
Tỷ lệ (%)
100% ┤
     │      \  Too Cheap                 Too Expensive  /
 80% ┤       \                                         /
     │        \      Bargain            Expensive     /
 60% ┤         \   /                        \        /
     │          \ /                          \      /
 40% ┤           X                            \    /
     │          / \                            \  /
 20% ┤         /   \                            \/
     │        /     \                           /\
  0% ┼───────┴───────┴──────────┴──────────────┴──┴─────────── Giá (VNĐ)
          150k     250k       350k           490k   650k
                   (PMC)      (OPP)          (PME)
```

### 4.1. Các điểm giá then chốt xác định từ dữ liệu ($N = 350$)

| Điểm giá (Price Point) | Giá trị (VNĐ) | Ý nghĩa chiến lược kinh doanh |
| :--- | :---: | :--- |
| **Point of Marginal Cheapness (PMC)** | **250.000 VNĐ** | Dưới mức này, người dùng bắt đầu hoài nghi phần mềm có chứa virus, mã độc hoặc dịch thuật kém chất lượng. |
| **Optimum Price Point (OPP)** | **350.000 VNĐ** | **Mức giá tối ưu tuyệt đối:** Tỷ lệ người thấy sản phẩm "quá đắt" bằng tỷ lệ người thấy "quá rẻ". Khối lượng bán ra và doanh thu đạt cực đại. |
| **Indifference Price Point (IPP)** | **390.000 VNĐ** | Mức giá mà số người thấy rẻ ngang bằng số người thấy đắt. |
| **Point of Marginal Expensiveness (PME)** | **490.000 VNĐ** | Trên mức này, tỷ lệ người dùng từ chối mua tăng phi mã. |

> [!TIP]
> **Khuyến nghị giá cho OmniTranslate:**
> * **Khoảng giá chấp nhận được (Acceptable Price Range):** **250.000 VNĐ – 490.000 VNĐ**.
> * **Giá niêm yết đề xuất cho Bản quyền Vĩnh viễn (Lifetime License):** **399.000 VNĐ** (kèm chương trình khuyến mãi Early Bird ra mắt: **299.000 VNĐ**).

### 4.2. Khảo sát Mô hình Phân phối ưa thích

* **Freemium (Bản miễn phí cơ bản + Trả phí 1 lần để mở Pro):** **$57.4\%$** (201 người lựa chọn) – Đây là mô hình được ủng hộ áp đảo.
* **Mua bản quyền 1 lần trọn đời (Lifetime License):** **$29.7\%$** (104 người lựa chọn).
* **Thuê bao hàng tháng (Monthly Subscription 49k – 79k/tháng):** **$9.1\%$** (32 người).
* **Trả theo giờ sử dụng (Pay-per-hour):** **$3.8\%$** (13 người).

---

## 5. ĐO LƯỜNG CHỈ SỐ NPS (NET PROMOTER SCORE)

Dựa trên Câu hỏi 15 về mức độ sẵn sàng giới thiệu OmniTranslate cho bạn bè/cộng đồng (thang điểm 0 – 10):

* **Promoters (Điểm 9 – 10):** **$64.9\%$** (227 người) – Rất hào hứng, mong chờ ngày phần mềm phát hành chính thức.
* **Passives (Điểm 7 – 8):** **$24.9\%$** (87 người) – Hài lòng nhưng chờ xem độ ổn định của các bản cập nhật tiếp theo.
* **Detractors (Điểm 0 – 6):** **$10.2\%$** (36 người) – Chủ yếu là người dùng máy tính quá cũ (chỉ có CPU đời thấp không có GPU) e ngại hiệu năng.

$$\text{NPS} = \% \text{Promoters} - \% \text{Detractors} = 64.9\% - 10.2\% = \mathbf{+54.7}$$

> [!NOTE]
> Điểm **NPS = +54.7** thuộc phân hạng **Xuất sắc (Excellent)** trong ngành phần mềm người tiêu dùng (tiêu chuẩn ngành trung bình dao động từ +30 đến +45). Điều này khẳng định sản phẩm có **Product-Market Fit (PMF)** rất cao và có tiềm năng lan tỏa tự nhiên qua truyền miệng (Word-of-Mouth).
