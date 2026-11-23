# Model card: phát hiện ngã đeo cổ, v1

Ngày chốt: 23/11/2026. Mọi số trong file này lấy từ CSV trong `results/tables/` (tên file ghi cạnh từng số).
Chi tiết đầy đủ ở `REPORT.md`, mục 12.

## 1. Model

| | |
|---|---|
| Loại | LightGBM (`LGBMClassifier`), phân loại nhị phân: cửa sổ có chứa cú ngã hay không |
| Tham số | 150 cây × 7 lá, learning rate 0,1, min_child_samples 20, không class weight; subsample 0,8 (mỗi vòng), colsample_bytree 0,8, random_state 20261123 |
| Tham số có tinh chỉnh không | Không. Chốt cố định, dựa trên nested CV ở bản sửa 2 (mục 11.3: lr 0,1 được chọn ở 14/14 fold, 7 lá ở 11/14) |
| Cảm biến | Gia tốc + áp suất (A+B). Không dùng gyro. |
| Đặc trưng | 20 đặc trưng bất biến hướng đeo: 16 của gia tốc, 4 của áp suất. Danh sách và thứ tự ở `features.json` |
| Cửa sổ | 4 s ở 60 Hz (240 mẫu), trượt bước 0,5 s. Thời điểm quyết định là cuối cửa sổ. |
| Đầu ra | Xác suất; báo ngã khi xác suất ≥ ngưỡng |

**File trong thư mục này:**

- `model.txt`: model LightGBM, định dạng text (`lgb.Booster(model_file=...)`). Đã kiểm: dự đoán của file nạp lại khớp với model trong bộ nhớ, sai lệch 0,0.
- `features.json`: 20 đặc trưng theo đúng thứ tự đầu vào, kèm vị trí cột trong `src/features/feats.py:features()`.
- `preprocessing.json`: đơn vị, resample, chuỗi lọc áp suất, cửa sổ.
- `thresholds.json`: hai ngưỡng (đích recall 98 % và 99 %).
- `model_info.json`: tham số, số mẫu train, phiên bản thư viện.
- `fallback_A/`: model dự phòng chỉ dùng gia tốc (16 đặc trưng), cùng tham số, cùng cách chọn ngưỡng. Dùng khi barometer lỗi (mục 5).

**Phiên bản thư viện:** Python 3.11.18, LightGBM 4.7.0, NumPy 1.26.4, SciPy 1.17.1, pandas 3.0.6, scikit-learn 1.9.1.

## 2. Tiền xử lý (phải làm giống hệt khi dùng)

1. **Đổi đơn vị:**
   - gia tốc: 0,244 mg/LSB (±8 g);
   - gyro: 70 mdps/LSB (không dùng trong v1);
   - áp suất: hPa × 100 → Pa.
2. **IMU 238 Hz → 60 Hz:** `scipy.signal.resample_poly`, có lọc chống aliasing.
3. **Áp suất 10 Hz:**
   - trung vị trượt 5 mẫu về quá khứ (0,5 s);
   - Butterworth bậc 2, 1 Hz, nhân quả, trạng thái đầu bằng giá trị đầu tiên;
   - nội suy tuyến tính lên lưới 60 Hz của IMU.
4. **Cửa sổ:** 240 mẫu × 7 kênh [ax ay az gx gy gz p]. Tính đặc trưng bằng `features()`, rồi lấy 20 cột theo `features.json`.

Code tham chiếu: `src/data/preprocess.py`, `src/features/feats.py`.

```python
import json, lightgbm as lgb
from src.features.feats import features
b = lgb.Booster(model_file="models/v1/model.txt")
cols = [f["source_column_in_feats_features"] for f in json.load(open("models/v1/features.json"))["features"]]
thr = json.load(open("models/v1/thresholds.json"))["recall98"]["threshold"]
F, _, _ = features(win, 60)            # win: (N, 240, 7), đã tiền xử lý như trên
alert = b.predict(F[:, cols]) >= thr
```

## 3. Dữ liệu train

- **Nguồn:** FallAllD, thiết bị đeo cổ (D1). 14 người (thiếu S06), 2.292 bản ghi, mỗi bản đúng 20 s.
  - 733 ngã (ActivityID 101–135, kể cả ngã rồi tự đứng dậy);
  - 1.485 ADL;
  - 74 near-fall (ID 15, 23), tính là mẫu âm.
- S04 và S10 không có cú ngã nào.
- **Mẫu dương:** cửa sổ đặt va chạm ở 1/3 cửa sổ, lệch thêm ±0,5 s (5 bản mỗi cú ngã). Tổng 3.665 mẫu.
- **Mẫu âm:** 68.224, gồm:
  - mọi cửa sổ trượt của bản ghi ADL và near-fall;
  - cửa sổ của bản ghi ngã cách va chạm hơn 0,5 s.
- Ngã là **ngã mô phỏng của người trẻ** (21–53 tuổi), ADL theo kịch bản.

## 4. Giao thức đánh giá và kết quả

**Giao thức (bản sửa 2):**
- Để riêng từng người ra kiểm tra (LOSO, 14 fold).
- Ngưỡng chọn trên dự đoán out-of-fold (GroupKFold 4 phần theo người) của chính các người train.
- **Chấm theo sự kiện:**
  - cảnh báo cách nhau dưới 10 s gộp thành một sự kiện;
  - ngã được tính là phát hiện nếu có cảnh báo trong [−1 s, +5 s] quanh va chạm;
  - mọi sự kiện khác là báo nhầm, kể cả sự kiện trong bản ghi ngã.
