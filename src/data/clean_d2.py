"""
===============================================================================
BƯỚC 3.2: LÀM SẠCH DỮ LIỆU D2 — SolRPDS / Solana (src/data/clean_d2.py)
===============================================================================
MỤC ĐÍCH CỦA FILE NÀY (Clean những gì?):
1. Gộp 4 file CSV theo năm (2021, 2022, 2023, Jan_2024-Nov_2024) thành 1 bảng,
   gắn thêm cột 'source_year' để Bước 4 dễ chia tập theo thời gian tiến
   (2021-2023 train / 2024 test) và tái lập bài báo cũ (2022 train / 2021 test).
2. Xóa 4 dòng rác UTF-8 BOM (cuối mỗi file CSV, toàn NaN) và xóa 3 dòng trùng
   lặp hoàn toàn -> còn đúng 63.520 pool duy nhất (khớp Table 2 bài báo gốc).
3. Chuyển nhãn 'INACTIVITY_STATUS' về chuẩn nhị phân:
   1 = Inactive (nghi rug pull), 0 = Active (bình thường).
4. Giữ 'MINT' làm khóa nhóm (để nhiều pool của cùng 1 token không bị chia tách
   sang 2 bên train/test) và 'first_activity_ts' để chia theo thời gian;
   xóa 'LIQUIDITY_POOL_ADDRESS' và 'LAST_SWAP_TX_ID' khỏi đặc trưng.
5. Chống lộ đề (Cải tiến I2 — Phương án dự phòng sau khi xác nhận Hugging Face
   không có dữ liệu mức sự kiện event-level):
   - Bắt buộc XÓA các cột thời gian cuối (LAST_POOL_ACTIVITY_TIMESTAMP,
     LAST_SWAP_TIMESTAMP) vì chúng làm lộ trực tiếp trạng thái hiện tại.
   - Nén các cột số lượng thanh khoản bị lệch mạnh (1e-9 đến 5e18) bằng log1p.
   - Xuất song song 2 bảng để chạy thí nghiệm lộ đề (E1 vs E3):
     + features_d2_orig.csv  : giữ đủ 5 cột tổng hợp gốc của bài báo (gồm cả
       số tiền đã rút, số lần rút, tỷ lệ nạp/rút) để tái lập kết quả cũ.
     + features_d2_noleak.csv: XÓA sạch các cột liên quan đến rút thanh khoản
       (REMOVED / REMOVE / RATIO), chỉ giữ tín hiệu nạp thanh khoản và đặc trưng
       thời điểm tạo pool ban đầu.

ĐẦU VÀO : data/raw/d2_solrpds/{2021,2022,2023,Jan_2024-Nov_2024}.csv
ĐẦU RA  : data/processed/features_d2_orig.csv
          data/processed/features_d2_noleak.csv
          data/processed/d2_schema.json
===============================================================================
"""
import json
import os
import numpy as np
import pandas as pd

RAW_DIR = os.path.join("data", "raw", "d2_solrpds")
YEAR_FILES = [
    (2021, "2021.csv"),
    (2022, "2022.csv"),
    (2023, "2023.csv"),
    (2024, "Jan_2024-Nov_2024.csv"),
]

OUT_ORIG = os.path.join("data", "processed", "features_d2_orig.csv")
OUT_NOLEAK = os.path.join("data", "processed", "features_d2_noleak.csv")
OUT_SCHEMA = os.path.join("data", "processed", "d2_schema.json")

# Major Solana quote mints (SOL, USDC, USDT) recorded as metadata for optional analysis
MAJOR_QUOTE_MINTS = {
    "So11111111111111111111111111111111111111112",   # Wrapped SOL
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT
}


