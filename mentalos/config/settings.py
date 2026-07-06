"""
MentalOS Configuration Module

This module contains all configurable aspects of the MentalOS pipeline.
Keeping configuration separate from logic allows easy customization
without touching core transformation functions.

Gate sequence and prompts are defined here rather than hard-coded
in the pipeline logic, fulfilling the requirement for configurable behavior.

Pipeline Order (Strict Priority-Based Workflow per DEFINITIONS.md):
    Requested Output → Primary Operation Lock → Bucket → Model → Tool → Execution → Interpretation

Gates 0-1 (Requested Output, Primary Operation) are globally locked after first pass.
Secondary operations restart at gate index 2 (Bucket).
"""

from dataclasses import dataclass, field
from typing import Mapping

from mentalos.core.models import PhysicalConstant, UnitConversion


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
    
    Architecture notes:
    - Gate sequence is configurable but follows strict priority order
    - Prompts are mapped by gate name for O(1) lookup
    - Secondary operations restart at configurable gate index (default: 2 = Bucket)
    - LLM endpoint is configurable for different local servers
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
    # These prompts guide the user through the cognitive workflow
    gate_prompts: Mapping[str, str] = field(default_factory=lambda: {
        "Requested Output": "What must be produced? Specify the exact output type (e.g., 'W_app in Joules', numerical value, derivation).",
        "Primary Operation Lock": "What MUST fundamentally be done? Select exactly ONE operation (Winner-Takes-All). No 'or' statements.",
        "Bucket": "What kind of world is this operation acting upon? (A-F: Geometry/Change/Accumulation/Estimation/Transformation/Decision)",
        "Model": "What assumptions govern this world? Identify the theorem, law, or conceptual model.",
        "Tool": "What method operates within that model? Specify the formula or algorithm.",
        "Execution": "Compute the value. Step-by-step derivation/calculation. Use :defer for sub-operations.",
        "Interpretation": "Does the result make physical/mathematical sense? Contextualize the answer.",
    })
    
    # Index where secondary operations restart (Bucket gate - index 2)
    # Requested Output and Primary Operation Lock are globally locked
    secondary_op_start_gate_idx: int = 2
    
    # LLM audit endpoint configuration
    # Default expects a local server like LM Studio or Ollama
    llm_endpoint: str = "http://localhost:1234/v1/chat/completions"
    llm_model: str = "qwen2.5-math-7b-instruct"
    
    # Audit system prompt - instructs LLM to provide feedback without solutions
    audit_prompt: str = (
        "You are a MentalOS auditor. Point out any vague, incomplete, or incorrect gate answers. "
        "Do NOT provide solutions, only precise feedback. "
        "Focus on: unclear constraints, missing assumptions, unit inconsistencies, "
        "and logical gaps in the reasoning chain."
    )
    
    # Bucket definitions (A-F) per DEFINITIONS.md
    # Each bucket represents a category of mathematical/physical operation
    buckets: Mapping[str, str] = field(default_factory=lambda: {
        "A": "Geometry → shape / position / trig / vectors",
        "B": "Change → motion / calculus / kinematics",
        "C": "Accumulation → integrals / totals / surfaces",
        "D": "Estimation → noise / least squares / uncertainty",
        "E": "Transformation → coordinates / matrices / projections",
        "F": "Decision → action under uncertainty",
    })
    
    # Bucket-owning operations: these operations DEFINE their bucket
    # When one of these is the primary operation, the bucket is determined by it
    bucket_owning_ops: tuple[str, ...] = (
        "Estimate",
        "Decide",
        "Change",
        "Accumulate",
        "Transform",
        "Convert",
    )
    
    # Bucket-neutral operations: inherit bucket from what is being acted upon
    # These operations can work in any bucket depending on context
    bucket_neutral_ops: tuple[str, ...] = (
        "Compare",
        "Classify",
        "Represent",
        "Describe",
        "Organize",
    )
    
    # Allowed operations for Winner-Takes-All lock
    # User must select exactly one of these as their primary operation
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
    # Higher priority operations win in case of ambiguity
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
# FORMULA DATABASE
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class Formula:
    """
    Immutable formula definition for the calculation engine.
    
    Attributes:
        id: Unique identifier for formula selection
        name: Human-readable name
        equation: Display equation (e.g., "W = F * d")
        python_expr: Executable Python expression (e.g., "F * d")
        result_var: Name of the result variable
        required_vars: Tuple of variable names needed for calculation
        category: Category for filtering (Mechanics, Energy, Vectors, etc.)
    """
    id: str
    name: str
    equation: str
    python_expr: str
    result_var: str
    required_vars: tuple[str, ...]
    category: str


