# ROADMAP ĐỒ ÁN — RugBench (Nhóm 5 · Trunginator · IS355)

> **Tài liệu chung cho cả nhóm** — Đọc để hiểu nhanh đề tài đang làm gì, đã xong tới đâu và từng bước tiếp theo cần làm gì từ đầu đến cuối.
> - **Repo GitHub:** https://github.com/shaorankun/rugbench
> - **Tên đề tài:** *RugBench: A Fair Benchmark of Five Machine Learning Methods for Rug Pull Detection on Public Datasets*

---

## 1. Hiểu nhanh đồ án trong 3 câu

1. **So sánh công tâm 5 AI trên 3 bộ dữ liệu:** Các bài báo trước mỗi bài chỉ test trên 1 bộ dữ liệu riêng rồi tự nhận mô hình của họ mạnh nhất. Nhóm mình gom cả **3 bộ dữ liệu công khai** (đều có đủ cả coin lừa đảo lẫn coin sạch) và chạy chung **5 mô hình AI** theo cùng một luật chơi công bằng.
2. **Bắt lỗi "lộ đề" và "học vẹt" của các bài báo cũ:** Không chỉ chấm điểm lại, nhóm chứng minh các điểm số 95%–98% trong bài báo cũ bị thổi phồng do **lộ đề** (ở D2 – SolRPDS) và **học vẹt theo phiên bản compiler** (ở D3 – RPHunter), rồi đo xem điểm thật sự còn bao nhiêu.
3. **Đưa kết quả AI lên Blockchain (Vyper):** Thay vì chỉ chạy AI trên máy tính như các bài báo cũ, nhóm ghi điểm rủi ro từ mô hình tốt nhất lên Smart Contract (`RugRiskRegistry.vy`) để một sàn giao dịch AMM mini (`GuardedPool.vy`) tự động chặn hoặc cảnh báo khi người dùng định mua coin nguy hiểm.

---

## 2. Tóm tắt 3 bộ dữ liệu & lỗi của các bài báo tham khảo

| Bộ dữ liệu | Nội dung & Tỷ lệ | Bài báo liên quan & Lỗi cần kiểm chứng | Vai trò trong đồ án |
| :--- | :--- | :--- | :--- |
| **D1 – TM-RugPull** | **1.000 dự án** × 27 cột, 8 chuỗi EVM (59,9% scam / 40,1% normal). Gồm giao dịch on-chain + tín hiệu Google/X. | **TM-RugPull [3]** chưa chạy model nào. **LROO [2]** test quá nhỏ (200 dự án), chạy 1 lần, không chỉnh tham số cho đối thủ (thiên vị TabPFN), bảng số liệu tự mâu thuẫn. | Bộ dữ liệu sạch nhất để dựng khung benchmark chuẩn và kiểm chứng lại kết quả bài LROO. |
| **D2 – SolRPDS** | **4 file CSV theo năm** (2021–11/2024) trên **Solana** (~63,5k pool / ~33,7k token, ~65,8% inactive). | **SolRPDS [1]** bị **lộ đề** (dùng số tiền đã rút / số lần rút để đoán nhãn vốn định nghĩa từ việc rút tiền), **chia ngược thời gian** (train 2022 → test 2021), không chỉnh tham số. | Thử sức AI trên dữ liệu lớn & mạng Solana; chứng minh mức độ tụt điểm khi bỏ các cột lộ đề (**I2**). |
| **D3 – RPHunter** | **2.320 token EVM** dạng bytecode (645 rug pull = 27,8% / 1.675 benign = 72,2%). | **RPHunter [4]** bị **học vẹt** (96% coin sạch dùng compiler đời cũ vs. 92% coin lừa đảo dùng đời mới → nhìn compiler đoán trúng ~95%) và **trùng đề** (1.146 coin copy code giống hệt nhau bị chia lẫn train/test). | Kiểm tra khả năng đoán chỉ từ code; gom nhóm clone; đo **chỉ số học vẹt SDI** (**I3**). |

*(Ngoài ra có 2 bài nền tảng không dùng làm dataset train: **SoK Rug Pulls [5]** lấy phân loại 35 kiểu rug pull; **SoK AMM DEXs [6]** lấy công thức sàn AMM $x \cdot y = k$ để code `GuardedPool.vy`.)*

---

