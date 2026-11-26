"""Verify manually downloaded D3 (RPHunter) files, compute SHA-256 manifest, and inspect ZIP contents."""
import hashlib
import json
import os
import zipfile

SOURCE_URL = "https://figshare.com/s/e6e7cce0b6574770e7ce"
RAW_DIR = os.path.join("data", "raw", "d3_rphunter")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def inspect_zip(zip_path: str):
    with zipfile.ZipFile(zip_path) as z:
        names = [n for n in z.namelist() if not n.endswith("/")]
        print(f"    ZIP contents ({len(names)} files):")
        top_dirs = {}
        for n in names:
            parts = n.split("/")
            key = "/".join(parts[:2]) if len(parts) > 2 else parts[0]
            top_dirs[key] = top_dirs.get(key, 0) + 1
        for k, v in sorted(top_dirs.items()):
            print(f"      - {k}: {v} files")


def main():
    if not os.path.isdir(RAW_DIR):
        print(f"Directory not found: {RAW_DIR}")
        return

    files = sorted(
        f for f in os.listdir(RAW_DIR)
        if f not in (".gitkeep", "manifest.json") and os.path.isfile(os.path.join(RAW_DIR, f))
    )

    if not files:
        print(f"No downloaded files found in {RAW_DIR}.")
        print(f"Please download from: {SOURCE_URL}")
        return

    print(f"=== VERIFYING D3 (RPHunter) IN {RAW_DIR} ===")
    records = []
    for fname in files:
        fpath = os.path.join(RAW_DIR, fname)
        size = os.path.getsize(fpath)
        digest = sha256_file(fpath)
        print(f"  - {fname} ({size / (1024 * 1024):.2f} MB)")
        print(f"    SHA-256: {digest}")
        if fname.lower().endswith(".zip"):
            try:
                inspect_zip(fpath)
            except zipfile.BadZipFile:
                print("    [WARNING] Invalid ZIP archive.")
        records.append({
            "local_path": fpath.replace("\\", "/"),
            "size_bytes": size,
            "sha256": digest,
        })

    manifest = {
        "dataset": "D3_RPHunter",
        "source": SOURCE_URL,
        "download_method": "manual_browser_download",
        "files": records,
    }
    manifest_path = os.path.join(RAW_DIR, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nWrote manifest: {manifest_path}")


if __name__ == "__main__":
    main()