# Comprehensive formula database covering Mechanics, Energy, Vectors, Kinematics
# Organized by category for intelligent filtering based on operation type
FORMULA_DATABASE: tuple[Formula, ...] = (
    # -------------------------------------------------------------------------
    # Mechanics - Work & Energy
    # -------------------------------------------------------------------------
    Formula("work_parallel", "Work (Parallel Force)", 
            "W = F_∥ × d", "F_parallel * d", 
            "W", ("F_parallel", "d"), "Mechanics"),
    
    Formula("work_angle", "Work (Angled Force)", 
            "W = F × d × cos(θ)", "F * d * math.cos(math.radians(theta))", 
            "W", ("F", "d", "theta"), "Mechanics"),
    
    Formula("kinetic_energy", "Kinetic Energy", 
            "KE = ½ × m × v²", "0.5 * m * v**2", 
            "KE", ("m", "v"), "Energy"),
    
    Formula("potential_energy", "Gravitational Potential Energy", 
            "PE = m × g × h", "m * 9.81 * h", 
            "PE", ("m", "h"), "Energy"),
    
    Formula("elastic_pe", "Elastic Potential Energy (Spring)", 
            "PE_elastic = ½ × k × x²", "0.5 * k * x**2", 
            "PE_elastic", ("k", "x"), "Energy"),
    
    Formula("work_energy_theorem", "Work-Energy Theorem", 
            "W_net = ΔKE = KE_f - KE_i", "KE_final - KE_initial", 
            "W_net", ("KE_final", "KE_initial"), "Energy"),
    
    # -------------------------------------------------------------------------
    # Vectors & Forces
    # -------------------------------------------------------------------------
    Formula("force_x", "Force X-Component", 
            "F_x = F × cos(θ)", "F * math.cos(math.radians(theta))", 
            "F_x", ("F", "theta"), "Vectors"),
    
    Formula("force_y", "Force Y-Component", 
            "F_y = F × sin(θ)", "F * math.sin(math.radians(theta))", 
            "F_y", ("F", "theta"), "Vectors"),
    
    Formula("vector_magnitude", "Vector Magnitude", 
            "|v| = √(v_x² + v_y²)", "math.sqrt(v_x**2 + v_y**2)", 
            "v_mag", ("v_x", "v_y"), "Vectors"),
    
    Formula("vector_angle", "Vector Angle", 
            "θ = tan⁻¹(v_y / v_x)", "math.degrees(math.atan2(v_y, v_x))", 
            "theta", ("v_x", "v_y"), "Vectors"),
    
    Formula("friction", "Friction Force", 
            "f = μ × N", "mu * N", 
            "f", ("mu", "N"), "Mechanics"),
    
    Formula("newton_2", "Newton's Second Law", 
            "F = m × a", "m * a", 
            "F", ("m", "a"), "Mechanics"),
    
    Formula("net_force", "Net Force (1D)", 
            "F_net = ΣF", "sum(forces)", 
            "F_net", ("forces",), "Mechanics"),
    
    Formula("weight", "Weight (Gravitational Force)", 
            "W = m × g", "m * 9.81", 
            "W", ("m",), "Mechanics"),
    
    Formula("normal_incline", "Normal Force on Incline", 
            "N = m × g × cos(θ)", "m * 9.81 * math.cos(math.radians(theta))", 
            "N", ("m", "theta"), "Mechanics"),
    
    Formula("gravity_parallel_incline", "Gravity Component Parallel to Incline", 
            "F_g∥ = m × g × sin(θ)", "m * 9.81 * math.sin(math.radians(theta))", 
            "F_g_parallel", ("m", "theta"), "Mechanics"),
    
    # -------------------------------------------------------------------------
    # Kinematics
    # -------------------------------------------------------------------------
    Formula("velocity_const_acc", "Velocity with Constant Acceleration", 
            "v = v₀ + a × t", "v0 + a * t", 
            "v", ("v0", "a", "t"), "Kinematics"),
    
    Formula("displacement_const_acc", "Displacement with Constant Acceleration", 
            "d = v₀ × t + ½ × a × t²", "v0 * t + 0.5 * a * t**2", 
            "d", ("v0", "a", "t"), "Kinematics"),
    
    Formula("velocity_displacement", "Velocity with Displacement (No Time)", 
            "v² = v₀² + 2 × a × Δx", "v0**2 + 2 * a * d", 
            "v_squared", ("v0", "a", "d"), "Kinematics"),
    
    Formula("avg_velocity", "Average Velocity", 
            "v_avg = (v₀ + v) / 2", "(v0 + v) / 2", 
            "v_avg", ("v0", "v"), "Kinematics"),
    
    Formula("displacement_avg_vel", "Displacement from Average Velocity", 
            "d = v_avg × t", "v_avg * t", 
            "d", ("v_avg", "t"), "Kinematics"),
    
    Formula("free_fall_velocity", "Free Fall Velocity", 
            "v = g × t", "9.81 * t", 
            "v", ("t",), "Kinematics"),
    
    Formula("free_fall_distance", "Free Fall Distance", 
            "d = ½ × g × t²", "0.5 * 9.81 * t**2", 
            "d", ("t",), "Kinematics"),
    
    # -------------------------------------------------------------------------
    # Power & Momentum
    # -------------------------------------------------------------------------
    Formula("power_work", "Power from Work", 
            "P = W / t", "W / t", 
            "P", ("W", "t"), "Energy"),
    
    Formula("power_force_vel", "Power from Force and Velocity", 
            "P = F × v", "F * v", 
            "P", ("F", "v"), "Energy"),
    
    Formula("momentum", "Momentum", 
            "p = m × v", "m * v", 
            "p", ("m", "v"), "Mechanics"),
    
    Formula("impulse", "Impulse", 
            "J = F × Δt = Δp", "F * delta_t", 
            "J", ("F", "delta_t"), "Mechanics"),
)


