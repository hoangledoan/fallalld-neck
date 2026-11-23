# DATA_AUDIT – FallAllD, thiết bị đeo cổ (D1)

Mọi số trong file này do `python -m src.data.audit` sinh ra, nằm trong `results/tables/audit_*.csv`.
Hình: `results/figures/audit_examples.png`, `results/figures/audit_peak_hist.png`.

## 1. Nguồn và cách xác minh

| Mục | Nguồn | Đã đọc bản gốc? |
|---|---|---|
| Tên file, mã Device | `FallAllD_to_PYTHON_Structure.py` (đi kèm dữ liệu) và `FallAllD_to_MATLAB_Structure.m` (IEEE DataPort) | Có |
| Bảng ActivityID → mô tả | "simulated falls and ADLs- list.pdf" và `ActivityID2Str.m` trên IEEE DataPort (Majd Saleh, 04/2020) | Có. Zip cục bộ **không có** PDF và video; bản tải về nằm ở `configs/activities.csv` |
| Đơn vị, hệ số đổi | `Plot_FallAllD_Record.m` (IEEE DataPort), datasheet LSM9DS1 DocID025715 Rev 2 | Có |
| Bài báo FallAllD (IEEE Sensors J. 2021) | IEEE Xplore, closed access | **Chỉ đọc abstract** |
| Cách đeo logger cổ (dây, độ dài, trong/ngoài áo) | không tìm được trong nguồn mở; video cần đăng nhập | **Chưa xác minh** |

## 2. Các giả thuyết trong prompt: kết quả xác minh

| Giả thuyết | Kết quả | Bằng chứng |
|---|---|---|
| Device 1 = cổ, 2 = cổ tay, 3 = eo | **Đúng** | script gốc: ký tự thứ 6 của tên file; `D1` → `'Neck'` |
| ActivityID ≥ 101 là ngã, < 101 là ADL | **Đúng** | PDF: ADL 1–44, ngã 101–135 |
| Có nhóm near-fall riêng | **Không có** | Không ID nào được gắn near-fall. Quy ước ở đây: ID 15 ("cố đứng dậy khỏi ghế nhưng không được, sau khi đã đứng lên một nửa") và ID 23 ("vấp khi đi nhưng không ngã") gắn nhãn `NEAR_FALL`, tính là âm (ADL) khi train và chấm điểm, nhưng báo cáo riêng |
| Mỗi bản ghi ~20 s | **Đúng, chính xác 20,0 s** | 2.292/2.292 bản ghi: 4.760 mẫu IMU (238 Hz), 1.600 mẫu từ kế (80 Hz), 200 mẫu áp suất (10 Hz) — `audit_lengths.csv` |
| Gia tốc 0,244 mg/LSB (±8 g), gyro 70 mdps/LSB (±2000 dps) | **Đúng** | datasheet LSM9DS1; số liệu: \|a\| khi đứng yên trung vị 0,979 g (phân vị 1–99 %: 0,826–1,091 g) |
| Cột barometer | **Cột 1 = áp suất [hPa], cột 2 = nhiệt độ [°C]** | nhãn trục trong `Plot_FallAllD_Record.m`; số liệu: trung vị 1012,3 hPa, nhiệt độ 16,8–37,2 °C |

Hai điểm không khớp giữa hai nguồn chính thức (không ảnh hưởng nhãn ngã/không ngã):
- ID 111: PDF ghi "ngã ra sau", `ActivityID2Str.m` ghi "ngã về trước". Trong PDF, dòng 111 và 112 giống hệt nhau, nên có lẽ PDF sai (suy luận, chưa xác nhận).
- ID 124: `.m` ghi "rev.", PDF ghi "with recovery".

## 3. Kiểm kê

### 3.1 Người tham gia và số bản ghi (`audit_counts_subject_label.csv`)

- **14 người có dữ liệu cổ** (S01–S15, **thiếu S06**). 2.292 bản ghi: 1.485 ADL, 74 NEAR_FALL, 733 FALL.
- **S04 và S10 không có bản ghi ngã nào** ở thiết bị cổ. Hệ quả cho LOSO: độ nhạy chỉ tính được trên 12 người; báo nhầm/giờ tính trên cả 14 người.
- Thiết bị cổ **không có ADL 1–12** (vỗ tay, vẫy tay, bắt tay…: các ADL riêng cho cổ tay). ADL của cổ là ID 13–44.
- ADL 41–42 (đứng/ngồi trên xe buýt/metro) chỉ có ở 3 người.
- Tổng thời lượng âm (ADL + NEAR_FALL): 1.559 × 20 s ≈ **8,7 giờ**. Đây là con số mẫu số cho "báo nhầm/giờ", và là ADL dày đặc động tác, không phải một ngày sống thật.

