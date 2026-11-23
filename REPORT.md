# Báo cáo: mô hình phát hiện ngã trên dữ liệu đeo cổ của FallAllD

Ngày 23/11/2026. Mọi con số dưới đây lấy từ file CSV trong `results/tables/` (tên file ghi cạnh từng bảng).
Đây là baseline trên dữ liệu **mô phỏng** (người trẻ tự ngã có chủ đích), không phải hiệu năng trên người cao tuổi.

## 1. Tóm tắt

> **Cập nhật Bản sửa 2 (mục 11):**
> - **Khuyến nghị mô hình không đổi:** LightGBM trên đặc trưng bất biến hướng, gia tốc + áp suất, 60 Hz, cửa sổ 4 s.
> - Theo cách đếm và cách train mới: đích 98 % cho recall 98,2 % và 1,51 báo nhầm/giờ; đích 99 % cho 99,5 % và 2,59 báo nhầm/giờ.
> - **Không cách sửa nào tốt hơn có ý nghĩa thống kê:** tinh chỉnh tham số, thêm đặc trưng ngã chậm, thêm bộ phát hiện nằm lâu.
> - **H2 được chấp nhận rõ:** đặc trưng theo trục thô tăng báo nhầm 4 lần khi mặt dây bị lật.
> - Các con số trong mục 1–10 dưới đây là của bản 1 và được giữ nguyên.

- **Có, mô hình hoạt động trên dữ liệu này.** Mô hình tốt nhất là **đặc trưng pha ngã + LightGBM (M1), dùng gia tốc + áp suất, 60 Hz, cửa sổ 4 s**.
- Đánh giá để riêng từng người ra kiểm tra (LOSO, 14 người); ngưỡng chỉ chọn trên những người còn lại. Kết quả:
  - đặt đích recall 98 %: **recall 98,1 %** [97,2–99,0], **1,26 báo nhầm/giờ ADL** [0,14–2,91];
  - đặt đích recall 99 %: **recall 99,6 %** [99,1–100], **3,1 báo nhầm/giờ** [0,95–6,1].
  
  (`summary_trees.csv`)
- **Q1 – kênh cảm biến:** giữ **gia tốc + áp suất (A+B)**.
  - Ở đích recall 98 %, áp suất giảm báo nhầm từ 10,2 xuống 1,26/giờ. 13/14 người giảm, 0 người tăng; Wilcoxon p = 0,0015.
  - Thêm gyro vào A+B không giúp: 1,12 so với 1,26/giờ, p = 0,32.
  - Recall giữa các cấu hình không khác nhau có ý nghĩa (p ≥ 0,13). (`paired_tests.csv`)
- **Q2 – tần số và cửa sổ:**
  - **60 Hz là đủ**; 120 Hz không tốt hơn một cách nhất quán.
  - Cửa sổ **2 s kém rõ** (3,0 báo nhầm/giờ). 3–6 s cho kết quả gần nhau (0,64–1,32/giờ, khoảng tin cậy chồng nhau). Chọn 4 s; tối thiểu 3 s. (`summary_q2.csv`)
- **Q3 – mô hình:**
  - **LightGBM** (300 cây × 15 lá, 20 đặc trưng) tốt nhất.
  - CNN nhỏ (2.753 tham số) ở cùng đích 98 % chỉ đạt recall 97,0 % với 9,4 báo nhầm/giờ (p = 0,005).
  - Một cây quyết định đơn độ sâu 6 (65 nút) đạt recall 98,9 % nhưng 7,7 báo nhầm/giờ.
  - Luật ngưỡng (M0) không dùng được khi đòi recall ≥ 98 %.
- **Q4 – lỗi:**
  - Bỏ sót nhiều nhất: **ngã trượt dọc tường** (7/20 lần) và ngã khỏi giường.
  - Báo nhầm (9 lần): xoay người trên giường, dừng/bắt đầu chạy, đứng dậy, cúi nhặt đồ.
  - Không có áp suất thì "đứng dậy hụt", "vấp không ngã" và xoay người trên giường gây phần lớn báo nhầm.
- **Khuyến nghị:** gia tốc + áp suất, không cần gyro, 60 Hz, cửa sổ 4 s bước 0,5 s, LightGBM trên đặc trưng pha ngã, ngưỡng chọn cho recall 98–99 %.

## 2. Dữ liệu

Chi tiết trong `DATA_AUDIT.md`. Những điểm ảnh hưởng tới kết quả:

- **Quy mô:** 14 người có dữ liệu cổ (thiếu S06). 2.292 bản ghi, mỗi bản đúng 20 s: 733 ngã, 1.485 ADL, 74 near-fall.
- **S04 và S10 không có ngã**, nên recall tính trên 12 người, còn báo nhầm tính trên 14 người.
- **Nhãn:**
  - FALL = ActivityID 101–135, kể cả 12 loại "ngã rồi tự đứng dậy".
  - NEAR_FALL = 15 (đứng dậy hụt) và 23 (vấp không ngã). Tính là âm, báo cáo riêng.
- **Va chạm nằm ở khoảng giây thứ 10** của bản ghi (91 % bản ghi ngã).
- **Ở cổ, gia tốc không bao giờ chạm ±8 g** (lớn nhất 7,88 g).
- **Áp suất:** khi ngã, áp suất tăng trung vị +11,3 Pa (hạ khoảng 0,9 m); ADL +0,1 Pa. Barometer có nhiễu xung lớn nên phải lọc trung vị.
- **Thời gian ADL dùng làm mẫu số cho "báo nhầm/giờ" là 7,1 giờ.** Mỗi cửa sổ quyết định tính 0,5 s, trên 1.559 bản ghi âm. ADL ở đây là chuỗi động tác dày đặc theo kịch bản, **không phải một ngày sống thật**. Không được quy đổi thẳng sang báo nhầm/ngày.

### 2.1 Đặt trong bối cảnh nghiên cứu

Chi tiết trong `LITERATURE.md`.

| Nghiên cứu | Dữ liệu, vị trí đeo | Cách chia | Kết quả công bố | So với kết quả này |
|---|---|---|---|---|
| Wang và cộng sự 2024 | FallAllD, cổ | ngẫu nhiên 75/25 | độ nhạy 98,24 %, độ đặc hiệu 99,47 % (có thể bị đảo nhãn) | Ở mức cửa sổ, ngưỡng 0,5: mô hình này đạt 98,4 % / 99,85 % khi chia theo người, 99,9 % / 99,9 % khi chia ngẫu nhiên (`h5_random_vs_loso.csv`). Số cửa sổ không nói được báo nhầm theo thời gian. |
| Khóa luận Tilburg 2024 | FallAllD, cổ | ngẫu nhiên 80/20, cả bản ghi 20 s | accuracy 0,977 | Không so được: không trượt cửa sổ, không có chỉ số theo sự kiện. |
| Saleh và cộng sự 2021 | viện dưỡng lão thật, cổ, thiết bị khác | – | 1 báo nhầm / 25 ngày; 2/2 ngã thật | Mốc đích cho thiết bị thật. Không so được trực tiếp: ADL thật thưa hơn nhiều so với ADL kịch bản. |
| NEON (Wang C. 2018) | dây đeo cổ, gia tốc + barometer | – | độ nhạy 91 %, 0,115 báo nhầm/giờ đeo | Cùng hướng gia tốc + áp suất. Giờ đeo thật khác giờ ADL kịch bản. |
| Palmerini 2020 | ngã thật (FARSEEING), lưng dưới | theo người | độ nhạy > 80 %, 0,56 báo nhầm/giờ | Ngã thật khó hơn ngã mô phỏng nhiều. |
| Bagalà 2012 | ngã thật, 13 thuật toán | – | độ nhạy trung bình 57 %, độ đặc hiệu 83 % | Lý do không coi recall 98 % ở đây là recall thật. |

### 2.2 Giả thuyết H1–H5

| | Giả thuyết | Kết luận | Bằng chứng |
|---|---|---|---|
| H1 | A+B ≈ A+G+B > A+G > A | **Chấp nhận phần chính.** A+B ≈ A+G+B; A+B tốt hơn A+G và A. Còn "A+G > A" thì không ổn định. | Đích 98 %, A+B so với A: 1,26 vs 10,2/giờ, p = 0,0015. A+B so với A+G: 1,26 vs 7,7/giờ, p = 0,004. A+B so với A+G+B: p = 0,32. A+G so với A: p = 0,04 ở đích 98 %, nhưng 0,72 (95 %) và 0,07 (99 %). |
| H2 | Đặc trưng bất biến hướng (hoặc xoay ngẫu nhiên khi train) giảm báo nhầm so với trục thô | **Chưa đủ bằng chứng** | M1 chỉ dùng đặc trưng bất biến; chưa có phép so trực tiếp. CNN (trục thô + xoay ngẫu nhiên) kém hơn, nhưng khác cả loại mô hình. |
| H3 | Đặc trưng pha ngã giúp M1 gần bằng M2/M3 với kích thước nhỏ hơn | **Chấp nhận** (M1 còn tốt hơn M2). Chưa thử bỏ riêng nhóm đặc trưng pha. | M1 vs M2 (A+B, đích 98 %): 1,26 vs 9,4/giờ, p = 0,005. Ba đặc trưng mạnh nhất: đỉnh \|a\|, số đỉnh > 2 g, tỉ lệ nằm yên sau va chạm (`feature_importance_M1lgbm_AB.csv`). |
| H4 | CNN + LSTM/GRU không tốt hơn CNN | **Chưa kiểm** | Người dùng dừng phần CNN; chưa chạy M3. |
| H5 | Chia ngẫu nhiên cho số cao hơn chia theo người | **Chấp nhận** | Cùng mô hình, cùng cửa sổ, ngưỡng 0,5: tỉ lệ cửa sổ ngã bị bỏ sót 0,14 % (ngẫu nhiên) so với 1,56 % (theo người), tức thấp hơn khoảng 11 lần. Accuracy 99,92 % so với 99,76 %. Chỉ để minh họa. |

