# Video Frame Extractor

A cross-platform Python 3.10+ command-line tool that streams video through OpenCV, selects frames for model training, filters low-quality and near-duplicate images, records audit metadata, and optionally creates a CVAT-ready ZIP. It requires no GPU and does not load the full video into memory.

## Installation

### Ubuntu/Linux

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip
git clone https://github.com/Harsh-Kumar-Sharma/extract_frames_tool.git
cd video-frame-extractor
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
pip install -r requirements.txt
```

### Windows PowerShell

```powershell
git clone https://github.com/Harsh-Kumar-Sharma/extract_frames_tool.git
cd video-frame-extractor
py -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Quick start

Default extraction is one frame per second with blur and brightness filtering enabled:

```bash
python extract_frames.py --video "/path/to/video.mp4" --output "./output"
```

Only one selection mode can be supplied: `--fps`, `--interval`, or `--every-n-frames`. Run `python extract_frames.py --help` for every option.

### Ubuntu examples

```bash
python3 extract_frames.py \
  --video "/home/harsh/videos/highway.mp4" \
  --output "/home/harsh/datasets/highway_frames" \
  --fps 1 \
  --create-cvat-zip

python3 extract_frames.py \
  --video "/home/harsh/videos/traffic.mp4" \
  --output "/home/harsh/datasets/traffic" \
  --fps 2 \
  --min-sharpness 100 \
  --min-brightness 30 \
  --remove-duplicates \
  --duplicate-threshold 5 \
  --jpeg-quality 95 \
  --create-cvat-zip

python3 extract_frames.py \
  --video "/home/harsh/videos/traffic.mp4" \
  --output "/home/harsh/datasets/traffic_part" \
  --fps 1 \
  --start-time "00:10:00" \
  --end-time "00:30:00" \
  --create-cvat-zip
```

### Windows PowerShell examples

```powershell
python .\extract_frames.py `
  --video "D:\Videos\highway.mp4" `
  --output "D:\Datasets\highway_frames" `
  --fps 1 `
  --create-cvat-zip

python .\extract_frames.py `
  --video "D:\Videos\traffic.mp4" `
  --output "D:\Datasets\traffic" `
  --fps 2 `
  --min-sharpness 100 `
  --min-brightness 30 `
  --remove-duplicates `
  --duplicate-threshold 5 `
  --jpeg-quality 95 `
  --create-cvat-zip

python .\extract_frames.py --video "D:\Videos\traffic.mp4" --output "D:\Datasets\traffic" --fps 2 --remove-duplicates --create-cvat-zip
```

### Selection and ROI examples

```bash
# One frame every five seconds
python extract_frames.py --video "traffic.mp4" --output "./frames" --interval 5

# Every 60th decoded source frame
python extract_frames.py --video "traffic.mp4" --output "./frames" --every-n-frames 60

# Use the ROI only for quality checks; saved images remain complete
python extract_frames.py --video "traffic.mp4" --output "./frames" --fps 2 --roi "100,200,1800,900" --remove-duplicates
```

Use `--width` or `--height` to preserve aspect ratio. With both dimensions, `--resize-mode fit` (default) fits inside the box without padding; `stretch` forces the exact dimensions. Use `--format png` for lossless output.

## Safe output behavior

The tool writes `images/`, `metadata/frames.csv`, `metadata/skipped_frames.csv`, `metadata/summary.json`, and `logs/extraction.log`. Existing extracted images are protected by default. `--overwrite` removes only these tool-generated directories and `cvat_upload.zip`; it never deletes the selected output directory or its unrelated files. `--resume` reads the CSVs and skips source frame numbers already handled.

Use `--dry-run` to inspect video metadata, expected frame count, filters, output destination, and a conservative storage estimate without creating anything. Ctrl+C closes the capture and writes partial CSV and summary data before returning exit code 6.

## CVAT upload

1. Run extraction with `--create-cvat-zip` (add `--zip-with-metadata` if desired).
2. Open CVAT and create a project or task.
3. Configure vehicle or other labels.
4. Upload `output/cvat_upload.zip` in the task data section.
5. Confirm images appear in sequential order.
6. Start manual or automatic annotation.
7. Export annotations in YOLO format after labeling.

Review the images before labeling: automatic filtering improves a dataset but cannot guarantee every image is useful.

## Testing and quality checks

```bash
pip install -r requirements-dev.txt
pytest -v
pytest --cov=frame_extractor --cov-report=term-missing
ruff check .
mypy frame_extractor
```

## Exit codes and codec notes

`0` success, `1` general error, `2` invalid arguments, `3` video error, `4` output error, `5` insufficient storage, and `6` interrupted. Standard MP4, AVI, MOV, MKV, and MPEG support depends on codecs bundled with the installed OpenCV wheel. If OpenCV cannot decode a file, install FFmpeg or convert the video to H.264 MP4. CUDA is not used or required.

`--workers` is accepted for deployment/config compatibility. Extraction intentionally retains ordered single-stream processing because random-access decoding and duplicate filtering are sequential; increasing it currently does not alter output or memory use.
