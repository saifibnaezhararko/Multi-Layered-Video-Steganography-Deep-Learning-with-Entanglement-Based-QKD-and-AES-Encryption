from pathlib import Path

import cv2
import numpy as np

'''
Video helpers for frame-by-frame steganography.
OpenCV works in BGR, the stego models were trained on RGB, so every frame is
converted on the way in and on the way out.
'''

# Input size of hide.h5 / reveal.h5
MODEL_SIZE = 224

# The stego video must be stored losslessly: lossy codecs (mp4v, H.264, ...)
# destroy the hidden secret. PNG-in-AVI keeps frames as RGB24 (no chroma subsampling).
LOSSLESS_FOURCC = "png "
LOSSLESS_SUFFIX = ".avi"

VIDEO_EXTENSIONS = (".mp4", ".avi", ".mkv", ".mov", ".m4v", ".webm")


def is_video(path):
    return Path(path).suffix.lower() in VIDEO_EXTENSIONS


def probe(path):
    """Return (fps, frame_count, width, height) of a video."""
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {path}")
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    return fps, frame_count, width, height


def read_frames(path, size=MODEL_SIZE, max_frames=None):
    """Yield RGB uint8 frames resized to size x size."""
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {path}")
    count = 0
    try:
        while max_frames is None or count < max_frames:
            success, frame = cap.read()
            if not success:
                break
            if frame.shape[:2] != (size, size):
                frame = cv2.resize(frame, (size, size), interpolation=cv2.INTER_AREA)
            yield cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            count += 1
    finally:
        cap.release()


def first_frame(path):
    """Return the first frame as a full-resolution RGB array, or None."""
    cap = cv2.VideoCapture(str(path))
    success, frame = cap.read()
    cap.release()
    if not success:
        return None
    return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)


def lossless_path(path):
    """Force the lossless container suffix."""
    return Path(path).with_suffix(LOSSLESS_SUFFIX)


def open_lossless_writer(path, fps, size=MODEL_SIZE):
    """Open a lossless video writer for size x size frames."""
    path = lossless_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*LOSSLESS_FOURCC), fps, (size, size))
    if not writer.isOpened():
        raise RuntimeError(f"Could not open a lossless video writer for {path}")
    return writer, path


def write_rgb(writer, frames):
    """Write a batch of RGB uint8 frames."""
    for frame in frames:
        writer.write(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
