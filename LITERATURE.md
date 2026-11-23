# LITERATURE.md — Tổng quan tài liệu cho baseline TinyML phát hiện ngã đeo cổ (AN GIA MINI, FallAllD neck)

Ngày đọc: 2026-11-23. Làm theo mục 5.0b của `PROMPT_FallAllD_neck_TinyML.md`.

## 0. Cách đọc và quy ước

- Mỗi bài ghi rõ **đã đọc gì**:
  - "toàn văn": đọc cả bài.
  - "chỉ đọc abstract": chỉ ghi những gì abstract nói, không suy đoán phần còn lại.
  - "thứ cấp": thông tin lấy từ bài khác trích lại.
- Phần lớn bài tôi tự tải và đọc. Một số bài bổ sung (B1–B7, B9, B10) do agent phụ trong cùng phiên đọc, theo cùng quy tắc; tôi chỉ dùng báo cáo của agent và không tự mở lại PDF. Các bài này có ghi "(agent phụ)".
- Ba nhãn độ tin cậy, theo mục 5.0b:
  - **đáng tin**: chia theo người, hoặc test trên ngã thật.
  - **có thể đánh giá quá cao**: chia ngẫu nhiên, hoặc không nói cách chia.
  - **không so sánh được**: khác vị trí đeo, cảm biến hoặc chỉ số so với nhiệm vụ này (cổ, IMU + barometer, báo nhầm/giờ ở độ nhạy ≥ 95%).
  - Một kết quả có thể mang hai nhãn.
- "Nhận xét của tôi" là suy luận riêng, không phải điều bài báo nói.
- Số liệu ghi đúng như bài gốc. Bảng hoặc mục nguồn ghi trong ngoặc khi cần.

---

## 1. Tóm tắt những điều ảnh hưởng nhiều nhất tới thiết kế thí nghiệm

1. **Saleh 2021 (TNSRE) không chạy trên chip.**
   - Bộ phân loại chỉ dùng gia tốc. Barometer chỉ dùng trong bước sàng lọc (trigger).
   - Trigger có ba điều kiện:
     - |a| ≥ 2,25 g;
     - sau đó nằm yên ≥ 3,2 s;
     - độ cao giảm ≥ 25 cm.
   - Cửa sổ 13 s (3 s trước ngã, 1 s tới hạn, 9 s sau), bước 200 ms.
   - Ba đặc trưng: entropy, thay đổi hướng, và pNN0.7.
   - Thiết bị trong bài là logger LIS3DH 50 Hz + MS5611, **khác logger LSM9DS1 238 Hz của FallAllD**.
2. **Bài FallAllD (IEEE Sensors J.) không có bản mở.**
   - Tôi chỉ đọc abstract, trang DataPort và file PDF danh sách hoạt động chính thức.
   - **Chưa biết logger cổ đeo thế nào**: dây dài bao nhiêu, trong hay ngoài áo. Cũng chưa có kết quả baseline theo từng vị trí đeo.
   - Phải xem video trong bộ dữ liệu (mục 5.0).
3. **FallAllD không có nhãn near-fall.** Hai hoạt động gần nhất là ADL 23 (vấp nhưng không ngã) và ADL 15 (đứng dậy không nổi).
   - 12/35 kiểu ngã là ngã **có đứng dậy (recovery)**. Một trigger đòi nằm yên ≥ 3,2 s như của Saleh có thể bỏ sót chúng.
4. **Đặc trưng "nhiều pha" của Palmerini 2020 chỉ có 5 đặc trưng**, đều tính từ |a|. Không có gyro, không có ΔP, không có góc trọng lực.
   - Pha sau va chạm của Palmerini dài **24,5 s**. Theo Aderinola 2024, bản ghi FallAllD dài 20 s và va chạm ở khoảng giây thứ 10, nên không thể dùng nguyên.
5. **Câu "báo nhầm và bỏ sót mỗi loại khoảng một lần mỗi ba ngày" của Aderinola 2024 không đứng vững.**
   - Phụ lục A của bài có lỗi đơn vị (xem bài 11a).
   - Thí nghiệm FallAllD của họ dùng logger **eo**, không phải cổ.
6. **arXiv 2509.11789 đã đổi nội dung.**
   - Bản v2 (12/11/2026) có tên mới là "costream" và không còn các con số recall 1,00 / precision 0,84 / F1 0,91 mà mục 1A trích từ v1.
7. **Bằng chứng cho H1 (A+B tốt hơn) yếu.** Ba nguồn hỗ trợ đều có hạn chế:
   - arXiv 2308.12481: cổ tay, chỉ báo accuracy, không nói cách chia.
   - Ejupi 2017: chỉ có abstract.
   - Saleh 2021: dùng barometer làm cổng sàng lọc, làm báo nhầm của thiết bị đeo cổ giảm từ 25 xuống 3,5 lần/ngày. Đây là bằng chứng mạnh nhất, nhưng cho vai trò "cổng", không phải "đặc trưng".
8. **Mốc thực tế cho thiết bị đeo cổ:**
   - Mặt dây thương mại trong viện dưỡng lão (Lipsitz 2016) chỉ phát hiện 19% số cú ngã, và 87% cảnh báo là báo nhầm.
   - Mặt dây NEON (Wang C. 2018), gia tốc + barometer 1 Hz, cây quyết định: độ nhạy 91%, 0,115 báo nhầm/giờ đeo.

---

## 2. Mâu thuẫn hoặc bổ sung so với mục 1A

| # | Mục 1A nói | Bản gốc nói | Điều chỉnh kế hoạch |
|---|---|---|---|
| 1 | Saleh 2021: hệ thống dùng cho cổ và cổ tay, chống xoay; "86.400 quyết định/ngày" | Đúng. Nhưng ví dụ 86.400 chỉ là giả định; hệ thống thật ra quyết định mỗi 200 ms (432.000 lần/ngày). Barometer chỉ dùng trong trigger, bộ phân loại chỉ dùng gia tốc. Không chạy trên chip ("embeddability" để làm sau). Thiết bị khác FallAllD. Con số 95,43% là khi train bằng ADL mô phỏng của FallAllD thay cho ADL thật. | Thêm M0-Saleh (trigger C1&C2&C3) làm mốc. Thử ΔP cả làm cổng lẫn làm đặc trưng. Ghi rõ là không có mốc on-chip từ Saleh. |
| 2 | FallAllD: "đọc kỹ giao thức, cách đeo logger cổ, baseline theo vị trí" | Toàn văn không truy cập được. Danh sách hoạt động có 35 kiểu ngã (101–135) và 44 ADL (1–44). Không có nhãn near-fall riêng. | Cách đeo logger cổ phải xác minh bằng video và dữ liệu trong `DATA_AUDIT.md`. Ánh xạ ADL 23 và 15 thành NEAR_FALL khi báo cáo. |
| 3 | Wang 2024: Random Forest; độ nhạy 98,24%, độ đặc hiệu 99,47% (cổ) | Bảng 3 không nêu tên bộ phân loại cho từng dòng; phần kết luận nói "mô hình cây tổ hợp". Mục 4.1 định nghĩa TP là "ADL được phân loại đúng", tức đảo ngược quy ước, nên độ nhạy và độ đặc hiệu có thể bị hoán đổi. Ngưỡng sàng lọc cần cả gyro (SMA). | Chỉ dùng như ví dụ "chia ngẫu nhiên" cho H5. Không dùng làm mục tiêu. Danh sách đặc trưng vẫn dùng được cho M1. |
| 4 | Tilburg: "luận văn thạc sĩ", accuracy 0,977 | Là **khóa luận cử nhân** (BSc Cognitive Science & AI, 6/2024). 0,977 là trung bình có trọng số của hai lớp, không phải recall của lớp ngã. Đặc trưng tính trên **toàn bản ghi 20 s**, không có cửa sổ trượt. | Không dùng 0,977 để so sánh. Thêm cảnh báo về ActivityID âm (xem bài 4). |
| 5 | arXiv 2308.12481: kết quả theo tổ hợp cảm biến | Số khớp với 1A. Bổ sung: tác giả là học sinh phổ thông; chỉ báo accuracy; không nói cửa sổ, tần số hay cách chia. | Đây là bằng chứng rất yếu cho H1. H1 phải tự kiểm. |
| 6 | Bianchi: bài hội nghị 2009 có độ nhạy 97,8% và độ đặc hiệu 96,7% | Đúng với abstract EMBC 2009. Abstract bài TNSRE 2010 cho: accuracy/độ nhạy/độ đặc hiệu 96,9/97,5/96,5% (trong nhà) với áp suất, so với 85,3/75/91,5% khi chỉ dùng gia tốc. | Ghi cả hai bộ số. |
| 7 | Ejupi 2017: cần lấy kết quả ở vị trí ngực và cách xử lý near-fall | Chỉ có abstract. Abstract chỉ nói ngực tốt nhất khi dùng gia tốc (accuracy trong khoảng 82–96%), không cho số riêng của ngực. Near-fall được tách khỏi ngã, không có chi tiết. | Không có số theo vị trí ngực. Giữ quy ước near-fall = ADL. |
| 8 | Lu 2016: mô hình hóa độ trễ của màng thông khí | Đúng. Nhưng mục đích của màng là **cố ý làm trễ** cân bằng áp suất để barometer chỉ cần bật sau khi có trigger, nhằm tiết kiệm điện. Độ nhạy 94,0%, độ đặc hiệu 90,0%. | Ghi cho EVT-A: vỏ và màng là một bộ lọc thông thấp lên P. Phép thử ΔP nên có biến thể "trễ áp suất". |
| 9 | Bagalà 2012: độ đặc hiệu 83,0% ± 30,3%, tối đa 98% | Đúng. Nhưng 1A bỏ qua chỗ giảm nặng hơn: **độ nhạy trung bình 57,0% ± 27,3% (tối đa 82,8%)**. Báo nhầm là 3–85 lần/ngày ở 3 người. | Phần Giới hạn của báo cáo phải nói cả độ nhạy. |
| 10 | Palmerini 2020: đặc trưng theo 5 pha (trước ngã, rơi, va chạm, nằm yên, đứng dậy) | Chỉ có 5 đặc trưng, tính từ |a|, trên 3 đoạn: 1 s trước đỉnh, 1 s sau đỉnh, 24,5 s sau va chạm. Không có ΔP, gyro hay góc trọng lực. Báo nhầm/giờ được tính bằng cách đếm mọi cửa sổ dương tính sai, không gộp. | Dùng "Palmerini-5" đúng như bài. Phần mở rộng (ΔP, ω, góc) ghi là đóng góp riêng của nhiệm vụ này. Rút ngắn pha sau va chạm cho vừa bản ghi 20 s. |
| 11 | Aderinola 2024: khoảng một báo nhầm mỗi ba ngày; F1 90,7% | F1 90,7% đúng (Hydra, FARSEEING). Con số "1 lần/3 ngày" sai đơn vị (bài 11a). Thí nghiệm FallAllD dùng logger **eo**, 14 người. | Không dùng "1 lần/3 ngày" làm mốc. Mốc thực tế: Palmerini 0,56 FA/h ở độ nhạy 81%; costream QUANT 0,35 FA/h ở recall 0,75. |
| 12 | Aderinola 2025, arXiv 2509.11789: recall 1,00, precision 0,84, F1 0,91 | Những số này chỉ có ở **v1** (9/2025, "Watch Your Step"). **v2** (11/2026, "costream") là bài giao thức đánh giá dạng luồng, cho số khác. Ở tập giữ lại với ngưỡng chọn theo chi phí c = 2: QUANT recall 0,905, precision 0,826. | Dùng v2 làm mẫu cho đánh giá dạng luồng (mục 5.3). Trích dẫn ghi rõ phiên bản. |
| 13 | Duan 2026: vị trí đeo không nêu rõ | Đúng, bài không nêu. Nhưng KFall chỉ có cảm biến ở lưng dưới (bài B6), nên vị trí thực tế là lưng dưới. Chạy float32, không lượng tử hóa. Không có báo nhầm/giờ. | Mốc RAM/thời gian cho M3 giữ nguyên. Ghi chú là khác vị trí đeo. |
| 14 | MicroNAS: chia theo người | Đúng (leave-one-participant-out). Bổ sung: cảm biến ở cẳng chân; "vấp rồi lấy lại thăng bằng" được gộp vào lớp **ngã**, ngược với quy ước của nhiệm vụ này. | Chỉ tham khảo cách tìm kiến trúc. |

