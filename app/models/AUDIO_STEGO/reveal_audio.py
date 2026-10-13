import argparse
import re
from pathlib import Path

from app.models.AUDIO_STEGO import audio_lsb
from app.models.encryption import aes_payload
from app.models.encryption.keyfile import load_key

PROJECT_ROOT = Path(__file__).resolve().parents[3]
AUDIO_DIR = PROJECT_ROOT / "audio"
DEFAULT_KEY_FILE = AUDIO_DIR / "e91_key.txt"


FALLBACK_NAME = "secret.bin"
INVALID_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
WINDOWS_RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
MAX_NAME_BYTES = 150


def safe_filename(name):
    """A file name that is valid on Windows, macOS and Linux and stays inside the output folder.

    The name was stored by whoever hid the secret, possibly on another OS, so it is not trusted.
    """
    name = re.split(r'[/\\]', name)[-1]  # last path component, whatever the separator
    name = INVALID_CHARS.sub('_', name).rstrip(' .')  # Windows drops trailing dots/spaces; ':' would open an ADS
    if not name or name.split('.')[0].upper() in WINDOWS_RESERVED:
        return FALLBACK_NAME
    if len(name.encode('utf-8')) > MAX_NAME_BYTES:
        suffix = Path(name).suffix
        return "secret" + suffix if 0 < len(suffix.encode('utf-8')) <= 16 else FALLBACK_NAME
    return name


def unpack_secret(plaintext):
    name_length = int.from_bytes(plaintext[:2], 'big')
    name = plaintext[2:2 + name_length].decode('utf-8', errors='replace')
    return safe_filename(name), plaintext[2 + name_length:]


def reveal_audio(stego_audio_filepath, key, output_dir=None, progress=None):
    """Extract and decrypt the secret hidden by hide_audio(). Returns the revealed file's path.

    Raises audio_lsb.NoHiddenDataError or aes_payload.WrongKeyError when the key
    is wrong or the audio holds no (intact) hidden data.
    """
    params, raw = audio_lsb.read_wav(stego_audio_filepath)
    payload = audio_lsb.extract(raw, params.sampwidth, key)
    secret_name, secret_data = unpack_secret(aes_payload.decrypt_bytes(payload, key))

    output_dir = Path(output_dir) if output_dir is not None else AUDIO_DIR / "revealed"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_filepath, i = output_dir / secret_name, 1
    while output_filepath.is_dir():
        output_filepath, i = output_dir / f"{Path(secret_name).stem}_{i}{Path(secret_name).suffix}", i + 1
    output_filepath.write_bytes(secret_data)

    print(f"Revealed {secret_name} ({len(secret_data)} bytes) to {output_filepath}")
    if progress:
        progress(1, 1)
    return str(output_filepath)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reveal and decrypt the secret hidden in a WAV file")
    parser.add_argument("--stego", required=True, help="stego audio (.wav)")
    parser.add_argument("--out-dir", default=None, help="folder for the revealed file (default audio/revealed)")
    parser.add_argument("--key-file", default=str(DEFAULT_KEY_FILE), help="E91 key file used when hiding")
    args = parser.parse_args()
    if not Path(args.key_file).exists():
        parser.error(f"key file {args.key_file} not found (use the key file that hide_audio created)")

    reveal_audio(args.stego, load_key(args.key_file), args.out_dir)

'''
Sample run (from the repository root):
python -m app.models.AUDIO_STEGO.reveal_audio --stego audio/steg_audio.wav
'''