| Người | ADL | NEAR_FALL | FALL |
|---|---|---|---|
| S01 | 96 | 4 | 79 |
| S02 | 127 | 6 | 56 |
| S03 | 111 | 3 | 61 |
| S04 | 108 | 5 | **0** |
| S05 | 111 | 6 | 59 |
| S07 | 111 | 6 | 66 |
| S08 | 108 | 6 | 62 |
| S09 | 107 | 6 | 44 |
| S10 | 88 | 6 | **0** |
| S11 | 111 | 6 | 47 |
| S12 | 111 | 6 | 65 |
| S13 | 107 | 5 | 66 |
| S14 | 111 | 6 | 65 |
| S15 | 78 | 3 | 63 |

Số bản ghi theo từng ActivityID × người: `audit_counts_activity_subject.csv`; theo ActivityID kèm mô tả: `audit_activity.csv`.

### 3.2 Kênh thiếu, mẫu mất, tần số thực tế

- Không bản ghi nào thiếu kênh; không có NaN trong áp suất.
- Không có cột timestamp → **không đo được tần số thực tế**. Chỉ kiểm được rằng số mẫu khớp đúng 238 / 80 / 10 Hz × 20 s ở mọi bản ghi.
- Mẫu gia tốc lặp y hệt mẫu trước (dấu hiệu giữ mẫu/mất mẫu): trung vị 0,02 % (ADL) và 0,04 % (ngã), tối đa 0,57 % → không đáng kể.

### 3.3 Vị trí sự kiện trong bản ghi (quan trọng cho đánh giá)

- Đỉnh |a| của bản ghi ngã nằm trong **10 ± 0,5 s ở 91 %** bản ghi; 41 % mọi bản ghi có đỉnh đúng ở mẫu 2.380 ± 5.
- Với ADL, 45 % bản ghi cũng có đỉnh trong 10 ± 0,5 s.
- Kết luận: logger lưu một đoạn 20 s quanh một mốc (có lẽ là lúc người thực hiện động tác). Hệ quả:
  - Đánh giá theo sự kiện vẫn trượt liên tục trên cả 20 s, như prompt yêu cầu.
  - Không được dùng vị trí trong bản ghi làm đặc trưng. Cửa sổ train cho ngã đặt đỉnh ở vị trí cố định trong cửa sổ, không phải ở vị trí cố định trong bản ghi.

### 3.4 "Ngã có phục hồi" (with recovery) nghĩa là gì (`audit_recovery.csv`)

PDF không định nghĩa. Kiểm bằng dữ liệu: góc giữa vector trọng lực 2 s đầu và 2 s cuối bản ghi.

| recovery | số bản ghi | góc thay đổi (trung vị) | tỉ lệ < 30° | độ lệch chuẩn \|a\| 2 s cuối |
|---|---|---|---|---|
| no | 493 | 85,0° | 7,7 % | 0,003 g (nằm yên) |
| yes | 240 | 17,3° | 65,4 % | 0,146 g (đang cử động) |

→ "with recovery" = **ngã thật (có va chạm), rồi tự đứng dậy** trong 20 s. Vẫn là FALL. Nhưng đặc trưng "nằm yên sau ngã" và "tư thế thay đổi" sẽ yếu ở 12 loại ngã này (102, 104, 106, 108, 110, 116, 118, 120, 122, 124, 126, 128) → báo cáo độ nhạy riêng cho nhóm này ở Q4.

### 3.5 Dải đo và cắt đỉnh (`audit_summary_label.csv`, `audit_recordings.csv`)

| | ADL | NEAR_FALL | FALL |
|---|---|---|---|
| Bản ghi có \|a_trục\| ≥ 7,9 g | 0 % | 0 % | **0 %** |
| Bản ghi có \|a_trục\| ≥ 7,5 g | 0,9 % | – | 1,1 % |
| Bản ghi có \|a_trục\| ≥ 6,0 g | 3,3 % | – | 13,8 % |
| Đỉnh \|a\| (trung vị) | 1,66 g | 3,92 g | 4,43 g |
| Bản ghi có \|ω_trục\| ≥ 1.990 dps | 1 | 0 | 5 |