---

## 3. Từng nghiên cứu trong mục 1A

### Bài 1 — Saleh et al. 2021, TNSRE

| Mục | Nội dung |
|---|---|
| Trích dẫn | Saleh M., Abbas M., Prud'Homm J., Somme D., Le Bouquin Jeannès R. *A Reliable Fall Detection System Based on Analyzing the Physical Activities of Older Adults Living in Long-Term Care Facilities.* IEEE TNSRE 29:2587–2594, 2021. doi:10.1109/TNSRE.2021.3133616. Bản chấp nhận: https://hal.science/hal-03510580 (CC BY-NC-ND 4.0) |
| Đã đọc | Toàn văn (bản HAL) |
| Dataset | **RealAct**: 16 người ≥ 80 tuổi ở viện dưỡng lão, 400 ngày (214 ngày cổ tay + 186 ngày cổ), 2 cú ngã thật (1 cổ, 1 cổ tay). **FallAllD**: chỉ lấy các cú ngã mô phỏng |
| Vị trí đeo | Mặt dây cổ (Fig. 1) và cổ tay. Mô hình train chung trên dữ liệu của cả hai vị trí |
| Cảm biến | LIS3DH ±8 g; barometer MS5611; MCU STM32L431 (logger RF-Track). **Không phải logger LSM9DS1 của FallAllD** |
| Tần số mẫu | Gia tốc 50 Hz, barometer 10 Hz |
| Áp suất → độ cao | Lọc "slope limit", rồi đổi sang độ cao theo công thức khí áp có nhiệt độ |
| Trigger | C1: ‖a‖ ≥ 2,25 g. C2: nằm yên ≥ 3,2 s, tức 16 đoạn 200 ms liên tiếp có phương sai < 0,005625; bài không ghi đơn vị, nhận xét của tôi là nhiều khả năng g², tức độ lệch chuẩn 0,075 g. C3: ΔH ≤ −25 cm, tương đương khoảng +3 Pa |
| Cửa sổ | Cửa sổ trượt 13 s (3 s trước ngã, 1 s tới hạn, 9 s sau), bước 200 ms, tức 432.000 quyết định/ngày |
| Chia pha động | Tìm đỉnh ‖a‖ trong giây thứ 3–4 của cửa sổ. "Va chạm" = 0,2 s quanh đỉnh. "Trước va chạm" = 0,5 s trước đó. "Trước ngã" = 2,4–3,4 s. "Nằm yên" = 3,2 s, tìm sau pha tới hạn. "Điều chỉnh" = đoạn giữa va chạm và nằm yên, dài 0–6,7 s |
| Đặc trưng | Ba đặc trưng. F1: tổng entropy phân bố của ax, ay, az trong pha va chạm + điều chỉnh. F2: Σ trên các trục của \|trung bình lúc nằm yên − trung bình trước ngã\|. F3: max trên các trục của pNN0.7, tức tỉ lệ cặp mẫu liên tiếp chênh nhau > 0,7 g, trong pha va chạm + điều chỉnh |
| Mô hình | 19 cấu hình thuộc 9 họ mô hình scikit-learn. Tốt nhất: Gradient Boosting, 100 cây, learning rate 0,4, độ sâu 2 |
| Tham số / kích thước | Không nêu |
| Phần cứng chạy mô hình | **Không chạy trên chip.** Mục VI chỉ bàn hai phương án: gửi dữ liệu thô (khoảng 13 KB/ngày cho thiết bị đeo cổ) lên máy chủ, hoặc nhúng với quyết định trễ vài giây. Kết luận để việc nhúng cho nghiên cứu sau |
| Cách chia | Train 1259 mẫu: 621 ADL "mơ hồ" (đã qua trigger) từ 97 ngày RealAct + 638 cú ngã FallAllD (≈ 75%). Test 2406 mẫu: 2170 ADL từ 303 ngày + 2 ngã thật + ≈ 25% ngã FallAllD. Bài nói train lấy từ 21 người và test từ 17 người khác |
| Độ nhạy | Cổ: 100% (GB100), gồm cả 2/2 ngã thật. Khi train bằng ADL mô phỏng của FallAllD: cổ 95,43%, cổ tay 80,12% |
| Độ đặc hiệu | Cổ: 98,52%. Cổ tay: 96,73% |
| Báo nhầm | Mô hình GB100: cổ 0,04/ngày (≈ 1 lần/25 ngày), cổ tay 0,32/ngày. Chỉ dùng trigger, cho thiết bị đeo cổ: C1 33/ngày, C1&C2 25/ngày, C1&C2&C3 3,5/ngày (cao nhất 15/ngày) |
| Hạn chế | Chỉ 2 cú ngã thật. Báo nhầm chỉ tính trên các cửa sổ đã qua trigger. Ngã có đứng dậy nhanh bị loại theo thiết kế (C2). Khác cảm biến so với FallAllD. 21 + 17 = 38 người, nhiều hơn 16 + 15 = 31 người có thật, nên không rõ cách chia ngã FallAllD theo người (nhận xét của tôi). F2 là tổng trị tuyệt đối theo từng trục, F1 và F3 cũng tính theo trục, nên chỉ bất biến với đảo dấu hoặc hoán vị trục, không bất biến với mọi phép xoay (nhận xét của tôi) |
| Đánh giá | Báo nhầm/ngày trên ADL thật: **đáng tin**, nhưng chỉ 7 người đeo cổ. Độ nhạy: **có thể đánh giá quá cao** (2 ngã thật; chưa rõ chia ngã FallAllD theo người). So với FallAllD-neck: **không so sánh được trực tiếp** (cảm biến 50 Hz LIS3DH, ADL thật) |

### Bài 2 — Saleh et al. 2021, FallAllD (IEEE Sensors J.)

| Mục | Nội dung |
|---|---|
| Trích dẫn | Saleh M., Abbas M., Le Bouquin Jeannès R. *FallAllD: An Open Dataset of Human Falls and Activities of Daily Living for Classical and Deep Learning Applications.* IEEE Sensors J. 21(2):1849–1858, 2021. doi:10.1109/JSEN.2020.3018335. Dataset: doi:10.21227/bnya-mn34 (IEEE DataPort, CC BY) |
| Đã đọc | **Chỉ đọc abstract** (bài đóng; HAL hal-03102536 không có file). Đọc thêm trang DataPort và toàn bộ file "simulated falls and ADLs- list.pdf" |
| Dataset | 15 người, 26.420 file, ba logger RF-Track giống nhau ở eo, cổ tay và cổ. 35 kiểu ngã (ID 101–135) và 44 ADL (ID 1–44) |
| Cảm biến, tần số | LSM9DS1: gia tốc 238 Hz ±8 g, gyro 238 Hz ±2000 dps, từ kế 80 Hz ±4 G. Barometer MS5607-02BA03 10 Hz |
| Giao thức ngã (theo file danh sách) | Tư thế trước ngã: đi bộ (101–114), định ngồi/nằm (115–120), chạy chậm (121–126), nằm trên giường (127–128), ngồi ghế (129–131), đứng (132–135). Nguyên nhân: vấp, trượt, ngất, mất thăng bằng, xoay người trên giường. Hướng ngã: trước, sau, ngang, thẳng đứng. Có ngã kèm xoay người. **12 kiểu có đứng dậy**: 102, 104, 106, 108, 110, 116, 118, 120, 122, 124, 126, 128. Có ngã được "đỡ": 114 chống tay lên bàn; 135 trượt chậm dọc tường |
| ADL đáng chú ý | Gần ngã: 23 (vấp khi đi nhưng không ngã), 15 (đứng dậy khỏi sofa không nổi). Va mạnh: 12 (đập tay lên bàn), 26–27 (nhảy), 35–36 (lên/xuống cầu thang nhanh). Có thay đổi áp suất: 29–36 (cầu thang), 37–40 (thang máy), 41–42 (xe buýt/metro). Dễ nhầm với ngã: 13 (ngồi xuống), 16 (nằm xuống giường) |
| Vị trí đeo cổ | **Chưa xác minh.** DataPort chỉ ghi "neck-worn". Fig. 1 của bài 1 là thiết bị RealAct, khác thiết bị FallAllD. Video (169,6 MB) cần đăng nhập DataPort, tôi chưa xem |
| Mô hình, cách chia, kết quả | Abstract chỉ nói có đánh giá cả mô hình học sâu và học máy cổ điển, và hiệu năng khác nhau nhiều giữa các bộ dữ liệu. **Không có số liệu theo vị trí đeo** |
| Thông tin thứ cấp | Bài 1 trích [8] để nói đeo ở eo "có lẽ là một trong những vị trí tốt nhất". arXiv 2308.12481 nói "LSTM trên FallAllD đạt 87,18%" (có lẽ là phân loại nhiều lớp, chưa kiểm). Wang 2024 nói dữ liệu cổ có ADL và ngã của 12 người (câu viết rối, chưa kiểm). Tilburg đếm được 2292 bản ghi cổ, 25,79% là ngã |
| Hạn chế | Người trẻ, ngã mô phỏng có đồ bảo hộ (theo bài 1). Phân bố ADL không giống đời thực, ví dụ số mẫu nhảy gần bằng số mẫu đi bộ (theo bài 1) |
| Đánh giá | Không có kết quả để gắn nhãn |

