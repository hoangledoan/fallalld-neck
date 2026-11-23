# LOG – quyết định và giả định (theo thứ tự thời gian)

## 2026-11-23

- **Đường dẫn dữ liệu.** Prompt để trống `<ĐIỀN_ĐƯỜNG_DẪN_FALLALLD>`. Dùng file `../FallAllD__zip.zip` (cùng thư mục với prompt, 26.420 file). Zip là bản gốc, chỉ đọc. Chỉ giải nén các file thiết bị D1 (cổ) vào `cache/FallAllD/` (9.168 file = 2.292 bản ghi × 4 file A/G/M/B).
- **Không có PDF danh sách hoạt động và video** trong zip. Bảng ActivityID → mô tả lấy từ nguồn web (xem `DATA_AUDIT.md` mục nguồn); ghi rõ nguồn.
- **Mã Device** xác minh từ script gốc `FallAllD_to_PYTHON_Structure.py`: ký tự thứ 6 của tên file, 1 = Neck, 2 = Wrist, 3 = Waist.
- **Môi trường.** Tạo conda env mới `fallalld` (Python 3.11, TensorFlow 2.15.1 để có Keras 2 + tfmot cho QAT, LightGBM, scikit-learn). Bước kiểm kê chạy bằng env `viocr_bench` có sẵn (pandas/numpy/matplotlib) trong lúc env mới đang cài.
- **Máy:** 4 nhân CPU, 15 GB RAM, RTX A2000 12 GB nhưng đang có tiến trình khác dùng ~8 GB. Ngân sách tính toán hạn chế → ước tính thời gian trước khi chạy lưới M2/M3.
- **Kiểm kê sơ bộ:** mọi bản ghi dài đúng 20 s (4.760 mẫu IMU, 1.600 mẫu từ kế, 200 mẫu áp suất). Đỉnh |a| của bản ghi ngã nằm trong 10 ± 0,5 s ở 91 % bản ghi → logger lưu đoạn 20 s quanh một mốc kích hoạt. Hệ quả: đánh giá theo sự kiện trượt trên bản ghi 20 s; cửa sổ ADL cũng thường có đỉnh ở giữa (45 %), nên ADL không phải đoạn "ngẫu nhiên" mà là đoạn quanh động tác mạnh nhất.
- **Barometer có nhiễu xung lớn** (31 % bản ghi có bước nhảy > 30 Pa giữa hai mẫu 0,1 s, nhiều nhất ở quanh va chạm). Quyết định cho 5.1: dùng trung vị (không dùng trung bình) trước khi lọc thông thấp, và ΔP tính bằng trung vị đoạn 1–3 s như prompt.
- **Bảng hoạt động.** Lấy từ PDF và `ActivityID2Str.m` chính thức trên IEEE DataPort → `configs/activities.csv`. Không có nhóm near-fall riêng. Quy ước: ID 15 và 23 = `NEAR_FALL` (tính là âm, báo cáo riêng).
- **"With recovery"** = ngã thật rồi tự đứng dậy (kiểm bằng dữ liệu: tư thế cuối gần tư thế đầu, trung vị 17° so với 85°). Giữ nhãn FALL, báo cáo riêng.
- **Dải đo:** không mẫu gia tốc nào ở cổ chạm ±8 g (max 7,88 g, không có bậc phẳng). Phép thử ±8/±16 g ở 5.3 vẫn chạy nhưng dự kiến không khác biệt.
- **Mốc va chạm cho đánh giá theo sự kiện:** đỉnh |a| (tần số gốc) trong khoảng 8–12 s của bản ghi ngã (91 % bản ghi ngã có đỉnh trong 10 ± 0,5 s).
- **ΔP ở cổ:** ngã +11,3 Pa (trung vị), ADL +0,1 Pa → kênh B có tín hiệu. Ngã từ giường chỉ +5,5 Pa.
- **Điểm dừng 5.0:** người dùng đang theo dõi (phiên VS Code) → dừng sau kiểm kê và đọc tài liệu, chờ xác nhận trước khi sang 5.1.

## 2026-11-23 (tiếp) — người dùng: "go, do everything"