# -----------------------------------------------------------------------------
# PHYSICAL CONSTANTS
# -----------------------------------------------------------------------------

PHYSICAL_CONSTANTS: tuple[PhysicalConstant, ...] = (
    PhysicalConstant("g", "Standard Gravity", 9.81, "m/s²", 
                     "Acceleration due to gravity at Earth's surface"),
    PhysicalConstant("G", "Gravitational Constant", 6.674e-11, "N·m²/kg²", 
                     "Universal gravitational constant"),
    PhysicalConstant("c", "Speed of Light", 2.998e8, "m/s", 
                     "Speed of light in vacuum"),
    PhysicalConstant("k_e", "Coulomb Constant", 8.988e9, "N·m²/C²", 
                     "Electrostatic constant"),
    PhysicalConstant("e", "Elementary Charge", 1.602e-19, "C", 
                     "Electric charge of a proton"),
    PhysicalConstant("m_e", "Electron Mass", 9.109e-31, "kg", 
                     "Rest mass of an electron"),
    PhysicalConstant("m_p", "Proton Mass", 1.673e-27, "kg", 
                     "Rest mass of a proton"),
    PhysicalConstant("h", "Planck Constant", 6.626e-34, "J·s", 
                     "Quantum of action"),
    PhysicalConstant("k_B", "Boltzmann Constant", 1.381e-23, "J/K", 
                     "Relates temperature to energy"),
    PhysicalConstant("R", "Ideal Gas Constant", 8.314, "J/(mol·K)", 
                     "Universal gas constant"),
    PhysicalConstant("N_A", "Avogadro Number", 6.022e23, "mol⁻¹", 
                     "Number of particles per mole"),
)