### Bài 3 — Wang, Alipour Sarvari, Khadraoui 2024, BIOSIGNALS

| Mục | Nội dung |
|---|---|
| Trích dẫn | Wang Y., Alipour Sarvari P., Khadraoui D. *Fusion of Machine Learning and Threshold-Based Approaches for Fall Detection in Healthcare Using Inertial Sensors.* BIOSIGNALS 2024, pp. 573–582. doi:10.5220/0012250500003657. https://www.scitepress.org/Papers/2024/122505/122505.pdf (CC BY-NC-ND) |
| Đã đọc | Toàn văn |
| Dataset | SisFall, và FallAllD tách riêng cổ tay, eo, cổ |
| Cảm biến | Gia tốc + gyro. Không dùng barometer |
| Tiền xử lý | Butterworth bậc 4, 10 Hz, lọc hai chiều. Giữ nguyên tần số gốc |
| Cửa sổ | Ngã: 2 s quanh đỉnh SMV. ADL: trượt 2 s, bước 0,2 s |
| Mô hình | Tầng 1: SMVmax > CT1 **và** SMAmax > CT2, với CT1 và CT2 là giá trị nhỏ nhất của các cú ngã trong tập train. Tầng 2: SVM, KNN, DT, RF hoặc XGBoost trên 65 đặc trưng (max, min, mean, std, skew, kurtosis, range, thời gian từ đáy đến đỉnh của Ax..ωz, SMV, SMA, NAng = pitch + roll). Dùng SHAP để chọn 15 đặc trưng hàng đầu |
| Tham số / phần cứng | Không có. Không chạy trên vi điều khiển |
| Cách chia | **Chia ngẫu nhiên 75/25 toàn bộ dữ liệu** sau khi cắt cửa sổ. Không chia theo người. Cửa sổ ADL bước 0,2 s chồng lên nhau rất nhiều, nên cửa sổ gần giống nhau rơi vào cả train và test |
| Độ nhạy / độ đặc hiệu (cổ) | 98,24% / 99,47%, accuracy 99,52% (Bảng 3, 65 đặc trưng). Dùng 15 đặc trưng thì lệch < 1%. Lưu ý: mục 4.1 định nghĩa TP = "ADL đúng", nên hai số này có thể bị đảo |
| Báo nhầm/giờ | Không có |
| Hạn chế | Chia ngẫu nhiên. Pitch/roll phụ thuộc hướng đặt cảm biến. Ngưỡng tầng 1 cần gyro. Định nghĩa F1 dựa trên độ nhạy và độ đặc hiệu, không theo chuẩn |
| Đánh giá | **Có thể đánh giá quá cao** |

### Bài 4 — Tummers 2024, khóa luận Tilburg (arno.uvt.nl fid=180019)

| Mục | Nội dung |
|---|---|
| Trích dẫn | Tummers M. *Fall Detection Using Machine Learning: Finding the Optimal Positions for Wearable Inertial Sensors.* BSc thesis, Cognitive Science & AI, Tilburg University, 24/06/2024. http://arno.uvt.nl/show.cgi?fid=180019 |
| Đã đọc | Toàn văn |
| Dataset | FallAllD, tách theo cổ, eo, cổ tay. Loại những người không có ngã ở vị trí đó. Bộ dữ liệu cổ còn 1943 dòng, 30,42% là ngã |
| Cảm biến | Gia tốc + gyro |
| Cửa sổ | **Không có**: mỗi bản ghi 20 s là một mẫu |
| Đặc trưng | 18: mean, std, range cho mỗi trục gia tốc và gyro |
| Mô hình | kNN, RF, Gradient Boosting. Có SMOTE. Siêu tham số chọn bằng random search với Leave-One-Group-Out theo người |
| Cách chia | Train/test 80/20. Bài không nói phần chia test có theo người hay không. Chỉ phần chỉnh siêu tham số chắc chắn chia theo người |
| Kết quả cổ | GB: accuracy 0,977, precision/recall/F1 0,977. Đây là **trung bình có trọng số của hai lớp**, không phải recall lớp ngã. Eo tốt nhất (GB 0,986), cổ tay kém nhất (0,959) |
| Báo nhầm | Không có |
| Lưu ý dữ liệu | Tác giả gặp các ActivityID từ −121 đến −128 và **xóa đi** vì không hiểu. **Nhận xét của tôi:** đây gần như chắc chắn là ID 128–135 bị tràn khi lưu bằng int8 (128 → −128, …, 135 → −121). Nghĩa là khóa luận đã bỏ mất 8 kiểu ngã: ngã từ giường có đứng dậy, và các kiểu ngất khi ngồi hoặc đứng, kể cả kiểu trượt dọc tường. Script trong thư mục dự án đọc ID bằng `np.uint8`, nên vẫn đúng với ID ≤ 255 |
| Đánh giá | **Có thể đánh giá quá cao** (chia test không rõ; một mẫu cho mỗi bản ghi) |

### Bài 5 — arXiv 2308.12481 (Zhou et al. 2023)

| Mục | Nội dung |
|---|---|
| Trích dẫn | Zhou H., Chen A., Buer C., Tang K., Gong L., Chen E., Liu Z., Tang J. *Fall Detection using Knowledge Distillation Based LSTM for Offline Embedded and Low Power Devices.* arXiv:2308.12481, 2023 |
| Đã đọc | Toàn văn (4 trang) |
| Dataset | FallAllD, **chỉ dữ liệu cổ tay** |
| Cảm biến | Gia tốc (A), barometer (B), gyro (G), dùng giá trị thô |
| Tần số / cửa sổ | Không nêu. Phần đo độ trễ nhắc tới "20 mẫu gia tốc" |
| Mô hình | LSTM 512 → Dense 128 → Dense 1. Mô hình chưng cất (KD) có một nửa số nơ-ron |
| Tham số | Không nêu |
| Phần cứng | Raspberry Pi 4: < 20 ms cho 20 mẫu |
| Cách chia | **Không nêu** |
| Kết quả | Chỉ accuracy: ABG 93,55%, AB 92,28%, BG 89,43%, B 88,09%, AG 82,37%, A 80,39%, G 79,18%. KD với AB: 89,52%. Không có độ nhạy, độ đặc hiệu hay báo nhầm |
| Hạn chế | Tác giả là học sinh phổ thông. Không có cách chia. Chỉ báo accuracy. Bảng dòng điện ghi BMP280 tiêu thụ 3,2 mA; theo tôi hiểu, đó không phải dòng trung bình khi đo thưa, cần kiểm datasheet |
| Đánh giá | **Có thể đánh giá quá cao** và **không so sánh được** (cổ tay; chỉ có accuracy) |

### Bài 6 — Bianchi et al. 2010, TNSRE (và bài hội nghị EMBC 2009)

| Mục | Nội dung |
|---|---|
| Trích dẫn | Bianchi F., Redmond S.J., Narayanan M.R., Cerutti S., Lovell N.H. *Barometric Pressure and Triaxial Accelerometry-Based Falls Event Detection.* IEEE TNSRE 18(6):619–627, 2010. doi:10.1109/TNSRE.2010.2070807. Bài hội nghị: Bianchi F. et al., EMBC 2009:6111–6114, doi:10.1109/IEMBS.2009.5334922 |
| Đã đọc | **Chỉ đọc abstract** (cả hai bài) |
| Dataset | 2010: 20 người trẻ, ngã mô phỏng xuống nệm + ADL; có thêm một lần thử ADL kéo dài. 2009: 15 người trẻ |
| Vị trí đeo | Eo |
| Cảm biến | Gia tốc 3 trục + barometer. Thiết bị Bluetooth, phân tích offline |
| Tần số / cửa sổ / phần cứng | Abstract không nêu |
| Mô hình | Cây quyết định đặt ngưỡng theo kinh nghiệm |
| Cách chia | Abstract không nêu |
| Kết quả 2010 | Có áp suất, trong nhà: accuracy 96,9%, độ nhạy 97,5%, độ đặc hiệu 96,5%; không có báo nhầm trong lần thử ADL kéo dài. Chỉ gia tốc: 85,3 / 75 / 91,5% |
| Kết quả 2009 | Độ nhạy 97,8%, độ đặc hiệu 96,7% |
| Đánh giá | **Không so sánh được** (eo). Không rõ cách chia, nên cũng **có thể đánh giá quá cao** |

### Bài 7 — Ejupi et al. 2017, EMBC (PubMed 29060322)

