import numpy as np

from photo_toolkit.trip_filter import normalize, cosine


def test_embedding_helpers():
    a = normalize(np.array([1.0, 0.0], dtype=np.float32))
    b = normalize(np.array([1.0, 0.0], dtype=np.float32))
    assert abs(cosine(a, b) - 1.0) < 1e-6
