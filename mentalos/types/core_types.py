"""
MentalOS Types - Core Type Definitions

Strict typing with NewType and Annotated arrays for physics/spatial inference.
Data-Oriented Design: frozen dataclasses only, no OOP business logic.
"""
from __future__ import annotations
from typing import Optional, List, Dict, Any, Literal, Union
from dataclasses import dataclass, field
import numpy as np
from numpy.typing import NDArray
from typing_extensions import Annotated

# =============================================================================
# TYPE ALIASES - Strict NumPy Array Types
# =============================================================================

Vector2D = Annotated[NDArray[np.float64], "Shape[2]"]
Vector3D = Annotated[NDArray[np.float64], "Shape[3]"]
Vector4D = Annotated[NDArray[np.float64], "Shape[4]"]
Matrix2x2 = Annotated[NDArray[np.float64], "Shape[2,2]"]
Matrix3x3 = Annotated[NDArray[np.float64], "Shape[3,3]"]
Matrix4x4 = Annotated[NDArray[np.float64], "Shape[4,4]"]
Quaternion = Annotated[NDArray[np.float64], "Shape[4]"]
TransformMatrix = Annotated[NDArray[np.float64], "Shape[4,4]"]

Scalar = float
AngleRad = Annotated[float, "radians"]
AngleDeg = Annotated[float, "degrees"]
Distance = Annotated[float, "meters"]
Time = Annotated[float, "seconds"]
Velocity = Annotated[float, "m/s"]
Acceleration = Annotated[float, "m/s^2"]
Force = Annotated[float, "newtons"]
Mass = Annotated[float, "kg"]
Work = Annotated[float, "joules"]
Energy = Annotated[float, "joules"]
Power = Annotated[float, "watts"]
Momentum = Annotated[float, "kg*m/s"]

# =============================================================================
# PRIMARY OPERATIONS (The 5 Verbs)
# =============================================================================

PrimaryOperation = Literal[
    "accumulate",      # Integration, summation, work, energy accumulation
    "transform",       # Coordinate transforms, vector resolution, rotations
    "scale",           # Ratios, proportions, scaling factors
    "estimate",        # Averages, approximations, statistical estimates
    "differentiate"    # Rates of change, derivatives, slopes
]

# =============================================================================
# BUCKETS (6 Cognitive Buckets)
# =============================================================================

Bucket = Literal[
    "accumulation",    # Work, energy, impulse, charge accumulation
    "transformation",  # Vector resolution, coordinate systems, rotations
    "geometry",        # Distances, angles, shapes, spatial relationships
    "kinematics",      # Motion without forces, velocity, acceleration
    "dynamics",        # Forces, Newton's laws, momentum
    "conservation"     # Conservation laws, energy, momentum, charge
]

# =============================================================================
# MODELS (Physics Frameworks)
# =============================================================================

Model = Literal[
    "newtonian_mechanics",
    "work_energy_theorem",
    "conservation_of_energy",
    "conservation_of_momentum",
    "kinematics_constant_acceleration",
    "kinematics_projectile_motion",
    "circular_motion",
    "rotational_dynamics",
    "simple_harmonic_motion",
    "gravitation",
    "fluid_mechanics",
    "thermodynamics",
    "electrostatics",
    "electric_circuits",
    "magnetism",
    "electromagnetic_induction",
    "waves_optics",
    "special_relativity",
    "quantum_mechanics",
    "statistical_mechanics",
    "equilibrium_statics"
]

# =============================================================================
# TOOLS (Mathematical Tools)
# =============================================================================

Tool = Literal[
    "trigonometry",
    "vector_algebra",
    "calculus_derivative",
    "calculus_integral",
    "linear_algebra",
    "differential_equations",
    "statistics",
    "complex_numbers",
    "matrix_operations",
    "coordinate_geometry",
    "unit_conversion",
    "algebraic_manipulation"
]