| Mục | Nội dung |
|---|---|
| Trích dẫn | Ejupi A., Galang C., Aziz O., Park E.J., Robinovitch S. *Accuracy of a wavelet-based fall detection approach using an accelerometer and a barometric pressure sensor.* EMBC 2017:2150–2153. doi:10.1109/EMBC.2017.8037280 |
| Đã đọc | **Chỉ đọc abstract** (bài đóng) |
| Dataset | 15 người, 525 lượt: 194 ngã, 105 gần ngã, 226 ADL |
| Vị trí đeo | Lưng dưới, ngực, cổ tay, đùi |
| Cảm biến | Gia tốc + barometer |
| Mô hình | Biến đổi wavelet với wavelet "thích nghi theo mẫu". Thêm một mô hình học máy kết hợp đặc trưng wavelet và đặc trưng thống kê theo mô hình nhiều pha |
| Cách chia / tần số / cửa sổ | Abstract không nêu |
| Kết quả | Chỉ gia tốc: accuracy 82–96% tùy vị trí, **ngực cao nhất**, nhưng không có số riêng. Thêm áp suất: +3,4% trung bình (p = 0,041; SD 3,0%). Tốt nhất 98% |
| Near-fall | Abstract chỉ nói phương pháp tách được ngã khỏi gần ngã và ADL. Tức gần ngã thuộc lớp âm; không có chi tiết |
| Đánh giá | **Có thể đánh giá quá cao** (không rõ cách chia; chỉ có accuracy) |

### Bài 8 — Lu et al. 2016, EMBC (và bài nối tiếp: B8)

| Mục | Nội dung |
|---|---|
| Trích dẫn | Lu W., Wang C., Stevens M.C., Redmond S.J., Lovell N.H. *Low-power operation of a barometric pressure sensor for use in an automatic fall detector.* EMBC 2016:2010–2013. doi:10.1109/EMBC.2016.7591120 |
| Đã đọc | **Chỉ đọc abstract** |
| Ý chính | Vỏ kín, chống nước, có một cửa sổ nhỏ phủ màng bán thấm. Màng làm chậm cân bằng áp suất trong và ngoài vỏ, nên barometer chỉ cần bật trong thời gian ngắn mà vẫn bắt được thay đổi áp suất |
| Dataset | Bộ dữ liệu ngã mô phỏng và ADL có sẵn. Áp suất được làm trễ bằng mô hình toán của vỏ + màng. Có phép thử trên bàn để đo điện |
| Kết quả | Độ nhạy 94,0%, độ đặc hiệu 90,0%. Pin ước tính 995,7 ngày |
| Đánh giá | **Không so sánh được** (abstract không nêu vị trí đeo hay cách chia) |
| Hệ quả | Vỏ và màng là một bộ lọc thông thấp có độ trễ lên kênh B. ΔP đo trên mẫu thật sẽ nhỏ hơn và đến chậm hơn so với FallAllD (barometer để hở) |

### Bài 9 — Bagalà et al. 2012, PLoS ONE

| Mục | Nội dung |
|---|---|
| Trích dẫn | Bagalà F., Becker C., Cappello A., Chiari L., Aminian K., Hausdorff J.M., Zijlstra W., Klenk J. *Evaluation of Accelerometer-Based Fall Detection Algorithms on Real-World Falls.* PLoS ONE 7(5):e37062, 2012. doi:10.1371/journal.pone.0037062 |
| Đã đọc | Toàn văn |
| Dataset | 29 cú ngã thật (từ 32 cú; 3 cú bị cắt đỉnh ở ±2 g nên bị loại) từ 15 người, phần lớn bị PSP. ADL: 7 người, 168 giờ, cắt thành 10.050 cửa sổ 60 s. Chỉ giữ 1170 cửa sổ "có hoạt động", tức khoảng max−min > 1,01 g |
| Vị trí đeo | Lưng dưới, đeo bằng đai (DynaPort MiniMod) |
| Cảm biến / tần số | LIS3LV02DQ, ±2 g hoặc ±6 g, 12 bit, 100 Hz |
| Mô hình | 13 thuật toán ngưỡng đã công bố: Chen; Kangas 1a–d, 2a–b, 3a–c; Bourke 1a, 1b, 2, 3 |
| Cách chia | Không có huấn luyện. Ngưỡng Bourke1 được chỉnh lại trên chính các cú ngã thật |
| Độ nhạy | Trung bình **57,0% ± 27,3%**, tối đa 82,8% |
| Độ đặc hiệu | Trung bình 83,0% ± 30,3%, tối đa 98%. Hai thuật toán cân bằng nhất (Chen, Bourke3): độ nhạy 75,9–82,8%, độ đặc hiệu 94,2–96,7% |
| Báo nhầm | 3–85 lần trong 24 giờ, đo trên 3 người ngã. Các thuật toán Kangas có < 9 lần nhưng độ nhạy < 55% |
| Đánh giá | **Đáng tin** (ngã thật), nhưng **không so sánh được** (lưng dưới, cửa sổ 60 s, không có học máy) |

### Bài 10 — Palmerini, Klenk, Becker, Chiari 2020, Sensors

| Mục | Nội dung |
|---|---|
| Trích dẫn | Palmerini L., Klenk J., Becker C., Chiari L. *Accelerometer-Based Fall Detection Using Machine Learning: Training and Testing on Real-World Falls.* Sensors 20(22):6479, 2020. doi:10.3390/s20226479, PMC7697900 |
| Đã đọc | Toàn văn (PMC/BioC) |
| Dataset | FARSEEING: 143 cú ngã thật từ 40 người (69,2 ± 12,7 tuổi). ADL: 15 người × 12 giờ = 180 giờ, không có ngã được báo cáo |
| Vị trí đeo | Lưng dưới (đai ở eo, hoặc dán băng y tế) |
| Cảm biến / tần số | Gia tốc 3 trục ±2 g; 16 cú ngã ghi ở ±6 g được cắt về ±2 g. 100 Hz |
| Cửa sổ | Cửa sổ trượt 27,5 s, bước 1 s. Tìm đỉnh \|a\| trong giây đầu. Nếu đỉnh < 1,4 g thì bỏ (cú ngã thật thấp nhất có đỉnh 1,6 g). Cửa sổ ngã ứng viên 26,5 s: 1 s trước đỉnh, 1 s sau đỉnh, 24,5 s sau va chạm |
| Đặc trưng nhiều pha (5, đều từ \|a\|) | 1. LPV: giá trị nhỏ nhất của \|a\| trước đỉnh (pha trước đỉnh). 2. UPV: giá trị đỉnh. 3. Hệ số wavelet: độ giống với một "wavelet mẹ" là trung bình các cú ngã trong tập train (pha va chạm). 4. Tính chu kỳ sau va chạm: dựa trên tự tương quan trong 2 s, bắt đầu 0,5 s sau đỉnh. 5. Độ lệch chuẩn của \|a\| trong pha sau va chạm |
| Đặc trưng thông thường | max, min, mean, std của ax, ay, az, \|a\| (16 đặc trưng) |
| Mô hình | Naïve Bayes, hồi quy logistic, KNN (k = 3), RF (20 cây), SVM RBF (chọn C và γ bằng 5-fold lồng bên trong). Ngưỡng đầu ra 0,5 |
| Tham số / phần cứng | Laptop. SVM + đặc trưng nhiều pha: 0,7 ms mỗi cửa sổ |
| Cách chia | **5-fold theo người, có phân tầng.** Trong tập train, giữ ngẫu nhiên 10% số cửa sổ ADL |
| Kết quả tốt nhất | SVM + nhiều pha: độ nhạy 81,1%, độ đặc hiệu 99,5%, **0,56 báo nhầm/giờ**, PPV 53,7%, F 64,6%, AUC 0,993. NB + thông thường: độ nhạy 95,1% nhưng 5,23 FA/h. Thuật toán Kangas: độ nhạy 30,1%, 0,82 FA/h |
| Đánh đổi (SVM, Bảng 3) | Độ nhạy 53,8 / 64,3 / 81,1 / 93,7 / 95,1% ứng với 0,06 / 0,11 / 0,56 / 2,78 / 5,56 FA/h |
| Cách tính FA/h | Số cửa sổ dương tính sai chia cho 180 giờ; mỗi cửa sổ sai tính là một cảnh báo, không gộp |
| Hạn chế | Báo cáo ngã có thể sai hoặc thiếu. Lưng dưới. Người có nguy cơ ngã trung bình đến cao |
| Đánh giá | **Đáng tin** (ngã thật, chia theo người), nhưng **không so sánh được** (lưng dưới, ±2 g) |

### Bài 11a — Aderinola et al. 2024, AALTD

| Mục | Nội dung |
|---|---|
| Trích dẫn | Aderinola T.B., Palmerini L., D'Ascanio I., Chiari L., Klenk J., Becker C., Caulfield B., Ifrim G. *Accurate and Efficient Real-World Fall Detection Using Time Series Techniques.* AALTD 2024 (Springer), pp. 52–79. PDF và code: https://github.com/mlgig/ts_fall_detection |
| Đã đọc | Toàn văn (PDF trong repo), README, và các file CSV kết quả FallAllD |
| Dataset | FARSEEING (41 người, lưng dưới L5, 100 Hz; 145 cửa sổ ngã, 1064 cửa sổ ADL). **FallAllD: chỉ logger eo, 14 người** (466 ngã, 1279 ADL). SisFall |
| Cửa sổ | 7 s: 1 s rơi, 1 s va chạm, 5 s sau ngã. Bước 1 s. Cửa sổ ADL chỉ giữ nếu đỉnh \|a\| trong pha va chạm > 1,4 g. Mỗi cú ngã lấy một cửa sổ |
| Mô hình | Dạng bảng (ExtraTrees, KNN, LogisticCV, RF, RidgeCV) trên vector thô. Chuỗi thời gian (Catch22, Hydra, MultiRocketHydra, QUANT, Rocket) bằng thư viện aeon |
| Cách chia | 5-fold theo người. Thử chéo bộ dữ liệu bằng một lần chia theo người |
| Kết quả FallAllD eo | MultiRocketHydra: F1 97,21 ± 1,87, recall 98,72, độ đặc hiệu 98,25. QUANT: F1 96,45, recall 97,15, độ đặc hiệu 98,4 |
| Kết quả FARSEEING | Hydra: F1 90,7 ± 6,5% |
| Train FallAllD → test FARSEEING | Recall thấp, precision hơi cao hơn. Trộn dữ liệu mô phỏng với dữ liệu thật thì tốt hơn |
| Báo nhầm/giờ | **Không đáng tin.** Phụ lục A chia 3600 cửa sổ/giờ theo tỉ lệ lớp của tập train, tức giả định 442 "cú ngã" mỗi giờ. Từ đó tính FP ≈ 44 rồi chia thêm cho 3600 để ra "0,012 lần/giờ". **Nhận xét của tôi:** 44 cửa sổ sai mỗi giờ là khoảng 44 cảnh báo/giờ, không phải 0,012. Câu "1 báo nhầm mỗi 3 ngày" vì vậy không có cơ sở. Bài sau của chính nhóm này (11b) đo được QUANT 0,35 FA/h ở recall 0,75 |
| Giấy phép code | Repo **không có file LICENSE** (GitHub API: license = none), nên mặc định là giữ mọi quyền: chỉ đọc để tham khảo, không chép. Riêng `scripts/ConvTran/` có LICENSE MIT (Monash) |
| Cấu trúc repo | `evaluation.ipynb` (toàn bộ thí nghiệm), `results/*.csv`, `figs/`, `paper/`, `scripts/ConvTran/`. Bản tiền xử lý FallAllD/SisFall để trên Google Drive |
| Đánh giá | F1 trên FARSEEING: **đáng tin**. FallAllD: chia theo người nhưng **không so sánh được** (eo). Báo nhầm/giờ: sai phương pháp |

