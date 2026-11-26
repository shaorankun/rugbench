"""
===============================================================================
BƯỚC 3.1: LÀM SẠCH DỮ LIỆU D1 — TM-RugPull (src/data/clean_d1.py)
===============================================================================
MỤC ĐÍCH CỦA FILE NÀY (Clean những gì?):
1. Chuẩn hóa tên cột (xóa khoảng trắng thừa) và xóa dòng trùng lặp nếu có.
2. Chuyển cột nhãn 'class' về chuẩn nhị phân: 1 = scam (rug pull), 0 = normal.
3. Chống lộ đề (Data Leakage):
   - XÓA cột 'project end date' (chứa ngày dự án sập -> làm lộ đáp án).
   - XÓA các cột định danh/đường link ('Project Title', 'Sign', 'Smart Contract',
     URL của website và X) để AI không học thuộc tên dự án.
   - Giữ lại 'start_date' CHỈ để chia tập train/test theo thời gian ở Bước 4.
4. Sửa dữ liệu số bị dính ký tự rác:
   - Cứu 66 giá trị số bị dính dấu phẩy ',', ký tự '\xa0', '\n' ở cột số giao
     dịch và tỷ lệ tập trung holder.
   - Đổi 6 ô nhập lỗi thật ('ROBIN HOOD', ngày tháng trong cột số, dấu '-')
     thành NaN (KHÔNG điền giá trị thiếu ở đây; Bước 4 mới điền trên tập train).
5. Nén các cột số dương quá lệch (lên tới 10^117) bằng log1p để chống tràn số.
6. Tạo 2 cờ nhị phân (has_website, has_x_profile), gộp chuỗi trùng tên
   (FANTOM -> FTM) và one-hot encode 'Blockchain' & 'Blockchain Type'.

ĐẦU VÀO : data/raw/d1_tm_rugpull/dataset.xlsx (1.000 dòng x 27 cột)
ĐẦU RA  : data/processed/features_d1.csv (1.000 dòng x 36 cột)
          data/processed/d1_schema.json
===============================================================================
"""
import json
import os
import re
import numpy as np
import pandas as pd

RAW_PATH = os.path.join("data", "raw", "d1_tm_rugpull", "dataset.xlsx")
OUT_CSV = os.path.join("data", "processed", "features_d1.csv")
OUT_SCHEMA = os.path.join("data", "processed", "d1_schema.json")

NUMERIC_RENAME = {
    "MaxPrice (Quarter 1)": "max_price_q1",
    "MaxPrice (Quarter 2)": "max_price_q2",
    "MaxPrice (Quarter 3)": "max_price_q3",
    "MaxPrice (Quarter 4)": "max_price_q4",
    "the number of Transactions": "n_transactions",
    "Token concentration ratio per holder": "token_concentration",
    "Total Variance": "total_variance",
    "Variance of holders with more than 1% tokens": "variance_holders_gt1pct",
    "Token balance": "token_balance",
    "first deposits": "first_deposits",
    "Google results for project title (first day)": "google_title_day1",
    "Google results for project title (project duration/2)": "google_title_mid",
    "Google results for project website (first day)": "google_website_day1",
    "Google results for project website (duration/2)": "google_website_mid",
    "Google results for project x profile (first days)": "google_x_day1",
    "Google results for project x profile (duration/2)": "google_x_mid",
}

DROP_COLS = [
    "Project Title",
    "Sign",
    "Smart Contract (online)",
    "smart Contract (offline)",
    "project end date",
]


def parse_clean_float(val) -> float:
    """Parse numeric values that may include non-breaking spaces, newlines, or thousands commas."""
    if pd.isna(val):
        return np.nan
    if isinstance(val, (int, float, np.integer, np.floating)):
        return float(val)
    s = str(val).replace("\xa0", "").replace(",", "").strip()
    if s in ("", "-", "/", "N/A", "nan", "None"):
        return np.nan
    try:
        return float(s)
    except ValueError:
        return np.nan


def has_valid_link(val) -> int:
    if pd.isna(val):
        return 0
    s = str(val).replace("\xa0", "").strip()
    return 0 if s in ("", "-", "/", "none", "None", "N/A") else 1


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower().strip()).strip("_")