## 3. Phương pháp

- **Tiền xử lý** (`src/data/preprocess.py`):
  - Đổi đơn vị: g, dps, Pa.
  - Lọc chống aliasing rồi resample IMU về 60 Hz (và 120 Hz cho Q2).
  - Áp suất: trung vị trượt 0,5 s để bỏ xung, lọc thông thấp 1 Hz (cả hai đều nhân quả, chỉ dùng mẫu quá khứ), nội suy lên lưới thời gian của IMU.
- **Cửa sổ** (`src/data/windows.py`):
  - Cửa sổ dài L, trượt bước 0,5 s trên mọi bản ghi.
  - Cửa sổ dương khi train: va chạm đặt ở vị trí L/3 trong cửa sổ, lệch thêm ±0,5 s (5 bản lệch cho mỗi cú ngã).
  - Cửa sổ âm: mọi cửa sổ trượt của bản ghi ADL và near-fall.
- **Đặc trưng M1** (`src/features/feats.py`): 27 đặc trưng, đều không phụ thuộc hướng đeo, nên mặt dây lật cũng không đổi. A dùng 16, A+B dùng 20.
  - thống kê của \|a\| và \|ω\|;
  - đặc trưng theo pha quanh đỉnh va chạm: \|a\| nhỏ nhất khi rơi, độ dốc va chạm, độ dao động sau va chạm, tỉ lệ nằm yên, góc thay đổi tư thế, góc quay;
  - đặc trưng áp suất: ΔP sau − trước va chạm, độ dốc, biên độ.
- **Mô hình** (`src/models/`):
  - M0: luật ngưỡng — đỉnh \|a\|, kèm điều kiện đổi tư thế và ΔP.
  - M1: LightGBM 300 cây, 15 lá; và một cây quyết định độ sâu 6.
  - M2: CNN depthwise-separable 2.753 tham số, xoay 3D ngẫu nhiên, nhiễu, co giãn ±10 %; 1 seed.
- **Chia dữ liệu:**
  - LOSO 14 người; có `assert` kiểm không người nào nằm ở cả train và test.
  - Ngưỡng M1 chọn trên dự đoán out-of-fold của GroupKFold 4 phần trên chính những người train.
  - Ngưỡng và early stopping của M2 dựa trên 3 người validation lấy trong nhóm train.
- **Chỉ số theo sự kiện** (`src/eval/events.py`):
  - Cảnh báo cách nhau < 10 s gộp thành một sự kiện.
  - Ngã tính là phát hiện nếu có cảnh báo trong [−1 s, +5 s] quanh va chạm.
  - Mọi sự kiện trong bản ghi ADL/near-fall là báo nhầm.
  - Khoảng tin cậy 95 %: bootstrap theo người, 2.000 lần.
  - So sánh: Wilcoxon ghép cặp theo người.

## 4. Kết quả chính (60 Hz, cửa sổ 4 s, LOSO)

Recall và báo nhầm/giờ ở ba đích recall; ngưỡng chọn trên vòng trong. (`summary_trees.csv`, `summary_nn.csv`)

| Mô hình | Cảm biến | Đích 95 %: recall · báo nhầm/giờ | **Đích 98 %: recall · báo nhầm/giờ** | Đích 99 %: recall · báo nhầm/giờ | PR-AUC cửa sổ |
|---|---|---|---|---|---|
| M1 LightGBM | A | 94,4 % · 3,2 | 98,0 % [97,0–98,9] · 10,2 [5,5–17,3] | 99,0 % · 19,9 | 0,975 |
| M1 LightGBM | A+G | 93,9 % · 3,6 | 97,7 % [96,4–98,8] · 7,7 [2,8–16,3] | 98,9 % · 17,2 | 0,969 |
| **M1 LightGBM** | **A+B** | 92,5 % · 0,42 | **98,1 % [97,2–99,0] · 1,26 [0,14–2,91]** | **99,6 % · 3,1** | **0,987** |
| M1 LightGBM | A+G+B | 92,1 % · 0,56 | 97,7 % [96,3–98,7] · 1,12 [0,14–2,46] | 98,9 % · 4,5 | 0,984 |
| M1 cây độ sâu 6 | A+B | 98,9 % · 7,7 | 98,9 % · 7,7 | 99,0 % · 8,7 | 0,840 |
| M0 luật ngưỡng | A+B | 93,0 % · 5,9 | 99,0 % · 187 | 100 % · 218 | 0,755 |
| M2 CNN | A+B | 92,9 % · 6,4 | 97,0 % [94,9–98,8] · 9,4 [3,8–16,1] | 98,6 % · 14,0 | 0,891 |

Ghi chú:
- **Ở đích 95 %, recall thật trên người test chỉ còn 92–94 %:** ngưỡng chọn trên người khác không giữ đủ 95 %. Ở đích 98–99 %, recall thật bám sát đích.
- Cây đơn và luật ngưỡng có ít mức điểm số, nên nhiều đích cho cùng một ngưỡng.

### 4.1 Q2: tần số mẫu và độ dài cửa sổ (M1 LightGBM, A+B, đích 98 %)

(`summary_q2.csv`)

| | 2 s | 3 s | 4 s | 6 s |
|---|---|---|---|---|
| 60 Hz | 97,3 % · 3,0/giờ | 97,1 % · 1,06/giờ | 98,1 % · 1,26/giờ | 97,8 % · 0,64/giờ |
| 120 Hz | 96,9 % · 2,0/giờ | 97,3 % · 1,32/giờ | 97,7 % · 1,12/giờ | 98,2 % · 0,80/giờ |

Cửa sổ 6 s có ít cửa sổ quyết định hơn trên mỗi bản ghi 20 s (6,3 giờ so với 7,1 giờ), nên phép so với 4 s không hoàn toàn ngang nhau. Khoảng tin cậy ở 3–6 s chồng lên nhau.

## 5. Hình

- `results/figures/q1_sensors.png`: báo nhầm/giờ theo cấu hình cảm biến ở ba đích recall, kèm khoảng tin cậy 95 %.
- `results/figures/curve_recall_vs_fah.png`: recall theo báo nhầm/giờ khi quét một ngưỡng chung trên toàn bộ điểm số test. Đường này lạc quan hơn bảng mục 4, vì ngưỡng không chọn trên vòng trong; chỉ dùng để xem dáng đánh đổi.
- `results/figures/examples_M1lgbm_AB_sens98.png`: 2 ca bỏ sót (trượt dọc tường, ngã khỏi giường) và 2 ca báo nhầm (dừng chạy, xoay người trên giường).
- `results/figures/audit_examples.png`, `audit_peak_hist.png`: kiểm kê dữ liệu.

## 6. Phân tích lỗi (M1 LightGBM, A+B, đích 98 %)

(`errors_trees_AB_60_4_M1lgbm_sens98.csv`, `recall_by_recovery_trees_AB_60_4_M1lgbm_sens98.csv`)

**Bỏ sót 14/733 cú ngã:**

| ActivityID | Loại ngã | Bỏ sót |
|---|---|---|
| 135 | ngất khi đứng, trượt chậm dọc tường | **7/20** |
| 127 | ngã khỏi giường khi xoay người | 2/41 |
| 102, 108, 122 | ngã có tự đứng dậy (vấp/trượt) | mỗi loại 1 |
| 113 | ngất khi đi, ngã sang bên | 1/25 |
| 130 | ngất từ ghế, ngã ra sau | 1/11 |

- Ngã trượt dọc tường không có cú va chạm rõ. Ngã khỏi giường hạ độ cao ít, ΔP trung vị chỉ +5,5 Pa.
- **Ngã có tự đứng dậy vẫn được bắt tốt:** recall 98,75 % (240 cú) so với 97,8 % ở ngã không đứng dậy (493 cú).

**Báo nhầm 9 lần trong 7,1 giờ:**
- xoay người trên giường 2, dừng chạy 2, bắt đầu chạy 1, đứng dậy 1, nằm xuống giường 1, cúi nhặt đồ 1, vấp không ngã (near-fall) 1;
- riêng S05 chiếm 5/9.

**Không có áp suất (A, đích 98 %), báo nhầm 73 lần.** Nhiều nhất là đứng dậy hụt (13), xoay người trên giường (11), vấp không ngã (11) và dừng chạy (9) (`errors_trees_A_60_4_M1lgbm_sens98.csv`). Đây chính là các động tác có va chạm mạnh nhưng không hạ độ cao, nên áp suất tách được.

