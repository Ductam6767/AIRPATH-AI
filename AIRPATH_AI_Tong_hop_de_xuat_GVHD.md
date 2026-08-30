# TÀI LIỆU TỔNG HỢP ĐỀ XUẤT NGHIÊN CỨU

**Hệ thống hỗ trợ giao thông đô thị thông minh:**  
Gợi ý tuyến giảm phơi nhiễm không khí trong giới hạn thời gian cho phép  
và hỗ trợ tự động xi nhan trên xe máy dựa trên dữ liệu dẫn đường  
*(AIRPATH-AI + Auto Turn-Signal Assistant)*

*Dành cho Giáo viên / Thạc sĩ hướng dẫn nghiên cứu khoa học kỹ thuật*

**Nhóm nghiên cứu:** Đ (chuyên Lý) · T (chuyên Toán)  
**Trường:** THPT chuyên, ĐHQG-HCM (High School for the Gifted, VNU-HCM)  
**Tháng 8/2025 — Phiên bản gửi xin hỗ trợ hướng dẫn**

---

## 1. Mục đích tài liệu

Tài liệu trình bày bối cảnh, ý tưởng, tiến độ và lộ trình đề tài để Giáo viên/Thạc sĩ hướng dẫn nắm tổng thể, đánh giá tính khả thi và quyết định đồng hành hỗ trợ chuyên môn trong suốt quá trình nghiên cứu, chế tạo prototype và tham dự các cuộc thi.

---

## 2. Bối cảnh nhóm

- **Đ — chuyên Lý:** phần cứng, mạch điện tử, prototype cơ điện, demo vật lý.
- **T — chuyên Toán:** số liệu, metric, logic thuật toán, báo cáo khoa học, trình bày.
- **Nền tảng kỹ thuật:** ESP32 cơ bản, Arduino cơ bản, Python cơ bản; đã chế tạo máy phát điện xoay tay mini.
- **Định hướng:** cơ điện tử / kỹ thuật ô tô — gắn trực tiếp hồ sơ du học.

**Quan điểm:** Không hướng tới máy đồ sộ; ưu tiên vấn đề thực tế, metric đo được, prototype chạy được, tư duy khoa học trung thực.

---

## 3. Vấn đề nghiên cứu

### 3.1. Phơi nhiễm không khí khi di chuyển
Người đi bộ và xe máy tại TP.HCM tiếp xúc PM2.5 thường xuyên. Ứng dụng dẫn đường phổ biến tối ưu thời gian, ít cho phép người dùng chấp nhận “chậm thêm X phút” để giảm phơi nhiễm.

### 3.2. Quên bật/tắt xi nhan trên xe máy
Nhiều người quên xi nhan khi rẽ. Vừa nhìn Google Maps vừa gạt xi nhan thủ công gây phân tâm. Cần trợ lý nhỏ gọn: tận dụng chỉ dẫn Maps để tự gạt xi nhan trước điểm rẽ.

### 3.3. Vì sao gộp thành một hệ thống?
Hai vấn đề cùng trong một hành trình xe máy đô thị: chọn tuyến tốt hơn trước khi đi, an toàn hơn khi đang đi. Dùng chung dữ liệu hình học tuyến đường.

---

## 4. Giải pháp đề xuất

**Tên làm việc:** Hệ thống hỗ trợ giao thông đô thị thông minh — AIRPATH-AI + Auto Turn-Signal Assistant.

### 4.1. AIRPATH-AI (đã có web demo)
- So sánh tuyến nhanh vs tuyến chậm hơn trong ngưỡng “thời gian bổ sung tối đa” (0–10 phút).
- Chỉ số phơi nhiễm: (µg/m³)·phút.
- Chế độ đi bộ và xe máy; khu vực thí điểm TP.HCM.
- Web prototype đã hoàn thành.

### 4.2. Auto Turn-Signal Assistant (ưu tiên tiếp theo)
- Đối tượng: xe máy Việt Nam.
- Maps → lớp trung gian Android → Bluetooth → ESP32 → servo gạt xi nhan trước điểm rẽ X mét.
- Còi/đèn tắt được; nút hủy tay; tự về giữa sau rẽ hoặc timeout.
- Thay Maps ở lộ trình đơn giản; bổ trợ Maps ở lộ trình phức tạp.
- Demo ưu tiên Android + Bluetooth; iOS/Type-C là hướng mở rộng.

### 4.3. Hộp cảm biến di động (hướng mở rộng)
PM2.5, CO, NOx trên phương tiện — mobile monitoring kiểu Trung Quốc. **Không ưu tiên giai đoạn thi sắp tới.**

---

## 5. Cơ sở khoa học

