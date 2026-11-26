"""
===============================================================================
BƯỚC 3.3: TRÍCH XUẤT ĐẶC TRƯNG & LÀM SẠCH D3 — RPHunter Bytecode
          (src/data/build_d3_features.py)
===============================================================================
MỤC ĐÍCH CỦA FILE NÀY (Clean & trích xuất những gì?):
Vì dữ liệu gốc D3 là mã máy hợp đồng (hex bytecode) chứ chưa phải bảng số,
file này đọc trực tiếp 2.320 file bytecode từ Dataset.zip và làm 4 việc chính:
1. Gán nhãn chuẩn nhị phân:
   - Rug-Bytecode.zip    (645 token)   -> label = 1 (rug pull)
   - Normal-Bytecode.zip (1.675 token) -> label = 0 (benign / sạch)
2. Tách phần đuôi metadata compiler (Solidity tự chèn cuối bytecode) để:
   - Trích nhóm đặc trưng 'era_*' (21 cột: định dạng metadata cũ bzzr0/bzzr1
     vs. mới ipfs, phiên bản solc 0.4-0.8, kiểu dispatcher, opcode EVM đời mới)
     -> phục vụ thí nghiệm đo chỉ số học vẹt SDI (Cải tiến I3).
   - Lấy phần bytecode thuần túy (đã cắt bỏ metadata) để so sánh trùng code.
3. Gom nhóm clone (trùng code) & đánh dấu xung đột nhãn (chống trùng đề):
   - Băm SHA-256 phần bytecode đã cắt metadata -> các token copy code y hệt
     nhau nhận chung 1 mã 'dup_group' để Bước 4 chia StratifiedGroupKFold.
   - Phát hiện các nhóm clone chứa cả nhãn 0 lẫn 1 (xung đột nhãn): gắn cờ
     'is_conflict_rug' (loại khỏi tập chính) và 'is_conflict_group' (dùng cho
     phân tích độ nhạy loại toàn bộ các nhóm xung đột).
4. Dịch ngược (disassemble) bytecode thành bảng số (~175+ cột) gồm 4 nhóm:
   - size     : kích thước bytecode, số lệnh EVM, số hàm (selector)...
   - opcode   : tần suất tương đối của từng lệnh EVM (op_PUSH, op_SSTORE, ...).
   - selector : kiểm tra 12 nhóm hàm rủi ro (owner, mint, burn, pause,
     blacklist, whitelist, đổi phí, miễn phí, bật/tắt trade, giới hạn tx,
     router/pair, rút tiền khẩn cấp / selfdestruct / delegatecall).
   - era      : 21 đặc trưng thế hệ trình biên dịch compiler.

ĐẦU VÀO : data/raw/d3_rphunter/Dataset.zip
ĐẦU RA  : data/processed/d3_features.csv           (toàn bộ 2.320 dòng + cờ xung đột)
          data/processed/d3_features_clean.csv     (đã loại các token rug xung đột nhãn)
          data/processed/d3_features_groups.json   (phân nhóm cột: size/opcode/selector/era)
===============================================================================
"""
import hashlib
import io
import json
import os
import zipfile
from collections import Counter
import numpy as np
import pandas as pd

RAW_ZIP = os.path.join("data", "raw", "d3_rphunter", "Dataset.zip")
OUT_ALL_CSV = os.path.join("data", "processed", "d3_features.csv")
OUT_CLEAN_CSV = os.path.join("data", "processed", "d3_features_clean.csv")
OUT_GROUPS_JSON = os.path.join("data", "processed", "d3_features_groups.json")