- Người dùng chấp nhận kết quả kiểm kê và các quy ước nhãn (NEAR_FALL = 15, 23; ngã có phục hồi = FALL). Chạy tiếp toàn bộ 5.1–5.6, tự quyết định trong phạm vi prompt, ghi lý do vào đây.
- **Đổi phạm vi (người dùng):** "chỉ cần build con TinyML trước để coi với data này nó có hoạt động không". → Bỏ cài ESP-IDF và phần firmware (đã xóa bản tải dở). Làm bản gọn trước: 60 Hz, cửa sổ 4 s, M1 (LightGBM) + M2 (CNN nhỏ), LOSO, chỉ số theo sự kiện, int8 TFLite kiểm trên Python. Lưới đầy đủ M0–M3 để sau nếu người dùng muốn.
- **Gỡ phần cứng (người dùng):** "xoá hết prompt hay code liên quan đến phần cứng". Đã sửa prompt (bản gốc lưu ở `cache/PROMPT_original_backup.md`): bỏ ESP32-S3/LSM6DSV16X/BMP390/MLC, mục 5.4 (TFLite/int8/firmware), phép thử dải đo ±8/±16 g, tiêu chí firmware/int8. Code: bỏ mô phỏng lượng tử hóa LSM6DSV16X trong tiền xử lý (dữ liệu giữ nguyên đơn vị vật lý từ LSM9DS1), xóa thư mục `firmware/` và `src/export/` (đang trống). Tài liệu: bỏ dòng LSM6DSV16X và khuyến nghị dải đo trong `DATA_AUDIT.md`, bỏ ghi chú MLC trong `LITERATURE.md`. Các mục trên trong LOG phía trên giữ nguyên vì là lịch sử.
- Tần số 60 Hz giữ lại như một lựa chọn mô hình (ít mẫu hơn → mô hình nhỏ hơn), không còn gắn với ODR của chip.
- **Tốc độ:** máy 4 nhân dùng chung (load 10–15). LightGBM 4 luồng chậm ~40 lần so với 2 luồng → dùng `n_jobs=2`. Chấm điểm sự kiện viết lại dạng vector (kiểm khớp với bản lặp trên 20 phép thử ngẫu nhiên).
- **Kết quả M0/M1 (60 Hz, 4 s, LOSO 14 người, ngưỡng chọn trên vòng trong, đích độ nhạy 95 %):** M1 LightGBM A+B: độ nhạy 92,5 % [87,7–95,8], 0,42 báo nhầm/giờ [0–1,1]; A: 94,4 %, 3,2/giờ; A+G: 93,9 %, 3,6/giờ; A+G+B: 92,1 %, 0,56/giờ. Barometer giảm báo nhầm ~8 lần; gyro không giúp. Độ nhạy trên người test thấp hơn đích 95 % vì ngưỡng chọn trên người khác.
- **Lỗi (M1 A+B):** bỏ sót nhiều nhất ở ngã trượt dọc tường (135: 13/20) và ngã khỏi giường (127/128); báo nhầm chỉ ở xoay người/nằm xuống giường. S05 chiếm 17/55 lần bỏ sót: ΔP khi ngã của S05 nhỏ (phân vị 10 % = 1,4 Pa).
- **CNN (M2):** phiên trước bị ngắt sau 1 fold; thêm lưu kết quả từng fold (`results/raw/folds/`) để chạy tiếp được, chạy tách khỏi phiên (setsid/nohup).
- **CNN:** fold S04 hết bộ nhớ GPU (GPU dùng chung với người khác). Chuyển sang CPU (CUDA_VISIBLE_DEVICES=""; đo trước: tốc độ một epoch như nhau 12,9 s vs 12,8 s). Fold S01–S03 đã train trên GPU được nạp lại, không train lại.
- **Ưu tiên recall (người dùng: "quan trọng nhất là recall"):** thêm đích độ nhạy 98 % và 99 % khi chọn ngưỡng (vòng trong). M1 LightGBM A+B: đích 98 % → recall 98,1 % [97,2–99,0], 1,26 báo nhầm/giờ [0,14–2,91]; đích 99 % → 99,6 % [99,1–100], 3,08/giờ [0,95–6,12]. A ở đích 98 %: 98,0 %, 10,2/giờ. M0 (luật ngưỡng) sụp ở đích 98–99 % (187–218/giờ) → loại M0.
- **M2 CNN A+B (1 seed, 2.753 tham số) so với M1 LightGBM A+B:** đích 98 %: CNN recall 97,0 %, 9,4 báo nhầm/giờ vs LightGBM 98,1 %, 1,26/giờ; đích 99 %: CNN 98,6 %, 14,0/giờ vs 99,6 %, 3,1/giờ. Wilcoxon ghép theo người (FA/h): p = 0,005 (98 %), 0,003 (99 %). PR-AUC cửa sổ 0,891 vs 0,987. Lưu ý: CNN chọn ngưỡng trên 3 người validation, LightGBM trên OOF của cả 13 người train. Fold S01–S03 train trên GPU, S04–S15 trên CPU.
- **Người dùng: dừng CNN, viết báo cáo với LightGBM.** Đã dừng CNN cấu hình A sau 2 fold (đã xóa các fold dở). Chỉ M2 A+B có đủ 14 fold.
- **Q2 (M1 LightGBM A+B, đích 98 %):** 60 Hz đủ; cửa sổ 2 s kém (3,0 báo nhầm/giờ), 3–6 s tương đương (0,64–1,32/giờ). Chọn 60 Hz, 4 s.
- **H5:** chia ngẫu nhiên 80/20 theo cửa sổ cho tỉ lệ cửa sổ ngã bị bỏ sót 0,14 % so với 1,56 % khi chia theo người (thấp hơn ~11 lần).
- **Kiểm định ghép cặp** (`paired_tests.csv`): ở đích 98 %, A+B < A (p = 0,0015), A+B < A+G (p = 0,004), A+B ≈ A+G+B (p = 0,32), M1 < M2 (p = 0,005).
- **REPORT.md** viết xong (tiếng Việt), số liệu đối chiếu với CSV trong `results/tables/`. `run_all.py --quick` chạy hết không lỗi (3 phút, CPU).