### Bài 11b — Aderinola et al., arXiv 2509.11789 (v1 2025, v2 2026)

| Mục | Nội dung |
|---|---|
| Trích dẫn | v1 (15/09/2025): *Watch Your Step: A Cost-Sensitive Framework for Accelerometer-Based Fall Detection in Real-World Streaming Scenarios.* v2 (12/11/2026): *costream: A Streaming Evaluation Protocol for Wearable Fall Detection.* Aderinola T.B., D'Ascanio I., Palmerini L., Chiari L., Klenk J., Becker C., Caulfield B., Ifrim G. arXiv:2509.11789. Code: https://github.com/mlgig/costream |
| Đã đọc | v2: toàn văn. v1: abstract, phần phương pháp, bảng chia dữ liệu và bảng CV |
| Dataset | FARSEEING, lưng dưới L5, 145 cú ngã từ 41 người. Mỗi bản ghi 20 phút, một cú ngã ở giữa |
| Cảm biến | Chỉ dùng \|a\|, 100 Hz |
| Cửa sổ | v2: w ∈ {3, 10, 30, 60} s, bước 1 s |
| Mô hình | Catch22, ExtraTrees, MiniRocket, QUANT, ResNet, dùng tham số mặc định |
| Cách chia | Theo người. 9 người (21 bản ghi) giữ lại hoàn toàn. 32 người còn lại chia 5-fold theo người |
| Giao thức luồng (v2) | 1. Cổng: cửa sổ chỉ được chấm điểm nếu đỉnh \|a\| trong giây thứ 1–2 > 1,4 g; nếu không, điểm = 0. 2. Điểm mỗi thời điểm = max điểm của các cửa sổ chứa nó ("bản đồ tin cậy"). 3. Áp ngưỡng τ. 4. Mỗi đoạn dương liên tục là một "episode"; gộp các episode cách nhau < 60 s thành một cảnh báo. 5. TP nếu cảnh báo chạm khoảng [va chạm − 1 s, va chạm + 20 s). 6. FA/h tính theo thời gian theo dõi thực. Ghi lại độ trễ phát hiện |
| Chọn ngưỡng theo chi phí | Tối đa g(τ) = −(FP + c·FN) trên 100 giá trị τ, bằng CV 5-fold trên tập phát triển. c ∈ {1, 2, 5, 10} |
| Kết quả v2 (CV) | QUANT ở τ = 0,5: recall 0,748, **0,35 FA/h**. Ở τ = 0,07: recall 0,94, 3,41 FA/h. Với c = 10: QUANT recall 0,891 ở 1,68 FA/h; Catch22 recall 0,881 ở 3,60 FA/h |
| Kết quả v2 (tập giữ lại) | τ = 0,5: MiniRocket 17 TP / 2 FP / 4 FN. Ngưỡng chọn với c = 2: QUANT 19 TP / 4 FP / 2 FN (recall 0,905, precision 0,826) |
| Kết quả v1 | Abstract ghi recall 1,00, precision 0,84, F1 0,91. Không còn trong v2 |
| Hạn chế (tác giả nêu) | Mỗi bản ghi 20 phút chỉ có một cú ngã, nên FA/h có thể khác FA/h khi theo dõi tự do. Kết quả nhạy với cách đặt khoảng chấm điểm |
| Giấy phép code | Repo costream **không có LICENSE**: chỉ tham khảo, không chép |
| Cấu trúc repo | `costream/segmentation/` (gate, streaming_segmenter, training_segmenter), `costream/evaluation/` (event_detection, presegmented, cross_validation, tester), `costream/model/cost_classifier_cv.py`, `scripts/`, `results/*.csv`. `smoke_test.py` chạy trên dữ liệu giả |
| Đánh giá | **Đáng tin** (ngã thật, chia theo người), nhưng **không so sánh được** (lưng dưới) |

### Bài 12 — Duan, Minh, Dung, Linh 2026, Int. J. Technology 17(3)

| Mục | Nội dung |
|---|---|
| Trích dẫn | Duan L.-C., Minh N.-N., Dung T.-C., Linh T.-T.-T. *Energy-Efficient TinyML Approach for Wearable Fall Detection on Edge Devices Using Spatial-Temporal Deep Learning.* International Journal of Technology 17(3):919–935, 2026. doi:10.14716/ijtech.v17i3.8445 (PTIT, Việt Nam) |
| Đã đọc | Toàn văn |
| Dataset | Train trên KFall (32 nam trẻ; 21 ADL và 15 kiểu ngã). Test zero-shot trên SisFall |
| Vị trí đeo | Bài không nêu. KFall chỉ có cảm biến ở lưng dưới (bài B6) |
| Cảm biến | Chỉ gia tốc: x, y, z và kênh RMS = \|a\| |
| Tần số | Hạ về 50 Hz |
| Cửa sổ | 4 s (200 mẫu), bước 2 s. Cửa sổ là ngã nếu chứa ≥ 50% khoảng ngã (từ lúc bắt đầu ngã đến va chạm + 0,5 s) |
| Chuẩn hóa | z-score trên từng bộ dữ liệu, tính trên toàn bộ dữ liệu trước khi chia. **Nhận xét của tôi:** đây là rò rỉ nhẹ |
| Mô hình | 4 nhánh Conv (16 bộ lọc, kernel 8) → nối → Conv2D 32 (4×3) → LSTM 32 → LSTM 16 → Dense 64 → 8 → 2 |
| Tham số / kích thước | 21.434 tham số. Model float32 99.176 B (96,9 KB). Flash 431,6 KB, RAM 199,5 KB |
| Huấn luyện | Adam 1e-3, 25 epoch. Trọng số lớp **0,8 cho ADL và 0,2 cho ngã**: tác giả nói tăng trọng số lớp ngã làm báo nhầm tăng mạnh |
| Phần cứng | Seeed XIAO ESP32-S3, 240 MHz, 512 KB SRAM, 8 MB PSRAM, 4 MB flash. TFLite-Micro **float32, không lượng tử hóa**, có ESP-NN. Light sleep, thức dậy mỗi 2 s |
| Thời gian / điện | 113,6 ms mỗi cửa sổ, 86,5 mA khi suy luận. Light sleep 0,927 mA. Trung bình 5,78 mA trong 1 phút. Khoảng 170 giờ với pin 1000 mAh (≈ 7 ngày), khoảng 21 ngày nếu dùng 8 giờ/ngày. Bài không nói con số này có gồm dòng của cảm biến hay không |
| Cách chia | **LOSO trên KFall** (32 fold), tính theo cửa sổ |
| Kết quả KFall | Trung bình theo người: accuracy 99,3%, recall 99,36%, precision 98,60%, F1 98,97%. Gộp toàn bộ: bỏ sót 224/15.131 cửa sổ ngã, 100 cửa sổ ADL báo nhầm |
| Kết quả SisFall | Tính theo lượt thử: ngã nếu có ≥ 2 cửa sổ liên tiếp dương. Accuracy 98,3%, F1 97,9%. Báo nhầm ở D10 (ngồi nhanh xuống ghế thấp), D17 (lên xuống xe hơi). Bỏ sót F11, F15 (ngã chậm) |
| Thử độ dài cửa sổ | F1 trên KFall tăng từ 96,0% (2 s) lên 98,97% (4 s). Ở 6 s, precision trên SisFall giảm từ 98,2% xuống 92,8% |
| Báo nhầm/giờ | Không có |
| Hạn chế | Ngã mô phỏng của người trẻ. Không có độ đặc hiệu theo thời gian. Công thức recall trong bài in sai (TP/(TP+TN)) |
| Đánh giá | Trong KFall: **đáng tin** (LOSO). So với nhiệm vụ này: **không so sánh được** (lưng dưới, chỉ số theo cửa sổ, float32) |

### Bài 13 — MicroNAS (arXiv 2504.07397)

| Mục | Nội dung |
|---|---|
| Trích dẫn | Mohasel S.M., Sheppard J., Molina L.K., Neptune R.R., Wurdeman S.R., Pew C.A. *MicroNAS: An Automated Framework for Developing a Fall Detection System.* arXiv:2504.07397v1, 2025. Theo agent phụ, bài đã đăng ở Eng. Appl. AI 2026; tôi chưa kiểm |
| Đã đọc | Toàn văn v1 (tôi kiểm các điểm chính; agent phụ đọc thêm) |
| Dataset | 35 người (30 người bình thường, 5 người cụt chi dưới), trong phòng thí nghiệm. 98,3% ADL, 1,7% ngã |
| Vị trí đeo | Cẳng chân |
| Cảm biến / tần số | Xsens IMU, 100 Hz |
| Cửa sổ | 1,2 s, chồng 90% |
| Mô hình | Tìm kiến trúc 1D-CNN và GRU, lấy dung lượng bộ nhớ ESP32-S2 (320 KB) làm giới hạn. Dùng trọng số lớp |
| Kích thước | 1D-CNN 198,22 ± 88,80 KB. GRU khoảng 163 KB float32 (41.873 tham số, theo agent phụ). Không đo độ trễ trên chip |
| Cách chia | Leave-one-participant-out cho test. Tập validation gồm 3 người cụt chi và 3 người bình thường chọn ngẫu nhiên |
| Kết quả | F1 lớp ngã: 1D-CNN 0,64 ± 0,17; GRU 0,66 ± 0,18 |
| Near-fall | "Vấp rồi lấy lại thăng bằng" (trip and recovery) được gộp vào lớp **ngã** |
| Đánh giá | **Đáng tin** (chia theo người), nhưng **không so sánh được** (cẳng chân, người cụt chi) |

