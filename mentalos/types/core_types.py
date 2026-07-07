"""
MentalOS Type Definitions
Strictly typed data structures for the cognitive pipeline.
No business logic here - only data containers.
"""

from __future__ import annotations
from typing import Literal, Optional, List, Dict, Any, Union
from dataclasses import dataclass, field
import numpy as np
from numpy.typing import NDArray
from typing_extensions import Annotated

# Type Aliases for strict typing
Vector2D = Annotated[NDArray[np.float64], "Shape[2]"]
Vector3D = Annotated[NDArray[np.float64], "Shape[3]"]
Vector4D = Annotated[NDArray[np.float64], "Shape[4]"]
Matrix2x2 = Annotated[NDArray[np.float64], "Shape[2,2]"]
Matrix3x3 = Annotated[NDArray[np.float64], "Shape[3,3]"]
Matrix4x4 = Annotated[NDArray[np.float64], "Shape[4,4]"]
TransformMatrix = Matrix4x4
Quaternion = Annotated[NDArray[np.float64], "Shape[4]"]

# Primary Operations (The 5 Verbs)
PrimaryOperation = Literal["accumulate", "transform", "scale", "estimate", "differentiate"]

# Cognitive Buckets (6 Domains)
Bucket = Literal["accumulation", "transformation", "geometry", "kinematics", "dynamics", "conservation"]

# Models (Physics/Math Frameworks)
Model = Literal[
    "work_energy_theorem",
    "newton_second_law",
    "kinematics_equations",
    "conservation_momentum",
    "conservation_energy",
    "thermodynamics_first_law",
    "thermodynamics_second_law",
    "wave_equation",
    "coulomb_law",
    "ohm_law",
    "gravitation_law",
    "projectile_motion",
    "circular_motion",
    "simple_harmonic_motion"
]

# Tools (Mathematical Methods)
Tool = Literal[
    "trigonometry",
    "vector_algebra",
    "calculus_derivative",
    "calculus_integral",
    "linear_algebra",
    "differential_equations",
    "statistics",
    "algebraic_manipulation"
]

# Question Part Identifier
QuestionPart = Literal["a", "b", "c", "d", "e", "f", "g", "h"]


@dataclass(frozen=True)
class ExtractedValue:
    """Immutable extracted value from problem statement."""
    name: str
    value: float
    unit: str
    confidence: float = 1.0


@dataclass(frozen=True)
class VectorData:
    """Immutable vector data structure."""
    magnitude: float
    direction_degrees: float
    components: Optional[Vector2D] = None
    
    def __post_init__(self):
        if self.components is None:
            theta_rad = np.deg2rad(self.direction_degrees)
            comp = np.array([
                self.magnitude * np.cos(theta_rad),
                self.magnitude * np.sin(theta_rad)
            ], dtype=np.float64)
            object.__setattr__(self, 'components', comp)


@dataclass(frozen=True)
class SpatialPoint:
    """Immutable 3D point."""
    x: float
    y: float
    z: float
    
    def to_array(self) -> Vector3D:
        return np.array([self.x, self.y, self.z], dtype=np.float64)


@dataclass(frozen=True)
class SpatialRay:
    """Immutable ray in 3D space."""
    origin: SpatialPoint
    direction: Vector3D
    
    def __post_init__(self):
        # Normalize direction
        norm = np.linalg.norm(self.direction)
        if norm > 0:
            normalized_dir = self.direction / norm
            object.__setattr__(self, 'direction', normalized_dir)


@dataclass(frozen=True)
class RayHit:
    """Immutable ray intersection result."""
    hit: bool
    t: float
    point: Optional[SpatialPoint] = None
    normal: Optional[Vector3D] = None
    
    def __post_init__(self):
        if self.hit and self.point is None and self.t >= 0:
            # Calculate hit point if not provided
            pass  # Will be calculated during execution


@dataclass(frozen=True)
class Transform:
    """Immutable transformation matrix."""
    matrix: TransformMatrix
    position: Vector3D = field(default_factory=lambda: np.zeros(3, dtype=np.float64))
    rotation: Optional[Quaternion] = None


@dataclass(frozen=True)
class BoundingBox:
    """Immutable axis-aligned bounding box."""
    min_point: SpatialPoint
    max_point: SpatialPoint
    
    def contains(self, point: SpatialPoint) -> bool:
        return (self.min_point.x <= point.x <= self.max_point.x and
                self.min_point.y <= point.y <= self.max_point.y and
                self.min_point.z <= point.z <= self.max_point.z)


@dataclass(frozen=True)
class SceneObject:
    """Immutable scene object."""
    id: str
    type: Literal["sphere", "box", "plane", "mesh"]
    transform: Transform
    bbox: BoundingBox
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Scene:
    """Immutable scene collection."""
    objects: tuple[SceneObject, ...]
    bounds: Optional[BoundingBox] = None
    
    def __post_init__(self):
        if self.bounds is None and self.objects:
            all_points = []
            for obj in self.objects:
                all_points.extend([obj.bbox.min_point, obj.bbox.max_point])
            min_coords = [min(p.x for p in all_points), 
                         min(p.y for p in all_points), 
                         min(p.z for p in all_points)]
            max_coords = [max(p.x for p in all_points), 
                         max(p.y for p in all_points), 
                         max(p.z for p in all_points)]
            bounds = BoundingBox(
                SpatialPoint(*min_coords),
                SpatialPoint(*max_coords)
            )
            object.__setattr__(self, 'bounds', bounds)


@dataclass(frozen=True)
class OperationNode:
    """Immutable node in the operation DAG."""
    operation: PrimaryOperation
    bucket: Bucket
    model: Model
    tool: Tool
    dependencies: tuple[str, ...] = field(default_factory=tuple)
    order: int = 0


@dataclass(frozen=True)
class CognitiveRequest:
    """Immutable cognitive processing request."""
    question_text: str
    part: Optional[QuestionPart] = None
    context: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CognitiveState:
    """Immutable cognitive state."""
    extracted_values: tuple[ExtractedValue, ...] = field(default_factory=tuple)
    identified_operation: Optional[PrimaryOperation] = None
    selected_bucket: Optional[Bucket] = None
    selected_model: Optional[Model] = None
    selected_tool: Optional[Tool] = None
    operation_dag: tuple[OperationNode, ...] = field(default_factory=tuple)
    intermediate_results: Dict[str, float] = field(default_factory=dict)
    final_answer: Optional[float] = None
    answer_unit: Optional[str] = None
    audit_log: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class PipelineResult:
    """Immutable pipeline execution result."""
    success: bool
    state: CognitiveState
    answer: Optional[float] = None
    unit: Optional[str] = None
    explanation: str = ""
    error_message: Optional[str] = None


@dataclass(frozen=True)
class EquationMatch:
    """Immutable equation match result."""
    equation_name: str
    formula: str
    variables: tuple[str, ...]
    description: str
    confidence: float


__all__ = [
    'Vector2D', 'Vector3D', 'Vector4D',
    'Matrix2x2', 'Matrix3x3', 'Matrix4x4',
    'TransformMatrix', 'Quaternion',
    'PrimaryOperation', 'Bucket', 'Model', 'Tool', 'QuestionPart',
    'ExtractedValue', 'VectorData', 'SpatialPoint', 'SpatialRay',
    'RayHit', 'Transform', 'BoundingBox', 'SceneObject', 'Scene',
    'OperationNode', 'CognitiveRequest', 'CognitiveState',
    'PipelineResult', 'EquationMatch'
]
