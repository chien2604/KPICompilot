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