**Lưu ý về S05:** ở đích 95 %, S05 chiếm 17/55 lần bỏ sót. ΔP khi S05 ngã nhỏ (phân vị 10 % chỉ 1,4 Pa, so với 5–7 Pa ở đa số người). Một mô hình dựa nhiều vào áp suất sẽ yếu với những người có ΔP nhỏ, ví dụ ngã chậm, hoặc ngồi/nằm sẵn trước khi ngã.

## 7. M2 (CNN) và M3 (CNN-LSTM/GRU)

- M2 chạy đủ 14 fold cho cấu hình A+B, 1 seed. Kết quả ở bảng mục 4.
- So với M1 LightGBM ở đích 98 %: báo nhầm 9,4 so với 1,26/giờ. CNN kém hơn ở 10/14 người và không tốt hơn ở người nào; p = 0,005. Recall không khác có ý nghĩa (p = 0,47) (`paired_tests.csv`).
- Phép so có hai điểm bất lợi cho CNN:
  - ngưỡng chọn trên 3 người validation, thay vì out-of-fold của 13 người như LightGBM;
  - CNN rất nhỏ (2.753 tham số) và chỉ có 1 seed.
- M3a–d (CNN + LSTM/GRU) đã viết trong `src/models/cnn.py` nhưng **chưa chạy**: người dùng dừng phần CNN để tập trung vào LightGBM.
- Kết luận một câu: trên dữ liệu này, chưa có lý do dùng mạng nơ-ron thay cho LightGBM trên đặc trưng pha ngã.

## 8. Giới hạn

- **Ngã mô phỏng của người trẻ** (21–53 tuổi, theo một nguồn thứ cấp). Ngã thật của người cao tuổi chậm hơn, ít va chạm hơn, và hay xảy ra từ giường/ghế. Trên ngã thật, các thuật toán công bố đạt độ nhạy trung bình chỉ 57 % (Bagalà 2012). Recall 98 % ở đây là **cận trên**.
- **ADL kịch bản dày đặc**, nên báo nhầm/giờ không quy đổi được sang báo nhầm/ngày. Chỉ dùng để so giữa các cấu hình.
- **Logger cổ của FallAllD có thể gắn khác mặt dây treo trên dây.** Bài gốc không truy cập được, video cần đăng nhập. Mặt dây lủng lẳng sẽ có thêm dao động và va đập riêng.
- **Barometer chỉ 10 Hz và nhiễu xung lớn.** ΔP của ngã từ giường/ghế nhỏ (+5–9 Pa), gần mức nhiễu.
- **Ít người:** 14 người, chỉ 12 có ngã, nên khoảng tin cậy rộng. Báo nhầm ở đích 98 % chỉ là 9 sự kiện; khoảng tin cậy 0,14–2,9/giờ.
- **Chưa kiểm:** H2 (bất biến hướng), H4 (M3), chọn siêu tham số LightGBM (dùng một bộ cố định), nhiều seed cho CNN.

## 9. Đề xuất cho đợt thu dữ liệu riêng của AN GIA MINI

Dựa trên phân tích lỗi:

1. **Thêm nhiều ngã chậm/không va chạm:** trượt dọc tường, khuỵu gối từ từ, ngồi sụp xuống. Đây là loại bị bỏ sót nhiều nhất (7/20).
2. **Thêm ngã từ giường và ghế**, với nhiều độ cao giường khác nhau. ΔP nhỏ nên dễ bỏ sót, mà người cao tuổi lại hay ngã ở đây.
3. **Thêm ADL quanh giường:** xoay người, nằm xuống, ngồi dậy mạnh. Đây là nguồn báo nhầm còn lại khi đã có áp suất.
4. **Thêm near-fall:** đứng dậy hụt, vấp rồi lấy lại thăng bằng, ngồi phịch xuống ghế. Không có áp suất, đây là nguồn báo nhầm lớn nhất.
5. **Ghi ADL dài, liên tục cả ngày** ở viện dưỡng lão, để đo báo nhầm/ngày thật. Đây là con số quyết định khi đưa vào dùng (mốc Saleh 2021: 1 lần / 25 ngày).
6. **Ghi rõ cách đeo** (độ dài dây, trong/ngoài áo), và thu cả dao động của mặt dây khi đi, cúi, chạy.
7. **Ghi những người có ΔP khi ngã nhỏ** (như S05), để kiểm mô hình không quá phụ thuộc vào áp suất.

## 10. Chạy lại

Xem `README.md`.
- Toàn bộ số trong báo cáo: `python run_all.py --stages audit,trees,report`, cộng với lệnh Q2, lệnh H5 và lệnh CNN trong README.
- `python run_all.py --quick` chạy thử mọi bước trên 2 fold.
- Mọi quyết định theo thời gian: `LOG.md`.

---

## 11. Bản sửa 2 (23/11/2026)

Phạm vi: chỉ phần mô hình, không có phần cứng, xuất C hay firmware. Giữ nguyên các quy tắc:
- LOSO theo người, có `assert` chống rò rỉ;
- ngưỡng chọn trên out-of-fold của người train (GroupKFold 4 phần);
- mọi số lấy từ CSV trong `results/tables/` (tên file ghi cạnh từng bảng).

Code nằm ở `src/experiments/` (`t1_clipping.py` … `t6_slow.py`, `r2_tables.py`).

### 11.0 Tóm tắt bản sửa 2

- **Khuyến nghị mô hình không đổi.** Vẫn là LightGBM trên đặc trưng bất biến hướng, gia tốc + áp suất (A+B), 60 Hz, cửa sổ 4 s.
- **Số chính thức mới, theo cách đếm mới (11.2):**
  - đích 98 %: **recall 98,2 %** [97,1–99,1], **1,51 báo nhầm/giờ** [0,33–3,38];
  - đích 99 %: **99,5 %** [99,0–99,9], **2,59/giờ** [0,88–4,89].
  
  (`r2_task2_fall_fa.csv`)
- **Không có cắt đỉnh** ở thiết bị cổ (11.1). Đặc trưng "đỉnh |a|" đúng như đo.
- **Cách đếm mới không thêm báo nhầm nào trong bản ghi ngã**, chỉ thêm 2,1 giờ vào mẫu số. Train thêm mẫu âm từ bản ghi ngã không khác biệt có ý nghĩa (p ≥ 0,05) (11.2).
- **Tinh chỉnh tham số bằng nested CV:** 0,97 so với 1,51 báo nhầm/giờ ở đích 98 %, nhưng p = 0,27, nên chưa đủ bằng chứng để đổi (11.3).
  - Learning rate 0,1 được chọn ở 14/14 fold; 7 lá ở 11/14 fold.
  - Mô hình nhỏ cũng đủ: 150 cây × 7 lá cho 1,08 báo nhầm/giờ.
- **H2 được chấp nhận** (11.4).
  - Đặc trưng bất biến cho 1,51 báo nhầm/giờ, không đổi khi dữ liệu test bị xoay.
  - Đặc trưng trục thô cho 4,42/giờ, và lên 18,0/giờ khi xoay (p = 0,0004).
- **Recall tăng theo cường độ ngã (11.5):**
  - theo đỉnh |a|: 94 % ở 2–3 g, lên 100 % ở trên 6 g;
  - theo ΔP: 90 % khi ΔP < 3 Pa, lên 99 % khi ΔP > 10 Pa.
- **Ngã chậm** (trượt dọc tường, ID 135) vẫn là điểm yếu: bỏ sót 8/20 (11.6).
  - Đặc trưng không cần va chạm trên cửa sổ 8 s bắt thêm 2 cú (đích 98 %) mà không tăng báo nhầm; không có ý nghĩa thống kê.
  - Bộ "nằm lâu" ghép bằng OR chỉ bắt thêm 2/13 cú ngã bị bỏ sót, nhưng báo nhầm tăng từ 1,51 lên 4,3–9,9/giờ. **Không khuyến nghị** trên dữ liệu 20 s.
- **Việc 7 (CNN/CNN-LSTM công bằng) chưa làm** vì chi phí tính toán (11.7). H4 vẫn chưa kiểm.

### 11.1 Cắt đỉnh trên giá trị thô (thiết bị cổ)

(`r2_clip_axes.csv`, `r2_clip_by_label.csv`, `r2_clip_hist_top1pct_acc.csv`, hình `r2_clip_hist_acc.png`)

**Hệ số đổi đơn vị đang dùng** (`src/data/load.py`):
- gia tốc 0,244 mg/LSB (±8 g); gyro 70 mdps/LSB (±2000 dps);
- nguồn: datasheet LSM9DS1 (DocID025715 Rev 2, Table 3) và script chính thức `Plot_FallAllD_Record.m` trên IEEE DataPort, cả hai dùng cùng hệ số;
- kiểm bằng dữ liệu: khi đứng yên, độ lớn thô trung vị là 4.012 LSB (ADL) và 4.072 LSB (ngã), tức 0,979 g và 0,993 g. Nếu logger đặt ±16 g (0,732 mg/LSB) thì 1 g chỉ khoảng 1.366 LSB.