def main():
    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    df = pd.read_excel(RAW_PATH)
    df.columns = [c.strip() for c in df.columns]

    n_raw = len(df)
    n_exact_dups = int(df.duplicated().sum())
    if n_exact_dups > 0:
        df = df.drop_duplicates().reset_index(drop=True)

    out = pd.DataFrame()
    out["row_id"] = np.arange(len(df), dtype=int)

    # Metadata for temporal split only (never passed to models as feature)
    start_dt = pd.to_datetime(df["project starting date"], errors="raise")
    out["start_date"] = start_dt.dt.strftime("%Y-%m-%d")

    # Binary target: 1 = rug pull (scam), 0 = legitimate (normal)
    label_map = {"scam": 1, "normal": 0}
    raw_cls = df["class"].astype(str).str.strip().str.lower()
    assert set(raw_cls.unique()) == {"scam", "normal"}, f"Unexpected labels: {raw_cls.unique()}"
    out["label"] = raw_cls.map(label_map).astype(int)

    # Clean numeric columns and apply log1p to compress extreme skew (up to 1e117)
    log1p_cols = []
    nan_report = {}
    for orig_col, new_col in NUMERIC_RENAME.items():
        vals = df[orig_col].map(parse_clean_float).astype(float)
        n_nan = int(vals.isna().sum())
        if n_nan > 0:
            nan_report[new_col] = n_nan
        # All numeric features here are non-negative; assert before log1p
        valid = vals.dropna()
        assert (valid >= 0).all(), f"Negative value found in {orig_col}: min={valid.min()}"
        col_log = f"{new_col}_log1p"
        out[col_log] = np.log1p(vals)
        log1p_cols.append(col_log)

    # Presence indicators from website / X profile (without leaking raw URLs)
    out["has_website"] = df["website"].map(has_valid_link).astype(int)
    out["has_x_profile"] = df["x profile"].map(has_valid_link).astype(int)

    # Normalize and one-hot encode Blockchain and Blockchain Type
    chain = (
        df["Blockchain"]
        .astype(str)
        .str.strip()
        .str.upper()
        .replace({"FANTOM": "FTM"})
    )
    chain_type = df["Blockchain Type"].astype(str).str.strip()

    chain_dummies = pd.get_dummies(chain.map(slugify), prefix="chain", dtype=int)
    type_dummies = pd.get_dummies(chain_type.map(slugify), prefix="chain_type", dtype=int)
    out = pd.concat([out, chain_dummies, type_dummies], axis=1)

    # Strict correctness checks
    meta_cols = ["row_id", "start_date", "label"]
    feature_cols = [c for c in out.columns if c not in meta_cols]

    assert len(out) == 1000, f"Expected 1000 rows, got {len(out)}"
    assert int((out["label"] == 1).sum()) == 599, "Expected 599 rug pull rows"
    assert int((out["label"] == 0).sum()) == 401, "Expected 401 normal rows"
    for forbidden in ["end_date", "project end date", "Project Title", "website", "x profile"]:
        assert forbidden not in feature_cols, f"Forbidden column leaked into features: {forbidden}"
    for c in feature_cols:
        assert pd.api.types.is_numeric_dtype(out[c]), f"Non-numeric feature column: {c}"
        assert not np.isinf(out[c].dropna()).any(), f"Infinite value in {c}"

    out.to_csv(OUT_CSV, index=False)

    schema = {
        "dataset": "D1_TM_RugPull",
        "source_file": RAW_PATH.replace("\\", "/"),
        "output_file": OUT_CSV.replace("\\", "/"),
        "n_rows_raw": n_raw,
        "n_exact_duplicates_dropped": n_exact_dups,
        "n_rows_clean": len(out),
        "label_counts": {"rug_pull_1": int((out["label"] == 1).sum()), "legitimate_0": int((out["label"] == 0).sum())},
        "meta_columns": meta_cols,
        "feature_columns": feature_cols,
        "n_features": len(feature_cols),
        "dropped_columns": DROP_COLS,
        "log1p_columns": log1p_cols,
        "missing_values_kept_for_fold_imputation": nan_report,
        "start_date_range": [str(out["start_date"].min()), str(out["start_date"].max())],
        "n_start_date_before_2015": int((start_dt.dt.year < 2015).sum()),
    }
    with open(OUT_SCHEMA, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)

    print("=== D1 CLEANING COMPLETE ===")
    print(f"Saved: {OUT_CSV} ({out.shape[0]} rows x {out.shape[1]} cols)")
    print(f"Features: {len(feature_cols)} numeric columns | Meta: {meta_cols}")
    print(f"Label balance: 1 (rug pull) = {(out['label']==1).sum()} (59.9%), 0 (legitimate) = {(out['label']==0).sum()} (40.1%)")
    print(f"NaNs preserved for fold imputation: {nan_report}")
    print(f"Schema saved: {OUT_SCHEMA}")


if __name__ == "__main__":
    main()
