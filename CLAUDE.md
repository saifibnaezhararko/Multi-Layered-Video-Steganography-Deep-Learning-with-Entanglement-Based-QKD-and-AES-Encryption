# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

StegaWe91: the implementation behind the paper in the repo root, *Multi-layered security system: Integrating quantum key distribution with classical cryptography to enhance steganographic security* (Sykot et al., Alexandria Engineering Journal 121, 2025). The pipeline:

1. A CNN hides a secret image (or, since PR #1, a secret video) inside a cover.
2. Qiskit simulates the E91 QKD protocol to give Alice and Bob a shared bit key.
3. SHA-256 of that key is the AES-256 key that encrypts the stego file.
4. The file is decrypted, then the CNN reveals the secret.

Audio steganography (the `audio-steg` branch) runs in the opposite order: it **encrypts first, then hides**. The secret (any file or a text message) is AES-256-GCM encrypted with the E91-derived key, then written into a WAV cover's sample LSBs, so the transmitted file is ordinary-looking audio.

`project_description.md` is a Banglish walkthrough of the code; keep it in sync when adding features. The user writes in Banglish and English.

## Commands

Run everything from the **repository root**: modules import each other as `app.…`.

```bash
pip install -r requirements.txt            # TF>=2.20 / Keras 3, qiskit>=2.0, PyQt5, opencv-python
python -m app.ui.main                       # desktop app (PyQt5)

# video-in-video steganography (CLI)
python -m app.models.DEEP_STEGO.hide_video --cover cover.mp4 --secret secret.mp4 [--out x.avi] [--max-frames N] [--batch-size 8]
python -m app.models.DEEP_STEGO.reveal_video --stego videos/steg_video.avi [--out y.avi]

# audio steganography (CLI); the first hide runs E91 and saves the key to audio/e91_key.txt
python -m app.models.AUDIO_STEGO.hide_audio --cover cover.wav (--secret file | --message "text") [--out x.wav] [--bits 1-4] [--key-file k.txt]
python -m app.models.AUDIO_STEGO.reveal_audio --stego audio/steg_audio.wav [--out-dir dir] [--key-file k.txt]
```

There is no test suite, linter or CI. Verify changes with scripts as described under "Verifying changes".

## Architecture

### QKD + AES: `app/models/encryption/aes.py`
- **The E91 simulation runs at import time.** It builds 500 circuits and runs each with 1 shot on `BasicProvider`, which takes several seconds. It produces module globals `aliceKey`/`bobKey` (bit strings). Importing `aes` or `app.ui.main` therefore pays that cost, and **the key changes every process start**: files encrypted in an earlier session can't be decrypted.
- **Measurement bases:**
  - Alice: A1 = X (`h`), A2 = W = (X+Z)/√2 (`s,h,t,h`), A3 = Z.
  - Bob: B1 = W, B2 = Z, B3 = (Z−X)/√2 (`s,h,tdg,h`).
  - Key bits come from (A2,B1) and (A3,B2). Expect about 2/9 of 500, roughly 111 bits.
  - In the bitstrings, Alice is `cr[0]` (last character) and Bob is `cr[1]`.
- **The prepared state is Φ+ (H + CNOT), not the singlet the paper describes.** Results are therefore *correlated*, and `aliceKey == bobKey` with no bit flip. If you switch to the singlet, Bob's bits must be inverted.
- **No CHSH test is computed.** `abKeyMismatches` is counted but never used.
- **`encrypt(path, key)`:** SHA-256(key string) becomes an AES-256-CBC key. The file bytes are base64-encoded, then encrypted with a random IV that is prepended. It **overwrites the input file in place**.
- **`decrypt(path, key)`:** writes `<stem>.dec<suffix>` (`x.png` → `x.dec.png`, `x.avi` → `x.dec.avi`). Returns `(0, filename)` on success, or `(-1, None)` for a wrong key (detected via an unpad/base64 `ValueError`).
- The keys and the AES key hash are printed to stdout.

### Deep steganography: `app/models/DEEP_STEGO/`
- `models/hide.h5` and `models/reveal.h5` come from the InvisiCipher repo, the paper's ref. [31]. Their input is fixed at **224×224×3**; the batch dimension is free.
  - The hide model's inputs are ordered **`[secret, cover]`**.
  - `reveal.h5` has no noise layer, so reveal is deterministic.
- **Preprocessing must stay identical everywhere.** Use `Utils/preprocessing.py`:
  - `uint8/255` → `normalize_batch`, which uses ImageNet mean/std.
  - Model output → `denormalize_batch` (clips to [0,1]) → `*255` → `np.uint8`, which truncates rather than rounds.
  - `to_model_input` / `from_model_output` wrap both directions.
- **`hide_image.py` / `reveal_image.py`:**
  - They reload the model on every call.
  - They resize with PIL.
  - They write to the tracked `images/` folder (and `hide_image` also writes `app/steg_image.png`).
  - They import `tkinter` without using it.
- **`hide_video.py` / `reveal_video.py` + `Utils/video_io.py`:**
  - Frame i of the secret is hidden in frame i of the cover, in batches.
  - Output is 224×224, uses the cover's fps (25 if unknown), and has as many frames as the shorter video. There is no audio.
  - Output goes to `videos/`, which is gitignored.
  - An optional `progress(done, total)` callback reports progress.
  - OpenCV is BGR and the models are RGB, so `video_io` converts in both directions.
- **The stego video must be lossless.** `video_io` writes PNG-in-AVI (fourcc `"png "`, which keeps RGB24) and forces the `.avi` suffix.
  - Verified exact round trips: PNG-in-AVI, FFV1, HuffYUV.
  - `mp4v` is lossy and revealing from it is ruined (≈8.8 dB PSNR).
  - Never switch the writer to a lossy codec.
- **`train.py`** is the joint prep+hide+reveal model, with `GaussianNoise(0.1)` between hide and reveal and loss weights 1.0 (cover) and 0.75 (secret). It is **broken on TF2/Keras 3**: wrong kwarg `direc`, TF1 `tf.summary.FileWriter`/`tf.Summary`, `fit_generator`, `.next()`, and no `dataset/` folder.
- **Other leftovers:**
  - `Utils/eval.py` globs the folder instead of the images.
  - `Utils/test.py` needs scikit-image, which isn't in requirements.
  - `Utils/enhance.py` is a video-enhance script that parses argv at import.
  - `app/main_CLI_v1.py` imports modules that don't exist (`blowfish`, `ESRGAN`).

### Audio steganography: `app/models/AUDIO_STEGO/`
- **`audio_lsb.py`** (pure numpy plus the stdlib `wave` module):
  - Bits go into the low bits of each sample's least significant byte (`raw[::sampwidth]`, since WAV PCM is little-endian). This works for 8/16/24/32-bit audio, mono or stereo.
  - Which samples are used is a key-seeded shuffle: `np.random.RandomState`, seeded from `sha256("audio-lsb-positions:" + key)`.
  - Use the legacy `RandomState` deliberately: its stream is frozen across numpy versions, so hide and reveal agree on any install.
  - The shuffle allocates one `uint32` per sample.
- **Layout in shuffled order:**
  - 40 header samples at 1 LSB each: `n_lsb` (8 bits) + payload length (32 bits).
  - Then the payload at `n_lsb` (1–4) bits per sample.
  - There is no plaintext magic marker: a wrong key reads a garbage header, and `extract` raises `NoHiddenDataError`.
- **`hide_audio.py`:**
  - Plaintext is a 2-byte name length + the UTF-8 file name + the file bytes; a text message is stored as `message.txt`.
  - It is encrypted with `aes_payload.encrypt_bytes`.
  - `n_lsb=None` picks the fewest LSBs that fit; if none fit, it raises `CapacityError`.
  - It prints the SNR.
- **`reveal_audio.py`:** extracts, decrypts (`WrongKeyError` if the GCM tag fails), and writes `audio/revealed/<basename>`; the name is sanitised with `Path(name).name`.
- Outputs and key files go to `audio/`, which is gitignored.
- Only uncompressed PCM WAV is supported: `read_wav` raises `ValueError` for anything else. Lossy re-encoding destroys the payload.
- **`app/models/encryption/aes_payload.py`:**
  - In-memory AES-256-GCM, laid out as `nonce(12) + tag(16) + ciphertext`.
  - It uses the same SHA-256 key derivation as `aes.py`.
  - It does *not* import `aes`, so it doesn't trigger the E91 simulation.
- **`app/models/encryption/keyfile.py`:** `load_or_create_key(path)` runs E91 (by importing `aes`) only when the key file doesn't exist. The CLI needs this because hide and reveal run in separate processes; the GUI uses the in-session `aes.aliceKey`/`bobKey`.

### GUI: `app/ui/main.py`
- **Import order matters:** the `app.models…` imports (TensorFlow) must come **before** PyQt5, or Windows fails with a TF DLL error. Put new model imports next to the existing ones at the top.
- **Pages:** one `MainAppWindow`. Each sidebar button calls a `show_*_page()` that clears `main_layout` (`deleteLater`) and rebuilds the page.
  - Pages: Image Hide, Encryption, Decryption, Image Reveal, Video Hide, Video Reveal, Audio Hide, Audio Reveal.
  - Encrypt and decrypt call `aes.encrypt(path, aes.aliceKey)` and `aes.decrypt(path, aes.bobKey)`.
- **Long jobs** (video and audio hide/reveal) go through `start_job(func, args, on_done, error_title)`.
  - It runs `func(*args, progress=...)` in a `JobWorker(QThread)` with signals `progress(int, int)`, `done(str)` and `failed(str)`.
  - `on_done(output_path)` runs on the UI thread, called from the bound slot `on_job_done`. Connect worker signals to bound methods, not lambdas.
  - While a job runs, `set_job_controls_enabled(False)` disables the sidebar and `self.job_page_buttons`, so the page can't be torn down mid-job.
  - Each job page calls `add_job_progress_widgets(format)` and sets `job_page_buttons`.
  - `closeEvent` refuses to close while the worker runs.
- **`preview_pixmap(path)`** returns a thumbnail for an image or a video's first frame, falling back to a dummy image.
- **`show_file_in_label`** shows a revealed secret: a thumbnail for an image or video, the text for `.txt`, otherwise the name and size.
- **Pre-existing patterns to know:**
  - The older handlers end in a bare `except: QMessageBox()`, which shows nothing, so errors are silently swallowed.
  - `download_*_button` and `key_text_box*` are never created (they stay `None`), so every image hide/reveal/encrypt/decrypt raises `AttributeError` *after* doing its work, and the bare except swallows it.
  - Use `QMessageBox.critical/warning` for new error paths.
- The launch code is under `if __name__ == "__main__":`, so `MainAppWindow` can be imported in tests.

## Verifying changes

The test assets are the 256×256 JPEGs in `app/ui/test/{bird,berry,dog,flower,other}/`. Build videos from them with OpenCV:
- **Lossless 224×224 clips** for exact comparisons.
- **mp4 clips at other sizes and lengths** to exercise the resize and shortest-video paths.

Checks that proved useful:
- **Codec round trip:** write random frames with `open_lossless_writer`, read them back with `read_frames`, and require `np.array_equal`.
- **Parity:** frame 0 of `hide_video` should be pixel-identical to `hide_image` on the same 224×224 PNGs, and likewise for reveal. Redirect `hide_image.IMAGES_DIR` and `PROJECT_ROOT` (and `reveal_image.IMAGES_DIR`) to a temp dir so tracked `images/` files aren't overwritten.
- **AES round trip:** `encrypt` then `decrypt` must give a file whose SHA-256 is identical to a copy taken before encryption. A key with one bit flipped must return `(-1, None)`.
- **Headless GUI:**
  - Set `QT_QPA_PLATFORM=offscreen`.
  - Stub `sys.modules["tkinter"]` if it isn't installed.
  - Patch `QFileDialog.getOpenFileName` and the `QMessageBox` static methods: a modal box blocks forever offscreen.
  - After switching pages, call `app.sendPostedEvents(None, QEvent.DeferredDelete)`. `processEvents()` doesn't run `deleteLater`, so the old page's buttons stay findable and visible.
  - Wait for workers with a `QEventLoop` on `finished`. **Never** call `QThread.wait()` on the main thread: it deadlocks with the worker's Python code.
  - The offscreen screen is 800×600, so call `resize(1400, 800)` *after* `show()` to get realistic screenshots.
- **Audio:**
  - The repo has no audio files, so make synthetic WAV covers with numpy + `wave` (tones + noise; 8/16/24-bit, mono and stereo, a long cover for big secrets).
  - Check that round trips are byte-identical and that `getparams()` is unchanged.
  - Check that max |sample diff| ≤ 2^n_lsb − 1.
  - Check the failures:
    - a wrong key and a cover with no hidden data raise `NoHiddenDataError`
    - flipping one payload bit at a shuffled position raises `WrongKeyError`
    - an oversized secret raises `CapacityError`
    - a non-WAV cover raises `ValueError`
- Delete generated `*.cpython-313.pyc` files (only 3.12 `.pyc` files are tracked) and the `videos/` and `audio/` output before committing.

## Session history

**Review of paper vs. code** (no code changed for these):
- **CHSH:** the eavesdropper check the paper describes is not implemented.
- **Entangled state:** the code prepares Φ+ rather than the singlet.
- **Design:** encrypting the stego image means the ciphertext itself is what gets sent, so the hiding step conceals nothing.
- **Key strength:**
  - 500 singlets give about 111 key bits.
  - The paper's examples use 7–22-bit keys, which can be brute-forced.
  - SHA-256 adds no entropy.
  - The hash *is* the AES key.
- **Paper metrics:**
  - The reported UACI of 56% exceeds the 50% maximum the paper's own formula allows for a uniform cipher image.
  - The NPCR/UACI definitions are non-standard (original vs. cipher).
  - The ≈0.1 adjacent-pixel correlation is high for AES output.
  - The encrypt/decrypt timings sit at the timer's ~1 ms resolution.
  - The 6 s hide time includes model loading.
  - The notebooks that produced these metrics are not in the repo.
- **Paper hashes:** every SHA-256 value in Table 5 and §4.8 matches `hashlib.sha256(key_bits.encode())`, so the paper's results came from this code.

**PR #1 (commit 712b2e7): video-in-video steganography**:
- **New files:** `Utils/video_io.py`, `hide_video.py`, `reveal_video.py`.
- **Preprocessing:** added the `to_model_input` / `from_model_output` helpers.
- **AES:** decrypt now keeps the original file extension.
- **GUI:**
  - Video Hide and Video Reveal pages with a worker thread and progress bar.
  - Video previews on the encryption and decryption pages.
  - A visible wrong-key warning.
  - The close guard.
  - The `__main__` guard on the launch code.
- **Also:** progress-bar and disabled-button styles in `styles/style.qss`, `.gitignore` for `videos/`, and the docs.

Results (Python 3.13, TF 2.21, Keras 3.15, CPU):
- **Losslessness and parity:** the lossless round trip was exact, and the video path matched the image path exactly (max pixel difference 0).
- **Quality:** stego vs. cover averaged 32.3 dB PSNR; revealed vs. secret averaged 30.8 dB.
- **Speed:** 40 frames took about 34 s, including TensorFlow startup.
- **Mismatched inputs:** a 320×240 cover with 36 frames and a 256×256 secret with 30 frames produced a 30-frame, 224×224, 12 fps stego video.
- **AES round trip** of the stego video was byte-identical.
- **Headless GUI:** the full flow passed.

Not yet done:
- Testing on real camera footage.
- Testing on a real Windows display.

**Known open issues** (deliberately out of scope so far):
- The GUI regenerates the E91 key on every launch. The audio CLI persists it with `keyfile.py`; the GUI doesn't yet.
- `encrypt` overwrites its input.
- There is no CHSH check.
- `train.py` and `eval.py` are broken.
- `main_CLI_v1.py` imports modules that don't exist.
- Older UI handlers silently swallow errors.

**`audio-steg` branch** (stacked on PR #1): audio steganography with encrypt-then-hide.
- **New files:** `AUDIO_STEGO/{audio_lsb,hide_audio,reveal_audio}.py`, `encryption/aes_payload.py`, `encryption/keyfile.py`.
- **GUI:** Audio Hide and Audio Reveal pages. Hide takes a cover WAV and either a secret file or a typed message, and shows capacity. Reveal shows an image or the text.
- **Refactor:** the video job helpers were renamed to the generic `JobWorker`/`start_job`/`job_*`.
- **`.gitignore`:** added `audio/`.

Results (synthetic covers):
- **Round trips:** byte-identical for text, a JPEG, a WAV clip, and the 4.4 MB stego `.avi` (inside a 120 s cover, auto 4 LSBs). Covers were 8/16/24-bit.
- **SNR:**
  - 16-bit stereo at 1 LSB: 80–113 dB
  - 24-bit: about 130 dB
  - 8-bit: about 56 dB
  - 4.4 MB secret at 4 LSBs: 59 dB
- **Speed:** hiding the 4.4 MB secret took 5.7 s; reveal took 1.5 s.
- **Failure detection:** a wrong key, re-quantisation, and a single flipped payload bit were all detected.
- **CLI:** the key file works across processes.
- **Headless GUI:** the full flow passed, including the video pages after the rename.