| Cảm biến | Trục | Mẫu = +32767 | Mẫu = −32768 | Mẫu có \|thô\| ≥ 32000 | Thô nhỏ nhất / lớn nhất | Vật lý |
|---|---|---|---|---|---|---|
| gia tốc | x | 0 | 0 | 0 | −30647 / 31827 | −7,48 / 7,77 g |
| gia tốc | y | 0 | 0 | 0 | −30600 / 31430 | −7,47 / 7,67 g |
| gia tốc | z | 0 | 0 | 4 | −32285 / 30895 | −7,88 / 7,54 g |
| gyro | x | 0 | 0 | 2 | −29504 / 32715 | −2065 / 2290 dps |
| gyro | y | 0 | 1 | 3 | −32768 / 30770 | −2294 / 2154 dps |
| gyro | z | 0 | 0 | 0 | −18166 / 23956 | −1272 / 1677 dps |

- **Phân bố đuôi:** 1 % giá trị |thô| lớn nhất của gia tốc (từ 6.244 LSB, tức 1,52 g trở lên) giảm đều tới khoảng 32.000 LSB. Không có cột dồn ở giới hạn int16.
- **Kết luận:** gia tốc **không bị cắt đỉnh** ở bản ghi nào: 0/733 cú ngã (0 %), 0/1.485 ADL.
  - Đặc trưng "đỉnh |a|" vì vậy không bị ảnh hưởng. Đỉnh |a| có thể vượt 8 g, vì đó là độ lớn của vector 3 trục.
  - Gyro chạm −32768 đúng 1 mẫu, ở 1 bản ghi ADL (0,07 % ADL), 0 cú ngã. Gyro không nằm trong cấu hình khuyến nghị.

### 11.2 Đếm lại báo nhầm và mẫu âm từ bản ghi ngã

(`r2_task2_fall_fa.csv`, `r2_task2_paired.csv`)

**Quy tắc mới** (`src/eval/events.py`, `COUNT_FALL_FA = True`):
- Trong bản ghi ngã, mọi sự kiện cảnh báo không chứa cảnh báo nào trong [−1 s, +5 s] quanh va chạm là báo nhầm. Một sự kiện là chuỗi cảnh báo cách nhau dưới 10 s.
- Thời gian quyết định nằm ngoài [−1 s, +5 s] được cộng vào mẫu số.
- Mẫu số tăng từ 7,145 lên 9,272 giờ.
- Kiểm bằng tay (nối chuỗi tường minh) và bằng 30 phép thử ngẫu nhiên so đường tính nhanh với đường tính chậm.

**Kết quả kiểm: không có báo nhầm nào trong bản ghi ngã**, ở mọi cấu hình và mọi đích recall.
- Ví dụ A, đích 99 %: có 154 cảnh báo nằm ngoài [−1 s, +5 s] trong bản ghi ngã, nhưng chúng thuộc 51 cú ngã đã được phát hiện, và đều cách lần phát hiện dưới 10 s nên gộp vào cùng sự kiện.
- 7 cú ngã bị bỏ sót không có cảnh báo nào.
- Lý do: bản ghi chỉ dài 20 s và va chạm ở khoảng giây thứ 10, nên phần ngoài khoảng chỉ kéo dài khoảng 5–6 s mỗi bên. Với dữ liệu ghi dài, quy tắc này sẽ có tác dụng.

**Mẫu âm khi train:**
- Bản 1 **không** dùng cửa sổ của bản ghi ngã làm mẫu âm.
- Bản 2 thêm mọi cửa sổ trượt của bản ghi ngã cách va chạm hơn 0,5 s, dù trước hay sau (`trees._train_rows`).

Bảng trước/sau. Mỗi ô: recall · báo nhầm/giờ (số báo nhầm).

| Cấu hình | Đích | Trước (bản 1) | Đếm mới, train cũ | **Đếm mới, train mới (bản 2)** | p (FA/h), train mới vs cũ |
|---|---|---|---|---|---|
| A | 98 % | 98,0 % · 10,2 (73) | 98,0 % · 7,87 (73) | 98,1 % · 7,33 (68) | 0,21 |
| A | 99 % | 99,0 % · 19,9 (142) | 99,0 % · 15,3 (142) | 99,2 % · 16,4 (152) | 0,051 |
| A+B | 98 % | 98,1 % · 1,26 (9) | 98,1 % · 0,97 (9) | **98,2 % · 1,51 (14)** | 0,35 |
| A+B | 99 % | 99,6 % · 3,08 (22) | 99,6 % · 2,37 (22) | **99,5 % · 2,59 (24)** | 0,61 |
| A+G+B | 98 % | 97,7 % · 1,12 (8) | 97,7 % · 0,86 (8) | 97,8 % · 1,40 (13) | 0,32 |
| A+G+B | 99 % | 98,9 % · 4,48 (32) | 98,9 % · 3,45 (32) | 99,2 % · 3,34 (31) | 0,69 |

Mẫu số: 7,145 giờ ở bản 1; 9,272 giờ ở cả hai cột đếm mới.

- Train lại không thay đổi kết quả một cách có ý nghĩa (mọi p ≥ 0,05, kể cả recall).
- Bản 2 vẫn dùng cách train mới làm chuẩn, vì nó đúng nguyên tắc: mọi cửa sổ không chứa va chạm là mẫu âm.
- **Từ đây, mọi so sánh trong mục 11 dùng giao thức bản 2.** Mốc so sánh là A+B: 98,2 % · 1,51/giờ.

Lỗi ở mốc này (đích 98 %; `errors_r2_AB_60_4_M1lgbm_sens98.csv`):
- **Bỏ sót 13/733 cú ngã:** 135 (trượt dọc tường) ×8, 127 ×2, 102, 128 và 130 mỗi loại ×1.
- **Báo nhầm 14 lần:** nằm xuống giường 3, xoay người trên giường 3, chạy nhanh 2, dừng chạy 2, chạy chậm 1, bắt đầu chạy 1, cúi nhặt đồ 1, vấp không ngã 1.
- Ngã có tự đứng dậy: recall 99,2 % (240 cú); ngã không đứng dậy: 97,8 % (493 cú).

### 11.3 Tinh chỉnh siêu tham số LightGBM bằng nested CV (A+B)

(`r2_tune_chosen_per_fold.csv`, `r2_tune_summary.csv`, `r2_tune_paired.csv`, `r2_tune_tradeoff.csv`, `r2_tune_inner_all.csv`, hình `r2_tune_tradeoff.png`)

- **Lưới (120 bộ):** số cây {50, 100, 150, 300, 500} × số lá {7, 15, 31} × learning rate {0,03; 0,1} × min_child_samples {20, 50} × class weight có/không.
- **Vòng trong:** GroupKFold 4 phần theo người, chỉ trên người train.
- **Tiêu chí chọn:** ít báo nhầm/giờ nhất ở ngưỡng đạt recall 98 % trên out-of-fold của vòng trong. Hòa thì chọn mô hình nhỏ hơn.
- **Cách tính rẻ:** mỗi bộ (lá, lr, min_child, class weight) chỉ fit một lần với 500 cây; các mức 50–300 cây đọc bằng `num_iteration`. Đã kiểm sai lệch so với train riêng là 0,0.

**Bộ được chọn ở từng fold:**

| Fold | Cây | Lá | lr | min_child | class weight |
|---|---|---|---|---|---|
| S01 | 300 | 7 | 0,1 | 20 | không |
| S02 | 300 | 15 | 0,1 | 20 | có |
| S03 | 500 | 31 | 0,1 | 50 | có |
| S04 | 500 | 7 | 0,1 | 20 | có |
| S05 | 500 | 7 | 0,1 | 50 | không |
| S07 | 100 | 7 | 0,1 | 20 | không |
| S08 | 150 | 7 | 0,1 | 50 | không |
| S09 | 500 | 7 | 0,1 | 20 | không |
| S10 | 150 | 7 | 0,1 | 50 | không |
| S11 | 500 | 31 | 0,1 | 20 | có |
| S12 | 500 | 7 | 0,1 | 50 | có |
| S13 | 150 | 7 | 0,1 | 20 | không |
| S14 | 300 | 7 | 0,1 | 20 | không |
| S15 | 300 | 7 | 0,1 | 20 | không |

Learning rate 0,1 được chọn ở 14/14 fold; 7 lá ở 11/14; không class weight ở 9/14. Số cây thay đổi từ 100 đến 500.

**LOSO: tinh chỉnh so với bộ cố định (300 cây × 15 lá, lr 0,05):**

| Đích | Tinh chỉnh (nested) | Cố định (bản 2) | p FA/h | p recall |
|---|---|---|---|---|
| 95 % | 94,1 % · 0,32/giờ (3) | 93,2 % · 0,32/giờ (3) | 1,0 | 0,19 |
| 98 % | 98,0 % [97,0–98,9] · 0,97/giờ [0,22–1,94] (9) | 98,2 % · 1,51/giờ (14) | 0,27 | 0,63 |
| 99 % | 99,2 % · 2,70/giờ (25) | 99,5 % · 2,59/giờ (24) | 0,92 | 0,88 |