## 3. Chốt xử lý Feedback Tuần 3 của giảng viên

| Mức ưu tiên | Nhận xét của thầy | Trạng thái & Cách xử lý |
| :---: | :--- | :--- |
| **Cao** | Xác nhận bản phát hành SolRPDS (D2) có dữ liệu event-level cho cải tiến I2 không. | **Đã xác nhận 100% KHÔNG có event-level** (Hugging Face chỉ có 4 file CSV/JSON tổng hợp theo năm 2021–2024). → **Chuyển sang phương án dự phòng cho I2:** so sánh bản đủ cột gốc vs. bản bỏ các cột rút thanh khoản & `LAST_*`. |
| **Cao** | Xác nhận số cột đặc trưng và ý nghĩa `W1`, `Q1–Q4` trong D1. | **Đã xác nhận từ `dataset.xlsx` & `README.md` của `RugPull-Defender`:** 1.000 dòng × 27 cột (1 nhãn, 8 cột định danh/lộ đề gồm `project end date`, 18 cột đặc trưng). `Q1–Q4` = `MaxPrice (Quarter 1..4)`. Không có cột `W1` trong bảng (chỉ có cặp cột Google website `first day` & `duration/2`; còn `W1/W2/W3` là tên 3 nhánh mô hình của bài *Rug-Pull Defender*). |
| **Trung bình** | Chọn ngưỡng cảnh báo `7.000` từ tập validation; thảo luận rủi ro reporter ghi sai / lộ khóa; cân nhắc thời hạn hiệu lực (TTL) điểm rủi ro. | **Sẽ đưa vào Báo cáo Tuần 4 & Code Giai đoạn 3:** chọn threshold tối ưu trên tập validation (ghi Precision/Recall); bổ sung phân tích rủi ro lộ khóa/ghi sai vào kịch bản bảo mật `T4`; cân nhắc thêm `max_age` / TTL trong `RugRiskRegistry.vy` hoặc `GuardedPool.vy`. |

---

## 4. Lộ trình 10 bước từ đầu đến cuối

### Giai đoạn 1: Chuẩn bị & Dữ liệu

- [x] **Bước 1: Đọc bài mẫu, chốt đề tài & nộp kế hoạch ban đầu**
  - Hoàn thành Proposal v2 và Báo cáo Tuần 3.
  - Khởi tạo cấu trúc thư mục chuẩn và push lên GitHub.
- [x] **Bước 2: Tải đủ 3 bộ dữ liệu gốc về máy + lưu mã băm SHA-256**
  - **D1:** `data/raw/d1_tm_rugpull/dataset.xlsx` + `manifest.json` (script: `src/data/download_d1.py`, repo `mohamadpishdar/RugPull-Defender`).
  - **D2:** `data/raw/d2_solrpds/{2021,2022,2023,Jan_2024-Nov_2024}.csv` + `manifest.json` (script: `src/data/download_d2.py`).
  - **D3:** `data/raw/d3_rphunter/Dataset.zip` + `manifest.json` (script kiểm tra: `src/data/verify_d3.py`).
- [ ] **Bước 2.5 (Ưu tiên nộp tuần này): Hoàn thành Báo cáo Tuần 4 (`Detailed Method & Test Plan`)**
  - Viết bằng tiếng Anh (12–18 trang) theo `docs/IS355_Week4_Project_Report_Template.docx` và `docs/IS355_Week4_Project_Requirements_VIE.docx`.
  - Gồm: bảng phản hồi feedback Tuần 3, sơ đồ quy trình cập nhật, đặc tả từng bước (có mã giả, công thức, tham số, schema Input/Output, kiểm tra đúng), đặc tả Smart Contract (biến, bảng hàm, ước tính gas EVM), giả thuyết `H1..Hk`, đủ 7 nhóm kịch bản test `T1–T7`, tính toán số lượt chạy + ngân sách Sepolia, kết quả dự kiến (+ chạy thử pilot nếu kịp), lịch kiểm thử theo tuần với 4 mốc `M1–M4`.
