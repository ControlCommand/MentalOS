"""
MentalOS Type Definitions - Public API
Re-exports all types from dedicated modules.
__init__.py is strictly a routing gatekeeper - no business logic.
"""

from mentalos.types.core_types import (
    # Primitive type aliases
    QuestionStr,
    AnswerStr,
    OperationName,
    BucketName,
    ModelName,
    ToolName,
    Vector2D,
    Vector3D,
    Vector4D,
    Matrix2D,
    TransformMatrix,
    Quaternion,
    AngleRad,
    AngleDeg,
    Distance,
    TimeSec,
    Probability,
    # Spatial data structures
    SpatialPoint,
    SpatialRay,
    RayHit,
    Transform,
    BoundingBox,
    SceneObject,
    Scene,
    # FCIS types
    CognitiveRequest,
    CognitiveState,
    PipelineStage,
    # Computational result types
    SimulationResult,
    SpatialQueryResult,
    StatisticalResult,
    # API types
    APIRequest,
    APIResponse,
)

from mentalos.types.type_utils import (
    validate_vector,
    validate_matrix,
    normalize_vector,
    create_transform_matrix,
)

__all__ = [
    # Primitive type aliases
    "QuestionStr",
    "AnswerStr",
    "OperationName",
    "BucketName",
    "ModelName",
    "ToolName",
    "Vector2D",
    "Vector3D",
    "Vector4D",
    "Matrix2D",
    "TransformMatrix",
    "Quaternion",
    "AngleRad",
    "AngleDeg",
    "Distance",
    "TimeSec",
    "Probability",
    # Spatial data structures
    "SpatialPoint",
    "SpatialRay",
    "RayHit",
    "Transform",
    "BoundingBox",
    "SceneObject",
    "Scene",
    # FCIS types
    "CognitiveRequest",
    "CognitiveState",
    "PipelineStage",
    # Computational result types
    "SimulationResult",
    "SpatialQueryResult",
    "StatisticalResult",
    # API types
    "APIRequest",
    "APIResponse",
    # Utility functions
    "validate_vector",
    "validate_matrix",
    "normalize_vector",
    "create_transform_matrix",
]