→ Tinh chỉnh **không cải thiện có ý nghĩa**. Giữ bộ cố định làm mốc. Bộ nhỏ hơn (7 lá, lr 0,1) là lựa chọn thay thế ngang hàng.

**Đánh đổi kích thước × báo nhầm** (đích 98 %, LOSO; lr / min_child / class weight chọn lồng bên trong cho từng cặp). Mỗi ô: báo nhầm/giờ (recall).

| Số cây | 7 lá | 15 lá | 31 lá |
|---|---|---|---|
| 50 | 1,62 (97,5 %) | 1,94 (98,5 %) | 2,27 (98,6 %) |
| 100 | 1,62 (98,2 %) | 1,73 (98,2 %) | 1,73 (98,2 %) |
| 150 | 1,08 (97,8 %) | 1,62 (98,0 %) | 1,19 (98,0 %) |
| 300 | 1,29 (98,0 %) | 0,97 (97,8 %) | 1,29 (98,2 %) |
| 500 | 0,86 (98,0 %) | 1,19 (98,0 %) | 1,08 (98,1 %) |

Đường này khá phẳng (0,86–2,27/giờ), và mọi khoảng tin cậy chồng nhau (hình `r2_tune_tradeoff.png`). Mô hình cỡ 50–150 cây × 7 lá đã gần bằng mô hình lớn. Bảng này dùng điểm test LOSO, chỉ để mô tả, không dùng để chọn.

### 11.4 H2: đặc trưng bất biến hướng so với đặc trưng theo trục thô

(`r2_h2_summary.csv`, `r2_h2_paired.csv`)

Bốn bộ đặc trưng (M1 A+B, giao thức bản 2), mỗi bộ thử trên dữ liệu test gốc và trên dữ liệu test bị xoay. Xoay nghĩa là một phép xoay 3D ngẫu nhiên cho mỗi bản ghi test, như mặt dây bị lật. Ngưỡng vẫn chọn trên dữ liệu train không xoay. Mỗi ô: recall · báo nhầm/giờ (số báo nhầm).

| Bộ đặc trưng | Số đặc trưng | Đích 98 %, test gốc | Đích 98 %, test xoay | Đích 99 %, test gốc | Đích 99 %, test xoay |
|---|---|---|---|---|---|
| **Bất biến (hiện tại)** | 20 | **98,2 % · 1,51 (14)** | **98,2 % · 1,51 (14)** | **99,5 % · 2,59 (24)** | **99,5 % · 2,59 (24)** |
| Trục thô + áp suất | 22 | 98,2 % · 4,42 (41) | 97,7 % · 18,0 (167) | 99,6 % · 7,23 (67) | 99,0 % · 23,9 (222) |
| Trục thô + xoay ngẫu nhiên khi train | 22 | 98,1 % · 3,02 (28) | 98,0 % · 7,77 (72) | 99,5 % · 4,64 (43) | 98,8 % · 10,9 (101) |
| Bất biến + trục thô | 38 | 97,5 % · 2,48 (23) | 97,4 % · 3,13 (29) | 98,9 % · 4,31 (40) | 99,3 % · 8,09 (75) |

- **Đặc trưng bất biến tốt nhất và hoàn toàn bền khi xoay:** cùng kết quả, cùng số báo nhầm.
- So bất biến với trục thô, trên dữ liệu gốc: ở đích 98 %, 1,51 so với 4,42/giờ, p = 0,21; ở đích 99 %, 2,59 so với 7,23, p = 0,023. So với trục thô có xoay khi train: p = 0,011 (98 %) và 0,021 (99 %).
- **Độ bền khi xoay:**
  - Trục thô: báo nhầm tăng 4 lần (4,42 → 18,0; 13/14 người tăng; p = 0,0004).
  - Xoay ngẫu nhiên khi train chỉ giảm bớt một phần (3,02 → 7,77; p = 0,002).
  - Ghép thêm trục thô vào đặc trưng bất biến làm mất độ bền: 4,31 → 8,09 ở đích 99 %, p = 0,002.
- **H2: chấp nhận.**

### 11.5 Recall theo cường độ ngã (M1 A+B, bản 2)

(`r2_strata_fixed.csv`)

Đỉnh |a| (238 Hz) và ΔP lấy từ phần kiểm kê dữ liệu, độc lập với mô hình. Không có cú ngã nào có đỉnh |a| dưới 2 g.

| Đỉnh \|a\| | Số ngã | Recall, đích 95 % | **Recall, đích 98 %** | Recall, đích 99 % |
|---|---|---|---|---|
| < 2 g | 0 | – | – | – |
| 2–3 g | 102 | 88,2 % | **94,1 %** | 97,1 % |
| 3–4 g | 200 | 92,0 % | **97,5 %** | 99,5 % |
| 4–6 g | 254 | 96,1 % | **99,2 %** | 100 % |
| > 6 g | 177 | 93,2 % | **100 %** | 100 % |

| ΔP | Số ngã | Recall, đích 95 % | **Recall, đích 98 %** | Recall, đích 99 % |
|---|---|---|---|---|
| < 3 Pa | 31 | 58,1 % | **90,3 %** | 100 % |
| 3–6 Pa | 44 | 77,3 % | **95,5 %** | 97,7 % |
| 6–10 Pa | 189 | 91,5 % | **97,4 %** | 98,9 % |
| > 10 Pa | 460 | 98,3 % | **99,3 %** | 99,8 % |
| không tính được | 9 | 66,7 % | 100 % | 100 % |

ΔP không tính được khi đỉnh quá gần mép bản ghi.

**Theo từng người (đích 98 %):**
- 12 người có ngã đạt từ 93,8 % (S14, 61/65) tới 100 % (S01, S03, S12).
- **S05: 98,3 % (58/59).** Ở đích 95 %, S05 chỉ đạt 69,5 % (41/59), vì ngưỡng cao làm lộ điểm yếu của S05 là ΔP nhỏ. Đặt đích 98–99 % thì gần như hết.

### 11.6 Ngã chậm và ngã khỏi giường (ID 135, 127, 130)

**(a) Đặc trưng không cần va chạm** (`src/features/extra.py: slow_features`; `r2_slow_summary.csv`, `r2_slow_by_id.csv`, `r2_slow_paired.csv`)

Sáu đặc trưng mới, đều bất biến hướng:
- thời gian nằm yên liên tục ở cuối cửa sổ;
- góc nghiêng giữa 1 s cuối và 1 s đầu;
- tốc độ hạ độ cao lớn nhất (dP/dt, Pa/s, trên 1 s);
- năng lượng chuyển động của nửa đầu và nửa sau;
- tỉ lệ thời gian |a| nằm trong 1 ± 0,05 g ở nửa sau.

Các đặc trưng này tính trên cửa sổ Ls = 4, 6 hoặc 8 s cùng thời điểm kết thúc, rồi ghép vào 20 đặc trưng cũ. Cửa sổ quyết định vẫn là 4 s.

| Biến thể | Đích 98 %: recall · báo nhầm/giờ | Đích 99 % | ID 135 phát hiện (98 % / 99 %) | ID 127 | ID 130 |
|---|---|---|---|---|---|
| Mốc (bản 2) | 98,2 % · 1,51 | 99,5 % · 2,59 | 12/20 / 16/20 | 39/41 / 41/41 | 10/11 / 11/11 |
| + chậm, Ls = 4 s | 97,8 % · 1,29 | 99,5 % · 2,48 | 12 / 16 | 39 / 41 | 10 / 11 |
| + chậm, Ls = 6 s | 97,1 % · 0,97 | 99,2 % · 2,48 | 13 / 16 | 39 / 41 | 11 / 11 |
| + chậm, Ls = 8 s | 97,5 % · 1,08 | 99,6 % · 1,83 | **14 / 19** | 39 / 41 | 10 / 11 |

- Ls = 8 s bắt thêm 2 cú trượt dọc tường ở đích 98 %, và 3 cú ở đích 99 %, mà không tăng báo nhầm (1,83 so với 2,59/giờ ở đích 99 %, p = 0,066).
- Không thay đổi nào có ý nghĩa thống kê (mọi p ≥ 0,066). Recall chung ở đích 98 % hơi giảm (97,1–97,8 %) nhưng không có ý nghĩa (p ≥ 0,81).

**(b) Bộ phát hiện "nằm lâu" độc lập, ghép với M1 bằng OR** (`src/experiments/t6_slow.py`; `r2_longlie_or.csv`, `r2_longlie_slow_ids.csv`)

Luật, với hằng số đặt trước, không chỉnh trên dữ liệu nào. Tại mỗi thời điểm t (bước 0,5 s), báo khi cả ba điều kiện đúng:
- **nằm yên:** chuỗi nằm yên hiện tại (độ lệch chuẩn \|a\| trên 0,5 s < 0,03 g) đã kéo dài ≥ T;
- **nằm:** góc giữa gia tốc trung bình của chuỗi nằm yên và của đoạn tham chiếu [s0 − 4 s, s0 − 1 s] ≥ 45°, với s0 là lúc bắt đầu chuỗi nằm yên;
- **hạ thấp:** ΔP (trung vị chuỗi nằm yên trừ trung vị đoạn tham chiếu) > 0.

