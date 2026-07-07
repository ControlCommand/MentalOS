"""
MentalOS - Deterministic Cognitive Control System

A Physics/Spatial inference engine using FCIS architecture with:
- Data-Oriented Design (zero OOP for business logic)
- Strict typing with NewType and Annotated arrays
- FastAPI for API boundaries
- numpy/scipy for vectorized computation
"""

__version__ = "1.0.0"
__author__ = "MentalOS Team"

from mentalos.types import (
    # Type aliases
    QuestionStr, AnswerStr, OperationName, BucketName, ModelName, ToolName,
    Vector2D, Vector3D, Vector4D, Matrix2D, TransformMatrix, Quaternion,
    AngleRad, AngleDeg, Distance, TimeSec, Probability,
    
    # Data structures
    SpatialPoint, SpatialRay, RayHit, Transform, BoundingBox,
    SceneObject, Scene,
    
    # FCIS types
    CognitiveRequest, CognitiveState, PipelineStage,
    
    # Result types
    SimulationResult, SpatialQueryResult, StatisticalResult,
    
    # API types
    APIRequest, APIResponse,
    
    # Validation helpers
    validate_vector, validate_matrix, normalize_vector, create_transform_matrix,
)

from mentalos.core.pipeline import (
    # Task identification
    identify_task_from_question,
    validate_single_operation_lock,
    
    # Model/Tool selection
    select_model_for_operation,
    select_tool_for_model,
    
    # Execution engines
    execute_spatial_transform,
    execute_monte_carlo_simulation,
    execute_graph_operation,
    
    # Result formatting
    format_answer_from_result,
    
    # Main pipeline
    execute_cognitive_pipeline,
)

__all__ = [
    # Version
    "__version__",
    
    # Types
    "QuestionStr", "AnswerStr", "OperationName", "BucketName", 
    "ModelName", "ToolName",
    "Vector2D", "Vector3D", "Vector4D", "Matrix2D", 
    "TransformMatrix", "Quaternion",
    "AngleRad", "AngleDeg", "Distance", "TimeSec", "Probability",
    
    # Data structures
    "SpatialPoint", "SpatialRay", "RayHit", "Transform", 
    "BoundingBox", "SceneObject", "Scene",
    
    # FCIS types
    "CognitiveRequest", "CognitiveState", "PipelineStage",
    
    # Result types
    "SimulationResult", "SpatialQueryResult", "StatisticalResult",
    
    # API types
    "APIRequest", "APIResponse",
    
    # Validation helpers
    "validate_vector", "validate_matrix", "normalize_vector", 
    "create_transform_matrix",
    
    # Pipeline functions
    "identify_task_from_question",
    "validate_single_operation_lock",
    "select_model_for_operation",
    "select_tool_for_model",
    "execute_spatial_transform",
    "execute_monte_carlo_simulation",
    "execute_graph_operation",
    "format_answer_from_result",
    "execute_cognitive_pipeline",
]
