# TÀI LIỆU KIỂM THỬ VÀ ĐẶC TẢ LOGIC TÍNH ĐIỂM KPI COPILOT

Tài liệu này cung cấp chi tiết về dữ liệu Đầu vào, Luồng xử lý của hệ thống, thông tin Đầu ra và toàn bộ các Kịch bản kiểm thử tính điểm cụ thể trong module thẩm định minh chứng KPI bằng AI.

---

## 1. ĐẦU VÀO (INPUT)

Khi người dùng thực hiện nộp tài liệu minh chứng cho một nhiệm vụ, hệ thống nhận các thông tin đầu vào sau:

### 1.1. Thông tin Nhiệm vụ
*   Tên nhiệm vụ: Tên gọi của nhiệm vụ cần đánh giá.
*   Mô tả nhiệm vụ: Đoạn văn mô tả chi tiết các yêu cầu mà tài liệu minh chứng cần đáp ứng.
*   Hạn chót: Ngày giới hạn hoàn thành nhiệm vụ.
*   Người thực hiện: Họ tên cán bộ nộp tài liệu minh chứng.
*   Phòng ban: Đơn vị công tác của cán bộ.

### 1.2. Thông tin Tài liệu Minh chứng
*   Tên file: Tên của tệp tin được tải lên hệ thống.
*   Loại file: Định dạng tệp tin (ví dụ: PDF, Word, Excel, hoặc hình ảnh).
*   Số trang: Tổng số trang hoặc số bảng tính của tài liệu.
*   Nội dung trích xuất: Toàn bộ nội dung chữ có trong tài liệu được hệ thống tự động đọc và trích xuất ra.

---

## 2. LUỒNG XỬ LÝ (PROCESSING LOGIC)

Quy trình thẩm định tài liệu và tính điểm được thực hiện tự động qua các bước sau:

*   Bước 1 (Bóc tách yêu cầu): Hệ thống gửi Tên nhiệm vụ và Mô tả nhiệm vụ cho AI để phân tích và bóc tách thành một danh sách các yêu cầu cụ thể cần kiểm tra. Nếu AI gặp lỗi, hệ thống sẽ sử dụng thuật toán tự động để chia nhỏ đoạn văn mô tả thành các dòng yêu cầu độc lập.
*   Bước 2 (Đối chiếu tài liệu): Hệ thống gửi danh sách yêu cầu đã bóc tách kèm theo nội dung tài liệu minh chứng cho AI. AI sẽ đọc tài liệu để xác định từng yêu cầu là Đạt hay Không đạt, đồng thời viết lời giải thích và trích dẫn thông tin kiểm chứng từ tài liệu. AI không được phép thêm hoặc bớt yêu cầu trong bước này.
*   Bước 3 (Lọc bỏ yêu cầu tự bịa): Hệ thống thực hiện so khớp từ khóa giữa các yêu cầu mà AI đánh giá với mô tả ban đầu của người dùng. Mọi tiêu chí đánh giá do AI tự ý thêm vào mà không liên quan đến yêu cầu gốc của nhiệm vụ sẽ bị hệ thống loại bỏ hoàn toàn.
*   Bước 4 (Chuẩn hóa thông số tiêu chí): Hệ thống tự động phân loại và áp đặt mức trừ điểm tối thiểu cho các yêu cầu không đạt:
    *   Yêu cầu Cốt lõi (yêu cầu chính yếu của nhiệm vụ): Điểm trừ khi không đạt tối thiểu là 30 điểm.
    *   Yêu cầu Phụ (yêu cầu hình thức, ngày tháng): Điểm trừ khi không đạt tối thiểu là 10 điểm.
    *   Nếu một yêu cầu bị chấm Không đạt nhưng điểm trừ bị thiếu hoặc bằng 0, hệ thống tự động gán điểm trừ mặc định là 20 điểm.
*   Bước 5 (Tính điểm và đồng bộ nhận xét): Hệ thống tự động tính điểm số cuối cùng dựa trên các mục bị đánh dấu Không đạt. Sau khi có điểm số chính xác, hệ thống sẽ tự động quét và sửa lại con số điểm hiển thị trong phần nhận xét bằng chữ của AI để đảm bảo khớp hoàn toàn với điểm số thực tế.

