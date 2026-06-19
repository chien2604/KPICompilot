# Danh Sách Test Cases Kiểm Thử Các Trường Hợp Tính Điểm (Scoring Logic)

Tài liệu này tổng hợp toàn bộ các trường hợp kiểm thử (test cases) cho chức năng đánh giá và tính điểm của AI Copilot, dùng để phục vụ quá trình QA/Testing và nghiệm thu chất lượng hệ thống.

---

## 📌 Các Quy Tắc Chung Về Trọng Số & Điểm Trừ
*   **Tiêu chí Cốt lõi (Core):** Là các yêu cầu chính, bắt buộc phải có (ví dụ: đúng họ tên, đúng số liệu thực tế, có chữ ký xác nhận). Điểm trừ mặc định khi không đạt: **từ 30 đến 40 điểm**.
*   **Tiêu chí Phụ (Minor):** Là các yêu cầu về hình thức, ngày tháng, thông tin bổ sung (ví dụ: ngày ban hành, thông tin phòng ban phụ). Điểm trừ mặc định khi không đạt: **từ 10 đến 15 điểm**.
*   **Điểm tối đa:** `100 điểm`.
*   **Điểm tối thiểu:** `0 điểm` (không có điểm số âm).

---

## 📊 Chi Tiết Các Kịch Bản Kiểm Thử (Test Cases)

### Test Case 1: Đạt Điểm Tối Đa (Perfect Score - 100 điểm)
*   **Mục tiêu:** Xác minh điểm số đạt tối đa khi mọi tiêu chí đều được đáp ứng đầy đủ.
*   **Dữ liệu đầu vào:**
    *   *Tên nhiệm vụ:* Báo cáo công việc tháng 6.
    *   *Mô tả nhiệm vụ:* "Yêu cầu nộp báo cáo kết quả công việc tháng 6, có chữ ký xác nhận của Trưởng phòng."
    *   *Tài liệu minh chứng:* Tệp báo cáo tháng 6, có ghi nhận kết quả và có chữ ký xác nhận của Trưởng phòng ở cuối trang.
*   **Checklist sinh ra:**
    1.  `Báo cáo kết quả công việc tháng 6` (Độ quan trọng: **Core** | Điểm trừ: 30) $\rightarrow$ **✓ Đạt (met: true)**
    2.  `Chữ ký xác nhận của Trưởng phòng` (Độ quan trọng: **Core** | Điểm trừ: 30) $\rightarrow$ **✓ Đạt (met: true)**
*   **Công thức tính:** $100 - 0 = 100$ điểm.
*   **Kết quả kỳ vọng:**
    *   **Điểm số:** `100`
    *   **Bình luận AI:** *"Tài liệu đạt 100 điểm. Minh chứng hoàn hảo, đáp ứng đầy đủ tất cả các tiêu chí và yêu cầu của nhiệm vụ."*

---

### Test Case 2: Trừ Điểm Thông Thường (Normal Deduction - Điểm từ 1 đến 99)
*   **Mục tiêu:** Xác minh điểm số bị trừ chính xác dựa trên trọng số của tiêu chí phụ bị thiếu, trong khi tiêu chí cốt lõi vẫn đạt.
*   **Dữ liệu đầu vào:**
    *   *Tên nhiệm vụ:* Kế hoạch hành động năm 2026.
    *   *Mô tả nhiệm vụ:* "1. Kế hoạch hành động năm 2026; 2. Có chữ ký của Giám đốc; 3. Ghi rõ ngày ban hành kế hoạch."
    *   *Tài liệu minh chứng:* Kế hoạch hành động năm 2026 có chữ ký của Giám đốc, nhưng không ghi rõ ngày ban hành.
*   **Checklist sinh ra:**
    1.  `Kế hoạch hành động năm 2026` (Độ quan trọng: **Core** | Điểm trừ: 30) $\rightarrow$ **✓ Đạt (met: true)**
    2.  `Có chữ ký của Giám đốc` (Độ quan trọng: **Core** | Điểm trừ: 30) $\rightarrow$ **✓ Đạt (met: true)**
    3.  `Ghi rõ ngày ban hành kế hoạch` (Độ quan trọng: **Minor** | Điểm trừ: 10) $\rightarrow$ **✗ Chưa đạt (met: false)** (Lý do: Tài liệu thiếu thông tin ngày ban hành)
*   **Công thức tính:** $100 - 10 = 90$ điểm.
*   **Kết quả kỳ vọng:**
    *   **Điểm số:** `90`
    *   **Bình luận AI:** *"Tài liệu đạt 90 điểm. Bị trừ 10 điểm ở tiêu chí Ghi rõ ngày ban hành kế hoạch do tài liệu thiếu thông tin ngày ban hành."* (Điểm số trong nhận xét tự động đồng bộ hóa với điểm backend).

---