Cách chấm:
- Cảnh báo nằm lâu tính là phát hiện nếu xảy ra từ (va chạm − 1 s) trở đi.
- Báo nhầm thêm = số sự kiện mới (gộp 10 s) mà nó tạo thêm so với M1, trong bản ghi ADL/near-fall và trong bản ghi ngã trước (va chạm − 1 s).
- M1 dùng ngưỡng đích 98 % của từng fold.

| T | M1 bỏ sót | Nằm lâu bắt thêm | Recall M1 → M1 OR nằm lâu | Recall riêng bộ nằm lâu | Báo nhầm thêm | Báo nhầm/giờ M1 → OR |
|---|---|---|---|---|---|---|
| 5 s | 13 | 2 (ID 127, 130) | 98,2 % → 98,5 % | 53,6 % | +78 | 1,51 → **9,92** |
| 8 s | 13 | 2 (ID 127, 130) | 98,2 % → 98,5 % | 50,5 % | +26 | 1,51 → **4,31** |
| 10 s | 13 | 0 | 98,2 % → 98,2 % | 0 % | 0 | 1,51 → 1,51 |

- Ngã trượt dọc tường (135): bộ nằm lâu chỉ thấy 2/20, có lẽ vì người ngồi tựa tường nên tư thế đổi ít. Hai cú đó M1 đã bắt được rồi.
- T = 10 s không bao giờ báo, vì 10 s nằm yên + 4 s tham chiếu + va chạm ở khoảng giây thứ 10 đã vượt quá bản ghi.
- **Lưu ý quan trọng: bản ghi 20 s quá ngắn để đánh giá đúng ngưỡng nằm lâu 30–60 s dùng ngoài thực tế.** Số báo nhầm thêm ở đây đến từ ADL ngắn như nằm xuống giường, xoay người. Với ngưỡng 30–60 s, cả bắt thêm lẫn báo nhầm thêm sẽ khác hẳn, nên cần dữ liệu ghi dài để đánh giá.
- **Kết luận:** trên dữ liệu này, không ghép bộ nằm lâu vào M1.

### 11.7 Việc 7 (tùy chọn): so sánh công bằng với mạng nơ-ron — chưa làm

Yêu cầu là CNN 10–30k tham số, CNN-LSTM và CNN-GRU, mỗi mô hình 3 seed, chọn ngưỡng out-of-fold như LightGBM. Như vậy cần khoảng 3 mô hình × 3 seed × 14 fold × 5 lần train (4 vòng trong + 1 lần cuối) = 630 lần train.

Ở bản 1, máy này (4 nhân dùng chung, GPU dùng chung) mất khoảng 2–4 phút cho một lần train CNN 2,7k tham số. Ước tính tổng cộng khoảng 20–40 giờ. Vì vậy chưa chạy; **H4 vẫn chưa kiểm**. Nếu cần, nên chạy trên máy có GPU riêng.

### 11.8 Checklist

**Bản sửa 2:**

- [x] 1. Cắt đỉnh trên giá trị thô từng trục: 0 % cú ngã bị cắt; có hệ số và nguồn; có histogram.
- [x] 2. Đếm lại báo nhầm trong bản ghi ngã, cộng mẫu số; thêm mẫu âm từ bản ghi ngã; chạy lại A, A+B, A+G+B; có bảng trước/sau và kiểm định ghép cặp.
- [x] 3. Nested CV 120 bộ tham số; có bộ chọn theo từng fold, so với bộ cố định, đường đánh đổi số cây × số lá.
- [x] 4. H2: trục thô so với bất biến; có phép thử xoay dữ liệu test.
- [x] 5. Recall theo đỉnh |a|, theo ΔP, theo người (có S05).
- [x] 6. Đặc trưng không cần va chạm (Ls 4/6/8 s); bộ nằm lâu 5/8/10 s ghép bằng OR; có ghi chú giới hạn 20 s.
- [ ] 7. (Tùy chọn) CNN/CNN-LSTM/GRU công bằng: chưa làm, lý do ở 11.7.

**Tiêu chí của prompt gốc** (đã bỏ phần phần cứng theo yêu cầu):

- [x] `DATA_AUDIT.md`: mã Device, nhãn, đơn vị, tỉ lệ cắt đỉnh (bổ sung ở 11.1)
- [x] `LITERATURE.md`: 13 bài mục 1A + 10 bài thêm, bảng "phát hiện → quyết định"
- [x] H1–H5 trả lời trong `REPORT.md`. H2 cập nhật thành chấp nhận (11.4); H4 vẫn chưa kiểm.
- [ ] M0, M1 chạy đủ lưới; M2 và M3a–d, mỗi biến thể 3 seed. M0/M1 chỉ chạy 4 cấu hình cảm biến ở 60 Hz/4 s, cộng lưới tần số × cửa sổ cho A+B. M2 chạy 1 seed, M3 chưa chạy.
- [ ] Bảng so sánh M2 với CNN-LSTM/GRU, kèm kiểm định: chưa, vì M3 chưa chạy.
- [x] Bảng chỉ số theo sự kiện kèm khoảng tin cậy 95 % cho mọi cấu hình đã chạy
- [x] Q1–Q4 trả lời bằng số trong phần tóm tắt
- [x] `REPORT.md`, `LOG.md`, `README.md`; `run_all.py --quick` chạy được (kiểm lại sau bản sửa 2)

---

## 12. Chốt v1 (23/11/2026)

Phạm vi: chỉ phần mô hình. Không có ESP32, xuất C hay firmware, và không thêm biến thể mô hình ngoài danh sách yêu cầu. Giao thức giữ như bản sửa 2:
- LOSO theo người;
- ngưỡng chọn trên out-of-fold của người train;
- đếm cả báo nhầm trong bản ghi ngã (mẫu số 9,27 giờ);
- mọi số lấy từ CSV trong `results/tables/`.

Code: `src/experiments/v1_freeze.py`, `src/experiments/v1_noise.py`. Model và model card: `models/v1/`.

### 12.0 Tóm tắt

- **v1** = M1 LightGBM, A+B, 20 đặc trưng bất biến, 60 Hz, cửa sổ 4 s, bước 0,5 s; 150 cây × 7 lá, lr 0,1, min_child_samples 20, không class weight.
  - LOSO, đích 98 %: **97,8 % · 1,08 báo nhầm/giờ**. Đích 99 %: **99,0 % · 3,13/giờ**.
  - Không khác mốc bản 2 (300 × 15) có ý nghĩa (mọi p ≥ 0,25), mà nhỏ hơn khoảng 4 lần.
- **Nhiễu áp suất ở mọi mức yêu cầu** (nhiễu trắng ≤ 4 Pa, trôi ≤ 20 Pa/phút, xung/bậc ≤ 10 Pa):
  - v1 vẫn giữ recall 97,5–97,9 % và tối đa 1,83 báo nhầm/giờ ở đích 98 %;
  - luôn tốt hơn model A (7,44/giờ, p ≤ 0,002).
- **A+B mất lợi thế so với A** khi nhiễu trắng khoảng **16 Pa** (mức thêm, ngoài yêu cầu; khoảng 4 lần nhiễu sẵn có của barometer).
  - Trôi đến 120 Pa/phút và xung đến 40 Pa: báo nhầm vẫn thấp hơn A, recall giảm 1–2 điểm nhưng không khác A có ý nghĩa.
  - **Không mức nào làm A+B kém hơn A có ý nghĩa.**
- **Barometer 25 Hz nội suy:** không thay đổi gì. Dữ liệu nội suy không chứa thông tin mới, nên chưa trả lời được câu hỏi "tần số thật cao hơn có giúp không".
- **Barometer kẹt hoặc mất:**
  - v1 sụp: recall còn 29,5 % ở đích 98 %.
  - **Khi phát hiện barometer lỗi, thiết bị phải chuyển sang model A dự phòng** (`models/v1/fallback_A/`, ngưỡng riêng): 97,5 % · 7,44 báo nhầm/giờ.

### 12.1 Spec v1 và kết quả

(`v1_summary.csv`, `v1_paired.csv`, `v1_final_thresholds.csv`, `v1_errors_AB.csv`)

| | v1 |
|---|---|
| Cảm biến | gia tốc + áp suất (không gyro) |
| Tiền xử lý | IMU 238 → 60 Hz (`resample_poly`). Áp suất 10 Hz: trung vị 0,5 s + Butterworth 1 Hz nhân quả, nội suy lên 60 Hz |
| Cửa sổ | 4 s (240 mẫu), bước 0,5 s, quyết định ở cuối cửa sổ |
| Đặc trưng | 20 đặc trưng bất biến (16 gia tốc + 4 áp suất), thứ tự trong `models/v1/features.json` |
| Model | LightGBM 150 cây × 7 lá, lr 0,1, min_child_samples 20, không class weight, subsample 0,8, colsample 0,8 |
| Ngưỡng (model cuối) | đích 98 %: 0,6104; đích 99 %: 0,3766 |

**LOSO, v1 so với mốc bản 2.** Mỗi ô: recall [KTC 95 %] · báo nhầm/giờ [KTC 95 %] (số báo nhầm).