- Giá trị thô lớn nhất của gia tốc: −32.285 / +31.827 LSB (≈ 7,88 g). Không có "bậc phẳng" ở một giá trị nào (mỗi giá trị ≥ 31.500 chỉ xuất hiện 1 lần) → **ở vị trí cổ, gia tốc gần như không bao giờ chạm ±8 g** trong FallAllD. Chỉ 66 mẫu trong toàn bộ dữ liệu cổ có \|a_trục\| ≥ 7,3 g.
- Gyro chạm ±2.000 dps (−32.768 LSB) ở 6 bản ghi.
- Hệ quả: dữ liệu cổ gần như không bị cắt đỉnh, nên không cần xử lý cắt đỉnh khi tiền xử lý.
- Tách bằng ngưỡng đơn: 22,2 % ADL có đỉnh \|a\| > 2,5 g; 3,4 % ngã có đỉnh < 2,5 g. Các ADL có đỉnh cao nhất: nhảy mạnh (27, trung vị 5,7 g), chạy nhanh (25, 5,6 g), dừng/bắt đầu chạy (43/44, 4,4–4,7 g), chạy chậm (24, 4,4 g), "vấp không ngã" (23, 4,2 g), "đứng dậy hụt" (15, 3,9 g).

### 3.6 Barometer (`audit_delta_p.csv`, `audit_summary_label.csv`)

- Áp suất tuyệt đối 990,7–1029,7 hPa, nằm trong khoảng 950–1050 hPa.
- **Nhiễu lớn:** độ lệch chuẩn của hiệu hai mẫu liên tiếp (0,1 s) có trung vị 5,9 Pa; 31 % bản ghi có bước nhảy > 30 Pa giữa hai mẫu, nhiều nhất ngay quanh va chạm (xung áp do va đập/dòng khí). → Lọc bằng trung vị trước, rồi mới lọc thông thấp (ghi trong `LOG.md`).
- ΔP theo định nghĩa của prompt (trung vị P 1–3 s sau đỉnh \|a\| trừ trung vị P 1–3 s trước đỉnh):

| nhóm | n | trung vị ΔP | phân vị 10 % | phân vị 90 % |
|---|---|---|---|---|
| FALL (mọi loại) | 724 | **+11,3 Pa** | +5,7 | +14,9 |
| ngã từ giường | 68 | +5,5 Pa | +2,7 | +9,2 |
| ngã từ ghế | 46 | +8,7 Pa | +6,7 | +11,7 |
| ngã khi đang đứng yên | 68 | +12,2 Pa | +9,2 | +15,6 |
| ADL | 1.312 | +0,1 Pa | −7,7 | +7,3 |
| NEAR_FALL | 74 | +0,3 Pa | −2,9 | +3,2 |

  (9 bản ghi ngã và 173 bản ghi ADL có đỉnh quá gần mép bản ghi nên không tính được ΔP.)
- +11 Pa ứng với hạ khoảng 0,9 m, khớp với ước tính "ngực hạ ~1 m → +10–12 Pa" trong prompt. **90,6 % ngã có ΔP > 5 Pa, so với 16,4 % ADL.** → Kênh B có tín hiệu rõ ở vị trí cổ; đây là bằng chứng sơ bộ ủng hộ H1, cần kiểm bằng mô hình.
- ADL gây ΔP > 5 Pa nhiều nhất: đi xuống cầu thang nhanh (36: 80 % bản ghi), dừng xuống cầu thang (34: 70 %), nằm xuống giường (16: 63 %), xuống cầu thang (33: 63 %). Thang máy (37–40) có biên độ áp suất lớn nhất (trung vị ~110–120 Pa trong 20 s) nhưng thay đổi chậm và đều, khác hình dạng bậc thang nhanh của ngã (hình `audit_examples.png`, ô cuối).

### 3.7 Hình ví dụ

`results/figures/audit_examples.png`: 3 ngã (chọn theo phân vị 25/50/75 % của đỉnh \|a\|) và 3 ADL dễ nhầm, chọn bằng dữ liệu: 2 hoạt động có đỉnh \|a\| trung vị cao nhất (chạy nhanh, nhảy mạnh) và 1 hoạt động có biên độ áp suất lớn nhất (thang máy). Mỗi ô có \|a\|, \|ω\|, áp suất tương đối thô và sau lọc trung vị 1,1 s.

## 4. Hệ quả cho các bước sau

1. LOSO trên 14 người; độ nhạy và khoảng tin cậy chỉ từ 12 người có ngã. S04, S10 chỉ góp phần báo nhầm.
2. Nhãn: FALL = 101–135 (kể cả ngã có phục hồi); ADL = 13–44 trừ 15 và 23; NEAR_FALL = 15, 23, tính là âm nhưng báo cáo riêng.
3. Kênh B: dùng trung vị để chống xung, ΔP là đặc trưng chính. Ngã từ giường có ΔP nhỏ nhất (~5 Pa) → dễ bị bỏ sót nếu M0 đặt ngưỡng ΔP cao.
4. Đánh giá theo sự kiện: vì đỉnh luôn ở ~10 s, cửa sổ [−1 s, +5 s] quanh đỉnh va chạm được xác định từ đỉnh \|a\| trong khoảng 8–12 s của bản ghi ngã.