# Standard EVM opcode table (0x00 - 0xff)
EVM_OPCODES = {
    0x00: "STOP", 0x01: "ADD", 0x02: "MUL", 0x03: "SUB", 0x04: "DIV",
    0x05: "SDIV", 0x06: "MOD", 0x07: "SMOD", 0x08: "ADDMOD", 0x09: "MULMOD",
    0x0A: "EXP", 0x0B: "SIGNEXTEND",
    0x10: "LT", 0x11: "GT", 0x12: "SLT", 0x13: "SGT", 0x14: "EQ",
    0x15: "ISZERO", 0x16: "AND", 0x17: "OR", 0x18: "XOR", 0x19: "NOT",
    0x1A: "BYTE", 0x1B: "SHL", 0x1C: "SHR", 0x1D: "SAR",
    0x20: "KECCAK256",
    0x30: "ADDRESS", 0x31: "BALANCE", 0x32: "ORIGIN", 0x33: "CALLER",
    0x34: "CALLVALUE", 0x35: "CALLDATALOAD", 0x36: "CALLDATASIZE",
    0x37: "CALLDATACOPY", 0x38: "CODESIZE", 0x39: "CODECOPY",
    0x3A: "GASPRICE", 0x3B: "EXTCODESIZE", 0x3C: "EXTCODECOPY",
    0x3D: "RETURNDATASIZE", 0x3E: "RETURNDATACOPY", 0x3F: "EXTCODEHASH",
    0x40: "BLOCKHASH", 0x41: "COINBASE", 0x42: "TIMESTAMP", 0x43: "NUMBER",
    0x44: "DIFFICULTY", 0x45: "GASLIMIT", 0x46: "CHAINID", 0x47: "SELFBALANCE",
    0x48: "BASEFEE",
    0x50: "POP", 0x51: "MLOAD", 0x52: "MSTORE", 0x53: "MSTORE8",
    0x54: "SLOAD", 0x55: "SSTORE", 0x56: "JUMP", 0x57: "JUMPI",
    0x58: "PC", 0x59: "MSIZE", 0x5A: "GAS", 0x5B: "JUMPDEST",
    0x5F: "PUSH0",
    0xA0: "LOG0", 0xA1: "LOG1", 0xA2: "LOG2", 0xA3: "LOG3", 0xA4: "LOG4",
    0xF0: "CREATE", 0xF1: "CALL", 0xF2: "CALLCODE", 0xF3: "RETURN",
    0xF4: "DELEGATECALL", 0xF5: "CREATE2", 0xFA: "STATICCALL",
    0xFD: "REVERT", 0xFE: "INVALID", 0xFF: "SELFDESTRUCT",
}
for _i in range(1, 33):
    EVM_OPCODES[0x5F + _i] = f"PUSH{_i}"
for _i in range(1, 17):
    EVM_OPCODES[0x7F + _i] = f"DUP{_i}"
for _i in range(1, 17):
    EVM_OPCODES[0x8F + _i] = f"SWAP{_i}"

