"""Download D2 (SolRPDS) CSV files from Hugging Face with live progress bar and quick inspection."""
import csv
import hashlib
import json
import os
import sys
import time
import urllib.request

DATASET_ID = "DeFiLab/SolRPDS"
OUT_DIR = os.path.join("data", "raw", "d2_solrpds")
HEADERS = {"User-Agent": "RugBench-Downloader"}

CSV_FILES = [
    "dataset/CSV/2021.csv",
    "dataset/CSV/2022.csv",
    "dataset/CSV/2023.csv",
    "dataset/CSV/Jan_2024-Nov_2024.csv",
]


def fetch_json(url: str):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def download_with_progress(url: str, out_path: str) -> tuple[int, str]:
    req = urllib.request.Request(url, headers=HEADERS)
    h = hashlib.sha256()
    downloaded = 0
    start = time.time()

    with urllib.request.urlopen(req, timeout=120) as resp, open(out_path, "wb") as f:
        total = int(resp.headers.get("Content-Length") or 0)
        chunk_size = 64 * 1024
        while True:
            chunk = resp.read(chunk_size)
            if not chunk:
                break
            f.write(chunk)
            h.update(chunk)
            downloaded += len(chunk)

            elapsed = max(time.time() - start, 1e-6)
            speed_mb = (downloaded / (1024 * 1024)) / elapsed
            dl_mb = downloaded / (1024 * 1024)
            if total > 0:
                pct = downloaded * 100.0 / total
                tot_mb = total / (1024 * 1024)
                filled = int(30 * downloaded // total)
                bar = "#" * filled + "-" * (30 - filled)
                sys.stdout.write(
                    f"\r  [{bar}] {pct:5.1f}% | {dl_mb:6.2f}/{tot_mb:6.2f} MB | {speed_mb:5.2f} MB/s"
                )
            else:
                sys.stdout.write(f"\r  Downloaded {dl_mb:6.2f} MB | {speed_mb:5.2f} MB/s")
            sys.stdout.flush()

    sys.stdout.write("\n")
    return downloaded, h.hexdigest()


def inspect_csvs(paths: list[str]):
    print("\n=== QUICK INSPECTION OF D2 (SolRPDS) ===")
    total_rows = 0
    all_mints = set()
    status_counts = {}
    columns = None

    for p in paths:
        with open(p, "r", encoding="utf-8", errors="replace", newline="") as f:
            reader = csv.DictReader(f)
            if columns is None:
                columns = reader.fieldnames
                print(f"Columns ({len(columns)}): {columns}")
            rows = 0
            file_mints = set()
            for row in reader:
                rows += 1
                mint = row.get("MINT") or row.get("mint") or ""
                if mint:
                    file_mints.add(mint)
                    all_mints.add(mint)
                st = row.get("INACTIVITY_STATUS") or row.get("INACTIVITY STATUS") or row.get("inactivity_status") or ""
                if st:
                    status_counts[st] = status_counts.get(st, 0) + 1
            total_rows += rows
            print(f"  - {os.path.basename(p):25s}: {rows:7,} rows | {len(file_mints):6,} unique MINTs")

    print(f"Total rows (pools): {total_rows:,}")
    print(f"Total unique MINTs (tokens): {len(all_mints):,}")
    if status_counts:
        print(f"Status distribution (by pool row): {status_counts}")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    meta = fetch_json(f"https://huggingface.co/api/datasets/{DATASET_ID}")
    sha = meta.get("sha", "main")
    print(f"Dataset: https://huggingface.co/datasets/{DATASET_ID}")
    print(f"Revision SHA: {sha}")
    print(f"Downloading {len(CSV_FILES)} CSV files (~33.55 MB total)...\n")

    downloaded_records = []
    local_paths = []

    for i, rel_path in enumerate(CSV_FILES, 1):
        fname = os.path.basename(rel_path)
        local_path = os.path.join(OUT_DIR, fname)
        url = f"https://huggingface.co/datasets/{DATASET_ID}/resolve/{sha}/{rel_path}"
        print(f"[{i}/{len(CSV_FILES)}] {fname}")
        size, digest = download_with_progress(url, local_path)
        print(f"  SHA-256: {digest}")
        downloaded_records.append({
            "repo_path": rel_path,
            "local_path": local_path.replace("\\", "/"),
            "url": url,
            "size_bytes": size,
            "sha256": digest,
        })
        local_paths.append(local_path)

    manifest = {
        "dataset": "D2_SolRPDS",
        "source": f"https://huggingface.co/datasets/{DATASET_ID}",
        "revision_sha": sha,
        "event_level_data_available": False,
        "note": "Hugging Face release contains only yearly pool-level aggregate CSV/JSON files (2021-2024); no event-level swap/liquidity logs.",
        "files": downloaded_records,
    }
    manifest_path = os.path.join(OUT_DIR, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nWrote manifest: {manifest_path}")

    inspect_csvs(local_paths)


if __name__ == "__main__":
    main()