---

## 3. ĐẦU RA (OUTPUT)

Sau khi xử lý xong, hệ thống trả về kết quả thẩm định bao gồm các thông tin sau:

*   Điểm tương thích: Số điểm từ 0 đến 100 thể hiện mức độ đáp ứng của tài liệu minh chứng so với yêu cầu nhiệm vụ.
*   Danh sách đánh giá chi tiết: Gồm danh sách các tiêu chí kiểm tra, trong đó mỗi tiêu chí ghi rõ:
    *   Tên tiêu chí cần kiểm tra.
    *   Trạng thái đáp ứng (Đạt hoặc Chưa đạt).
    *   Ghi chú giải thích chi tiết (trích dẫn thông tin trực tiếp từ tài liệu).
    *   Số điểm bị trừ nếu tiêu chí đó Chưa đạt.
    *   Phân loại độ quan trọng (Cốt lõi hoặc Phụ).
*   Nhận xét tổng quan của AI: Đoạn văn ngắn nhận xét chung và thông báo điểm số đã được đồng bộ chuẩn xác.
*   Danh sách các điểm mạnh của tài liệu.
*   Danh sách các điểm yếu hoặc điểm cần cải thiện của tài liệu.

---

## 4. CÁC KỊCH BẢN TÍNH ĐIỂM CÓ THỂ XẢY RA (SCENARIOS)

Dưới đây là 8 kịch bản tính điểm bao quát mọi trường hợp đánh giá của hệ thống:

### Kịch bản 4.1: Đạt điểm tuyệt đối (100 điểm)
*   Mục tiêu: Đánh giá tài liệu đáp ứng hoàn hảo tất cả yêu cầu.
*   Trạng thái checklist: Tất cả các tiêu chí kiểm tra đều được đánh giá là Đạt.
*   Tổng điểm trừ: 0 điểm.
*   Cách tính điểm: 100 - 0 = 100 điểm.
*   Nhận xét tổng quan của AI: Thông báo tài liệu đạt 100 điểm, minh chứng đáp ứng đầy đủ tất cả các yêu cầu của nhiệm vụ.

### Kịch bản 4.2: Trừ điểm tiêu chí Phụ đơn lẻ
*   Mục tiêu: Tài liệu đạt các yêu cầu cốt lõi nhưng thiếu một yêu cầu phụ (ví dụ: thiếu thông tin ngày tháng).
*   Trạng thái checklist:
    *   Tiêu chí chính (Cốt lõi): Đạt.
    *   Tiêu chí phụ: Chưa đạt (điểm trừ của tiêu chí này là 10 điểm).
*   Tổng điểm trừ: 10 điểm.
*   Cách tính điểm: 100 - 10 = 90 điểm.
*   Nhận xét tổng quan của AI: Thông báo tài liệu đạt 90 điểm và chỉ rõ bị trừ 10 điểm do thiếu tiêu chí phụ tương ứng.

### Kịch bản 4.3: Trừ điểm tiêu chí Cốt lõi đơn lẻ
*   Mục tiêu: Tài liệu thiếu một yêu cầu quan trọng (ví dụ: thiếu chữ ký xác nhận của trưởng phòng).
*   Trạng thái checklist:
    *   Tiêu chí chính (Cốt lõi): Chưa đạt (điểm trừ của tiêu chí này là 30 điểm).
    *   Tiêu chí phụ: Đạt.
*   Tổng điểm trừ: 30 điểm.
*   Cách tính điểm: 100 - 30 = 70 điểm.
*   Nhận xét tổng quan của AI: Thông báo tài liệu đạt 70 điểm và ghi rõ bị trừ 30 điểm ở tiêu chí cốt lõi tương ứng.

### Kịch bản 4.4: Trừ điểm đồng thời nhiều tiêu chí Cốt lõi và Phụ
*   Mục tiêu: Tài liệu bị thiếu nhiều yêu cầu khác nhau nhưng chưa đến mức bị hạ điểm về 0.
*   Trạng thái checklist:
    *   Tiêu chí chính thứ nhất (Cốt lõi): Đạt.
    *   Tiêu chí chính thứ hai (Cốt lõi): Chưa đạt (bị trừ 30 điểm).
    *   Tiêu chí phụ (Phụ): Chưa đạt (bị trừ 12 điểm).