---

## 4. Các bài bổ sung (10 bài)

Thứ tự ưu tiên theo mục 5.0b: (1) đeo cổ hoặc ngực, (2) có barometer, (3) chạy trên vi điều khiển, (4) chia theo người hoặc ngã thật.

### B1 — Lipsitz et al. 2016 (mặt dây cổ, viện dưỡng lão, ngã thật) (agent phụ)

| Mục | Nội dung |
|---|---|
| Trích dẫn | Lipsitz L.A., Tchalla A.E., Iloputaife I., Gagnon M., Dole K., Su Z.Z., Klickstein L. *Evaluation of an Automated Falls Detection Device in Nursing Home Residents.* J Am Geriatr Soc 64(2):365–368, 2016. doi:10.1111/jgs.13708 |
| Đã đọc | Chỉ đọc abstract. Palmerini 2020 cũng trích lại số 19% |
| Dataset | 62 người ở viện dưỡng lão, có ngã trong 12 tháng trước. Theo dõi 6 tháng, ngã thật. Đối chiếu với báo cáo của nhân viên trong khoảng ±8 giờ |
| Vị trí / cảm biến | Mặt dây quanh cổ, gia tốc 3 trục. Thiết bị "đang thử nghiệm"; abstract không nêu tên hãng |
| Tần số / cửa sổ / mô hình / cách chia | Abstract không nêu. Thuật toán là hộp đen |
| Kết quả | Phát hiện 17/89 cú ngã (19%). Trong 128 cảnh báo, 111 (87%) là báo nhầm. Không có FA/h |
| Đánh giá | **Đáng tin** (ngã thật, đúng vị trí cổ). Hộp đen, không có dữ liệu thô |

### B2 — Kangas et al. 2015 (ngã thật, theo dõi dài) (agent phụ)

| Mục | Nội dung |
|---|---|
| Trích dẫn | Kangas M., Korpelainen R., Vikman I., Nyberg L., Jämsä T. *Sensitivity and false alarm rate of a fall sensor in long-term fall detection in the elderly.* Gerontology 61(1):61–68, 2015. doi:10.1159/000362720 |
| Đã đọc | Chỉ đọc abstract |
| Dataset | 16 người cao tuổi, 15.500 giờ dữ liệu thật, 15 cú ngã |
| Vị trí đeo | Abstract không nêu |
| Mô hình | Thuật toán ngưỡng chạy thời gian thực |
| Kết quả | 12/15 cú ngã (80%). 0,049 báo nhầm/giờ. Sau khi chỉnh cách phân tích: 0,025/giờ (≈ 1 lần/40 giờ đeo). Lưu ý: bản chỉnh được đánh giá lại trên chính dữ liệu đó |
| Đánh giá | **Đáng tin** (ngã thật). **Không so sánh được** (không rõ vị trí đeo) |

### B3 — Becker et al. 2012 (mô hình ngã nhiều pha) (agent phụ)

| Mục | Nội dung |
|---|---|
| Trích dẫn | Becker C., Schwickert L., Mellone S., Bagalà F., Chiari L., Helbostad J.L., Zijlstra W., Aminian K., Bourke A., Todd C., Bandinelli S., Kerse N., Klenk J. *Proposal for a multiphase fall model based on real-world fall recordings with body-fixed sensors.* Z Gerontol Geriatr 45(8):707–715, 2012. doi:10.1007/s00391-012-0403-6 |
| Đã đọc | Toàn văn (bản sau bình duyệt, Manchester) |
| Dataset | 3 cú ngã thật minh họa, cùng một người. Cảm biến ở lưng dưới, 100 Hz, ±6 g |
| Các pha | 1. Trước ngã (ghi ≥ 1 phút). 2. Rơi: 0,4–0,8 s khi ngã từ tư thế đứng, trong đó khoảng 120–200 ms đầu chưa có phản xạ. 3. Va chạm: bắt đầu ở lần đổi hướng đột ngột đầu tiên, thường < 1 s, có thể nhiều đỉnh. 4. Nằm yên: từ gần 0 đến hàng giờ. 5. Đứng dậy: tự đứng, có người đỡ, hoặc không đứng dậy được (nằm lâu) |
| Gợi ý của tác giả | Dùng jerk và thời gian va chạm làm đặc trưng. Gyro và barometer giúp nhận ra gần ngã. Pha nằm yên và pha đứng dậy giúp tăng độ đặc hiệu |
| Đánh giá | Mô hình khái niệm, không có số liệu hiệu năng |

### B4 — Aziz et al. 2017 (có near-fall) (agent phụ)

| Mục | Nội dung |
|---|---|
| Trích dẫn | Aziz O., Musngi M., Park E.J., Mori G., Robinovitch S.N. *A comparison of accuracy of fall detection algorithms (threshold-based vs. machine learning) using waist-mounted tri-axial accelerometer signals from a comprehensive set of falls and non-fall trials.* Med Biol Eng Comput 55(1):45–55, 2017. doi:10.1007/s11517-016-1504-y |
| Đã đọc | Chỉ đọc abstract. Có thêm thông tin thứ cấp từ Aziz et al. 2017 PLoS ONE (PMC5498034), cùng nhóm tác giả |
| Dataset | 10 người trẻ. Ngã mô phỏng theo các nguyên nhân phổ biến ở người già, gần ngã, và ADL |
| Vị trí đeo | Eo. Theo nguồn thứ cấp, bộ dữ liệu của phòng thí nghiệm có 7 vị trí, gồm xương ức và đầu, 128 Hz |
| Mô hình | 5 thuật toán học máy (SVM tốt nhất) so với 5 thuật toán ngưỡng |
| Near-fall | Theo bài PLoS của cùng nhóm: gần ngã được gán nhãn **không ngã**. Gần ngã thường có gia tốc cao và sẽ gây báo nhầm nếu không có trong dữ liệu train |
| Cách chia / kết quả | Không đọc được số liệu |
| Đánh giá | **Không so sánh được** (eo; không có số) |

### B5 — Özdemir 2016 (so sánh vị trí đeo) (agent phụ)

| Mục | Nội dung |
|---|---|
| Trích dẫn | Özdemir A.T. *An Analysis on Sensor Locations of the Human Body for Wearable Fall Detection Devices: Principles and Practice.* Sensors 16(8):1161, 2016. doi:10.3390/s16081161 |
| Đã đọc | Toàn văn |
| Dataset | 14 người trẻ. 20 kiểu ngã, 16 ADL, 5 lần mỗi kiểu: 2520 bản ghi |
| Vị trí / cảm biến | 6 IMU Xsens ở đầu, ngực, eo, cổ tay, đùi, cổ chân. Không có vị trí cổ; tác giả coi ngực tương ứng với "vòng cổ hoặc trâm cài". Có barometer nhưng không dùng |
| Tần số / cửa sổ | 25 Hz. Cửa sổ 4 s, căn theo đỉnh của cảm biến **eo** cho mọi vị trí |
| Mô hình | k-NN, Bayes, SVM, bình phương tối thiểu, DTW, ANN, trên 30 thành phần PCA |
| Cách chia | **10-fold ngẫu nhiên**, không theo người |
| Kết quả | Accuracy trung bình 6 thuật toán: eo 98,42, đùi 97,89, cổ chân 97,00, đầu 96,61, **ngực 96,50**, cổ tay 94,92%. Tác giả giải thích ngực kém hơn do khác biệt cơ thể giữa người (giới tính, tư thế, béo phì) |
| Đánh giá | **Có thể đánh giá quá cao** (chia ngẫu nhiên) |

### B6 — Yu et al. 2021, KFall (agent phụ)

| Mục | Nội dung |
|---|---|
| Trích dẫn | Yu X., Jang J., Xiong S. *A Large-Scale Open Motion Dataset (KFall) and Benchmark Algorithms for Detecting Pre-impact Fall of the Elderly Using Wearable Inertial Sensors.* Front. Aging Neurosci. 13:692865, 2021. doi:10.3389/fnagi.2021.692865 |
| Đã đọc | Toàn văn |
| Dataset | 32 nam trẻ. 21 ADL, 15 kiểu ngã, 5075 file. Mốc bắt đầu ngã và va chạm gán từ video |
| Vị trí / cảm biến | **Lưng dưới**. LPMS-B2: gia tốc ±16 g, gyro ±2000°/s |
| Tần số / cửa sổ | 100 Hz. Cửa sổ 0,5 s (phát hiện trước va chạm) |
| Mô hình | Ngưỡng, SVM (40 đặc trưng), ConvLSTM |
| Cách chia | Theo người, 26 train / 6 test, một lần chia |
| Kết quả | ConvLSTM: độ nhạy 99,32%, độ đặc hiệu 99,01%, báo trước va chạm 403 ms. Trên 15 cú ngã thật của FARSEEING: độ nhạy 93,33%, **độ đặc hiệu 73,33%** |
| Đánh giá | **Đáng tin** (chia theo người), nhưng **không so sánh được** (lưng dưới; phát hiện trước va chạm) |

### B7 — Wang C. et al. 2018, mặt dây NEON (gia tốc + barometer, MCU) (agent phụ)

