import argparse
from pathlib import Path

import numpy as np
from tensorflow.keras.models import load_model

from app.models.DEEP_STEGO.Utils.preprocessing import to_model_input, from_model_output
from app.models.DEEP_STEGO.Utils.progressbarCL_animation import update_progress
from app.models.DEEP_STEGO.Utils import video_io
from app.models.output_paths import free_default

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MODEL_DIR = Path(__file__).resolve().parent / "models"
VIDEOS_DIR = PROJECT_ROOT / "videos"

DEFAULT_FPS = 25.0


def hide_video(cover_video_filepath, secret_video_filepath, output_filepath=None, batch_size=8, max_frames=None,
               progress=None):
    """Hide secret video frame i inside cover video frame i.

    The stego video is 224px*224px, has the cover's frame rate and as many frames
    as the shorter video. It is written losslessly (.avi); re-encoding it with a
    lossy codec destroys the hidden video. Returns the output path.
    """
    model = load_model(str(MODEL_DIR / "hide.h5"), compile=False)

    cover_fps, cover_count, cover_w, cover_h = video_io.probe(cover_video_filepath)
    _, secret_count, secret_w, secret_h = video_io.probe(secret_video_filepath)
    print("cover video : ", cover_count, "frames,", cover_w, "x", cover_h, ",", cover_fps, "fps")
    print("secret video : ", secret_count, "frames,", secret_w, "x", secret_h)
    if cover_count != secret_count:
        print("videos have different lengths, only the first", min(cover_count, secret_count), "frames are used")

    total = min(cover_count, secret_count)
    if max_frames is not None:
        total = min(total, max_frames)
    fps = cover_fps if cover_fps and cover_fps > 0 else DEFAULT_FPS

    if output_filepath is None:
        output_filepath = free_default(VIDEOS_DIR / "steg_video.avi", (cover_video_filepath, secret_video_filepath))
    writer, output_filepath = video_io.open_lossless_writer(output_filepath, fps,
                                                            inputs=(cover_video_filepath, secret_video_filepath))

    cover_frames = video_io.read_frames(cover_video_filepath, max_frames=max_frames)
    secret_frames = video_io.read_frames(secret_video_filepath, max_frames=max_frames)

    done = 0
    try:
        cover_batch, secret_batch = [], []
        for cover_frame, secret_frame in zip(cover_frames, secret_frames):
            cover_batch.append(cover_frame)
            secret_batch.append(secret_frame)
            if len(cover_batch) == batch_size:
                done += _hide_batch(model, writer, cover_batch, secret_batch)
                cover_batch, secret_batch = [], []
                if progress:
                    progress(done, max(total, done))
        if cover_batch:
            done += _hide_batch(model, writer, cover_batch, secret_batch)
            if progress:
                progress(done, max(total, done))
    finally:
        writer.release()

    if done == 0:
        raise RuntimeError("No frames could be read from the input videos")

    print("\nSaved steg video (", done, "frames ) to", output_filepath)
    return str(output_filepath)


def _hide_batch(model, writer, cover_batch, secret_batch):
    steg_batch = model.predict([to_model_input(np.stack(secret_batch)), to_model_input(np.stack(cover_batch))],
                               verbose=0)
    video_io.write_rgb(writer, from_model_output(steg_batch))
    return len(cover_batch)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hide a secret video inside a cover video")
    parser.add_argument("--cover", required=True, help="path to cover video")
    parser.add_argument("--secret", required=True, help="path to secret video")
    parser.add_argument("--out", default=None, help="output stego video (.avi, default videos/steg_video.avi)")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--max-frames", type=int, default=None, help="only process the first N frames")
    args = parser.parse_args()

    hide_video(args.cover, args.secret, args.out, args.batch_size, args.max_frames, progress=update_progress)

'''
Sample run (from the repository root):
python -m app.models.DEEP_STEGO.hide_video --cover cover.mp4 --secret secret.mp4
'''
