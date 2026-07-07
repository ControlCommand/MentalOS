"""
MentalOS Core Type Definitions
Data-Oriented Design with strict typing using NewType and Annotated arrays.
Zero OOP for business logic - only data containers.
"""

from typing import Annotated, Literal, Union, Optional
from dataclasses import dataclass, field
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
# SPATIAL DATA STRUCTURES
# =============================================================================

@dataclass(frozen=True)
class SpatialPoint:
    """Immutable 3D point with optional normal and UV coordinates."""
    position: Vector3D
    normal: Optional[Vector3D] = None
    uv: Optional[Vector2D] = None
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
    point: Optional[Vector3D] = None
    normal: Optional[Vector3D] = None
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
    vertices: Optional[Vector3D] = None  # For mesh types
    indices: Optional[NDArray[np.int32]] = None  # Triangle indices
    radius: Optional[float] = None  # For spheres/cylinders
    half_extents: Optional[Vector3D] = None  # For boxes


@dataclass(frozen=True)
class Scene:
    """Collection of scene objects with spatial acceleration structure info."""
    objects: tuple[SceneObject, ...]
    global_bounds: BoundingBox
    acceleration_type: Literal["BVH", "OCTREE", "GRID", "NONE"] = "BVH"
    # Precomputed acceleration data (opaque to core logic)
    acceleration_data: Optional[dict] = None


# =============================================================================
# FCIS (Functional Cognitive Inference System) TYPES
# =============================================================================

@dataclass(frozen=True)
class CognitiveRequest:
    """Input request to the cognitive pipeline."""
    question: QuestionStr
    context_bucket: BucketName
    requested_operation: OperationName
    input_data: dict
    parameters: Optional[dict] = None


@dataclass(frozen=True)
class CognitiveState:
    """Immutable state passed through the pipeline stages."""
    request: CognitiveRequest
    identified_operation: OperationName
    selected_model: ModelName
    selected_tool: ToolName
    intermediate_results: dict
    final_answer: Optional[AnswerStr] = None
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
    results: NDArray[np.float64]
    metadata: Optional[dict] = None


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
    headers: Optional[dict] = None
    query_params: Optional[dict] = None


@dataclass(frozen=True)
class APIResponse:
    """Standardized API response format."""
    status_code: int
    body: dict
    headers: Optional[dict] = None
    error_message: Optional[str] = None
