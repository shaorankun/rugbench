# RugBench — Group 5 (Trunginator) · IS355 Blockchain Technology

Đồ án môn học **IS355 – Blockchain Technology**:
*RugBench: A Fair Benchmark of Five Machine Learning Methods for Rug Pull Detection on Public Datasets.*

## 1. Cấu trúc thư mục

```text
PJ/
├── configs/                    # File cấu hình thực nghiệm (YAML: methods, seeds, trials, windows)
├── data/
│   ├── raw/                    # [Bước 2] Dữ liệu gốc tải trực tiếp từ nguồn công khai
│   │   ├── d1_tm_rugpull/      # D1: dataset.xlsx (TM-RugPull)
│   │   ├── d2_solrpds/         # D2: các file CSV/JSON theo năm (SolRPDS)
│   │   └── d3_rphunter/        # D3: Rug-Bytecode.zip, Normal-Bytecode.zip, Rug-Pull-Incidents.xlsx
│   ├── interim/                # Dữ liệu trung gian dạng Parquet (d1_raw, d2_raw, d3_raw)
│   └── processed/              # [Bước 3] Bảng đặc trưng đã làm sạch (features_d1.csv, features_d2_*.csv, d3_features.csv)
├── src/
│   ├── data/                   # [Bước 2–3] Script tải, kiểm tra, làm sạch D1–D3, trích xuất đặc trưng D3
│   ├── benchmark/              # [Bước 4–6] Chia tập, Optuna, train 5 models, đánh giá, thống kê, SHAP
│   └── reporter/               # [Bước 8] Cầu nối Python: chấm điểm, tính SHA-256, gửi lên RugRiskRegistry
├── contracts/                  # [Bước 7 & 9] Dự án Smart Contract (Vyper + Ape)
│   ├── contracts/              # RugRiskRegistry.vy, GuardedPool.vy, MockToken.vy
│   ├── scripts/                # Deploy lên Anvil/Sepolia, mô phỏng rug pull, đo gas & latency
│   └── tests/                  # Unit tests (Ape / pytest)
├── demo/                       # [Bước 10] Trang web demo Streamlit
├── artifacts/
│   ├── splits/                 # Chỉ số chia train/val/test (JSON) theo dataset, fold, seed
│   ├── params/                 # Bộ tham số Optuna tốt nhất (JSON)
│   └── models/                 # Các mô hình đã huấn luyện (.pkl) và best_model.pkl
└── results/
    ├── tables/                 # Bảng kết quả CSV (benchmark.csv, shortcut.csv, gas_report.csv, reporter_log.csv)
    └── figures/                # Biểu đồ PNG, SHAP plots đưa vào báo cáo
```

## 2. Nguồn tải 3 bộ dữ liệu (Bước 2)

| Dataset | Nguồn chính thức | Đặt vào thư mục |
| :--- | :--- | :--- |
| **D1 – TM-RugPull** | https://github.com/mohamadpishdar/RugPullDefender (`src/DataSet/dataset.xlsx`) | `data/raw/d1_tm_rugpull/` |
| **D2 – SolRPDS** | https://huggingface.co/datasets/DeFiLab/SolRPDS | `data/raw/d2_solrpds/` |
| **D3 – RPHunter** | https://figshare.com/s/e6e7cce0b6574770e7ce (`Dataset.zip` / bytecode & incidents) | `data/raw/d3_rphunter/` |

> **Lưu ý bảo mật:** Không bao giờ commit file `.env` hay private key của ví reporter lên Git (đã được chặn sẵn trong `.gitignore`).
