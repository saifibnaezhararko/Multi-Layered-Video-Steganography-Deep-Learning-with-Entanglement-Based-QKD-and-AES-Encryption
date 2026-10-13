import argparse
from pathlib import Path

import numpy as np
from tensorflow.keras.models import load_model

from app.models.DEEP_STEGO.Utils.preprocessing import to_model_input, from_model_output
from app.models.DEEP_STEGO.Utils.progressbarCL_animation import update_progress
from app.models.DEEP_STEGO.Utils import video_io

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MODEL_DIR = Path(__file__).resolve().parent / "models"
VIDEOS_DIR = PROJECT_ROOT / "videos"

DEFAULT_FPS = 25.0


def reveal_video(stego_video_filepath, output_filepath=None, batch_size=8, max_frames=None, progress=None):
    """Reveal the secret video hidden frame-by-frame in a stego video. Returns the output path."""
    model = load_model(str(MODEL_DIR / "reveal.h5"), compile=False)

    fps, total, width, height = video_io.probe(stego_video_filepath)
    print("stego video : ", total, "frames,", width, "x", height, ",", fps, "fps")
    if (width, height) != (video_io.MODEL_SIZE, video_io.MODEL_SIZE):
        print("stego video was resized to 224px * 224px")
    if max_frames is not None:
        total = min(total, max_frames)
    fps = fps if fps and fps > 0 else DEFAULT_FPS

    if output_filepath is None:
        output_filepath = VIDEOS_DIR / "secret_out_video.avi"
    writer, output_filepath = video_io.open_lossless_writer(output_filepath, fps, inputs=(stego_video_filepath,))

    done = 0
    try:
        batch = []
        for frame in video_io.read_frames(stego_video_filepath, max_frames=max_frames):
            batch.append(frame)
            if len(batch) == batch_size:
                done += _reveal_batch(model, writer, batch)
                batch = []
                if progress:
                    progress(done, max(total, done))
        if batch:
            done += _reveal_batch(model, writer, batch)
            if progress:
                progress(done, max(total, done))
    finally:
        writer.release()

    if done == 0:
        raise RuntimeError("No frames could be read from the stego video")

    print("\nSaved revealed video (", done, "frames ) to", output_filepath)
    return str(output_filepath)


def _reveal_batch(model, writer, batch):
    secret_batch = model.predict([to_model_input(np.stack(batch))], verbose=0)
    video_io.write_rgb(writer, from_model_output(secret_batch))
    return len(batch)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reveal the secret video hidden in a stego video")
    parser.add_argument("--stego", required=True, help="path to stego video")
    parser.add_argument("--out", default=None, help="output video (.avi, default videos/secret_out_video.avi)")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--max-frames", type=int, default=None, help="only process the first N frames")
    args = parser.parse_args()

    reveal_video(args.stego, args.out, args.batch_size, args.max_frames, progress=update_progress)

'''
Sample run (from the repository root):
python -m app.models.DEEP_STEGO.reveal_video --stego videos/steg_video.avi
'''