def main():
    os.makedirs(os.path.dirname(OUT_ORIG), exist_ok=True)

    frames = []
    for year, fname in YEAR_FILES:
        path = os.path.join(RAW_DIR, fname)
        df_y = pd.read_csv(path)
        df_y["source_year"] = year
        frames.append(df_y)

    df = pd.concat(frames, ignore_index=True)
    n_raw = len(df)

    # Drop UTF-8 BOM trailing empty rows (where MINT & INACTIVITY_STATUS are NaN)
    bom_mask = df["MINT"].isna() | df["INACTIVITY_STATUS"].isna()
    n_bom_dropped = int(bom_mask.sum())
    df = df.loc[~bom_mask].copy()

    # Drop exact duplicates (excluding source_year check first, keep first occurrence)
    data_cols = [c for c in df.columns if c != "source_year"]
    n_exact_dups = int(df.duplicated(subset=data_cols).sum())
    if n_exact_dups > 0:
        df = df.drop_duplicates(subset=data_cols, keep="first").reset_index(drop=True)
    else:
        df = df.reset_index(drop=True)

    # Validate status and encode binary label: 1 = Inactive (suspected rug pull), 0 = Active
    raw_status = df["INACTIVITY_STATUS"].astype(str).str.strip()
    assert set(raw_status.unique()) == {"Active", "Inactive"}, f"Unexpected status: {raw_status.unique()}"
    label = (raw_status == "Inactive").astype(int)

    # Parse FIRST_POOL_ACTIVITY_TIMESTAMP (used for temporal split + safe initial-time features)
    first_ts = pd.to_datetime(df["FIRST_POOL_ACTIVITY_TIMESTAMP"], errors="raise")

    # Numeric columns (check non-negative before log1p)
    num_cols = [
        "TOTAL_ADDED_LIQUIDITY",
        "TOTAL_REMOVED_LIQUIDITY",
        "NUM_LIQUIDITY_ADDS",
        "NUM_LIQUIDITY_REMOVES",
        "ADD_TO_REMOVE_RATIO",
    ]
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors="raise").astype(float)
        assert (df[c] >= 0).all(), f"Negative value in {c}"
        assert not np.isinf(df[c]).any(), f"Inf value in {c}"

    # Shared metadata columns (never passed to ML models as features)
    meta = pd.DataFrame({
        "row_id": np.arange(len(df), dtype=int),
        "pool_address": df["LIQUIDITY_POOL_ADDRESS"].astype(str).str.strip(),
        "mint": df["MINT"].astype(str).str.strip(),
        "is_major_quote": df["MINT"].astype(str).str.strip().isin(MAJOR_QUOTE_MINTS).astype(int),
        "source_year": df["source_year"].astype(int),
        "first_activity_ts": first_ts.dt.strftime("%Y-%m-%d %H:%M:%S"),
        "label": label,
    })

    # Table 1: Original 5 aggregate features (raw + log1p) for baseline reproduction (E1) & leakage comparison
    orig_feats = pd.DataFrame({
        "total_added_liquidity_log1p": np.log1p(df["TOTAL_ADDED_LIQUIDITY"]),
        "total_removed_liquidity_log1p": np.log1p(df["TOTAL_REMOVED_LIQUIDITY"]),
        "num_liquidity_adds_log1p": np.log1p(df["NUM_LIQUIDITY_ADDS"]),
        "num_liquidity_removes_log1p": np.log1p(df["NUM_LIQUIDITY_REMOVES"]),
        "add_to_remove_ratio_log1p": np.log1p(df["ADD_TO_REMOVE_RATIO"]),
    })
    df_orig = pd.concat([meta, orig_feats], axis=1)

    # Table 2: Leakage-reduced features (I2 fallback: strictly NO removal columns and NO LAST_* columns)
    avg_added_per_add = df["TOTAL_ADDED_LIQUIDITY"] / np.maximum(df["NUM_LIQUIDITY_ADDS"], 1.0)
    noleak_feats = pd.DataFrame({
        "total_added_liquidity_log1p": np.log1p(df["TOTAL_ADDED_LIQUIDITY"]),
        "num_liquidity_adds_log1p": np.log1p(df["NUM_LIQUIDITY_ADDS"]),
        "avg_added_per_add_log1p": np.log1p(avg_added_per_add),
        "first_activity_hour": first_ts.dt.hour.astype(int),
        "first_activity_dayofweek": first_ts.dt.dayofweek.astype(int),
        "first_activity_month": first_ts.dt.month.astype(int),
    })
    df_noleak = pd.concat([meta, noleak_feats], axis=1)

    # Strict correctness checks
    meta_cols = list(meta.columns)
    orig_feature_cols = list(orig_feats.columns)
    noleak_feature_cols = list(noleak_feats.columns)

    for c in noleak_feature_cols:
        cl = c.lower()
        assert "remove" not in cl and "ratio" not in cl and "last" not in cl, (
            f"Leakage column found in noleak table: {c}"
        )
    for table_name, table_df, fcols in [
        ("orig", df_orig, orig_feature_cols),
        ("noleak", df_noleak, noleak_feature_cols),
    ]:
        for c in fcols:
            assert pd.api.types.is_numeric_dtype(table_df[c]), f"{table_name}.{c} not numeric"
            assert not table_df[c].isna().any(), f"{table_name}.{c} has NaN"
            assert not np.isinf(table_df[c]).any(), f"{table_name}.{c} has Inf"

    df_orig.to_csv(OUT_ORIG, index=False)
    df_noleak.to_csv(OUT_NOLEAK, index=False)

    n_unique_pools = int(meta["pool_address"].nunique())
    n_unique_mints = int(meta["mint"].nunique())
    per_year_counts = meta["source_year"].value_counts().sort_index().to_dict()
    per_year_counts = {int(k): int(v) for k, v in per_year_counts.items()}

    schema = {
        "dataset": "D2_SolRPDS",
        "event_level_available": False,
        "i2_mode": "fallback_remove_leakage_columns",
        "n_rows_raw": n_raw,
        "n_bom_rows_dropped": n_bom_dropped,
        "n_exact_duplicates_dropped": n_exact_dups,
        "n_rows_clean": len(meta),
        "n_unique_pools": n_unique_pools,
        "n_unique_mints": n_unique_mints,
        "rows_per_year": per_year_counts,
        "label_counts_by_row": {
            "inactive_1": int((meta["label"] == 1).sum()),
            "active_0": int((meta["label"] == 0).sum()),
        },
        "major_quote_rows": int(meta["is_major_quote"].sum()),
        "meta_columns": meta_cols,
        "orig_feature_columns": orig_feature_cols,
        "noleak_feature_columns": noleak_feature_cols,
        "dropped_leakage_columns": [
            "LAST_POOL_ACTIVITY_TIMESTAMP",
            "LAST_SWAP_TIMESTAMP",
            "LAST_SWAP_TX_ID",
        ],
        "additional_removed_in_noleak": [
            "TOTAL_REMOVED_LIQUIDITY",
            "NUM_LIQUIDITY_REMOVES",
            "ADD_TO_REMOVE_RATIO",
        ],
        "output_files": {
            "orig": OUT_ORIG.replace("\\", "/"),
            "noleak": OUT_NOLEAK.replace("\\", "/"),
        },
    }
    with open(OUT_SCHEMA, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)

    print("=== D2 CLEANING COMPLETE ===")
    print(f"Raw rows: {n_raw:,} | Dropped BOM rows: {n_bom_dropped} | Dropped exact dups: {n_exact_dups}")
    print(f"Clean rows: {len(meta):,} | Unique pools: {n_unique_pools:,} | Unique MINTs: {n_unique_mints:,}")
    print(f"Rows per year: {per_year_counts}")
    print(f"Label (by row): 1 (Inactive) = {(meta['label']==1).sum():,} ({(meta['label']==1).mean()*100:.1f}%), "
          f"0 (Active) = {(meta['label']==0).sum():,} ({(meta['label']==0).mean()*100:.1f}%)")
    print(f"Saved: {OUT_ORIG} ({len(orig_feature_cols)} features)")
    print(f"Saved: {OUT_NOLEAK} ({len(noleak_feature_cols)} features)")
    print(f"Schema saved: {OUT_SCHEMA}")


if __name__ == "__main__":
    main()