# 12 risky function groups represented by standard 4-byte Keccak-256 selectors
RISKY_SELECTOR_GROUPS = {
    "sel_owner": {
        "8da5cb5b",  # owner()
        "f2fde38b",  # transferOwnership(address)
        "715018a6",  # renounceOwnership()
        "893d20e8",  # getOwner()
        "13af4035",  # setOwner(address)
    },
    "sel_mint": {
        "40c10f19",  # mint(address,uint256)
        "a0712d68",  # mint(uint256)
        "4e6ec247",  # _mint(address,uint256)
        "156e29f6",  # mint(address,uint256,uint256)
        "6a627842",  # mint(address)
    },
    "sel_burn": {
        "42966c68",  # burn(uint256)
        "79cc6790",  # burnFrom(address,uint256)
        "9dc29fac",  # burn(address,uint256)
    },
    "sel_pause": {
        "8456cb59",  # pause()
        "3f4ba83a",  # unpause()
        "5c975abb",  # paused()
    },
    "sel_blacklist": {
        "f9f92be4",  # blacklist(address)
        "44337ea1",  # blacklistAddress(address,bool)
        "fe575a87",  # isBlacklisted(address)
        "0ecb93c0",  # getBlackListStatus(address)
        "e47d6060",  # isBlackListed(address)
        "3bbac579",  # isBot(address)
        "b515566a",  # setBots(address[])
        "537df3b6",  # addBlacklist(address)
        "1d7ef879",  # setBlacklist(address,bool)
        "575a86b2",  # blacklist(address,bool)
    },
    "sel_whitelist": {
        "9b19251a",  # whitelist(address)
        "3af32abf",  # isWhitelisted(address)
        "e43252d7",  # addWhitelist(address)
        "53d6fd59",  # setWhitelist(address,bool)
    },
    "sel_fee_change": {
        "061c82d0",  # setTaxFeePercent(uint256)
        "8ee88c53",  # setLiquidityFeePercent(uint256)
        "69fe0e2d",  # setFee(uint256)
        "0b78f9c0",  # setFees(uint256,uint256)
        "7571336a",  # setAutomatedMarketMakerPair(address,bool)
        "c0246668",  # excludeFromFees(address,bool)
        "e57f14e1",  # setBuyFee(uint256)
        "2d838119",  # tokenFromReflection(uint256)
        "a9059cbb_fee_placeholder",  # (kept inert; never matched as 8-hex)
    },
    "sel_fee_exclude": {
        "437823ec",  # excludeFromFee(address)
        "ea2f0b37",  # includeInFee(address)
        "5342acb4",  # isExcludedFromFee(address)
        "52390c02",  # excludeFromReward(address)
        "3685d419",  # includeInReward(address)
        "88f82020",  # isExcludedFromReward(address)
        "4fbee193",  # isExcludedFromFees(address)
    },
    "sel_trading_switch": {
        "c9567bf9",  # openTrading()
        "8a8c523c",  # enableTrading()
        "4ada218b",  # tradingEnabled()
        "c49b9a80",  # setSwapAndLiquifyEnabled(bool)
        "4a74bb02",  # swapAndLiquifyEnabled()
        "6ddd1713",  # swapEnabled()
        "e01af92c",  # setSwapEnabled(bool)
    },
    "sel_tx_limit": {
        "d543dbeb",  # setMaxTxPercent(uint256)
        "ec28438a",  # setMaxTxAmount(uint256)
        "7d1db4a5",  # _maxTxAmount()
        "8c0b5e22",  # maxTxAmount()
        "8f9a55c0",  # _maxWalletSize()
        "aa4bde28",  # maxWalletAmount()
        "27c8f835",  # deadWallet()
    },
    "sel_router_pair": {
        "1694505e",  # uniswapV2Router()
        "49bd5a5e",  # uniswapV2Pair()
        "c45a0155",  # factory()
        "ad5c4648",  # WETH()
        "095ea7b3_router_placeholder",
    },
    "sel_admin_drain": {
        "3ccfd60b",  # withdraw()
        "db2e21bc",  # emergencyWithdraw()
        "51cff8d9",  # withdraw(address)
        "f3fef3a3",  # withdraw(address,uint256)
        "853828b6",  # withdrawAll()
        "1058d281",  # rescueTokens(...) / similar
        "c31c9c07",  # recoverERC20(...) / router
    },
}
# Keep only valid 8-hex-char selectors
for _k in list(RISKY_SELECTOR_GROUPS.keys()):
    RISKY_SELECTOR_GROUPS[_k] = {s for s in RISKY_SELECTOR_GROUPS[_k] if len(s) == 8}


def strip_solidity_metadata(code: bytes) -> tuple[bytes, bytes, dict]:
    """Strip trailing Solidity CBOR metadata and extract compiler-era indicators."""
    info = {
        "era_has_metadata": 0,
        "era_meta_len": 0,
        "era_old_meta_bzzr0": 0,
        "era_old_meta_bzzr1": 0,
        "era_old_meta_any": 0,
        "era_new_meta_ipfs": 0,
        "era_has_solc_ver": 0,
        "era_solc_minor": -1,
        "era_solc_patch": -1,
        "era_solc_0_4": 0,
        "era_solc_0_5": 0,
        "era_solc_0_6": 0,
        "era_solc_0_7": 0,
        "era_solc_0_8": 0,
    }

    if len(code) < 4:
        return code, b"", info

    meta_len = int.from_bytes(code[-2:], "big")
    # Valid Solidity CBOR metadata usually starts with 0xa1..0xa5 and length is between 20 and 200 bytes
    if 10 <= meta_len <= min(256, len(code) - 2):
        meta = code[-(meta_len + 2):-2]
        if len(meta) == meta_len and (meta[0] & 0xE0) == 0xA0:
            # Verify recognizable Solidity metadata markers
            has_marker = any(m in meta for m in (b"bzzr0", b"bzzr1", b"ipfs", b"solc", b"experimental"))
            if has_marker:
                info["era_has_metadata"] = 1
                info["era_meta_len"] = meta_len
                if b"bzzr0" in meta:
                    info["era_old_meta_bzzr0"] = 1
                    info["era_old_meta_any"] = 1
                if b"bzzr1" in meta:
                    info["era_old_meta_bzzr1"] = 1
                    info["era_old_meta_any"] = 1
                if b"ipfs" in meta:
                    info["era_new_meta_ipfs"] = 1
                idx = meta.find(b"solc\x43")
                if idx != -1 and idx + 8 <= len(meta):
                    major, minor, patch = meta[idx + 5], meta[idx + 6], meta[idx + 7]
                    if major == 0 and minor <= 9:
                        info["era_has_solc_ver"] = 1
                        info["era_solc_minor"] = int(minor)
                        info["era_solc_patch"] = int(patch)
                        if minor in (4, 5, 6, 7, 8):
                            info[f"era_solc_0_{minor}"] = 1
                return code[:-(meta_len + 2)], meta, info

    # Fallback: legacy pattern a165627a7a72305820...0029 (Solidity 0.4.7 - 0.5.8)
    idx_old = code.rfind(b"\xa1\x65bzzr0\x58\x20")
    if idx_old != -1 and len(code) - idx_old <= 60:
        meta = code[idx_old:]
        info["era_has_metadata"] = 1
        info["era_meta_len"] = len(meta)
        info["era_old_meta_bzzr0"] = 1
        info["era_old_meta_any"] = 1
        return code[:idx_old], meta, info

    return code, b"", info