Web demo dùng mô hình trên nền **HealthyAir HCMC** công bố trên **Environment International** (6 trạm quan trắc cố định). Trong bối cảnh chưa đo on-road trực tiếp, đây là cách tiếp cận thuyết phục và trung thực về hạn chế.

- Chỉ số: tổng PM2.5 × thời gian đoạn đường.
- Bộ chọn tuyến: trong tập khả thi theo Δt, ưu tiên phơi nhiễm dự đoán thấp hơn.
- Luôn ghi rõ: chưa phải liều hít lâm sàng; chưa quan trắc on-road thời gian thực.

---

## 6. So sánh với giải pháp hiện có

| Giải pháp | Tuyến sạch + giới hạn trễ | Xi nhan theo Maps | Xe máy VN |
|---|---|---|---|
| Google Maps (eco) | Một phần (nhiên liệu, không AQI) | Không | Có |
| Green Paths / Clean Air Routes (EU) | Gần | Không | Chủ yếu đi bộ |
| Xi nhan cảm biến chuyển động | Không | Một phần | Có |
| **Đề xuất nhóm** | **Có** | **Có** | **Trọng tâm** |

---

## 7. Tiến độ & cuộc thi

| Thời điểm | Cuộc thi | Sản phẩm |
|---|---|---|
| 25/8/2025 | Intel AI Impact Festival (sơ loại QG) | Web AIRPATH — **đã nộp** |
| ~30/8/2025 | JIGS (Hàn Quốc) | Bài báo + web — nhóm tự lo |
| ~20/9/2025 | Sáng tạo trẻ QG — AI | Chủ yếu AIRPATH |
| Đầu 10/2025 | **PIISE** (KHKT trường) | Báo cáo + web + **prototype xi nhan** |

PIISE là cột mốc then chốt: giải nhất → hướng KHKT TP / quốc gia.

---

## 8. Đánh giá tầm & khả thi

**Đủ tầm quốc gia** nếu đóng gói một hệ thống, có metric, prototype demo, trung thực hạn chế.

**Rủi ro & kiểm soát:**
- Thời gian hẹp + 1–2h/ngày tháng 9 → cắt phạm vi; làm xi nhan trước, bỏ cảm biến.
- iPhone/Type-C khó trong 1 tháng → demo Android + Bluetooth.
- Gắn xe thật sớm → rủi ro an toàn → demo bàn/mô hình cho PIISE.
- Dữ liệu chưa on-road → HealthyAir + nêu hạn chế.

---

## 9. Lộ trình triển khai (1–2 giờ/ngày)

| Tuần | Thời gian | Mục tiêu |
|---|---|---|
| 0 | đến 30/8 | JIGS — nhóm tự lo |
| 1 | 31/8 – 6/9 | Chốt đề tài, đặt mua linh kiện ESP32/servo |
| 2 | 7 – 13/9 | Firmware servo + Bluetooth |
| 3 | 14 – 20/9 | Nối Google Maps + Sáng tạo trẻ AI |
| 4 | 21 – 27/9 | Hoàn thiện hộp prototype + video |
| 5 | 28/9 – 10 | Hồ sơ PIISE — không thêm tính năng mới |

**Phân công:** Đ = phần cứng, demo; T = số liệu, báo cáo; cả hai = poster, bảo vệ.

---

## 10. Process nghiên cứu

1. Xác định vấn đề & giả thuyết  
2. Thiết kế hệ thống (sơ đồ khối)  
3. Prototype web AIRPATH-AI — **đã xong**  
4. Prototype hardware auto-xi-nhan — demo bàn  
5. Thử nghiệm & số liệu  
6. Báo cáo & bảo vệ  
7. Mở rộng cảm biến on-road (sau PIISE)

---

## 11. Kính mong từ GVHD

- Nhận xét phạm vi đề tài gộp AIRPATH + auto-xi-nhan.
- Hướng dẫn trình bày hạn chế dữ liệu khoa học.
- Góp ý an toàn cơ cấu gạt xi nhan.
- Đồng hành mốc ~20/9 và đầu tháng 10.
- Góp ý báo cáo trước khi nộp PIISE.

---

## 12. Cam kết nhóm

- Làm đều 1–2 giờ/ngày tháng 9.
- Ưu tiên prototype xi nhan trước cảm biến.
- Trung thực về dữ liệu mô phỏng.
- Báo cáo tiến độ ngắn hàng tuần cho GVHD.

---

## 13. Kết luận

Đề tài có nền HealthyAir HCMC, web prototype sẵn có, lộ trình phần cứng phù hợp thời gian học sinh. Với sự đồng hành GVHD, nhóm tin đủ điều kiện hoàn thiện PIISE và hướng tới cấp cao hơn.

*— Nhóm sẵn sàng trao đổi trực tiếp theo lịch Thầy/Cô —*