## 2026-11-23 (tiếp) — Bản sửa 2 (chỉ phần mô hình)

- **Yêu cầu:** 6 việc (+1 tùy chọn), chỉ phần mô hình, KHÔNG làm gì liên quan ESP32/xuất C/firmware (người dùng trả lời câu hỏi về cài ESP-IDF bằng danh sách việc mới). Không cài gì thêm.
- **Việc 1, cắt đỉnh:** gia tốc không có mẫu nào = ±32767/−32768 ở cả 3 trục; |thô| lớn nhất 32.285 (7,88 g); 0/733 cú ngã bị cắt. Gyro: 1 mẫu −32768 ở 1 bản ghi ADL. Hệ số 0,244 mg/LSB khớp với trung vị độ lớn khi đứng yên (≈ 4.012–4.072 LSB ≈ 0,98–0,99 g).
- **Việc 2, cách đếm mới** (`events.COUNT_FALL_FA = True`, mặc định từ giờ): sự kiện trong bản ghi ngã không chứa cảnh báo trong [−1, +5] s là báo nhầm; thời gian ngoài khoảng đó cộng vào mẫu số (7,145 → 9,272 giờ). Kiểm bằng tay và 30 phép thử ngẫu nhiên nhanh/chậm. Kết quả: 0 báo nhầm trong bản ghi ngã, vì bản ghi 20 s nên mọi cảnh báo ngoài khoảng đều gộp vào sự kiện phát hiện (gộp 10 s).
- **Việc 2, mẫu âm từ bản ghi ngã** (cửa sổ cách va chạm > 0,5 s): trước đây KHÔNG dùng; nay dùng (`trees._train_rows(neg_from_falls=True)` mặc định). Train lại A, A+B, A+G+B: không khác có ý nghĩa (mọi p ≥ 0,05). Mốc mới A+B: đích 98 % → 98,2 %, 1,51/giờ; đích 99 % → 99,5 %, 2,59/giờ.
- **Máy:** load 10 trên 4 nhân (job `bench.run` của người khác). Ba tiến trình × 2 luồng LightGBM làm mọi thứ chậm 10 lần → dừng tuning lần đầu (chưa fold nào xong), chạy lại với `LGBM_THREADS=1`. Hàng đợi tự động đầu tiên kẹt 30 phút vì `pgrep -f` khớp vào chính shell khởi chạy → bỏ hàng đợi, chạy thẳng.
- **Việc 3, nested CV** 120 bộ; mỗi bộ (lá, lr, min_child, class weight) fit 500 cây một lần, đọc 50–300 cây bằng `num_iteration` (đã kiểm: sai lệch 0,0 so với train riêng). lr 0,1 ở 14/14 fold, 7 lá ở 11/14. Tinh chỉnh: 98,0 %, 0,97/giờ so với cố định 98,2 %, 1,51/giờ (p = 0,27) → giữ bộ cố định.
- **Việc 4, H2:** bất biến 1,51/giờ, không đổi khi test bị xoay; trục thô 4,42 → 18,0/giờ khi xoay (p = 0,0004). Chấp nhận H2.
- **Việc 5:** recall tăng theo đỉnh |a| (2–3 g: 94,1 % → > 6 g: 100 %) và ΔP (< 3 Pa: 90,3 % → > 10 Pa: 99,3 %) ở đích 98 %. S05 98,3 % (đích 98 %), 69,5 % (đích 95 %).
- **Việc 6:**
  - Đặc trưng không cần va chạm Ls 4/6/8 s: không khác có ý nghĩa; Ls = 8 s bắt thêm 2 (98 %) / 3 (99 %) cú ngã ID 135.
  - Bộ nằm lâu: lần đầu dùng tham chiếu ngay trước cửa sổ nằm yên → chỉ bắt 14 % cú ngã (tham chiếu trượt vào đoạn nằm). Sửa thành tham chiếu [s0 − 4 s, s0 − 1 s] trước khi bắt đầu chuỗi nằm yên.
  - Ghép OR với M1 (đích 98 %): bắt thêm 2/13 cú, báo nhầm 1,51 → 9,92 (T = 5 s), 4,31 (T = 8 s); T = 10 s không bao giờ báo vì bản ghi 20 s. Không khuyến nghị.