| Đích | v1 (150 × 7) | Mốc bản 2 (300 × 15) | p FA/h | p recall |
|---|---|---|---|---|
| 95 % | 93,3 % · 0,22/giờ (2) | 93,2 % · 0,32/giờ (3) | 0,32 | 0,95 |
| **98 %** | **97,8 % [96,4–98,9] · 1,08 [0,22–2,31] (10)** | 98,2 % [97,1–99,1] · 1,51 [0,33–3,38] (14) | 0,25 | 0,75 |
| **99 %** | **99,0 % [98,4–99,6] · 3,13 [0,71–7,12] (29)** | 99,5 % [99,0–99,9] · 2,59 [0,88–4,89] (24) | 0,72 | 0,81 |

- v1 và mốc bản 2 ngang nhau. v1 được chọn vì nhỏ hơn: 1.050 lá so với 4.500.
- Kết quả đúng như dự báo từ đường đánh đổi ở 11.3 (150 × 7: 1,08/giờ).
- Ở đích 98 %, recall thật (97,8 %) thấp hơn đích một chút. v1 bỏ sót 16 cú, mốc bỏ sót 13 cú.

**Model cuối:**
- Train trên cả 14 người, gồm 3.665 mẫu dương và 68.224 mẫu âm.
- Ngưỡng chọn trên out-of-fold GroupKFold 4 phần trên 14 người.
  - Đích 98 %: ngưỡng 0,6104 → recall out-of-fold 98,1 %, 1,51 báo nhầm/giờ.
  - Đích 99 %: ngưỡng 0,3766 → 99,3 %, 2,16/giờ.
- Model lưu dạng text LightGBM. Nạp lại cho cùng dự đoán, sai lệch 0,0.

Các file đã lưu trong `models/v1/`:
- `model.txt`, `features.json`, `preprocessing.json`, `thresholds.json`;
- `model_info.json` (tham số, phiên bản thư viện: LightGBM 4.7.0, NumPy 1.26.4, SciPy 1.17.1, Python 3.11.18);
- `MODEL_CARD.md`.

Model dự phòng A (16 đặc trưng gia tốc, cùng tham số, cùng cách chọn ngưỡng) nằm ở `models/v1/fallback_A/`.

**Lỗi v1, đích 98 % (LOSO):**
- **Bỏ sót 16/733:** trượt dọc tường (135) 7/20, ngã khỏi giường (127) 2/41, và 102, 108, 115, 121, 122, 124, 130 mỗi loại 1.
- **Báo nhầm 10:** xoay người trên giường 3, nằm xuống giường 2, cúi nhặt đồ 2, chạy nhanh 1, bắt đầu chạy 1, đứng dậy hụt 1. S05 chiếm 5/10.

### 12.2 Độ bền với nhiễu áp suất

(`v1_noise_summary.csv`, `subj_v1_noise.csv` trong `results/raw/`, `v1_baro_native_noise.csv`, `v1_baro25_paired.csv`; hình `v1_noise_fah.png`)

**Cách làm:**
- Nhiễu chỉ thêm vào **dữ liệu test**, ở **tín hiệu thô** của barometer (10 Hz, Pa), cho mọi bản ghi: ADL, near-fall và ngã.
- Sau đó chạy lại đúng chuỗi lọc (trung vị 0,5 s, Butterworth 1 Hz, nội suy 60 Hz) và tính lại 4 đặc trưng áp suất. 16 đặc trưng gia tốc giữ nguyên.
- Mỗi fold dùng model v1 và ngưỡng của chính fold đó, chọn trên dữ liệu sạch.
- Đã kiểm: chạy lại không nhiễu cho đúng từng con số của LOSO v1.

**Các loại nhiễu:**
- **(a) nhiễu trắng:** cộng vào từng mẫu thô.
- **(b) trôi tuyến tính:** dấu ngẫu nhiên theo từng bản ghi. Có thêm bản dấu cố định (+ hoặc −), xem bên dưới bảng.
- **(c) kiểu đóng cửa:**
  - 1 lần mỗi 30 s, pha ngẫu nhiên. Với bản ghi 20 s, 2/3 số bản ghi có 1 sự kiện.
  - Biên độ ±A, dấu ngẫu nhiên. Dài ngẫu nhiên đều trong 0,5–2 s.
  - 50 % là "xung": lệch A trong khoảng thời gian đó rồi trở lại.
  - 50 % là "bậc": dốc lên A trong khoảng thời gian đó rồi giữ nguyên.
- Mỗi mức chạy 5 seed nhiễu. Khoảng tin cậy: bootstrap theo người trên số đếm cộng qua 5 seed.

**Mức nhiễu sẵn có trong dữ liệu:** độ lệch chuẩn phần dư quanh trung vị trượt 1,1 s là 3,7 Pa (trung vị, ADL) và 7,3 Pa (bản ghi ngã, có chuyển động). Như vậy mức 4 Pa xấp xỉ gấp đôi phương sai nhiễu sẵn có.

Mỗi ô: recall [KTC 95 %] · báo nhầm/giờ [KTC 95 %]. Dấu * là mức thêm, ngoài danh sách yêu cầu, chỉ để tìm điểm A+B mất lợi thế so với A.

| Nhiễu | Mức | Đích 98 % | Đích 99 % |
|---|---|---|---|
| không | – | 97,8 % [96,4–98,9] · 1,08 [0,22–2,31] | 99,0 % [98,4–99,6] · 3,13 [0,71–7,12] |
| (a) trắng | 0,5 Pa | 97,8 % [96,3–99,0] · 1,08 [0,22–2,31] | 99,2 % [98,6–99,7] · 3,09 [0,69–6,92] |
| | 1 Pa | 97,8 % [96,2–98,9] · 1,14 [0,28–2,39] | 99,2 % [98,6–99,7] · 3,30 [0,78–7,44] |
| | 2 Pa | 97,7 % [95,9–98,9] · 1,21 [0,32–2,53] | 99,2 % [98,7–99,7] · 3,78 [0,87–8,58] |
| | 4 Pa | 97,9 % [96,7–99,0] · 1,83 [0,77–3,20] | 99,3 % [98,8–99,8] · 4,75 [1,58–9,66] |
| | 8 Pa* | 98,2 % [97,2–99,2] · 5,00 [2,88–7,57] | 99,4 % [98,8–99,8] · 9,82 [5,19–16,68] |
| | 16 Pa* | 98,1 % [97,1–99,0] · 6,95 [4,30–10,05] | 99,3 % [98,7–99,8] · 12,77 [7,22–20,50] |
| | 32 Pa* | 96,9 % [95,1–98,4] · 7,01 [4,58–9,95] | 98,8 % [98,2–99,3] · 12,51 [7,46–19,65] |
| (b) trôi, dấu ngẫu nhiên | 5 Pa/phút | 97,9 % [96,3–99,1] · 1,08 [0,22–2,31] | 99,3 % [98,7–99,8] · 2,98 [0,71–6,65] |
| | 10 Pa/phút | 97,8 % [96,2–99,0] · 1,06 [0,20–2,32] | 99,2 % [98,6–99,7] · 3,28 [0,82–7,33] |
| | 20 Pa/phút | 97,6 % [96,0–98,8] · 1,08 [0,24–2,22] | 99,3 % [98,7–99,8] · 3,41 [0,86–7,47] |
| | 60 Pa/phút* | 96,7 % [94,1–98,5] · 1,53 [0,58–2,96] | 98,7 % [98,3–99,2] · 3,86 [1,27–7,70] |
| | 120 Pa/phút* | 95,4 % [90,7–97,9] · 3,02 [1,59–4,64] | 97,7 % [95,8–98,9] · 5,61 [2,71–9,60] |
| (c) xung/bậc kiểu đóng cửa | ±3 Pa | 97,8 % [96,4–98,9] · 1,17 [0,33–2,37] | 99,1 % [98,6–99,6] · 3,21 [0,82–7,22] |
| | ±6 Pa | 97,5 % [95,8–98,7] · 1,27 [0,37–2,52] | 98,9 % [98,3–99,6] · 3,54 [1,12–7,53] |
| | ±10 Pa | 97,6 % [95,9–98,7] · 1,62 [0,60–3,05] | 98,9 % [98,4–99,5] · 3,93 [1,30–8,15] |
| | ±20 Pa* | 97,1 % [95,5–98,4] · 2,03 [0,93–3,60] | 98,9 % [98,2–99,4] · 4,81 [1,95–9,44] |
| | ±40 Pa* | 96,7 % [95,1–98,1] · 1,81 [0,73–3,31] | 98,7 % [98,1–99,2] · 4,68 [1,64–9,54] |
| (d) barometer 25 Hz, chỉ test | 25 Hz | 97,7 % [96,0–98,9] · 1,08 [0,22–2,29] | 99,2 % [98,6–99,7] · 3,02 [0,78–6,71] |
| (d) barometer 25 Hz, train + test | 25 Hz | 98,2 % [97,1–99,2] · 1,19 [0,23–2,44] | 99,3 % [98,8–99,8] · 2,27 [0,56–4,41] |
| **Model A (không áp suất)** | – | **97,5 % [96,4–98,6] · 7,44 [4,70–11,41]** | **99,0 % [98,4–99,6] · 16,07 [10,90–23,34]** |

