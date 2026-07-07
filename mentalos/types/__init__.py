"""
MentalOS Type Definitions
Data-Oriented Design with strict typing using NewType and Annotated arrays.
Zero OOP for business logic - only data containers.
"""

from typing import Annotated, Literal, Union
from dataclasses import dataclass
import numpy as np
from numpy.typing import NDArray

# =============================================================================
# PRIMITIVE TYPE ALIASES (NewType-style via type hints)
# =============================================================================

# Scalar types with semantic meaning
QuestionStr = str
AnswerStr = str
OperationName = Literal[
    "IDENTIFY", "TRANSFORM", "PROJECT", "MEASURE", 
    "COMPARE", "AGGREGATE", "FILTER", "MAP", "REDUCE"
]
BucketName = Literal[
    "SPATIAL", "TEMPORAL", "LOGICAL", "CAUSAL", 
    "PROBABILISTIC", "OPTIMIZATION", "SIMULATION"
]
ModelName = Literal["FCIS", "RAYTRACE", "MONTECARLO", "GRAPH"]
ToolName = Literal["NUMPY", "SCIPY", "SPATIAL_INDEX", "VECTOR_ENGINE"]

# Vector/Array types with dimension annotations
Vector2D = Annotated[NDArray[np.float64], tuple[int, int]]  # (N, 2)
Vector3D = Annotated[NDArray[np.float64], tuple[int, 3]]  # (N, 3)
Vector4D = Annotated[NDArray[np.float64], tuple[int, 4]]  # (N, 4) homogeneous
Matrix2D = Annotated[NDArray[np.float64], tuple[int, int]]  # (M, N)
TransformMatrix = Annotated[NDArray[np.float64], tuple[4, 4]]  # 4x4 homogeneous transform
Quaternion = Annotated[NDArray[np.float64], tuple[4]]  # (w, x, y, z)

# Bounded scalar types
AngleRad = Annotated[float, "radians"]
AngleDeg = Annotated[float, "degrees"]
Distance = Annotated[float, "meters"]
TimeSec = Annotated[float, "seconds"]
Probability = Annotated[float, "0.0 to 1.0"]

# =============================================================================
# DATA STRUCTURES (Dataclasses for immutability where possible)
# =============================================================================

@dataclass(frozen=True)
class SpatialPoint:
    """Immutable 3D point with optional normal and UV coordinates."""
    position: Vector3D
    normal: Union[Vector3D, None] = None
    uv: Union[Vector2D, None] = None
    material_id: int = 0


@dataclass(frozen=True)
class SpatialRay:
    """Ray definition for raytracing operations."""
    origin: Vector3D
    direction: Vector3D  # Must be normalized
    t_min: float = 0.0
    t_max: float = np.inf


@dataclass(frozen=True)
class RayHit:
    """Result of a ray-scene intersection test."""
    hit: bool
    t: float = np.inf
    point: Union[Vector3D, None] = None
    normal: Union[Vector3D, None] = None
    object_id: int = -1
    material_id: int = 0


@dataclass(frozen=True)
class Transform:
    """4x4 homogeneous transformation matrix wrapper."""
    matrix: TransformMatrix
    
    def __post_init__(self):
        if self.matrix.shape != (4, 4):
            raise ValueError("Transform matrix must be 4x4")


@dataclass(frozen=True)
class BoundingBox:
    """Axis-aligned bounding box in 3D space."""
    min_point: Vector3D
    max_point: Vector3D
    
    def __post_init__(self):
        if not (self.min_point.shape == (3,) and self.max_point.shape == (3,)):
            raise ValueError("BoundingBox requires 3D points")
        if np.any(self.max_point < self.min_point):
            raise ValueError("max_point must be >= min_point component-wise")


@dataclass(frozen=True)
class SceneObject:
    """Generic scene object with geometry and transform."""
    object_id: int
    object_type: Literal["SPHERE", "BOX", "MESH", "PLANE", "CYLINDER"]
    transform: Transform
    material_id: int
    bounds: BoundingBox
    # Geometry data stored as flat arrays for cache efficiency
    vertices: Union[Vector3D, None] = None  # For mesh types
    indices: Union[NDArray[np.int32], None] = None  # Triangle indices
    radius: Union[float, None] = None  # For spheres/cylinders
    half_extents: Union[Vector3D, None] = None  # For boxes


@dataclass(frozen=True)
class Scene:
    """Collection of scene objects with spatial acceleration structure info."""
    objects: tuple[SceneObject, ...]
    global_bounds: BoundingBox
    acceleration_type: Literal["BVH", "OCTREE", "GRID", "NONE"] = "BVH"
    # Precomputed acceleration data (opaque to core logic)
    acceleration_data: dict = None


# =============================================================================
# FCIS (Functional Cognitive Inference System) TYPES
# =============================================================================

@dataclass(frozen=True)
class CognitiveRequest:
    """Input request to the cognitive pipeline."""
    question: QuestionStr
    context_bucket: BucketName
    requested_operation: OperationName
    input_data: dict  # Type-erased data container
    parameters: dict = None


@dataclass(frozen=True)
class CognitiveState:
    """Immutable state passed through the pipeline stages."""
    request: CognitiveRequest
    identified_operation: OperationName
    selected_model: ModelName
    selected_tool: ToolName
    intermediate_results: dict
    final_answer: Union[AnswerStr, None] = None
    execution_log: tuple[str, ...] = ()


@dataclass(frozen=True)
class PipelineStage:
    """Definition of a pipeline stage with pure function signature."""
    name: str
    input_types: tuple[type, ...]
    output_types: tuple[type, ...]
    is_deterministic: bool


# =============================================================================
# COMPUTATIONAL RESULT TYPES
# =============================================================================

@dataclass(frozen=True)
class SimulationResult:
    """Result from a physics/spatial simulation."""
    success: bool
    iterations: int
    final_state: dict
    convergence_metric: float
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class SpatialQueryResult:
    """Result from spatial queries (intersection, distance, etc.)."""
    query_type: str
    results: NDArray[np.float64]  # Flattened result array
    metadata: dict = None


@dataclass(frozen=True)
class StatisticalResult:
    """Result from probabilistic/statistical computation."""
    mean: NDArray[np.float64]
    variance: NDArray[np.float64]
    samples: int
    confidence_interval: tuple[float, float]
    distribution_type: str


# =============================================================================
# API REQUEST/RESPONSE TYPES
# =============================================================================

@dataclass(frozen=True)
class APIRequest:
    """Standardized API request format."""
    endpoint: str
    method: Literal["GET", "POST", "PUT", "DELETE"]
    payload: dict
    headers: dict = None
    query_params: dict = None


@dataclass(frozen=True)
class APIResponse:
    """Standardized API response format."""
    status_code: int
    body: dict
    headers: dict = None
    error_message: Union[str, None] = None


# =============================================================================
# VALIDATION HELPERS (Pure functions)
# =============================================================================

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
    translation: Vector3D = None,
    rotation_quaternion: Quaternion = None,
    scale: Vector3D = None
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