- **Việc 7 (tùy chọn):** không chạy; ước tính 630 lần train ≈ 20–40 giờ trên máy này.
- **REPORT.md:** thêm mục 11 "Bản sửa 2" và checklist; thêm ghi chú ở đầu mục 1; giữ nguyên số bản 1. `run_all.py --quick` chạy lại không lỗi (4 phút).

## 2026-11-23 (tiếp) — Chốt v1 (chỉ phần mô hình)

- **Yêu cầu:** chốt model v1 (150 cây × 7 lá, lr 0,1, min_child 20, không class weight, cố định); thử độ bền với nhiễu áp suất (chỉ trên dữ liệu test); chế độ dự phòng khi mất barometer; REPORT mục 12. Không ESP32, không thêm biến thể mô hình khác.
- **Code:** `src/experiments/v1_freeze.py`, `src/experiments/v1_noise.py`. Thêm tham số `keep` vào `trees.run` để giữ model và ngưỡng của từng fold. Không đổi hành vi cũ.
- **LOSO v1:**
  - đích 98 %: 97,8 % · 1,08/giờ (10 báo nhầm); đích 99 %: 99,0 % · 3,13/giờ;
  - so với mốc 300 × 15: p ≥ 0,25, không khác có ý nghĩa;
  - model A cùng tham số (dự phòng): 97,5 % · 7,44/giờ và 99,0 % · 16,07/giờ.
- **Model cuối:**
  - train trên 14 người; ngưỡng từ out-of-fold GroupKFold 4 phần trên 14 người: 0,6104 (98 %), 0,3766 (99 %);
  - lưu vào `models/v1/` (`model.txt`, `features.json`, `preprocessing.json`, `thresholds.json`, `model_info.json`, `MODEL_CARD.md`) và `models/v1/fallback_A/`;
  - đã kiểm: model nạp lại từ file cho cùng dự đoán (sai lệch 0,0).
- **Nhiễu áp suất:**
  - thêm vào tín hiệu thô 10 Hz rồi chạy lại chuỗi lọc; chỉ tính lại 4 đặc trưng áp suất (đã kiểm khớp từng bit với đặc trưng đã lưu); dùng model và ngưỡng của từng fold;
  - đã kiểm: chạy lại không nhiễu cho đúng LOSO v1;
  - 5 seed mỗi mức; mất khoảng 25 phút vì máy đang tải cao (load 7).
- **Kết quả nhiễu:**
  - Ở mọi mức yêu cầu, báo nhầm ≤ 1,83/giờ (đích 98 %), luôn tốt hơn A.
  - Vì không mức nào cho A+B kém hơn A, **đã thêm các mức ngoài yêu cầu** (trắng 8/16/32 Pa, trôi 60/120 Pa/phút, xung ±20/40 Pa; đánh dấu * trong báo cáo) để tìm điểm cắt.
  - A+B mất lợi thế khi nhiễu trắng 16 Pa (p = 0,76 so với A), nhưng không kém hơn A có ý nghĩa ở mức nào.
- **Quy tắc "kém hơn A":**
  - lần đầu dùng "recall thấp hơn A về số điểm", nên báo kém hơn cả khi chênh 0,1 điểm (dưới 1 cú ngã);
  - đổi thành: báo nhầm cao hơn A, hoặc recall thấp hơn A với Wilcoxon ghép cặp p < 0,05;
  - cột "recall thấp hơn về số điểm" vẫn giữ trong CSV.
- **25 Hz:** nội suy từ 10 Hz, không có thông tin mới. Thử cả chỉ trên test lẫn train lại: không khác v1 (p ≥ 0,25). Ghi rõ là không trả lời được câu hỏi về barometer 25 Hz thật.
- **Barometer hằng số / NaN:** kết quả giống hệt nhau (LightGBM coi NaN như 0, vì lúc train không có giá trị thiếu); recall 29,5 % ở đích 98 %. Khuyến nghị chuyển sang model A dự phòng.
- **Sự cố:** vòng chờ `pgrep -f` lại khớp vào chính shell của nó, và `pkill -f` để dọn lại giết luôn shell đang chạy. Tiến trình tính toán không bị ảnh hưởng. Từ giờ chờ theo PID.
- **REPORT.md:** thêm mục 12, không sửa các mục cũ.
