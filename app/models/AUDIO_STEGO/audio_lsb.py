import hashlib
import wave
from pathlib import Path

import numpy as np

'''
LSB steganography for uncompressed PCM WAV audio.

Bits go into the least significant bits of the samples' lowest byte (WAV PCM is
little-endian, so this works the same for 8/16/24/32-bit audio). Which samples
are used is a key-seeded shuffle, so the changes are spread over the whole file
and cannot be located without the key.

Layout, in shuffled sample order:
  first HEADER_BITS samples, 1 LSB each: n_lsb (8 bits) + payload length in bytes (32 bits)
  next samples, n_lsb LSBs each:          payload bits (MSB first)
'''

HEADER_BITS = 8 + 32
MAX_LSB = 4


class CapacityError(ValueError):
    """The secret does not fit in the cover audio."""


class NoHiddenDataError(ValueError):
    """No valid hidden data for this key (wrong key, or not a stego file)."""


def read_wav(path):
    """Return (params, raw sample bytes as a writable uint8 array)."""
    try:
        with wave.open(str(path), 'rb') as wav:
            params = wav.getparams()
            frames = wav.readframes(params.nframes)
    except (wave.Error, EOFError) as e:
        raise ValueError(f"{Path(path).name}: only uncompressed PCM .wav audio is supported ({e})") from None
    return params, np.frombuffer(frames, dtype=np.uint8).copy()


def write_wav(path, params, raw):
    path = Path(path).with_suffix('.wav')
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), 'wb') as wav:
        wav.setparams(params)
        wav.writeframes(raw.tobytes())
    return path


def wav_info(path):
    """Return (duration in seconds, sample rate, channels, bits per sample, total samples)."""
    params, _ = read_wav(path)
    return (params.nframes / params.framerate, params.framerate, params.nchannels, 8 * params.sampwidth,
            params.nframes * params.nchannels)


def samples_as_int(raw, sampwidth):
    """Decode raw little-endian PCM bytes to signed integers (for quality metrics)."""
    if sampwidth == 1:
        return raw.astype(np.int16) - 128
    if sampwidth in (2, 4):
        return np.frombuffer(raw, dtype=f'<i{sampwidth}')
    padded = raw.reshape(-1, sampwidth).astype(np.int32)
    values = padded[:, 0] | (padded[:, 1] << 8) | (padded[:, 2] << 16)
    return (values ^ 0x800000) - 0x800000


def sum_squares(values, chunk=1 << 20):
    """Sum of squares in float64, chunked to keep memory low on long audio."""
    total = 0.0
    for start in range(0, len(values), chunk):
        part = values[start:start + chunk].astype(np.float64)
        total += float(part @ part)
    return total


def payload_capacity(n_samples, n_lsb):
    """Largest payload (bytes) that fits in n_samples using n_lsb bits per sample."""
    return max(0, (n_samples - HEADER_BITS) * n_lsb // 8)


def _sample_order(key, n_samples):
    seed = np.frombuffer(hashlib.sha256(b"audio-lsb-positions:" + key.encode()).digest(), dtype=np.uint32)
    order = np.arange(n_samples, dtype=np.uint32)
    # RandomState's stream is frozen across numpy versions, so hide and reveal agree on any install
    np.random.RandomState(seed).shuffle(order)
    return order


def embed(raw, sampwidth, payload, key, n_lsb):
    """Write payload into raw (in place)."""
    if not 1 <= n_lsb <= MAX_LSB:
        raise ValueError(f"n_lsb must be between 1 and {MAX_LSB}")
    low = raw[::sampwidth]  # view of each sample's least significant byte
    if payload_capacity(low.size, n_lsb) < len(payload):
        raise CapacityError(f"Payload of {len(payload)} bytes does not fit in {low.size} samples at {n_lsb} LSB(s)")

    bits = np.unpackbits(np.frombuffer(payload, dtype=np.uint8))
    bits = np.concatenate([bits, np.zeros(-len(bits) % n_lsb, dtype=np.uint8)])
    values = np.zeros(len(bits) // n_lsb, dtype=np.uint8)
    for column in bits.reshape(-1, n_lsb).T:
        values = (values << 1) | column

    header = np.unpackbits(np.frombuffer(bytes([n_lsb]) + len(payload).to_bytes(4, 'big'), dtype=np.uint8))

    order = _sample_order(key, low.size)
    header_pos = order[:HEADER_BITS]
    payload_pos = order[HEADER_BITS:HEADER_BITS + len(values)]
    low[header_pos] = (low[header_pos] & 0xFE) | header
    low[payload_pos] = (low[payload_pos] & ((0xFF << n_lsb) & 0xFF)) | values


def extract(raw, sampwidth, key):
    """Read the payload hidden with embed(); raises NoHiddenDataError if there is none for this key."""
    low = raw[::sampwidth]
    if low.size <= HEADER_BITS:
        raise NoHiddenDataError("Audio is too short to contain hidden data")

    order = _sample_order(key, low.size)
    header = low[order[:HEADER_BITS]] & 1
    n_lsb = int(np.packbits(header[:8])[0])
    length = int.from_bytes(np.packbits(header[8:]).tobytes(), 'big')
    if not 1 <= n_lsb <= MAX_LSB or length == 0 or length > payload_capacity(low.size, n_lsb):
        raise NoHiddenDataError("No hidden data found for this key (wrong key, or the audio was modified)")

    count = -(-length * 8 // n_lsb)
    values = low[order[HEADER_BITS:HEADER_BITS + count]] & ((1 << n_lsb) - 1)
    bits = ((values[:, None] >> np.arange(n_lsb - 1, -1, -1, dtype=np.uint8)) & 1).ravel()[:length * 8]
    return np.packbits(bits).tobytes()