# -----------------------------------------------------------------------------
# UNIT CONVERSIONS
# -----------------------------------------------------------------------------

UNIT_CONVERSIONS: tuple[UnitConversion, ...] = (
    # Length conversions (to meters)
    UnitConversion("km", "m", 1000.0),
    UnitConversion("cm", "m", 0.01),
    UnitConversion("mm", "m", 0.001),
    UnitConversion("ft", "m", 0.3048),
    UnitConversion("in", "m", 0.0254),
    UnitConversion("mi", "m", 1609.34),
    UnitConversion("yd", "m", 0.9144),
    
    # Mass conversions (to kilograms)
    UnitConversion("g", "kg", 0.001),
    UnitConversion("lb", "kg", 0.4536),
    UnitConversion("oz", "kg", 0.02835),
    UnitConversion("slug", "kg", 14.59),
    
    # Time conversions (to seconds)
    UnitConversion("min", "s", 60.0),
    UnitConversion("h", "s", 3600.0),
    UnitConversion("ms", "s", 0.001),
    UnitConversion("μs", "s", 1e-6),
    UnitConversion("ns", "s", 1e-9),
    
    # Velocity conversions (to m/s)
    UnitConversion("km/h", "m/s", 1.0 / 3.6),
    UnitConversion("mph", "m/s", 0.44704),
    UnitConversion("ft/s", "m/s", 0.3048),
    UnitConversion("kt", "m/s", 0.5144),
    
    # Energy conversions (to Joules)
    UnitConversion("kJ", "J", 1000.0),
    UnitConversion("cal", "J", 4.184),
    UnitConversion("kcal", "J", 4184.0),
    UnitConversion("Wh", "J", 3600.0),
    UnitConversion("kWh", "J", 3.6e6),
    UnitConversion("eV", "J", 1.602e-19),
    
    # Force conversions (to Newtons)
    UnitConversion("kN", "N", 1000.0),
    UnitConversion("lbf", "N", 4.448),
    UnitConversion("dyn", "N", 1e-5),
    
    # Pressure conversions (to Pascals)
    UnitConversion("kPa", "Pa", 1000.0),
    UnitConversion("MPa", "Pa", 1e6),
    UnitConversion("bar", "Pa", 1e5),
    UnitConversion("atm", "Pa", 101325.0),
    UnitConversion("psi", "Pa", 6894.76),
    UnitConversion("torr", "Pa", 133.32),
    
    # Angle conversions (to degrees for internal use)
    UnitConversion("rad", "deg", 180.0 / 3.14159265359),
    UnitConversion("grad", "deg", 0.9),
)


# Smart defaults dictionary for quick lookup
# Maps common symbol names to their default values
SMART_DEFAULTS: dict[str, float] = {
    "g": 9.81,
    "G": 6.674e-11,
    "c": 2.998e8,
    "k_e": 8.988e9,
    "e": 1.602e-19,
    "m_e": 9.109e-31,
    "m_p": 1.673e-27,
    "h": 6.626e-34,
    "k_B": 1.381e-23,
    "R": 8.314,
    "N_A": 6.022e23,
    "pi": 3.14159265359,
    "e_const": 2.71828182846,  # Euler's number
}


# Single instance for import throughout the application
DEFAULT_CONFIG = Config()