### Test Case 3: Điểm Về 0 Do TẤT CẢ Tiêu Chí Không Đạt (All Failed)
*   **Mục tiêu:** Xác minh điểm số tự động đưa về 0 khi không có tiêu chí nào trong checklist được đáp ứng.
*   **Dữ liệu đầu vào:**
    *   *Tên nhiệm vụ:* Báo cáo tháng 6.
    *   *Mô tả nhiệm vụ:* "Báo cáo công việc tháng 6 có chữ ký Trưởng phòng."
    *   *Tài liệu minh chứng:* Bản nháp kế hoạch tháng 5 chưa ký (sai hoàn toàn loại tài liệu).
*   **Checklist sinh ra:**
    1.  `Báo cáo công việc tháng 6` (Độ quan trọng: **Core** | Điểm trừ: 30) $\rightarrow$ **✗ Chưa đạt (met: false)**
    2.  `Chữ ký Trưởng phòng` (Độ quan trọng: **Core** | Điểm trừ: 30) $\rightarrow$ **✗ Chưa đạt (met: false)**
*   **Công thức tính:** Kích hoạt điều kiện chặn dưới `all_failed = True`.
*   **Kết quả kỳ vọng:**
    *   **Điểm số:** `0`
    *   **Bình luận AI:** Nhận xét ghi nhận tài liệu đạt 0 điểm và liệt kê lý do không đạt của tất cả các tiêu chí.

---

### Test Case 4: Điểm Về 0 Do TẤT CẢ Tiêu Chí Cốt Lõi Không Đạt (All Core Failed)
*   **Mục tiêu:** Xác minh điểm số tự động đưa về 0 khi các phần cốt lõi của nhiệm vụ bị thiếu, dù cho các tiêu chí phụ (hình thức) vẫn đầy đủ.
*   **Dữ liệu đầu vào:**
    *   *Tên nhiệm vụ:* Báo cáo tài chính quý 1.
    *   *Mô tả nhiệm vụ:* "Nộp báo cáo tài chính quý 1, có bảng số liệu chi tiết, trình bày rõ ràng định dạng PDF."
    *   *Tài liệu minh chứng:* Một tài liệu PDF trắng chỉ ghi tiêu đề "Báo cáo tài chính quý 1" mà không hề có bảng số liệu chi tiết nào.
*   **Checklist sinh ra:**
    1.  `Nộp báo cáo tài chính quý 1` (Độ quan trọng: **Core** | Điểm trừ: 35) $\rightarrow$ **✓ Đạt (met: true)**
    2.  `Có bảng số liệu chi tiết` (Độ quan trọng: **Core** | Điểm trừ: 35) $\rightarrow$ **✗ Chưa đạt (met: false)**
    3.  `Trình bày rõ ràng định dạng PDF` (Độ quan trọng: **Minor** | Điểm trừ: 10) $\rightarrow$ **✓ Đạt (met: true)**
*   **Công thức tính:** Vì toàn bộ các tiêu chí Cốt lõi thiết yếu (Core) không được đáp ứng đủ (thiếu bảng số liệu là Core), hệ thống kích hoạt điều kiện chặn dưới `all_core_failed = True`.
*   **Kết quả kỳ vọng:**
    *   **Điểm số:** `0` (Thay vì tính theo phép trừ thông thường là $100 - 35 = 65$).

---

### Test Case 5: Giới Hạn Tối Thiểu Bằng 0 (Floor Limit)
*   **Mục tiêu:** Đảm bảo điểm số không bị âm khi tổng điểm trừ vượt quá 100 điểm, nhưng vẫn có ít nhất một tiêu chí Core đạt.
*   **Dữ liệu đầu vào:**
    *   *Tên nhiệm vụ:* Thẩm định hồ sơ dự án.
    *   *Mô tả nhiệm vụ:* Gồm 1 yêu cầu Core và 8 yêu cầu phụ Minor (Ví dụ: đầy đủ ngày tháng, tên các thành viên, số trang đúng quy định, đóng dấu giáp lai, ghi rõ địa phương, v.v.).
    *   *Tài liệu minh chứng:* Đáp ứng được yêu cầu Core nhưng không đạt toàn bộ 8 yêu cầu phụ.
*   **Checklist sinh ra:**
    1.  `Yêu cầu Core` (Độ quan trọng: **Core** | Điểm trừ: 30) $\rightarrow$ **✓ Đạt (met: true)**
    2.  `8 Yêu cầu phụ` (Độ quan trọng: **Minor** | Mỗi mục trừ 10 điểm) $\rightarrow$ **✗ 8 mục đều Chưa đạt (met: false)**
*   **Công thức tính:** 
    $$\text{Điểm số} = \max(0, 100 - (10 \times 8)) = \max(0, 100 - 80) = 20 \text{ điểm}$$
    *(Nếu tăng số yêu cầu phụ bị sai lên 11 mục: $100 - 110 = -10 \rightarrow \max(0, -10) = 0$ điểm)*