| Mục | Nội dung |
|---|---|
| Trích dẫn | Wang C., Lu W., Redmond S.J., Stevens M.C., Lord S.R., Lovell N.H. *A Low-Power Fall Detector Balancing Sensitivity and False Alarm Rate.* IEEE JBHI 22(6):1929–1937, 2018. doi:10.1109/JBHI.2017.2778271 |
| Đã đọc | Toàn văn (bản chấp nhận trên UNSW). Abstract tôi tự kiểm trên PubMed |
| Vị trí đeo | **Dây đeo cổ (lanyard)** |
| Phần cứng | MSP430FR5969; 2 × ADXL362; barometer ST LPS25H; radio CC1120; pin cúc áo 1 Ah |
| Tần số | Gia tốc 50 Hz, thêm 6 Hz để phân biệt chuyển động/đứng yên. Barometer 1 Hz. Kênh 50 Hz và barometer tắt khi người đứng yên |
| ΔP | Cửa sổ áp suất 12 mẫu (12 s) quanh trigger. ΔP = trung bình 4 mẫu cuối − trung bình 4 mẫu đầu; bỏ 4 mẫu giữa vì đang biến động |
| Mô hình | Cửa sổ gia tốc 6 s. Đặc trưng: SVMmax, SVMmin, ΔP, cờ nằm yên. Cây quyết định với ngưỡng tìm bằng giải thuật di truyền: 2,246 g; 0,601 g; 6,325 Pa. Tính bằng số nguyên cố định (fixed-point) |
| Dataset | 20 người trẻ × 10 kiểu ngã × 2 = 200 cú ngã mô phỏng. 10 người khác đeo trong sinh hoạt tự do khoảng một ngày |
| Cách chia | Theo người, chia đôi. Train: ngã của 10 người + dữ liệu tự do của 5 người. Test: phần còn lại |
| Kết quả | Độ nhạy 91%, **0,1149 báo nhầm/giờ đeo**. Công suất trung bình 111,1 µW, pin ước tính 1125 ngày |
| Đánh giá | **Đáng tin** (chia theo người; báo nhầm đo trong sinh hoạt tự do), nhưng người trẻ và mẫu nhỏ. Rất gần thiết bị AN GIA MINI |

### B8 — Lu et al. 2020, TBME (barometer kích hoạt thông minh qua màng bán thấm)

| Mục | Nội dung |
|---|---|
| Trích dẫn | Lu W., Stevens M.C., Wang C., Redmond S.J., Lovell N.H. *Smart Triggering of the Barometer in a Fall Detector Using a Semi-Permeable Membrane.* IEEE TBME 67(1):146–157, 2020. doi:10.1109/TBME.2019.2909907 |
| Đã đọc | Chỉ đọc abstract |
| Ý chính | Vỏ kín + màng bán thấm làm trễ cân bằng áp suất. Barometer được đánh thức khi có sự kiện và vẫn bắt được áp suất tăng do hạ độ cao. Hai cách phát hiện: bộ lọc trung bình trượt sai phân (DMAF) và bộ lọc Kalman (KF) |
| Dataset | Thử trong phòng thí nghiệm và trong sinh hoạt tự do. Áp suất ghi ngoài trời được cho qua mô hình toán của vỏ và màng |
| Vị trí / tần số / cách chia | Abstract không nêu |
| Kết quả | Độ nhạy 91,8% (DMAF) / 91,9% (KF). Độ đặc hiệu 95,2 / 95,5%. **0,035 / 0,064 báo nhầm/giờ.** Pin 447 / 444 ngày với pin 140 mAh |
| Đánh giá | Không rõ cách chia: **có thể đánh giá quá cao** |

### B9 — Campanella et al. 2024 (gia tốc + áp suất trên STM32U5) (agent phụ)

| Mục | Nội dung |
|---|---|
| Trích dẫn | Campanella S., Alnasef A., Falaschetti L., Belli A., Pierleoni P., Palma L. *A Novel Embedded Deep Learning Wearable Sensor for Fall Detection.* IEEE Sensors J., 2024. doi:10.1109/JSEN.2024.3375603 |
| Đã đọc | Toàn văn (bản của tác giả) |
| Vị trí / cảm biến | Túi quần (dữ liệu riêng của nhóm); eo (SisFall). LSM6DSOX 26 Hz + LPS25HB 25 Hz. Áp suất thô dùng làm đầu vào |
| Cửa sổ / mô hình | 10 s, bước 2 s. 42 đặc trưng FFT (Edge Impulse). Mạng truyền thẳng nhỏ, chỉ chạy sau trigger 2,5 g |
| Phần cứng | STM32U575 160 MHz. 25 ms mỗi lần suy luận, RAM đỉnh 2,8–3 KB, flash 94,6–105,1 KB |
| Cách chia | **Ngẫu nhiên 80/20 theo cửa sổ** |
| Kết quả | Accuracy 99,38%, độ nhạy 99,79%, độ đặc hiệu 98,62%. Dữ liệu riêng: 98,05% không có áp suất, 99,12% có áp suất. Train SisFall, test dữ liệu riêng: 94,86%. Một CNN sau khi lượng tử hóa giảm còn khoảng 70% |
| Đánh giá | **Có thể đánh giá quá cao** (chia ngẫu nhiên) |

### B10 — Villa & Casilari 2025/26 (ảnh hưởng của tần số mẫu) (agent phụ)

| Mục | Nội dung |
|---|---|
| Trích dẫn | Villa M., Casilari E. *The Impact of the Accelerometer Sampling Rate on the Performance of Machine and Deep Learning Models in Wearable Fall-Detection Systems.* Sensors 26(1):162, 2026. doi:10.3390/s26010162 |
| Đã đọc | Toàn văn, qua công cụ đọc web; các số chính được kiểm hai lần |
| Dataset / vị trí | SisFall, eo, ADXL345. Hạ mẫu từ 200 Hz xuống 100, 50, 20, 10 Hz |
| Cửa sổ / mô hình | 4 s quanh đỉnh. CNN-LSTM, CNN, LSTM, kNN, SVM |
| Cách chia | Theo người, một lần chia: 6 train / 2 validation / 2 test (chỉ 10 người) |
| Kết quả | CNN-LSTM ở 20 Hz: accuracy 98,89%, độ nhạy 96,67%, độ đặc hiệu 99,63%. Trung bình: 98,11 ± 0,54% ở 20 Hz so với 96,06 ± 0,73% ở 100 Hz. Kích thước mô hình giảm từ 2705 KB xuống 1030 KB. Tác giả khuyên khoảng 20 Hz |
| Thử ngoài | FARSEEING: độ nhạy 81,8% (18/22), độ đặc hiệu 96,3%. Một người đeo 7 ngày: 58 báo nhầm trong 1147 cửa sổ; không quy ra giờ |
| Đánh giá | **Đáng tin** (chia theo người) nhưng mẫu rất nhỏ. **Không so sánh được** (eo) |


---

## 5. Bảng "phát hiện → quyết định trong nhiệm vụ này"

