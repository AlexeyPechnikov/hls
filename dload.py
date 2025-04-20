#!/usr/bin/env python3.13

import sys
import os
import requests
import urllib.parse

# ——— 0) Read the master URL from argv ———
if len(sys.argv) < 2:
    print(f"Usage: {os.path.basename(sys.argv[0])} <master_playlist_url>")
    sys.exit(1)

raw_master = sys.argv[1]
MASTER_URL = raw_master.replace("\u2011", "-")   # normalize hyphens

# ——— 1) Figure out the parent‑ID folder name ———
# e.g. path "/d482.../manifest/video.m3u8" → ["d482...", "manifest", "video.m3u8"]
master_path = urllib.parse.urlparse(MASTER_URL).path.lstrip("/").split("/")
parent_id   = master_path[0]                    # "d482b94481f2498e24afa6334aee4774"
root_dir    = parent_id

# ——— Prepare directories ———
manifest_dir = os.path.join(root_dir, "manifest")
os.makedirs(manifest_dir, exist_ok=True)

# ——— Session headers to avoid 403s ———
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/119.0.0.0 Safari/537.36"
    ),
    # sometimes needed for Cloudflare‑protected streams
    "Referer": f"https://{urllib.parse.urlparse(MASTER_URL).netloc}/"
}
sess = requests.Session()
sess.headers.update(HEADERS)

# ——— 2) Download & save master playlist ———
r = sess.get(MASTER_URL); r.raise_for_status()
master_lines = r.text.splitlines()

master_file = os.path.join(manifest_dir, "video.m3u8")
print(f"↓ {master_file}")
with open(master_file, "w") as f:
    f.write("\n".join(master_lines))

# ——— 3) Collect every variant URI ———
variant_uris = []
for idx, line in enumerate(master_lines):
    if line.startswith("#EXT-X-MEDIA"):
        uri = line.split("URI=")[1].split(",")[0].strip().strip('"')
        variant_uris.append(uri)
    elif line.startswith("#EXT-X-STREAM-INF"):
        variant_uris.append(master_lines[idx+1].strip())

# remove duplicates, keep order
variant_uris = list(dict.fromkeys(variant_uris))

# ——— 4) For each variant, save its playlist + all .ts chunks ———
for uri in variant_uris:
    base = uri.split("?",1)[0]
    vname = os.path.basename(base)                    # e.g. stream_t…449.m3u8
    vpath = os.path.join(manifest_dir, vname)
    vurl  = urllib.parse.urljoin(MASTER_URL, uri)

    print(f"\n↓ {vpath}")
    rv = sess.get(vurl); rv.raise_for_status()
    lines = rv.text.splitlines()

    # write the variant playlist
    with open(vpath, "w") as f:
        f.write("\n".join(lines))

    # download each segment under root_dir/<parent_id>/*
    for ln in lines:
        if ln.startswith("#"):
            continue
        seg_uri = ln.strip()
        seg_url = urllib.parse.urljoin(vurl, seg_uri)

        # e.g. "/d482.../audio/131/seg_1.ts"
        parts = urllib.parse.urlparse(seg_url).path.lstrip("/").split("/")
        local_path = os.path.join(*parts)  # this starts with parent_id

        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        if not os.path.exists(local_path):
            print(f"→ {local_path}")
            with sess.get(seg_url, stream=True) as seg_r:
                seg_r.raise_for_status()
                with open(local_path, "wb") as outf:
                    for chunk in seg_r.iter_content(chunk_size=1<<20):
                        outf.write(chunk)

print(f"\n✅ All playlists in `{manifest_dir}/` and segments in `{root_dir}/…` are ready for your CDN.")
