from pathlib import Path

'''
Store the shared E91 key in a file, so steps that run in separate processes
(e.g. the audio hide and reveal commands) can use the same key. Alice and Bob
get identical keys from the simulation, so one file stands for both.
Keep key files private: anyone with the file can reveal the hidden data.
'''


def load_key(path):
    key = Path(path).read_text().strip()
    if not key or set(key) - {'0', '1'}:
        raise ValueError(f"{path} does not contain an E91 key (a string of 0s and 1s)")
    return key


def save_key(path, key):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(key + '\n')


def load_or_create_key(path):
    """Load the key from path, or run the E91 simulation and save a new one there."""
    path = Path(path)
    if path.exists():
        return load_key(path)
    from app.models.encryption import aes  # importing aes runs the E91 simulation
    save_key(path, aes.aliceKey)
    print(f"New E91 key ({len(aes.aliceKey)} bits) saved to {path}")
    return aes.aliceKey