| # | Phát hiện (nguồn) | Quyết định / ảnh hưởng | Liên quan |
|---|---|---|---|
| 1 | Trigger C1&C2&C3 (2,25 g; nằm yên ≥ 3,2 s; ΔH ≤ −25 cm) giảm báo nhầm của thiết bị đeo cổ từ 33 xuống 25 rồi 3,5 lần/ngày. Barometer chỉ dùng ở trigger (bài 1) | Thêm **M0-Saleh** đúng ba điều kiện này làm mốc M0. Ngưỡng nằm yên phải đổi đơn vị theo tần số và độ nhạy mới (đơn vị gốc không ghi). Barometer thử ở hai vai trò: **cổng** (C3) và **đặc trưng** (ΔP trong M1) | M0, M1, H1 |
| 2 | Ba đặc trưng của Saleh: entropy theo trục, tổng \|Δ trung bình\| theo trục, pNN0.7. Thực ra chỉ bất biến với đảo dấu hoặc hoán vị trục (bài 1, nhận xét của tôi) | Thêm nhóm "Saleh-3" vào M1, kèm phiên bản bất biến thật: entropy của \|a\|, góc giữa vector trọng lực trước và sau va chạm, pNN0.7 của \|a\|. So sánh hai phiên bản trong phép thử H2 | M1, H2 |
| 3 | FallAllD có 12 kiểu ngã có đứng dậy. Một trigger đòi nằm yên ≥ 3,2 s sẽ bỏ sót chúng (bài 1, bài 2) | Q4: báo độ nhạy **riêng** cho nhóm có/không đứng dậy. Không loại các kiểu này khỏi tập test. Nếu M0-Saleh bỏ sót, ghi đó là đặc tính của thiết kế, không phải lỗi. Việc có cần cảnh báo ngã có đứng dậy hay không để chủ sản phẩm quyết định | Q4, M0, chỉ số |
| 4 | FallAllD không có nhãn near-fall. ADL 23 (vấp không ngã) và 15 (đứng dậy không nổi) gần nhất. Ejupi và Aziz xếp near-fall vào lớp âm; MicroNAS làm ngược lại (bài 2, 7, 13, B4) | Giữ quy ước của đề: NEAR_FALL = {23, 15}. Train như ADL, báo cáo riêng tỉ lệ báo nhầm. Ghi quy ước này vào `DATA_AUDIT.md` và `LOG.md` | Q4, nhãn |
| 5 | Bản ghi FallAllD dài 20 s, va chạm ở khoảng giây thứ 10 (bài 11a; cần kiểm). Palmerini cần 24,5 s sau va chạm; Saleh dùng 13 s (3 + 1 + 9) | Đặc trưng sau va chạm chỉ dùng tối đa khoảng 9 s sau đỉnh. Cửa sổ 2/3/4/6 s theo đề giữ nguyên. Thêm một cấu hình tham khảo 13 s kiểu Saleh, chỉ cho M0/M1 | Q2, M1 |
| 6 | Đặc trưng nhiều pha của Palmerini chỉ là 5 đặc trưng trên \|a\| (LPV, UPV, hệ số wavelet, tính chu kỳ sau va chạm, SD sau va chạm), không có ΔP hay gyro (bài 10) | Thêm "Palmerini-5" đúng như bài. Template wavelet mẹ **chỉ tính trong fold train**, để tránh rò rỉ. Phần mở rộng (ΔP, \|ω\|, góc trọng lực, thời gian nằm yên) ghi là đóng góp riêng. H3 diễn đạt lại thành: "Palmerini-5 + mở rộng" so với "Palmerini-5" so với M2/M3 | M1, H3 |
| 7 | Bằng chứng cho H1 yếu: arXiv 2308 (cổ tay, chỉ có accuracy, không có cách chia); Ejupi (chỉ abstract, +3,4%); Campanella (chia ngẫu nhiên). Bằng chứng mạnh nhất là Saleh (barometer làm cổng) và NEON (ΔP 6,3 Pa trong cây quyết định) (bài 1, 5, 7, B7, B9) | Giữ H1 nhưng **không coi là đã biết trước**. So A, A+B, A+G, A+G+B trên cùng fold, theo FA/h ở độ nhạy ≥ 95%. Thêm biến thể "B chỉ làm cổng" | H1, Q1 |
| 8 | Cách tính ΔP khác nhau giữa các nghiên cứu: Saleh lọc slope-limit rồi đổi sang độ cao, ngưỡng 25 cm (≈ 3 Pa); NEON lấy trung bình 4 mẫu cuối trừ 4 mẫu đầu trong 12 s ở 1 Hz, ngưỡng ≈ 6,3 Pa. Ca ngã thật đeo cổ trong Saleh chỉ hạ 29 cm (ngã từ bồn cầu xuống nửa ngồi) | Tính ΔP theo đề (trung vị 1–3 s sau trừ trung vị 1–3 s trước), thêm biến thể NEON. Báo cáo phân bố ΔP của ngã theo tư thế trước ngã. Không mặc định 10–12 Pa: ngã từ ghế hoặc giường sẽ nhỏ hơn. Đo độ ồn của MS5607 lúc đứng yên trong `DATA_AUDIT.md` | H1, 5.1 |
| 9 | Vỏ + màng bán thấm làm trễ và làm mượt áp suất (bài 8, B8) | Thêm phép thử độ nhạy: cho P qua bộ lọc bậc 1 với vài hằng số thời gian, rồi đo lại lợi ích của ΔP. Ghi yêu cầu vỏ/màng cho EVT-A | H1, EVT-A |
| 10 | Câu "1 báo nhầm/3 ngày" của Aderinola 2024 sai đơn vị. Số FA/h trên ngã thật: Palmerini 0,56 FA/h ở độ nhạy 81% (5,56 FA/h ở 95%); costream QUANT 0,35 FA/h ở recall 0,75; NEON 0,115 FA/h ở 91%; Kangas 0,025–0,049 FA/h ở 80% (bài 10, 11a, 11b, B2, B7) | Không dùng "1 lần/3 ngày" làm mốc. Báo cáo ghi FA/h kèm độ nhạy ở cùng ngưỡng. Lưu ý FA/h trên FallAllD là "theo giờ ADL theo kịch bản", **không** phải giờ sinh hoạt thật. Mốc thực tế (≈ 0,1–0,6 FA/h ở 80–90%) chỉ để đối chiếu | Chỉ số, REPORT |
| 11 | Giao thức luồng của costream: cổng 1,4 g; lấy max điểm các cửa sổ chồng nhau; ngưỡng τ; gộp episode < 60 s; TP nếu chạm khoảng [va chạm − 1 s, + 20 s); có độ trễ phát hiện. Code không có giấy phép (bài 11b) | Mục 5.3 **tự viết lại**, không chép code, có ghi nguồn. Áp vào bản ghi 20 s của FallAllD: nối ADL của mỗi người thành luồng dài để đếm FA/h; khoảng TP giới hạn trong bản ghi ngã. Báo cáo cả phân bố độ trễ phát hiện | 5.3, chỉ số |
| 12 | Chọn ngưỡng theo chi phí g(τ) = −(FP + c·FN), c ∈ {1, 2, 5, 10}, trong CV lồng theo người (bài 11b) | Thêm vào 5.3: chọn τ trên fold train bên trong. Báo cáo bảng theo c, cạnh tiêu chí "độ nhạy ≥ 95%" của Q3 | 5.3, Q3 |
| 13 | Cổng va chạm khác nhau: 1,4 g (Palmerini, Aderinola, người già lưng dưới) so với 2,25 g (Saleh, đeo cổ). Cổng 1,4 g không loại cú ngã thật nào ở lưng dưới (đỉnh thấp nhất 1,6 g) | Đo phân bố đỉnh \|a\| của ngã ở dữ liệu cổ FallAllD. Chọn T1 trên fold train. Báo cáo tỉ lệ ngã bị cổng loại ở 1,4 / 1,8 / 2,25 g (Q4). Lưu ý: ngã của người trẻ mô phỏng có thể mạnh hơn ngã thật | M0, Q4 |
| 14 | Duan 2026: 21.434 tham số, float32 96,9 KB, RAM 199,5 KB, 113,6 ms trên ESP32-S3 240 MHz, cửa sổ 4 s ở 50 Hz, LOSO trên KFall (lưng dưới) | M3 lấy mốc: ≤ khoảng 25k tham số. Phải báo int8 so với float32 trên **cùng fold**, cùng cách đo thời gian. Thời gian trên chip phải đo, không ước lượng. Thử trọng số lớp như một siêu tham số trong CV bên trong | M3, Q3, firmware |
| 15 | Lượng tử hóa có thể làm giảm mạnh độ chính xác (Campanella: CNN còn khoảng 70%) (B9) | Bắt buộc so float32 với int8 (PTQ, nếu cần QAT) theo FA/h ở độ nhạy ≥ 95%, không chỉ theo accuracy | Q3 |
| 16 | 20–50 Hz đủ cho phát hiện sau va chạm (Villa & Casilari; Duan dùng 50 Hz). Phát hiện trước va chạm cần ≥ 100 Hz (KFall) | Dự kiến Q2: 60 Hz ≈ 120 Hz ≈ 238 Hz. Vẫn chạy cả ba theo đề. Nếu 60 Hz không thua thì khuyến nghị 60 Hz để tiết kiệm điện | Q2 |
| 17 | Các số rất cao trên FallAllD-neck đều đến từ chia ngẫu nhiên hoặc không rõ: Wang 2024 (99,52%), Tilburg (0,977), Özdemir (chia ngẫu nhiên) | Đây là các ví dụ cho H5. Chạy thêm một lần chia ngẫu nhiên cho mô hình tốt nhất. Đặt số của các bài này cạnh số LOSO chỉ để minh họa | H5 |
| 18 | ActivityID 128–135 có thể bị tràn thành −128…−121 khi lưu bằng int8 (Tilburg, suy luận của tôi). Có thể không phải người nào cũng có ngã ở logger cổ (Tilburg, Wang 2024) | `DATA_AUDIT.md`: đọc ID bằng int ≥ 16 bit; kiểm có ID âm hay không; đếm người có ngã và có ADL ở thiết bị đeo cổ. LOSO chỉ dùng những người có cả hai lớp, còn những người chỉ có ADL thì dùng để đếm báo nhầm | 5.0 |
| 19 | Thiết bị đeo cổ ít báo nhầm hơn cổ tay khoảng 8 lần (Saleh). Ngực thì kém eo do khác biệt cơ thể (Özdemir) | Đặc trưng bất biến với hướng là bắt buộc. Augmentation xoay chỉ áp cho train. Thí nghiệm 5.7 (eo, cổ tay) chỉ là tùy chọn | H2, 5.7 |
| 20 | Mặt dây thương mại trong viện dưỡng lão: 19% độ nhạy, 87% cảnh báo sai. Ngã thật làm độ nhạy giảm còn khoảng 57% (Bagalà), độ đặc hiệu ConvLSTM của KFall còn 73% (bài 9, B1, B6) | Phần Giới hạn của `REPORT.md` phải nói rõ: kết quả trên FallAllD (người trẻ, ±8 g) **không** đại diện cho viện dưỡng lão. Cần thu dữ liệu thật trước khi tuyên bố hiệu năng | REPORT |
| 21 | NEON (đeo cổ, MCU 16 bit, cây quyết định fixed-point, 111 µW): độ nhạy 91%, 0,115 FA/h (B7) | Mốc cho H4: nếu M1 (cây nhỏ) đạt gần M2/M3 thì ưu tiên M1, vì nhỏ và đơn giản hơn nhiều | H4, M1 |
| 22 | Mô hình chuỗi thời gian nhẹ (QUANT, MiniRocket) đứng đầu trên ngã thật; ResNet hay báo nhầm thành cụm (bài 11a, 11b) | Nếu còn thời gian, thử QUANT/MiniRocket làm mốc (dùng `aeon`, có ghi nguồn). Báo cáo "collapse ratio" (số cửa sổ sai trên mỗi cảnh báo) cho M3 | H4, 5.3 |

### Tóm tắt điều chỉnh kế hoạch

- **M0:** thêm M0-Saleh (C1&C2&C3), bên cạnh M0 theo đề.
- **M1:** đặc trưng gồm thống kê theo đề + Saleh-3 (bản gốc và bản bất biến thật) + Palmerini-5 + phần mở rộng riêng (ΔP, \|ω\|, góc trọng lực, thời gian nằm yên). Template wavelet chỉ tính trong fold train.
- **Chỉ số:**
  - Đánh giá dạng luồng có gộp episode, với cách chấm TP, FP, FN và độ trễ tự viết.
  - FA/h ghi rõ là "giờ ADL theo kịch bản".
  - Chọn ngưỡng theo chi phí c ∈ {1, 2, 5, 10}.
  - Báo độ nhạy riêng cho ngã có/không đứng dậy.
  - Báo tỉ lệ báo nhầm riêng cho near-fall (ADL 23, 15).
- **Giả thuyết:**
  - H1: kiểm cả hai vai trò của B (cổng và đặc trưng); thêm biến thể trễ áp suất.
  - H3: diễn đạt lại theo Palmerini-5 cộng phần mở rộng.
  - H4: thêm mốc NEON và QUANT.
  - H5: giữ nguyên.
- **Kiểm kê dữ liệu (mục 5.0):**
  - Cách đeo logger cổ (xem video).
  - Vị trí va chạm trong bản ghi 20 s.
  - ID âm do tràn int8.
  - Số người có ngã ở thiết bị đeo cổ.
  - Độ ồn của MS5607.