- **Độ dao động giữa 5 seed nhỏ.** Ví dụ nhiễu trắng 4 Pa ở đích 98 %: báo nhầm từ 1,62 đến 1,94/giờ (cột `fah_seed_min/max`).
- **Trôi có dấu cố định** (tất định, 1 seed), đích 98 %:
  - +20 Pa/phút (giống đang hạ độ cao): 98,1 % · 1,29/giờ, tức thêm báo nhầm;
  - −20 Pa/phút: 97,1 % · 0,86/giờ, tức mất recall.
  - Trong cửa sổ 4 s, 20 Pa/phút chỉ tương đương 1,3 Pa, nên ảnh hưởng nhỏ.
- **Nhiễu trắng là loại hại nhất.** Từ 8 Pa trở lên, đặc trưng áp suất gần như mất giá trị; báo nhầm tiến tới mức của A. Tuy vậy model không tệ hơn A: các cây vẫn còn 16 đặc trưng gia tốc.
- **(d) 25 Hz:**
  - Chỉ đổi dữ liệu test: kết quả gần như y hệt 10 Hz.
  - Train lại ở 25 Hz: 98,2 % · 1,19 (đích 98 %) và 99,3 % · 2,27 (đích 99 %), không khác v1 có ý nghĩa (p FA/h 0,29 và 0,42; p recall 0,25 và 0,88).
  - Vì 25 Hz ở đây chỉ là nội suy từ 10 Hz, không chứa thông tin mới, **thí nghiệm này không trả lời được** câu hỏi barometer 25 Hz thật có giúp không. Nó chỉ cho thấy chuỗi lọc không nhạy với tần số đầu vào. Cần dữ liệu 25 Hz thật từ AN GIA MINI.

**Mức nào thì A+B bắt đầu kém hơn A?** Cùng đích recall, A+B được so với A bằng Wilcoxon ghép cặp theo người.

| Nhiễu | A+B mất lợi thế về báo nhầm (không còn thấp hơn A có ý nghĩa) | A+B kém hơn A (báo nhầm cao hơn, hoặc recall thấp hơn với p < 0,05) |
|---|---|---|
| Trắng | **16 Pa** ở đích 98 % (6,95 so với 7,44/giờ, p = 0,76). Ở đích 99 %, A+B vẫn tốt hơn đến 32 Pa (12,5 so với 16,1/giờ, p = 0,023). | Không ở mức nào đến 32 Pa. Ở 32 Pa, recall 96,9 % so với 97,5 %, p = 0,52. |
| Trôi | Không ở mức nào đến 120 Pa/phút (3,02 so với 7,44/giờ, p < 0,001) | Không. Từ 60 Pa/phút, recall thấp hơn A về số điểm (96,7 % và 95,4 % so với 97,5 %), nhưng không có ý nghĩa (p = 0,82 và 0,38). |
| Xung/bậc | Không ở mức nào đến ±40 Pa (1,81 so với 7,44/giờ, p < 0,001) | Không. Từ ±20 Pa, recall thấp hơn A về số điểm (97,1 % và 96,7 %), nhưng p = 0,16 và 0,11. |

**Kết luận:**
- Ở mọi mức yêu cầu, A+B vẫn tốt hơn A rất xa về báo nhầm (ít hơn 4–7 lần ở đích 98 %, 3–5 lần ở đích 99 %) với recall như nhau.
- A+B chỉ mất lợi thế khi nhiễu trắng khoảng 16 Pa, gấp khoảng 4 lần nhiễu sẵn có của barometer trong FallAllD.
- Với trôi lớn (≥ 60 Pa/phút) và xung lớn (≥ ±20 Pa), điểm cần theo dõi là **recall**, không phải báo nhầm.
- Trên dữ liệu AN GIA MINI, cần đo nhiễu barometer thật và so với các mức này.

### 12.3 Chế độ dự phòng khi mất barometer

(`v1_noise_summary.csv`: dòng `const`, `nan`, `model_A`)

- **Hằng số:** áp suất thô giữ bằng mẫu đầu tiên suốt bản ghi, giống barometer bị kẹt.
- **NaN:** 4 đặc trưng áp suất là NaN, giống barometer không trả dữ liệu.
- Hai trường hợp cho **kết quả giống hệt nhau**. Lúc train không có giá trị thiếu, nên LightGBM xử lý NaN giống 0, mà 0 chính là giá trị các đặc trưng áp suất khi áp suất hằng số.

| Chế độ | Đích 98 % | Đích 99 % |
|---|---|---|
| v1 A+B, barometer bình thường | 97,8 % [96,4–98,9] · 1,08/giờ | 99,0 % [98,4–99,6] · 3,13/giờ |
| (ii) v1 A+B, áp suất hằng số | **29,5 %** [20,4–39,1] · 0,00/giờ (bỏ sót 517/733) | **52,1 %** [43,9–59,7] · 0,54/giờ |
| (ii) v1 A+B, áp suất NaN | 29,5 % · 0,00/giờ | 52,1 % · 0,54/giờ |
| **(i) Model A dự phòng** (`models/v1/fallback_A/`) | **97,5 % [96,4–98,6] · 7,44/giờ** [4,70–11,41] | **99,0 % [98,4–99,6] · 16,07/giờ** [10,90–23,34] |

- Không có áp suất, v1 thấy "không hạ độ cao" nên gần như không báo gì: recall 29,5 %, thấp hơn A có ý nghĩa (p < 0,001).
- **Khuyến nghị:**
  - Khi phát hiện barometer lỗi, thiết bị **chuyển sang model A dự phòng với ngưỡng riêng của nó.** Ngưỡng model cuối: 0,1390 (đích 98 %) và 0,0759 (đích 99 %).
  - Chấp nhận báo nhầm cao hơn khoảng 7 lần (7,4 so với 1,1/giờ ở đích 98 %), để giữ recall.
  - Không chạy v1 với áp suất hỏng.
- **Phát hiện barometer lỗi (gợi ý, chưa kiểm trên phần cứng):**
  - Giá trị NaN hoặc nằm ngoài dải vật lý → lỗi.
  - Độ lệch chuẩn của áp suất thô trên 2 s gần 0 → bị kẹt. Trong FallAllD, mọi bản ghi (2.292) có độ lệch chuẩn 2 s thô ≥ 1,24 Pa (`v1_baro_native_noise.csv`). Vì vậy một ngưỡng kẹt cỡ 0,1 Pa sẽ không báo nhầm trên dữ liệu này.
  - Ngưỡng thật phải đặt theo nhiễu của barometer trên AN GIA MINI.
- Nhiễu áp suất ở mức vừa phải (mục 12.2) **không** cần chuyển sang A.

### 12.4 Biến thể ứng viên để thử lại trên dữ liệu AN GIA (không áp dụng bây giờ)

| Biến thể | Bằng chứng trên FallAllD | Vì sao chờ dữ liệu AN GIA |
|---|---|---|
| Thêm đặc trưng ngã chậm, cửa sổ Ls = 8 s (11.6a) | Bắt thêm 2–3/20 cú trượt dọc tường, không tăng báo nhầm, nhưng không có ý nghĩa thống kê (p ≥ 0,066) | Chỉ 20 cú ngã ID 135; cần thêm nhiều ngã chậm, khuỵu từ từ |
| Bộ phát hiện nằm lâu 30–60 s, ghép OR (11.6b) | Ở 5–8 s chỉ bắt thêm 2/13 cú, báo nhầm lên 4,3–9,9/giờ | Bản ghi 20 s không đánh giá được ngưỡng 30–60 s; cần bản ghi dài và ADL liên tục |
| CNN / CNN-LSTM / CNN-GRU, so công bằng (11.7, H4) | CNN 2,7k tham số kém hơn LightGBM (bản 1); bản công bằng chưa chạy | Khoảng 630 lần train; nên chạy trên máy có GPU riêng, với dữ liệu AN GIA |

### 12.5 Checklist chốt v1

- [x] 1. v1 cố định (150 × 7, lr 0,1, min_child 20, không class weight). LOSO ở đích 98/99 % so với mốc 300 × 15. Model cuối trên 14 người, ngưỡng out-of-fold. Đã lưu model, đặc trưng, tiền xử lý, ngưỡng, phiên bản thư viện và `MODEL_CARD.md` vào `models/v1/`.
- [x] 2. Nhiễu áp suất chỉ trên dữ liệu test: trắng 0,5/1/2/4 Pa, trôi 5/10/20 Pa/phút, xung/bậc ±3/6/10 Pa, 25 Hz. 5 seed, có khoảng tin cậy và hình. Có nêu mức mà A+B mất lợi thế so với A; phải thêm vài mức ngoài yêu cầu (đánh dấu *) mới tìm được.
- [x] 3. Dự phòng: model A so với v1 có áp suất hằng số / NaN; khuyến nghị chuyển sang A.
- [x] 4. Mục 12 trong REPORT.md (không sửa mục cũ); cập nhật LOG.md.