# =============================================================================
# DATA EXTRACTION TYPES
# =============================================================================

@dataclass(frozen=True)
class ExtractedValue:
    """A single extracted value from problem text."""
    symbol: str
    value: float
    unit: str
    description: str
    uncertainty: Optional[float] = None


@dataclass(frozen=True)
class ExtractedVector:
    """A vector value with magnitude and direction."""
    symbol: str
    magnitude: float
    direction_angle: AngleDeg
    direction_reference: str  # e.g., "horizontal", "positive_x_axis"
    unit: str
    components: Optional[Dict[str, float]] = None


@dataclass(frozen=True)
class ProblemContext:
    """Background context extracted from problem statement."""
    objects: List[str]
    conditions: List[str]
    constraints: List[str]
    assumptions: List[str]
    known_values: List[Union[ExtractedValue, ExtractedVector]]


# =============================================================================
# COGNITIVE PIPELINE STATE
# =============================================================================

@dataclass(frozen=True)
class QuestionAnalysis:
    """Stage 1: Question parsing and intent recognition."""
    raw_text: str
    parts: Dict[str, str]  # a, b, c, d -> question text
    current_part: Optional[str]  # Which part we're solving
    context: ProblemContext
    keywords: List[str]
    tokens: List[str]


@dataclass(frozen=True)
class RequestedOutput:
    """Stage 2: What the question wants."""
    target_quantity: str  # e.g., "work", "velocity", "acceleration"
    output_type: Literal["instantaneous", "average", "maximum", "minimum", "total", "net"]
    symbol: str
    unit: str
    description: str


@dataclass(frozen=True)
class ConstraintLock:
    """Stage 3: Isolate variables and constraints."""
    relevant_variables: List[str]
    ignored_variables: List[str]
    fixed_parameters: Dict[str, ExtractedValue]
    variable_parameters: Dict[str, ExtractedValue]
    boundary_conditions: List[str]
    scope_keywords: List[str]


@dataclass(frozen=True)
class OperationLock:
    """Stage 4: Primary operation determination (Winner Takes All)."""
    primary_operation: PrimaryOperation
    confidence: float
    reasoning: str
    secondary_operations: List[PrimaryOperation] = field(default_factory=list)
    operation_order: List[PrimaryOperation] = field(default_factory=list)


@dataclass(frozen=True)
class BucketAssignment:
    """Stage 5: Bucket determination."""
    primary_bucket: Bucket
    confidence: float
    reasoning: str
    alternative_buckets: List[Bucket] = field(default_factory=list)


@dataclass(frozen=True)
class ModelSelection:
    """Stage 6: Physics model selection."""
    primary_model: Model
    confidence: float
    reasoning: str
    supporting_principles: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class ToolSelection:
    """Stage 7: Mathematical tool selection."""
    primary_tool: Tool
    confidence: float
    reasoning: str
    required_formulas: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class NestedOperation:
    """Represents a nested/sub-operation in the dependency chain."""
    order: int  # 1st, 2nd, 3rd, etc.
    operation: PrimaryOperation
    bucket: Bucket
    model: Model
    tool: Tool
    target_variable: str
    dependencies: List[str] = field(default_factory=list)
    result: Optional[float] = None
    result_unit: Optional[str] = None


@dataclass(frozen=True)
class ExecutionPlan:
    """Stage 8: Complete execution plan with nested operations."""
    primary_operation: OperationLock
    nested_operations: List[NestedOperation]
    execution_order: List[int]
    final_formula: str
    intermediate_results: Dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class EquationMatch:
    """Matched equation from database."""
    equation_id: str
    formula: str
    variables: List[str]
    description: str
    applicable_models: List[Model]
    applicable_tools: List[Tool]


@dataclass(frozen=True)
class SpatialVisualization:
    """Spatial representation for vector resolution, etc."""
    visualization_type: Literal["vector_triangle", "free_body_diagram", "coordinate_system", "motion_diagram"]
    elements: Dict[str, Any]
    annotations: List[str]
    svg_representation: Optional[str] = None


