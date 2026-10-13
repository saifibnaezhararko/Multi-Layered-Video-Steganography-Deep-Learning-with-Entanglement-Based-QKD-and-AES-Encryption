import numpy as np


# Preprocessing functions
def normalize_batch(images):
    """Performs channel-wise z-score normalization"""

    return (images - np.array([0.485, 0.456, 0.406])) / np.array([0.229, 0.224, 0.225])


def denormalize_batch(images, should_clip=True):
    """Denormalize the images for prediction"""

    images = (images * np.array([0.229, 0.224, 0.225])) + np.array([0.485, 0.456, 0.406])

    if should_clip:
        images = np.clip(images, 0, 1)
    return images


def to_model_input(images):
    """uint8 RGB batch -> normalized model input (same steps as hide_image/reveal_image)"""

    return normalize_batch(np.asarray(images) / 255.0)


def from_model_output(images):
    """Model output -> uint8 RGB batch (same steps as hide_image/reveal_image)"""

    return np.uint8(denormalize_batch(images) * 255.0)
