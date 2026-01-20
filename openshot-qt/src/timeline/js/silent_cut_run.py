import soundfile as sf
import numpy as np
import sys
import json



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

if __name__ == "__main__":
    path = sys.argv[1]
    data, sr = sf.read(path)
    result = detect_silences(data, sr)
    print(json.dumps(result))