# =============================================================================
# RESULTS AND AUDIT
# =============================================================================

@dataclass(frozen=True)
class StepResult:
    """Result of a single computation step."""
    step_number: int
    operation: PrimaryOperation
    variable_name: str
    value: float
    unit: str
    formula_used: str
    inputs: Dict[str, float]
    success: bool
    error_message: Optional[str] = None


@dataclass(frozen=True)
class CognitiveResult:
    """Final result of cognitive pipeline."""
    question_part: str
    requested_output: RequestedOutput
    final_value: float
    unit: str
    significant_figures: int
    step_results: List[StepResult]
    audit_feedback: Optional[str] = None


@dataclass(frozen=True)
class AuditFeedback:
    """LLM audit feedback on solution approach."""
    approach_correct: bool
    succinct_feedback: str  # 250-300 words max
    thought_provoking_questions: List[str]
    identified_issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


# =============================================================================
# USER INTERACTION TYPES
# =============================================================================

@dataclass(frozen=True)
class UserPrompt:
    """Prompt for user interaction."""
    prompt_type: Literal[
        "select_question_part",
        "confirm_primary_operation",
        "identify_secondary_operations",
        "select_equation",
        "input_values",
        "confirm_units",
        "continue_next_part",
        "provide_spatial_input"
    ]
    message: str
    options: Optional[List[str]] = None
    required_input_type: Optional[str] = None


@dataclass(frozen=True)
class UserResponse:
    """User response to prompts."""
    prompt_type: str
    response: Any
    confirmed: bool
    additional_notes: Optional[str] = None


# =============================================================================
# COMPLETE COGNITIVE STATE
# =============================================================================

@dataclass(frozen=True)
class CognitiveState:
    """Complete state of the cognitive pipeline."""
    session_id: str
    question_analysis: QuestionAnalysis
    requested_output: Optional[RequestedOutput] = None
    constraint_lock: Optional[ConstraintLock] = None
    operation_lock: Optional[OperationLock] = None
    bucket_assignment: Optional[BucketAssignment] = None
    model_selection: Optional[ModelSelection] = None
    tool_selection: Optional[ToolSelection] = None
    execution_plan: Optional[ExecutionPlan] = None
    step_results: List[StepResult] = field(default_factory=list)
    final_result: Optional[CognitiveResult] = None
    audit_feedback: Optional[AuditFeedback] = None
    user_prompts: List[UserPrompt] = field(default_factory=list)
    user_responses: List[UserResponse] = field(default_factory=list)
    current_stage: str = "question_analysis"
    is_complete: bool = False
    has_errors: bool = False
    error_messages: List[str] = field(default_factory=list)


# =============================================================================
# API REQUEST/RESPONSE TYPES
# =============================================================================

@dataclass(frozen=True)
class CognitiveRequest:
    """Request to process a physics/math problem."""
    question_text: str
    question_parts: Optional[Dict[str, str]] = None
    selected_part: Optional[str] = None
    user_context: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class CognitiveResponse:
    """Response from cognitive pipeline."""
    session_id: str
    stage: str
    state: CognitiveState
    requires_user_input: bool
    user_prompt: Optional[UserPrompt] = None
    partial_result: Optional[StepResult] = None
    final_result: Optional[CognitiveResult] = None
    audit_feedback: Optional[AuditFeedback] = None

+++ mentalos/types/core_types.py (修改后)
"""MentalOS Type Definitions - Strictly Typed, Immutable Data Structures"""
from __future__ import annotations
from typing import Literal, Optional, List, Dict, Any, NewType
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
from numpy.typing import NDArray

# Type Aliases
Vector2D = NDArray[np.float64]
Vector3D = NDArray[np.float64]
Vector4D = NDArray[np.float64]
TransformMatrix = NDArray[np.float64]
Quaternion = NDArray[np.float64]
AnswerStr = str