*   Tổng điểm trừ: 42 điểm.
*   Cách tính điểm: 100 - 42 = 58 điểm.
*   Nhận xét tổng quan của AI: Thông báo tài liệu đạt 58 điểm và liệt kê các tiêu chí bị trừ điểm.

### Kịch bản 4.5: Điểm số về 0 do tất cả tiêu chí Cốt lõi không đạt
*   Mục tiêu: Minh chứng nộp lên bị thiếu toàn bộ các phần nội dung quan trọng nhất của nhiệm vụ.
*   Trạng thái checklist:
    *   Toàn bộ các tiêu chí được phân loại là Cốt lõi đều ở trạng thái Chưa đạt.
    *   Các tiêu chí phụ hình thức có thể ở trạng thái Đạt hoặc Chưa đạt.
*   Cách tính điểm: Kích hoạt quy tắc chặn dưới do tất cả tiêu chí Cốt lõi thất bại. Điểm số cuối cùng lập tức được hạ về 0 điểm.
*   Nhận xét tổng quan của AI: Thông báo tài liệu đạt 0 điểm do không đáp ứng được các yêu cầu cốt lõi.

### Kịch bản 4.6: Điểm số về 0 do tất cả tiêu chí đều không đạt
*   Mục tiêu: Tài liệu minh chứng nộp lên sai hoàn toàn nội dung hoặc là file trắng, không đáp ứng bất kỳ yêu cầu nào.
*   Trạng thái checklist: Tất cả các tiêu chí trong danh sách kiểm tra đều ở trạng thái Chưa đạt.
*   Cách tính điểm: Kích hoạt quy tắc chặn dưới do tất cả các tiêu chí thất bại. Điểm số cuối cùng lập tức được hạ về 0 điểm.
*   Nhận xét tổng quan của AI: Thông báo tài liệu đạt 0 điểm.

### Kịch bản 4.7: Điểm số về 0 do tổng điểm trừ vượt quá hoặc bằng 100
*   Mục tiêu: Tài liệu đáp ứng được một tiêu chí chính nhưng sai sót quá nhiều tiêu chí phụ hình thức dẫn đến tổng điểm trừ lớn hơn hoặc bằng 100.
*   Trạng thái checklist: Một tiêu chí chính Đạt, nhưng có từ 8 đến 10 tiêu chí phụ trở lên bị đánh dấu Chưa đạt (mỗi mục bị trừ từ 10 đến 15 điểm).
*   Cách tính điểm: Lấy 100 trừ đi tổng điểm trừ của các mục Chưa đạt. Nếu kết quả ra số âm hoặc bằng 0, điểm số cuối cùng được giới hạn tối thiểu là 0 điểm để tránh điểm số bị âm.
*   Nhận xét tổng quan của AI: Thông báo tài liệu đạt 0 điểm.

### Kịch bản 4.8: Tự động chuẩn hóa điểm trừ không hợp lệ
*   Mục tiêu: Khắc phục trường hợp AI chấm sai số điểm trừ quy định (ví dụ: tiêu chí chính cốt lõi nhưng AI chỉ trừ 5 điểm).
*   Trạng thái checklist ban đầu từ AI:
    *   Tiêu chí Cốt lõi: Chưa đạt, điểm trừ ghi nhận là 5 điểm.
    *   Tiêu chí Phụ: Chưa đạt, điểm trừ ghi nhận là 2 điểm.
*   Cách tính điểm của hệ thống: 
    *   Hệ thống tự động nâng điểm trừ của Tiêu chí Cốt lõi lên mức tối thiểu quy định là 30 điểm.
    *   Hệ thống tự động nâng điểm trừ của Tiêu chí Phụ lên mức tối thiểu quy định là 10 điểm.
    *   Tổng điểm trừ thực tế sau khi chuẩn hóa là: 30 + 10 = 40 điểm.
    *   Điểm số cuối cùng: 100 - 40 = 60 điểm (thay vì 100 - 7 = 93 điểm như điểm số AI trả về ban đầu).
