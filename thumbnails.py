#!/usr/bin/env python3
import os
import requests

# —— CONFIGURE HERE ——
STREAM_ID = "d482b94481f2498e24afa6334aee4774"
BASE_URL  = f"https://customer-tx9j032qb5s3pjfo.cloudflarestream.com/{STREAM_ID}/thumbnails/thumbnail.gif"
HEIGHTS   = [64, 128, 256]
FPS_LIST  = [4, 8]
TIMEPOINTS = range(0, 21)    # 0 through 20 inclusive
DURATIONS  = range(8, 16)    # 8 through 15 inclusive

# —— MAIN LOOP ——
for height in HEIGHTS:
    for fps in FPS_LIST:
        for tp in TIMEPOINTS:
            for dur in DURATIONS:
                # build directory and filename
                out_dir = os.path.join("thumbnails", STREAM_ID, str(height), str(fps), str(tp))
                os.makedirs(out_dir, exist_ok=True)
                out_path = os.path.join(out_dir, f"{dur}.gif")

                # skip if already downloaded
                if os.path.exists(out_path):
                    continue

                # build URL with query params
                params = {
                    "time":     f"{tp}s",
                    "height":   str(height),
                    "duration": f"{dur}s",
                    "fps":      str(fps),
                }
                # requests will encode ?time=...&height=...
                resp = requests.get(BASE_URL, params=params, stream=True)
                try:
                    resp.raise_for_status()
                except requests.HTTPError as e:
                    print(f"ERROR {e} for {resp.url}")
                    continue

                # save to disk
                with open(out_path, "wb") as f:
                    for chunk in resp.iter_content(1024*64):
                        f.write(chunk)

                print(f"↓ {out_path}")

print("✅ Done.")
