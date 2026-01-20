import soundfile as sf
import numpy as np
import sys
import json
import os
import tempfile
import subprocess


def detect_silences(data, samplerate, threshold=0.05, min_silence_duration=0.5):
    amp = np.abs(data)
    b = (amp > threshold)
    silences = []
    prev = 0
    entered = 0
    for i, v in enumerate(b):
        if prev == 1 and v == 0:
            entered = i
        if prev == 0 and v == 1:
            duration = (i - entered) / samplerate
            if duration > min_silence_duration:
                silences.append({
                    "from": round(entered / samplerate, 3),
                    "to": round(i / samplerate, 3)
                })
                entered = 0
        prev = v
    if entered > 0 and entered < len(b):
        silences.append({
            "from": round(entered / samplerate, 3),
            "to": round(len(b) / samplerate, 3)
        })
    return silences

def is_audio_file(path):
    return os.path.splitext(path)[1].lower() in [".wav", ".flac", ".ogg"]

if __name__ == "__main__":
    FFMPEG_BIN = "/home/kato.haruna/.conda/envs/openshot/bin/ffmpeg"
    if len(sys.argv) < 2:
        print("[ERROR] No input file provided")
        sys.exit(1)

    path = sys.argv[1]

    if is_audio_file(path):
        path_to_read = path
    else:
        # 動画なら一時 wav を作成
        tmp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
        # print(f"[DEBUG] Temporary WAV path: {tmp_wav}")
        subprocess.run([
            FFMPEG_BIN, "-y", "-i", path, "-vn", "-acodec", "pcm_s16le", tmp_wav
        ], check=True)
        path_to_read = tmp_wav
        
    try:
        # 音声データ読み込み & 無音検出
        data, sr = sf.read(path_to_read)
        # ステレオ → モノラル変換（2次元配列のとき）
        if len(data.shape) > 1:
            data = data.mean(axis=1)
        result = detect_silences(data, sr)
        print(json.dumps(result), flush=True)
    finally:
        # 一時ファイル削除
        if not is_audio_file(path) and os.path.exists(tmp_wav):
            os.remove(tmp_wav)
    
            