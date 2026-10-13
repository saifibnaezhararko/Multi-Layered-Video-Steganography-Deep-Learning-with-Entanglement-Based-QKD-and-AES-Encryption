import hashlib

from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

'''
AES-256-GCM for in-memory payloads (used by audio steganography).
Same key derivation as aes.py: the E91 key bit string is hashed with SHA-256.
GCM authenticates the data, so a wrong key or a modified payload is detected
instead of producing garbage. This module does not run the E91 simulation.
'''

NONCE_SIZE = 12
TAG_SIZE = 16
OVERHEAD = NONCE_SIZE + TAG_SIZE


class WrongKeyError(ValueError):
    """Raised when the key is wrong or the encrypted payload was modified."""


def derive_key(key):
    return hashlib.sha256(key.encode()).digest()


def encrypt_bytes(data, key):
    """Return nonce + tag + ciphertext."""
    nonce = get_random_bytes(NONCE_SIZE)
    cipher = AES.new(derive_key(key), AES.MODE_GCM, nonce=nonce)
    ciphertext, tag = cipher.encrypt_and_digest(data)
    return nonce + tag + ciphertext


def decrypt_bytes(blob, key):
    if len(blob) < OVERHEAD:
        raise WrongKeyError("Encrypted payload is too short")
    nonce, tag, ciphertext = blob[:NONCE_SIZE], blob[NONCE_SIZE:OVERHEAD], blob[OVERHEAD:]
    cipher = AES.new(derive_key(key), AES.MODE_GCM, nonce=nonce)
    try:
        return cipher.decrypt_and_verify(ciphertext, tag)
    except ValueError:
        raise WrongKeyError("Wrong key, or the data was modified") from None