def disassemble_bytecode(code: bytes) -> tuple[Counter, set[str], int, int, int]:
    """Disassemble EVM runtime bytecode while skipping PUSH immediate payloads."""
    op_counts: Counter = Counter()
    selectors: set[str] = set()
    n_instructions = 0
    push_data_bytes = 0
    old_dispatcher_push29 = 0

    i = 0
    n = len(code)
    while i < n:
        op = code[i]
        op_counts[op] += 1
        n_instructions += 1
        i += 1
        if 0x60 <= op <= 0x7F:
            push_len = op - 0x5F
            payload = code[i:i + push_len]
            push_data_bytes += len(payload)
            if push_len == 4 and len(payload) == 4:
                selectors.add(payload.hex())
            elif push_len == 29 and len(payload) == 29:
                # Classic solc <0.5.6 selector shift constant: 0x010000...00
                if payload[0] == 0x01 and all(b == 0 for b in payload[1:]):
                    old_dispatcher_push29 = 1
            i += push_len

    return op_counts, selectors, n_instructions, push_data_bytes, old_dispatcher_push29


def extract_token_record(address: str, hex_str: str, label: int) -> tuple[dict, Counter]:
    s = hex_str.strip()
    if s.startswith(("0x", "0X")):
        s = s[2:]
    if len(s) % 2 == 1:
        s = s[:-1]
    raw_bytes = bytes.fromhex(s)

    code_no_meta, _meta, era_info = strip_solidity_metadata(raw_bytes)
    dup_hash = hashlib.sha256(code_no_meta).hexdigest()

    op_counts, selectors, n_instr, push_data_bytes, old_disp = disassemble_bytecode(code_no_meta)

    # Additional compiler-era features from bytecode header and newer EVM opcodes (total 21 era_* features)
    era_info["era_init_6080"] = int(code_no_meta.startswith(b"\x60\x80\x60\x40\x52"))
    era_info["era_init_6060"] = int(code_no_meta.startswith(b"\x60\x60\x60\x40\x52"))
    era_info["era_old_dispatcher_push29"] = int(old_disp)
    era_info["era_has_shr"] = int(op_counts.get(0x1C, 0) > 0)
    era_info["era_has_shl"] = int(op_counts.get(0x1B, 0) > 0)
    era_info["era_has_extcodehash"] = int(op_counts.get(0x3F, 0) > 0)
    era_info["era_has_chainid"] = int(op_counts.get(0x46, 0) > 0)
    era_info["era_has_selfbalance"] = int(op_counts.get(0x47, 0) > 0)
    era_info["era_has_push0"] = int(op_counts.get(0x5F, 0) > 0)
    era_info["era_has_returndatasize"] = int(op_counts.get(0x3D, 0) > 0)

    # Size features
    size_feats = {
        "size_bytes": len(raw_bytes),
        "size_no_meta_bytes": len(code_no_meta),
        "n_instructions": n_instr,
        "n_unique_opcodes": len(op_counts),
        "n_selectors": len(selectors),
        "push_data_ratio": float(push_data_bytes) / max(len(code_no_meta), 1),
    }

    # Risky selector groups (12 groups)
    sel_feats = {}
    for gname, gset in RISKY_SELECTOR_GROUPS.items():
        matches = len(selectors & gset)
        sel_feats[gname] = int(matches > 0)
    # Enhance sel_admin_drain if SELFDESTRUCT or DELEGATECALL opcode is present
    if op_counts.get(0xFF, 0) > 0 or op_counts.get(0xF4, 0) > 0:
        sel_feats["sel_admin_drain"] = 1

    rec = {
        "address": address,
        "label": label,
        "code_hash": dup_hash,
    }
    rec.update(size_feats)
    rec.update(sel_feats)
    rec.update(era_info)
    return rec, op_counts