- [ ] **Bước 3: Làm sạch dữ liệu & tạo bảng đặc trưng (`src/data/` → `data/processed/`)**
  - **Làm D1 trước:** bỏ `project end date` và cột định danh, ép kiểu số 6 cột đang ở dạng chuỗi, `log1p`, one-hot `Blockchain`/`Blockchain Type`, giữ nguyên `NaN` → xuất `data/processed/features_d1.csv`.
  - **Làm D3 thứ hai:** giải nén `Rug-Bytecode.zip` & `Normal-Bytecode.zip`, chạy `src/data/build_d3_features.py` (tách metadata compiler, trích 170+ đặc trưng opcode/selector/size/era, gán `dup_group`, loại 9 token xung đột nhãn) → xuất `data/processed/d3_features.csv` + `d3_features_groups.json`.
  - **Làm D2 thứ ba:** gom 4 file CSV, nhóm theo `MINT`, xuất 2 bản: `features_d2_orig.csv` (đủ cột gốc để tái lập bài báo [1]) và `features_d2_noleak.csv` (bỏ các cột rút thanh khoản & `LAST_*` theo phương án dự phòng I2).

---

### Giai đoạn 2: Chạy AI & So sánh — Phần Off-chain (`src/benchmark/`)

> **Thứ tự thực hiện:** Dựng khung code chuẩn trên **D1** trước (nhẹ, chạy nhanh) → cắm **D3** vào → cắm **D2** vào sau cùng.

- [ ] **Bước 4: Thiết lập giao thức chia tập & tinh chỉnh thống nhất (I1)**
  - **D1:** Chia theo thời gian (`project starting date`): 80% cũ nhất train (20% cuối của train làm validation), 20% mới nhất test.
  - **D2:** Chia theo thời gian tiến (2021–2023 train, 3 tháng cuối 2023 validation, 2024 test; giữ các pool cùng `MINT` chung 1 bên). Bản tái lập [1]: train 2022 / test 2021.
  - **D3:** `StratifiedGroupKFold(k=5)` theo `dup_group` (không để coin copy code nằm lẫn 2 bên).
  - Trong fold train: điền thiếu bằng median, chuẩn hóa (cho LR), cân bằng trọng số lớp, tinh chỉnh **Optuna TPE (50 trials)** tối ưu **MCC** trên validation, lặp **5 seeds (0–4)**. Lưu chỉ số chia vào `artifacts/splits/` và tham số vào `artifacts/params/`.
- [ ] **Bước 5: Huấn luyện 5 mô hình AI**
  - Chạy **Logistic Regression, Random Forest, XGBoost, LightGBM, TabPFN** (TabPFN chạy mặc định trên GPU Google Colab).
  - Chạy thêm cấu hình **công bằng 10.000 dòng** trên D2 cho cả 5 mô hình để so sánh công bằng với TabPFN (`E5`).
  - Lưu model ra `artifacts/models/`.
- [ ] **Bước 6: Chấm điểm, kiểm chứng bài cũ, giải thích SHAP & chọn model tốt nhất**
  - **E1 vs. E2:** Đối chiếu kết quả tái lập bài [1], [2] với kết quả theo giao thức công bằng của nhóm. Tính **MCC** (chính), F1, PR-AUC, ROC-AUC kèm 95% bootstrap CI, McNemar (D1, D2) và corrected resampled t-test (D3).
  - **E3 (Lộ đề D2):** So sánh điểm bản gốc vs. bản bỏ cột rút thanh khoản.
  - **E4 (Học vẹt D3):** Chạy 4 cấu hình (`all`, `era-only`, `no-era`, `same-era`) và tính chỉ số `SDI = F1(all) - F1(same-era)`.
  - **E6 / T7 (Độ bền theo thời gian):** Train trên 2021–2022, test riêng trên 2023 và 2024.
  - Chạy **SHAP** trên mô hình cây tốt nhất để lấy top đặc trưng quan trọng.
  - Chọn ngưỡng cảnh báo tối ưu trên tập validation (đáp ứng feedback thầy), lưu mô hình tốt nhất `artifacts/models/best_model.pkl` kèm mã băm SHA-256 (`model_id`) → xuất `results/tables/benchmark.csv`, `shortcut.csv`, biểu đồ vào `results/figures/`.

---

### Giai đoạn 3: Smart Contract & Kết nối AI — Phần On-chain (`contracts/` & `src/reporter/`)

> *Lưu ý: Giai đoạn 3 có thể **làm song song** với Giai đoạn 2 ngay từ Tuần 5 (chia người code Vyper/Ape độc lập với phần ML).*

