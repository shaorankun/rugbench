"""Download D1 (TM-RugPull) from mohamadpishdar/RugPull-Defender and inspect metadata."""
import hashlib
import json
import os
import urllib.request

REPO = "mohamadpishdar/RugPull-Defender"
OUT_DIR = os.path.join("data", "raw", "d1_tm_rugpull")
HEADERS = {"User-Agent": "RugBench-Downloader"}


def fetch_json(url: str):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    commits = fetch_json(f"https://api.github.com/repos/{REPO}/commits?per_page=1")
    sha = commits[0]["sha"]
    commit_date = commits[0]["commit"]["committer"]["date"]
    print(f"Repo: https://github.com/{REPO}")
    print(f"Latest commit: {sha} ({commit_date})")

    tree = fetch_json(f"https://api.github.com/repos/{REPO}/git/trees/{sha}?recursive=1")["tree"]
    files = [item["path"] for item in tree if item["type"] == "blob"]
    print(f"Total files in repo: {len(files)}")
    for f in files:
        print("  -", f)

    targets = [f for f in files if f == "data/dataset.xlsx"]
    downloaded = []
    for rel_path in targets:
        raw_url = f"https://raw.githubusercontent.com/{REPO}/{sha}/{urllib.request.quote(rel_path)}"
        local_name = os.path.basename(rel_path)
        local_path = os.path.join(OUT_DIR, local_name)
        print(f"\nDownloading {rel_path} -> {local_path} ...")
        req = urllib.request.Request(raw_url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=60) as resp, open(local_path, "wb") as out:
            out.write(resp.read())
        digest = sha256_file(local_path)
        size = os.path.getsize(local_path)
        print(f"  Saved: {size:,} bytes | SHA-256: {digest}")
        downloaded.append({
            "repo_path": rel_path,
            "local_path": local_path.replace("\\", "/"),
            "url": raw_url,
            "size_bytes": size,
            "sha256": digest,
        })

    manifest = {
        "dataset": "D1_TM_RugPull",
        "repo": f"https://github.com/{REPO}",
        "commit_sha": sha,
        "commit_date": commit_date,
        "files": downloaded,
    }
    manifest_path = os.path.join(OUT_DIR, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nWrote manifest: {manifest_path}")


if __name__ == "__main__":
    main()