- Mẫu số báo nhầm/giờ: 9,27 giờ.
- Khoảng tin cậy 95 %: bootstrap theo người.

**Kết quả LOSO** (`v1_summary.csv`, `v1_paired.csv`). Mỗi ô: recall · báo nhầm/giờ (số báo nhầm).

| Đích recall | v1 (150 × 7) | Mốc bản 2 (300 × 15) | p (báo nhầm/giờ) | p (recall) |
|---|---|---|---|---|
| 98 % | **97,8 %** [96,4–98,9] · **1,08/giờ** [0,22–2,31] (10) | 98,2 % · 1,51/giờ (14) | 0,25 | 0,75 |
| 99 % | **99,0 %** [98,4–99,6] · **3,13/giờ** [0,71–7,12] (29) | 99,5 % · 2,59/giờ (24) | 0,72 | 0,81 |

Hai model không khác nhau có ý nghĩa. v1 nhỏ hơn khoảng 4 lần (1.050 lá so với 4.500).

**Model cuối** train trên cả 14 người. Ngưỡng chọn trên out-of-fold của GroupKFold 4 phần trên 14 người (`v1_final_thresholds.csv`):

| | Ngưỡng | Recall out-of-fold | Báo nhầm/giờ out-of-fold |
|---|---|---|---|
| Đích 98 % | 0,6104 | 98,1 % | 1,51 |
| Đích 99 % | 0,3766 | 99,3 % | 2,16 |

Số out-of-fold là của model train trên 3/4 số người, chỉ để tham khảo. Số ước lượng chính là bảng LOSO ở trên.

**Lỗi ở đích 98 %, LOSO** (`v1_errors_AB.csv`):
- **Bỏ sót 16/733 cú ngã:**
  - 135 (ngất, trượt dọc tường): 7/20;
  - 127 (ngã khỏi giường): 2/41;
  - 102, 108, 115, 121, 122, 124, 130: mỗi loại 1.
- **Báo nhầm 10 lần:**
  - xoay người trên giường 3;
  - nằm xuống giường 2;
  - cúi nhặt đồ 2;
  - chạy nhanh 1, bắt đầu chạy 1;
  - đứng dậy hụt (near-fall) 1.
- Riêng S05 chiếm 5/10 lần báo nhầm.

## 5. Độ bền và chế độ dự phòng

Chi tiết ở `REPORT.md` mục 12.2–12.3, số trong `v1_noise_summary.csv`. Nhiễu chỉ thêm vào dữ liệu test; train và ngưỡng giữ nguyên.

**Nhiễu áp suất ở các mức yêu cầu**, đích 98 %:
- nhiễu trắng ≤ 4 Pa, trôi ≤ 20 Pa/phút, xung/bậc ≤ 10 Pa;
- báo nhầm tăng từ 1,08 lên tối đa 1,83/giờ;
- recall nằm trong 97,5–97,9 %;
- luôn tốt hơn model A (7,44/giờ; p ≤ 0,002).

**A+B mất lợi thế so với A** khi nhiễu trắng khoảng 16 Pa (mức thêm, ngoài yêu cầu), tức khoảng 4 lần nhiễu sẵn có của barometer. Ở mọi mức đã thử, A+B không kém hơn A có ý nghĩa.

**Barometer kẹt (hằng số) hoặc mất (NaN):**
- v1 chỉ còn recall 29,5 % ở đích 98 %, và 52,1 % ở đích 99 %. **Không được dùng v1 khi barometer lỗi.**
- Chuyển sang `fallback_A/` với ngưỡng riêng của nó:
  - đích 98 %: ngưỡng 0,1390 → LOSO 97,5 % · 7,44 báo nhầm/giờ;
  - đích 99 %: ngưỡng 0,0759 → 99,0 % · 16,1 báo nhầm/giờ.

## 6. Giới hạn đã biết

- **Ngã mô phỏng, người trẻ, ADL kịch bản dày đặc.**
  - Báo nhầm/giờ ở đây không quy đổi được sang báo nhầm/ngày ngoài đời.
  - Recall là cận trên; ngã thật của người cao tuổi chậm hơn và ít va chạm hơn.
- **Ngã chậm** (trượt dọc tường, khuỵu từ từ) và **ngã khỏi giường** là điểm yếu chính.
- **Bản ghi chỉ 20 s:**
  - chưa đánh giá được bộ phát hiện nằm lâu 30–60 s;
  - chưa đánh giá được báo nhầm trên chuỗi ghi liên tục.
- **14 người** (12 có ngã), nên khoảng tin cậy rộng. Báo nhầm ở đích 98 % chỉ dựa trên 10 sự kiện.
- **Dữ liệu từ logger FallAllD** (LSM9DS1 và barometer 10 Hz), không phải phần cứng AN GIA MINI.
  - Cách đeo, mặt dây, cảm biến và mức nhiễu barometer sẽ khác.
  - Phải đánh giá lại và chọn lại ngưỡng trên dữ liệu AN GIA trước khi dùng thật.
- Model phụ thuộc nhiều vào áp suất. Những người có ΔP khi ngã nhỏ (như S05) dễ bị bỏ sót hơn khi ngưỡng cao.