- [ ] **Bước 7: Viết & Unit-test Smart Contract bằng Vyper + Ape (`contracts/`)**
  - `contracts/contracts/MockToken.vy`: Token ERC-20 giả để làm vật thí nghiệm.
  - `contracts/contracts/RugRiskRegistry.vy`: Lưu `RiskRecord` (`score: uint16`, `flagged: bool`, `feature_hash: bytes32`, `model_id: bytes32`, `updated_at: uint256`, `reporter: address`), quản lý quyền `owner`/`reporters`/`models`/`threshold` (và cân nhắc thời hạn hiệu lực TTL), hỗ trợ `submit_score`, `submit_batch` (tối đa 50 token), `get_record`, `is_high_risk`.
  - `contracts/contracts/GuardedPool.vy`: Sàn AMM constant-product ($x \cdot y = k$) gọi `registry.is_high_risk(token)` trước `swap` và `add_liquidity` (revert nếu rủi ro cao mà `accept_risk == False`, ngược lại emit `RiskWarning`).
  - Viết đủ bộ test chức năng (`T3`: mỗi hàm ≥1 ca hợp lệ + ≥1 ca revert) và test bảo mật/fuzzing (`T4`: ≥5 ca + Hypothesis ≥200 input ngẫu nhiên) trong `contracts/tests/`.
- [ ] **Bước 8: Viết cầu nối Python Reporter (`src/reporter/`)**
  - Tải `best_model.pkl`, chấm điểm token (`score = round(p_rug * 10000)`), tính `feature_hash` (SHA-256 JSON chuẩn hóa) và `model_id` (SHA-256 file model).
  - Đọc private key từ biến môi trường `.env` (tuyệt đối không hardcode), gọi `submit_score` / `submit_batch` qua Ape, ghi log `results/tables/reporter_log.csv`.
- [ ] **Bước 9: Chạy thử trên Anvil & Sepolia, mô phỏng Rug Pull & đo Gas/Latency (`T5`, `T6`)**
  - Deploy lên **Anvil** (local) để chạy kịch bản mô phỏng rug pull (`E8`: Lần 1 chưa gắn cờ → 5 ví nạn nhân mua và mất tiền; Lần 2 đã gắn cờ → 5 ví bị chặn) và đo **gas** ở 3 kích thước input (1, 10, 50 token; ghi mới vs. ghi đè; so sánh swap có guard vs. không guard).
  - Deploy lên **Sepolia testnet** để đo **độ trễ xác nhận thật** (≥30 giao dịch/hàm chính ở ≥2 khung giờ, báo cáo median & p95 — không dùng Anvil làm độ trễ) và chạy kiểm thử đầu–cuối (`T6`: 3 lượt, đối chiếu hash off-chain ↔ on-chain). Xuất `results/tables/gas_report.csv`.

---

### Giai đoạn 4: Sản phẩm Demo & Báo cáo Cuối kỳ

- [ ] **Bước 10: Web demo Streamlit, Báo cáo cuối kỳ & Thuyết trình**
  - Xây trang web demo đơn giản trong `demo/` (chọn token → hiển thị điểm rủi ro, biểu đồ SHAP giải thích lý do, và trạng thái xác thực trên `RugRiskRegistry`).
  - Tổng hợp toàn bộ bảng số liệu, biểu đồ, đối chiếu kết quả thực tế với kết quả dự kiến ở Tuần 4 (giải thích mọi sai lệch nếu có).
  - Hoàn thiện báo cáo cuối kỳ, slide thuyết trình và quay video demo.

---

## 5. 4 Mốc bàn giao chính (Milestones từ Tuần 5)

- **M1 – Cài đặt xong:** Smart contract và pipeline off-chain chạy trơn tru trên Anvil; 100% test chức năng `T3` pass.
- **M2 – Chốt cấu hình:** Code, siêu tham số và ngưỡng cảnh báo được commit chốt; từ mốc này tập test chỉ dùng để đánh giá, không chỉnh sửa thêm.
- **M3 – Chạy xong kiểm thử:** Hoàn thành đủ `T1–T7` theo đúng số lượt đã đăng ký ở Tuần 4; lưu đủ bảng kết quả thô (`results/tables/`).
- **M4 – Hoàn thiện phân tích & báo cáo:** So sánh kết quả thật với dự kiến, hoàn thành bản nháp báo cáo cuối kỳ và demo.