class PrimaryOperation(str, Enum):
    ACCUMULATE = "accumulate"
    TRANSFORM = "transform"
    SCALE = "scale"
    ESTIMATE = "estimate"
    DIFFERENTIATE = "differentiate"

class Bucket(str, Enum):
    ACCUMULATION = "accumulation"
    TRANSFORMATION = "transformation"
    GEOMETRY = "geometry"
    KINEMATICS = "kinematics"
    DYNAMICS = "dynamics"
    CONSERVATION = "conservation"

class Model(str, Enum):
    WORK_ENERGY = "work_energy_theorem"
    NEWTONIAN_MECHANICS = "newtonian_mechanics"
    KINEMATICS_1D = "kinematics_1d"
    KINEMATICS_2D = "kinematics_2d"
    CONSERVATION_ENERGY = "conservation_of_energy"
    CONSERVATION_MOMENTUM = "conservation_of_momentum"
    THERMODYNAMICS = "thermodynamics"
    ELECTROSTATICS = "electrostatics"
    CIRCUITS = "circuits"
    WAVES = "waves"
    ROTATIONAL_DYNAMICS = "rotational_dynamics"

class Tool(str, Enum):
    TRIGONOMETRY = "trigonometry"
    VECTOR_ALGEBRA = "vector_algebra"
    CALCULUS_DERIVATIVE = "calculus_derivative"
    CALCULUS_INTEGRAL = "calculus_integral"
    LINEAR_ALGEBRA = "linear_algebra"
    DIFFERENTIAL_EQUATIONS = "differential_equations"
    STATISTICS = "statistics"
    ALGEBRAIC_MANIPULATION = "algebraic_manipulation"

@dataclass(frozen=True)
class ExtractedValue:
    """Immutable extracted numerical value with metadata"""
    name: str
    value: float
    unit: str
    context: str = ""

@dataclass(frozen=True)
class CognitiveRequest:
    """Immutable cognitive processing request"""
    question_text: str
    part_label: Optional[str] = None
    custom_operation: Optional[PrimaryOperation] = None
    custom_bucket: Optional[Bucket] = None
    custom_model: Optional[Model] = None
    user_notes: str = ""

@dataclass(frozen=True)
class OperationNode:
    """Immutable node in the operation DAG"""
    operation: PrimaryOperation
    bucket: Bucket
    model: Model
    tool: Tool
    confidence: float
    dependencies: List[str] = field(default_factory=list)
    resolved_value: Optional[float] = None
    resolved_unit: Optional[str] = None
    explanation: str = ""

@dataclass(frozen=True)
class CognitiveState:
    """Immutable state of cognitive processing"""
    request: CognitiveRequest
    extracted_values: List[ExtractedValue]
    primary_operation: OperationNode
    nested_operations: List[OperationNode]
    execution_order: List[str]
    current_step: int = 0
    results: Dict[str, float] = field(default_factory=dict)
    is_complete: bool = False
    audit_feedback: str = ""

@dataclass(frozen=True)
class EquationEntry:
    """Immutable equation database entry"""
    id: str
    name: str
    formula: str
    variables: List[str]
    description: str
    operation_hint: PrimaryOperation
    bucket_hint: Bucket
    model_hint: Model
    tool_hint: Tool
    keywords: List[str]

@dataclass(frozen=True)
class ExecutionStep:
    """Immutable execution step record"""
    step_number: int
    operation_node_id: str
    equation_used: str
    inputs: Dict[str, float]
    output_value: float
    output_unit: str
    explanation: str

@dataclass(frozen=True)
class CognitiveResult:
    """Immutable final result of cognitive processing"""
    success: bool
    final_answer: Optional[float]
    final_unit: Optional[str]
    answer_explanation: str
    execution_steps: List[ExecutionStep]
    total_steps: int
    warnings: List[str]
    audit_summary: str
