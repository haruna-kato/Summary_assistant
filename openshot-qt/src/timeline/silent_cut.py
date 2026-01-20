import soundfile as sf
import os
import numpy as np
from matplotlib import pyplot as plt

root_path = 'enigm_test'
thres = 0.05
src_file = os.path.join(root_path,"44.wav")

data, samplerate = sf.read(src_file)




t = np.arange(0, len(data))/samplerate

plt.figure(figsize=(18, 6))
plt.plot(t, data)
plt.show()
plt.savefig(root_path+"test_wave.jpg")

thres = 0.05
amp = np.abs(data)
b = (amp > thres)

plt.figure(figsize=(18, 6))
plt.step(t, b, linewidth=1.5)
plt.plot(t, amp)

plt.savefig(root_path+"amp.jpg")

# 無音と判定する最小時間（秒）
min_silence_duration = 0.5

# 無音区間を記録するリスト
silences = []
# 1つ前のサンプル（初期値は無音）
prev = 0
# 無音に入った位置（インデックス）
entered = 0
#現在の値（0=無音, 1=音）
for i, v in enumerate(b):
  #音から無音に変わったら entered にその位置を保存。
  if prev == 1 and v == 0: # enter silence
    entered = i
  #無音から音に戻ったとき、**無音区間の長さ（秒）**を計算。
  if prev == 0 and v == 1: # exit silence
    duration = (i - entered) / samplerate 
    #無音時間がしきい値 0.5秒 より長いときだけ、silences に保存
    if duration > min_silence_duration:
      silences.append({"from": entered, "to": i, "suffix": "cut"})
      entered = 0
  prev = v
if entered > 0 and entered < len(b):
  silences.append({"from": entered, "to": len(b), "suffix": "cut"})
# print(silences)

# デジタル信号（例：ある閾値を超えたら1、以下なら0）
digital =(amp > thres).astype(int)
# 例: 全体長さ（サンプル数）
length = len(amp)

# 1: 音、0: 無音 の信号を全て1で初期化
signal = np.zeros(length, dtype=int)


# silences区間は1にする
for s in silences:
    signal[s["from"]:s["to"]] = 1

# step関数用に値を拡張（階段をきれいに）
step_data = np.repeat(signal, 2)[1:]
step_t = np.repeat(t, 2)[1:]
plt.figure(figsize=(18, 6))
plt.step(step_t, step_data, where='post', linewidth=2)
plt.plot(t, amp)
plt.savefig(root_path+"plot.jpg")


min_keep_duration = 0.2

cut_blocks = []
blocks = silences
while 1:
  if len(blocks) == 1:
    cut_blocks.append(blocks[0])
    break

  block = blocks[0]
  next_blocks = [block]
  for i, b in enumerate(blocks):
    if i == 0:
      continue
    interval = (b["from"] - block["to"]) / samplerate
    if interval < min_keep_duration:
      block["to"] = b["to"]
      next_blocks.append(b)

  cut_blocks.append(block)
  blocks = list(filter(lambda b: b not in next_blocks, blocks))
  
keep_blocks = []
for i, block in enumerate(cut_blocks):
  if i == 0 and block["from"] > 0:
    keep_blocks.append({"from": 0, "to": block["from"], "suffix": "keep"})
  if i > 0:
    prev = cut_blocks[i - 1]
    keep_blocks.append({"from": prev["to"], "to": block["from"], "suffix": "keep"})
  if i == len(cut_blocks) - 1 and block["to"] < len(data):
    keep_blocks.append({"from": block["to"], "to": len(data), "suffix": "keep"})

import time
import subprocess
mov_file = os.path.join(root_path,"44.mp4")
padding_time = 0.2
# 出力用テキストファイルパス
list_files_path = []
# out_dir = os.path.join("silent_exp", "{}".format(int(time.time())))
# os.mkdir(out_dir)
for i, block in enumerate(keep_blocks):
  # fr = block["from"] / samplerate
  # to = block["to"] / samplerate
  # duration = to - fr
  # out_path = os.path.join("{:2d}_{}.mov".format(i, block["suffix"]))
  #空白をいれたもの
  fr = max(block["from"] / samplerate - padding_time, 0)
  to = min(block["to"] / samplerate + padding_time, len(data) / samplerate)
  duration = to - fr

  out_path = os.path.join("{:2d}_{}_padding.mov".format(i, block["suffix"]))
  # 出力用テキストファイルに追加
  list_files_path.append(out_path)
  # !ffmpeg -ss {fr} -i "{mov_file}" -t {duration} "{out_path}"
  # ffmpegコマンドを組み立てて実行
  subprocess.run([
      "ffmpeg",
      "-ss", str(fr),
      "-i", mov_file,
      "-y",
      "-t", str(duration),
      out_path
  ])

# 結合用テキストファイル
text_path = root_path+'marge_test.txt'
with open(text_path, mode='w', encoding="utf-8") as fw:
      for path in list_files_path:
        fw.write(f"file '{path}'\n")
 
# 動画の結合
save_path = root_path+'marge_padding.mov'
command_merge = ["ffmpeg", "-f", "concat", "-safe", "0", "-i", text_path, "-c", "copy", save_path]
# 実行
subprocess.run(command_merge)
