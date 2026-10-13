import argparse
from pathlib import Path

import numpy as np

from app.models.AUDIO_STEGO import audio_lsb
from app.models.encryption import aes_payload
from app.models.encryption.keyfile import load_or_create_key
from app.models.output_paths import append_suffix, ensure_not_input, free_default

PROJECT_ROOT = Path(__file__).resolve().parents[3]
AUDIO_DIR = PROJECT_ROOT / "audio"
DEFAULT_KEY_FILE = AUDIO_DIR / "e91_key.txt"

MESSAGE_FILENAME = "message.txt"


def pack_secret(name, data):
    """Plaintext layout: name length (2 bytes) + UTF-8 file name + file bytes."""
    name = name.encode('utf-8')
    return len(name).to_bytes(2, 'big') + name + data


def hide_audio(cover_audio_filepath, secret_filepath, key, output_filepath=None, message=None, n_lsb=None,
               progress=None):
    """Encrypt a secret file (or a text message) with the E91 key and hide it in a WAV cover.

    The secret is AES-256-GCM encrypted first, then written into the cover's sample
    LSBs. n_lsb=None picks the fewest LSBs per sample (1-4) that fit. The stego
    audio must stay .wav: lossy formats (mp3, aac, ...) destroy the hidden data.
    Returns the output path.
    """
    if (secret_filepath is None) == (message is None):
        raise ValueError("Give either a secret file or a text message")
    if secret_filepath is not None:
        secret_name, secret_data = Path(secret_filepath).name, Path(secret_filepath).read_bytes()
    else:
        secret_name, secret_data = MESSAGE_FILENAME, message.encode('utf-8')

    if output_filepath is None:
        output_filepath = free_default(AUDIO_DIR / "steg_audio.wav", (cover_audio_filepath, secret_filepath))
    output_filepath = append_suffix(output_filepath, '.wav')
    ensure_not_input(output_filepath, (cover_audio_filepath, secret_filepath))

    params, raw = audio_lsb.read_wav(cover_audio_filepath)
    n_samples = params.nframes * params.nchannels
    print("cover audio : ", round(params.nframes / params.framerate, 2), "s,", params.framerate, "Hz,",
          params.nchannels, "channel(s),", 8 * params.sampwidth, "bit")

    if n_lsb is not None and not 1 <= n_lsb <= audio_lsb.MAX_LSB:
        raise ValueError(f"n_lsb must be between 1 and {audio_lsb.MAX_LSB}")

    payload = aes_payload.encrypt_bytes(pack_secret(secret_name, secret_data), key)
    overhead = len(payload) - len(secret_data)

    def fits(n):
        return audio_lsb.payload_capacity(n_samples, n) >= len(payload)

    def max_secret(n):
        return max(0, audio_lsb.payload_capacity(n_samples, n) - overhead)

    if n_lsb is None:
        fitting = [n for n in range(1, audio_lsb.MAX_LSB + 1) if fits(n)]
        if not fitting:
            raise audio_lsb.CapacityError(
                f"Secret is {len(secret_data)} bytes but this cover holds at most {max_secret(audio_lsb.MAX_LSB)} "
                f"bytes (at {audio_lsb.MAX_LSB} LSBs per sample). Use a longer cover audio.")
        n_lsb = fitting[0]
    elif not fits(n_lsb):
        raise audio_lsb.CapacityError(
            f"Secret is {len(secret_data)} bytes but this cover holds at most {max_secret(n_lsb)} bytes "
            f"at {n_lsb} LSB(s) per sample. Use more LSBs per sample or a longer cover audio.")

    # SNR against the cover's AC energy: a DC offset is inaudible and would inflate it
    signal = audio_lsb.ac_energy(audio_lsb.samples_as_int(raw, params.sampwidth), params.nchannels)
    cover_low = raw[::params.sampwidth].astype(np.int16)
    audio_lsb.embed(raw, params.sampwidth, payload, key, n_lsb)
    # Only each sample's lowest byte changes, so its difference is the sample difference
    noise = audio_lsb.sum_squares(raw[::params.sampwidth] - cover_low)

    output_filepath = audio_lsb.write_wav(output_filepath, params, raw)

    snr = "inf" if noise == 0 else "-inf" if signal == 0 else f"{10 * np.log10(signal / noise):.1f}"
    print(f"hid {secret_name} ({len(secret_data)} bytes) using {n_lsb} LSB(s) per sample, SNR {snr} dB")
    print("Saved steg audio to", output_filepath)
    if progress:
        progress(1, 1)
    return str(output_filepath)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Encrypt a secret with the E91 key and hide it in a WAV file")
    parser.add_argument("--cover", required=True, help="cover audio (uncompressed PCM .wav)")
    secret = parser.add_mutually_exclusive_group(required=True)
    secret.add_argument("--secret", help="secret file to hide (any type)")
    secret.add_argument("--message", help="secret text message to hide")
    parser.add_argument("--out", default=None, help="output stego audio (.wav, default audio/steg_audio.wav)")
    parser.add_argument("--key-file", default=str(DEFAULT_KEY_FILE),
                        help="E91 key file; created with a new E91 key if it does not exist")
    parser.add_argument("--bits", type=int, default=None, choices=range(1, audio_lsb.MAX_LSB + 1),
                        help="LSBs per sample (default: fewest that fit)")
    args = parser.parse_args()

    hide_audio(args.cover, args.secret, load_or_create_key(args.key_file), args.out, args.message, args.bits)

'''
Sample run (from the repository root):
python -m app.models.AUDIO_STEGO.hide_audio --cover cover.wav --secret secret.png
python -m app.models.AUDIO_STEGO.hide_audio --cover cover.wav --message "meet at 5"
'''
