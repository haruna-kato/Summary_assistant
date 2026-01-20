#!/usr/bin/env python3
import sys
import os
import json
import subprocess

def cut_worker(path, cut_ranges_json, mode="cut"):
    # JSON をパース
    cut_ranges = json.loads(cut_ranges_json)
    cut_ranges = sorted(cut_ranges, key=lambda x: x['start'])

    base, ext = os.path.splitext(path)
    suffix = f"_{mode}"  # "cut" or "sum"
    output_path = f"{base}{suffix}{ext}"

    # ffmpeg の filter_complex 用に残す範囲を計算
    # 例: cut_ranges = [{"start":14.6,"end":37.2},{"start":50.666,"end":50.667}]
    # 残す範囲 = [0->14.6, 37.2->50.666]
    keep_ranges = []
    prev_end = 0.0
    # 動画の長さを取得
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=duration", "-of", "default=noprint_wrappers=1:nokey=1", path],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    duration = float(result.stdout.strip())

    for r in cut_ranges:
        start, end = r['start'], r['end']
        if start > prev_end:
            keep_ranges.append((prev_end, start))
        prev_end = max(prev_end, end)
    if prev_end < duration:
        keep_ranges.append((prev_end, duration))

    # ffmpeg コマンドの構築
    inputs = []
    filter_parts = []
    for i, (start, end) in enumerate(keep_ranges):
        inputs += ["-ss", str(start), "-to", str(end), "-i", path]
        filter_parts.append(f"[{i}:v:0][{i}:a:0]")  # ビデオとオーディオ

    # concat 用フィルター
    concat_filter = "".join(filter_parts) + f"concat=n={len(keep_ranges)}:v=1:a=1[outv][outa]"

    cmd = ["ffmpeg"]
    cmd += inputs
    cmd += ["-filter_complex", concat_filter, "-map", "[outv]", "-map", "[outa]", "-y", output_path]

    print("[Worker] Running ffmpeg...")
    subprocess.run(cmd, check=True)
    print("[Worker] Exported:", output_path)
    print(output_path)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("[ERROR] Usage: cut_worker.py <file_path> <cut_ranges_json>", flush=True)
        sys.exit(1)
    path = sys.argv[1]
    cut_ranges_json = sys.argv[2]
    mode = sys.argv[3] if len(sys.argv) > 3 else "cut"
    cut_worker(path, cut_ranges_json, mode)
