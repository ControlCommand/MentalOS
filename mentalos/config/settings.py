"""
MentalOS Configuration Module

This module contains all configurable aspects of the MentalOS pipeline.
Keeping configuration separate from logic allows easy customization
without touching core transformation functions.

Gate sequence and prompts are defined here rather than hard-coded
in the pipeline logic, fulfilling the requirement for configurable behavior.

Pipeline Order (Strict Priority-Based Workflow):
    Question → Requested Output → Primary Operation → Bucket → Model → Tool → Execution → Answer
"""

from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True)
class GateConfig:
    """Immutable configuration for a single gate."""
    name: str
    prompt: str


@dataclass(frozen=True)
class Config:
    """
    Master configuration for MentalOS.
    
    All fields are immutable (frozen dataclass) to prevent accidental mutation.
    This ensures configuration remains constant throughout program execution.
    """
    # Default gate sequence - STRICT ORDER per DEFINITIONS.md
    # Gates 0-1 (Requested Output, Primary Operation) are globally locked after first pass
    # Secondary operations restart at gate index 2 (Bucket)
    gate_sequence: tuple[str, ...] = (
        "Requested Output",
        "Primary Operation Lock",
        "Bucket",
        "Model",
        "Tool",
        "Execution",
        "Interpretation",
    )
    
    # Prompts mapped by gate name for lookup during pipeline execution
    gate_prompts: Mapping[str, str] = field(default_factory=lambda: {
        "Requested Output": "What must be produced? Specify the exact output type (e.g., 'W_app in Joules', numerical value, derivation).",
        "Primary Operation Lock": "What MUST fundamentally be done? Select exactly ONE operation (Winner-Takes-All). No 'or' statements.",
        "Bucket": "What kind of world is this operation acting upon? (A-F: Geometry/Change/Accumulation/Estimation/Transformation/Decision)",
        "Model": "What assumptions govern this world? Identify the theorem, law, or conceptual model.",
        "Tool": "What method operates within that model? Specify the formula or algorithm.",
        "Execution": "Compute the value. Step-by-step derivation/calculation.",
        "Interpretation": "Does the result make physical/mathematical sense? Contextualize the answer.",
    })
    
    # Index where secondary operations restart (Bucket gate - index 2)
    # Requested Output and Primary Operation Lock are globally locked
    secondary_op_start_gate_idx: int = 2
    
    # LLM audit endpoint configuration
    llm_endpoint: str = "http://localhost:1234/v1/chat/completions"
    llm_model: str = "qwen2.5-math-7b-instruct"
    
    # Audit system prompt
    audit_prompt: str = (
        "You are a MentalOS auditor. Point out any vague, incomplete, or incorrect gate answers. "
        "Do NOT provide solutions, only precise feedback."
    )
    
    # Bucket definitions (A-F) per DEFINITIONS.md
    buckets: Mapping[str, str] = field(default_factory=lambda: {
        "A": "Geometry → shape / position / trig / vectors",
        "B": "Change → motion / calculus / kinematics",
        "C": "Accumulation → integrals / totals / surfaces",
        "D": "Estimation → noise / least squares / uncertainty",
        "E": "Transformation → coordinates / matrices / projections",
        "F": "Decision → action under uncertainty",
    })
    
    # Bucket-owning operations: these operations DEFINE their bucket
    bucket_owning_ops: tuple[str, ...] = (
        "Estimate",
        "Decide",
        "Change",
        "Accumulate",
        "Transform",
        "Convert",
    )
    
    # Bucket-neutral operations: inherit bucket from what is being acted upon
    bucket_neutral_ops: tuple[str, ...] = (
        "Compare",
        "Classify",
        "Represent",
        "Describe",
        "Organize",
    )
    
    # Allowed operations for Winner-Takes-All lock
    allowed_operations: tuple[str, ...] = (
        "Estimate",
        "Compare",
        "Decide",
        "Change",
        "Accumulate",
        "Transform",
        "Convert",
        "Classify",
    )
    
    # Tie-break priority order (highest to lowest)
    # Used when multiple operations compete for the lock
    tie_break_priority: tuple[str, ...] = (
        "Convert",
        "Transform",
        "Accumulate",
        "Change",
        "Estimate",
        "Compare",
        "Decide",
    )

# -----------------------------------------------------------------------------
# FORMULA DATABASE & UNITS
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class Formula:
    """Immutable formula definition for the calculation engine."""
    id: str
    name: str
    equation: str  # Human readable: "W = F * d"
    python_expr: str  # Executable: "F * d"
    result_var: str  # e.g., "W"
    required_vars: tuple[str, ...]  # e.g., ("F", "d")
    category: str


FORMULA_DATABASE: tuple[Formula, ...] = (
    # Mechanics - Work & Energy
    Formula("work_parallel", "Work (Parallel Force)", "W = F_|| * d", "F_parallel * d", "W", ("F_parallel", "d"), "Mechanics"),
    Formula("work_angle", "Work (Angled Force)", "W = F * d * cos(θ)", "F * d * math.cos(math.radians(theta))", "W", ("F", "d", "theta"), "Mechanics"),
    Formula("kinetic_energy", "Kinetic Energy", "KE = 0.5 * m * v²", "0.5 * m * v**2", "KE", ("m", "v"), "Energy"),
    Formula("potential_energy", "Gravitational PE", "PE = m * g * h", "m * 9.81 * h", "PE", ("m", "h"), "Energy"),
    
    # Vectors & Forces
    Formula("force_x", "Force X-Component", "F_x = F * cos(θ)", "F * math.cos(math.radians(theta))", "F_x", ("F", "theta"), "Vectors"),
    Formula("force_y", "Force Y-Component", "F_y = F * sin(θ)", "F * math.sin(math.radians(theta))", "F_y", ("F", "theta"), "Vectors"),
    Formula("friction", "Friction Force", "f = μ * N", "mu * N", "f", ("mu", "N"), "Mechanics"),
    Formula("newton_2", "Newton's Second Law", "F = m * a", "m * a", "F", ("m", "a"), "Mechanics"),
    Formula("net_force", "Net Force (1D)", "F_net = ΣF", "sum(forces)", "F_net", ("forces",), "Mechanics"),
    
    # Kinematics
    Formula("velocity_const_acc", "Velocity w/ Const Accel", "v = v₀ + a * t", "v0 + a * t", "v", ("v0", "a", "t"), "Kinematics"),
    Formula("displacement_const_acc", "Displacement w/ Const Accel", "d = v₀ * t + ½ * a * t²", "v0 * t + 0.5 * a * t**2", "d", ("v0", "a", "t"), "Kinematics"),
    Formula("velocity_displacement", "Velocity w/ displacement no time","v² = v₀² + 2aΔx", "v0**2 + 2 * a * d", "v_final_sq", ("v0", "a", "d"), "Kinematics"),
)

UNITS: dict[str, list[str]] = {
    "Force": ["N", "kN", "lbf"],
    "Distance": ["m", "km", "cm", "ft", "mi"],
    "Mass": ["kg", "g", "lb", "slug"],
    "Time": ["s", "min", "h", "ms"],
    "Energy": ["J", "kJ", "cal", "kcal"],
    "Velocity": ["m/s", "km/h", "mph", "ft/s"],
    "Acceleration": ["m/s²", "ft/s²"],
    "Angle": ["deg", "rad"],
    "Pressure": ["Pa", "kPa", "atm", "bar", "psi"],
}


# Single instance for import throughout the application
DEFAULT_CONFIG = Config()