*   **Kết quả kỳ vọng:**
    *   **Điểm số:** `0` (hoặc điểm tương ứng theo số lượng tiêu chí phụ không đạt, không bao giờ hiển thị điểm âm).

---

## ⚙️ Logic Xử Lý & Tính Toán Chi Tiết Ở Backend

Dưới đây là mã nguồn/thuật toán logic cụ thể được lập trình tại Backend giúp bạn hiểu rõ cách thức hệ thống xử lý tính điểm và chuẩn hóa dữ liệu:

### 1. Phân loại và Ràng buộc Chặn dưới của Tiêu chí
Để tránh trường hợp AI chấm điểm tùy tiện (ví dụ: đánh dấu tiêu chí cốt lõi nhưng chỉ trừ 5 điểm, hoặc tiêu chí phụ nhưng trừ tận 50 điểm), Backend áp dụng bộ quy chuẩn bắt buộc:
*   **Phân loại tự động:** 
    *   Nếu AI trả về `importance: "core"` hoặc `deduction >= 30` $\rightarrow$ Hệ thống xác định đó là tiêu chí **Cốt lõi (Core)**.
    *   Các trường hợp còn lại $\rightarrow$ Tiêu chí **Phụ (Minor)**.
*   **Ràng buộc điểm trừ tối thiểu:**
    *   Đối với tiêu chí **Core**: Điểm trừ tối thiểu khi không đạt bắt buộc là **30 điểm**.
    *   Đối với tiêu chí **Minor**: Điểm trừ tối thiểu khi không đạt bắt buộc là **10 điểm**.
*   **Dự phòng điểm trừ (Fallback):**
    *   Nếu một tiêu chí bị đánh dấu là Không đạt (`met: false`) nhưng điểm trừ trả về bằng 0 hoặc không hợp lệ, hệ thống sẽ quét chuỗi nhận xét để tìm cụm từ chỉ điểm trừ (ví dụ: *"trừ 15"*). Nếu không tìm thấy, hệ thống tự động gán điểm trừ mặc định là **20 điểm**.

---

### 2. Bộ lọc chống ảo giác (Keyword Sanitizer)
Thuật toán so khớp từ khóa được chạy ngay sau khi AI trả về kết quả để loại bỏ các tiêu chí "tự bịa":
1.  **Loại bỏ Stop-words:** Hệ thống loại bỏ các từ dừng tiếng Việt không mang ý nghĩa phân biệt (ví dụ: *tài liệu, có, và, là, của, trong, về, cho, với, được, theo, đầy đủ...*).
2.  **Tách Từ Khóa Yêu Cầu (Requirements Pool):** Lấy toàn bộ từ khóa từ Tên nhiệm vụ và danh sách yêu cầu thô đã được tách ở Phase 1.
3.  **Kiểm tra Overlap (Giao thoa từ khóa):** 
    *   Với mỗi mục checklist AI trả về, hệ thống tách tập từ khóa của mục đó.
    *   Nếu mục checklist **không trùng bất kỳ từ khóa nào** với danh sách yêu cầu của nhiệm vụ $\rightarrow$ Mục đó sẽ bị **loại bỏ (dropped)** ngay lập tức.

---

### 3. Thuật toán Tính điểm Lập trình tại Backend
Backend tự động tính điểm độc lập thông qua đoạn mã Python sau:

```python
# Tính tổng điểm trừ của các tiêu chí không đạt (met = False)
total_deductions = sum(it.deduction for it in checklist if not it.met)

# Kiểm tra điều kiện hạ điểm về 0
all_failed = all(not it.met for it in checklist)
core_items = [it for it in checklist if it.importance == "core" or it.deduction >= 30]
all_core_failed = all(not it.met for it in core_items) if core_items else False

# Xác định điểm số cuối cùng
if all_failed or all_core_failed:
    score = 0
else:
    score = max(0, 100 - total_deductions)
```

---

### 4. Logic Đồng bộ hóa Nhận xét AI (AI Comment Sync)
Sau khi có điểm số chính xác từ Backend, hệ thống tiến hành đồng bộ chuỗi văn bản nhận xét `ai_comment` từ AI để tránh mâu thuẫn số liệu:
*   **Đồng bộ điểm tổng:** Sử dụng biểu thức chính quy (Regex) để tìm các cụm từ như `đạt 85 điểm` hoặc `đạt 85%` trong `ai_comment` và thay thế chúng thành con số điểm chính xác vừa tính được (ví dụ: `đạt 90 điểm`).
*   **Đồng bộ điểm trừ đơn lẻ:** Nếu cả checklist chỉ có duy nhất 1 tiêu chí không đạt, hệ thống sẽ tự động đồng bộ điểm trừ nêu trong bình luận (ví dụ: `bị trừ 10 điểm`) trùng khớp với số điểm trừ thực tế của tiêu chí đó.

