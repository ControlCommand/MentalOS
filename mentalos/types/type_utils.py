"""
MentalOS Type Utilities
Helper functions for type validation and transformation.
Pure functions only - no side effects.
"""

import numpy as np
from numpy.typing import NDArray
from typing import Optional

from mentalos.types.core_types import Vector3D, Quaternion, TransformMatrix


def validate_vector(v: NDArray, expected_dim: int) -> bool:
    """Validate vector dimensionality."""
    return v.ndim == 1 and v.shape[0] == expected_dim


def validate_matrix(m: NDArray, expected_shape: tuple[int, int]) -> bool:
    """Validate matrix dimensions."""
    return m.ndim == 2 and m.shape == expected_shape


def normalize_vector(v: Vector3D) -> Vector3D:
    """Normalize a 3D vector (pure function)."""
    norm = np.linalg.norm(v)
    if norm < 1e-10:
        raise ValueError("Cannot normalize zero-length vector")
    return v / norm


def create_transform_matrix(
    translation: Optional[Vector3D] = None,
    rotation_quaternion: Optional[Quaternion] = None,
    scale: Optional[Vector3D] = None
) -> TransformMatrix:
    """Create a 4x4 homogeneous transform matrix from components."""
    matrix = np.eye(4, dtype=np.float64)
    
    if translation is not None:
        matrix[:3, 3] = translation
    
    if scale is not None:
        matrix[0, 0] = scale[0]
        matrix[1, 1] = scale[1]
        matrix[2, 2] = scale[2]
    
    if rotation_quaternion is not None:
        w, x, y, z = rotation_quaternion
        # Convert quaternion to rotation matrix
        matrix[0, 0] = 1 - 2*y*y - 2*z*z
        matrix[0, 1] = 2*x*y - 2*z*w
        matrix[0, 2] = 2*x*z + 2*y*w
        matrix[1, 0] = 2*x*y + 2*z*w
        matrix[1, 1] = 1 - 2*x*x - 2*z*z
        matrix[1, 2] = 2*y*z - 2*x*w
        matrix[2, 0] = 2*x*z - 2*y*w
        matrix[2, 1] = 2*y*z + 2*x*w
        matrix[2, 2] = 1 - 2*x*x - 2*y*y
    
    return matrix