def main():
    os.makedirs(os.path.dirname(OUT_ALL_CSV), exist_ok=True)

    records = []
    all_op_counters = []
    seen_opcodes = set()

    with zipfile.ZipFile(RAW_ZIP) as outer:
        for inner_name, label in [("Rug-Bytecode.zip", 1), ("Normal-Bytecode.zip", 0)]:
            inner_bytes = outer.read(inner_name)
            with zipfile.ZipFile(io.BytesIO(inner_bytes)) as inner:
                members = sorted(m for m in inner.namelist() if not m.endswith("/"))
                for m in members:
                    address = os.path.splitext(os.path.basename(m))[0]
                    hex_str = inner.read(m).decode("utf-8", errors="ignore")
                    rec, op_cnt = extract_token_record(address, hex_str, label)
                    records.append(rec)
                    all_op_counters.append(op_cnt)
                    seen_opcodes.update(op_cnt.keys())

    # Build relative opcode frequency columns for all observed known EVM opcodes
    valid_ops = sorted(op for op in seen_opcodes if op in EVM_OPCODES)
    op_col_names = [f"op_{EVM_OPCODES[op]}" for op in valid_ops]

    op_matrix = np.zeros((len(records), len(valid_ops)), dtype=np.float64)
    for row_idx, (rec, op_cnt) in enumerate(zip(records, all_op_counters)):
        denom = max(rec["n_instructions"], 1)
        for col_idx, op in enumerate(valid_ops):
            if op in op_cnt:
                op_matrix[row_idx, col_idx] = op_cnt[op] / denom

    df_base = pd.DataFrame(records)
    df_ops = pd.DataFrame(op_matrix, columns=op_col_names)
    df = pd.concat([df_base, df_ops], axis=1)

    # Assign integer clone group IDs (dup_group) based on metadata-stripped SHA-256 hash
    hash_to_gid = {h: idx for idx, h in enumerate(df["code_hash"].unique())}
    df["dup_group"] = df["code_hash"].map(hash_to_gid).astype(int)
    group_sizes = df["dup_group"].map(df["dup_group"].value_counts())
    df["dup_group_size"] = group_sizes.astype(int)
    df["is_duplicate"] = (df["dup_group_size"] > 1).astype(int)

    # Identify label-conflicting clone groups (contain both label=0 and label=1)
    labels_per_group = df.groupby("dup_group")["label"].nunique()
    conflict_groups = set(labels_per_group[labels_per_group > 1].index)
    df["is_conflict_group"] = df["dup_group"].isin(conflict_groups).astype(int)
    df["is_conflict_rug"] = ((df["is_conflict_group"] == 1) & (df["label"] == 1)).astype(int)

    # Strict correctness checks
    assert len(df) == 2320, f"Expected 2320 tokens, got {len(df)}"
    assert int((df["label"] == 1).sum()) == 645, "Expected 645 rug pull tokens"
    assert int((df["label"] == 0).sum()) == 1675, "Expected 1675 benign tokens"

    # Categorize columns for downstream experiments (all / no-era / era-only / same-era)
    meta_cols = ["address", "label", "code_hash", "dup_group", "dup_group_size", "is_duplicate", "is_conflict_group", "is_conflict_rug"]
    size_cols = ["size_bytes", "size_no_meta_bytes", "n_instructions", "n_unique_opcodes", "n_selectors", "push_data_ratio"]
    selector_cols = sorted(RISKY_SELECTOR_GROUPS.keys())
    era_cols = sorted(c for c in df.columns if c.startswith("era_"))
    opcode_cols = op_col_names
    all_feature_cols = size_cols + selector_cols + era_cols + opcode_cols

    for c in all_feature_cols:
        assert pd.api.types.is_numeric_dtype(df[c]), f"Feature {c} not numeric"
        assert not df[c].isna().any(), f"Feature {c} has NaN"
        assert not np.isinf(df[c]).any(), f"Feature {c} has Inf"

    # Reorder columns cleanly
    df = df[meta_cols + all_feature_cols]
    df.to_csv(OUT_ALL_CSV, index=False)

    # Clean table for main experiment: exclude conflicting rug tokens (keeping benign clones)
    df_clean = df.loc[df["is_conflict_rug"] == 0].reset_index(drop=True)
    df_clean.to_csv(OUT_CLEAN_CSV, index=False)

    # Summary statistics to verify Week 3 findings
    old_meta_benign = float(df.loc[df["label"] == 0, "era_old_meta_any"].mean())
    old_meta_rug = float(df.loc[df["label"] == 1, "era_old_meta_any"].mean())
    n_dup_tokens = int(df["is_duplicate"].sum())
    n_conflict_groups = len(conflict_groups)
    n_conflict_tokens = int(df["is_conflict_group"].sum())
    n_conflict_rugs = int(df["is_conflict_rug"].sum())

    groups_info = {
        "dataset": "D3_RPHunter_Bytecode",
        "source_file": RAW_ZIP.replace("\\", "/"),
        "output_all": OUT_ALL_CSV.replace("\\", "/"),
        "output_clean": OUT_CLEAN_CSV.replace("\\", "/"),
        "n_tokens_total": len(df),
        "n_tokens_clean": len(df_clean),
        "label_counts_total": {"rug_pull_1": 645, "benign_0": 1675},
        "label_counts_clean": {
            "rug_pull_1": int((df_clean["label"] == 1).sum()),
            "benign_0": int((df_clean["label"] == 0).sum()),
        },
        "shortcut_stats": {
            "old_meta_share_benign": round(old_meta_benign, 4),
            "old_meta_share_rug": round(old_meta_rug, 4),
            "same_era_old_meta_counts": {
                "benign_0": int(((df_clean["label"] == 0) & (df_clean["era_old_meta_any"] == 1)).sum()),
                "rug_pull_1": int(((df_clean["label"] == 1) & (df_clean["era_old_meta_any"] == 1)).sum()),
            },
        },
        "clone_stats": {
            "n_unique_code_hashes": int(df["dup_group"].nunique()),
            "n_duplicate_tokens": n_dup_tokens,
            "n_conflict_groups": n_conflict_groups,
            "n_conflict_tokens": n_conflict_tokens,
            "n_conflict_rug_excluded": n_conflict_rugs,
        },
        "meta_columns": meta_cols,
        "feature_groups": {
            "size": size_cols,
            "selector": selector_cols,
            "era": era_cols,
            "opcode": opcode_cols,
        },
        "n_features_total": len(all_feature_cols),
    }
    with open(OUT_GROUPS_JSON, "w", encoding="utf-8") as f:
        json.dump(groups_info, f, indent=2)

    print("=== D3 FEATURE EXTRACTION & CLEANING COMPLETE ===")
    print(f"Total tokens: {len(df):,} (645 rug, 1675 benign) | Total columns: {df.shape[1]} ({len(all_feature_cols)} features)")
    print(f"Feature breakdown: size={len(size_cols)}, selector={len(selector_cols)}, era={len(era_cols)}, opcode={len(opcode_cols)}")
    print(f"Old Solidity metadata share: benign={old_meta_benign*100:.1f}% vs rug={old_meta_rug*100:.1f}%")
    print(f"Clones: {n_dup_tokens:,} tokens share code | {n_conflict_groups} conflict groups ({n_conflict_tokens} tokens, {n_conflict_rugs} rug excluded)")
    print(f"Saved: {OUT_ALL_CSV}")
    print(f"Saved: {OUT_CLEAN_CSV} ({len(df_clean):,} rows)")
    print(f"Saved: {OUT_GROUPS_JSON}")


if __name__ == "__main__":
    main()
