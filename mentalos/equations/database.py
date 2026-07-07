"""
MentalOS Equation Database
Comprehensive physics and math equation repository.
Supports fuzzy search and variable matching.
"""

from __future__ import annotations
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import re


@dataclass(frozen=True)
class Equation:
    """Immutable equation definition."""
    name: str
    formula: str
    variables: Tuple[str, ...]
    description: str
    category: str
    keywords: Tuple[str, ...]
    
    def matches_keyword(self, keyword: str) -> bool:
        """Check if keyword matches any equation keyword (case-insensitive)."""
        keyword_lower = keyword.lower()
        return any(keyword_lower in kw.lower() for kw in self.keywords)
    
    def get_variable_count(self) -> int:
        """Return number of variables in equation."""
        return len(self.variables)


# Comprehensive equation database
EQUATION_DATABASE: Tuple[Equation, ...] = (
    # Work and Energy
    Equation(
        name="work_constant_force",
        formula="W = F * d * cos(theta)",
        variables=("W", "F", "d", "theta"),
        description="Work done by a constant force at an angle",
        category="work_energy",
        keywords=("work", "force", "distance", "angle", "constant", "push", "pull")
    ),
    Equation(
        name="work_horizontal_force",
        formula="W = F * d",
        variables=("W", "F", "d"),
        description="Work done by a horizontal force",
        category="work_energy",
        keywords=("work", "force", "distance", "horizontal", "parallel")
    ),
    Equation(
        name="kinetic_energy",
        formula="KE = 0.5 * m * v^2",
        variables=("KE", "m", "v"),
        description="Kinetic energy of a moving object",
        category="work_energy",
        keywords=("kinetic", "energy", "mass", "velocity", "speed")
    ),
    Equation(
        name="potential_energy_gravity",
        formula="PE = m * g * h",
        variables=("PE", "m", "g", "h"),
        description="Gravitational potential energy",
        category="work_energy",
        keywords=("potential", "energy", "gravity", "height", "mass")
    ),
    Equation(
        name="work_energy_theorem",
        formula="W_net = KE_final - KE_initial",
        variables=("W_net", "KE_final", "KE_initial"),
        description="Net work equals change in kinetic energy",
        category="work_energy",
        keywords=("work", "energy", "theorem", "net", "change")
    ),
    
    # Forces and Newton's Laws
    Equation(
        name="newton_second_law",
        formula="F = m * a",
        variables=("F", "m", "a"),
        description="Newton's second law of motion",
        category="forces",
        keywords=("force", "mass", "acceleration", "newton", "motion")
    ),
    Equation(
        name="friction_force",
        formula="f = mu * N",
        variables=("f", "mu", "N"),
        description="Friction force equation",
        category="forces",
        keywords=("friction", "coefficient", "normal", "force")
    ),
    Equation(
        name="weight",
        formula="W = m * g",
        variables=("W", "m", "g"),
        description="Weight of an object",
        category="forces",
        keywords=("weight", "mass", "gravity", "force")
    ),
    Equation(
        name="vector_component_x",
        formula="F_x = F * cos(theta)",
        variables=("F_x", "F", "theta"),
        description="X-component of a vector",
        category="vectors",
        keywords=("component", "x", "horizontal", "cosine", "vector", "resolve")
    ),
    Equation(
        name="vector_component_y",
        formula="F_y = F * sin(theta)",
        variables=("F_y", "F", "theta"),
        description="Y-component of a vector",
        category="vectors",
        keywords=("component", "y", "vertical", "sine", "vector", "resolve")
    ),
    Equation(
        name="vector_magnitude",
        formula="|F| = sqrt(F_x^2 + F_y^2)",
        variables=("F", "F_x", "F_y"),
        description="Magnitude of a vector from components",
        category="vectors",
        keywords=("magnitude", "vector", "components", "pythagorean")
    ),
    Equation(
        name="vector_angle",
        formula="theta = atan(F_y / F_x)",
        variables=("theta", "F_y", "F_x"),
        description="Angle of a vector from components",
        category="vectors",
        keywords=("angle", "direction", "vector", "arctangent")
    ),
    
    # Kinematics
    Equation(
        name="velocity_average",
        formula="v_avg = (v_initial + v_final) / 2",
        variables=("v_avg", "v_initial", "v_final"),
        description="Average velocity for constant acceleration",
        category="kinematics",
        keywords=("velocity", "average", "initial", "final", "constant")
    ),
    Equation(
        name="displacement_velocity_time",
        formula="d = v * t",
        variables=("d", "v", "t"),
        description="Displacement with constant velocity",
        category="kinematics",
        keywords=("displacement", "distance", "velocity", "time", "constant")
    ),
    Equation(
        name="velocity_time_acceleration",
        formula="v = v0 + a * t",
        variables=("v", "v0", "a", "t"),
        description="Velocity as function of time and acceleration",
        category="kinematics",
        keywords=("velocity", "time", "acceleration", "initial")
    ),
    Equation(
        name="displacement_acceleration_time",
        formula="d = v0 * t + 0.5 * a * t^2",
        variables=("d", "v0", "t", "a"),
        description="Displacement with constant acceleration",
        category="kinematics",
        keywords=("displacement", "distance", "acceleration", "time", "initial")
    ),
    Equation(
        name="velocity_squared_displacement",
        formula="v^2 = v0^2 + 2 * a * d",
        variables=("v", "v0", "a", "d"),
        description="Velocity-displacement relation",
        category="kinematics",
        keywords=("velocity", "displacement", "acceleration", "squared")
    ),
    
    # Power
    Equation(
        name="power_work_time",
        formula="P = W / t",
        variables=("P", "W", "t"),
        description="Power as work per unit time",
        category="power",
        keywords=("power", "work", "time", "rate")
    ),
    Equation(
        name="power_force_velocity",
        formula="P = F * v",
        variables=("P", "F", "v"),
        description="Power as force times velocity",
        category="power",
        keywords=("power", "force", "velocity", "instantaneous")
    ),
    
    # Momentum
    Equation(
        name="momentum",
        formula="p = m * v",
        variables=("p", "m", "v"),
        description="Linear momentum",
        category="momentum",
        keywords=("momentum", "mass", "velocity", "linear")
    ),
    Equation(
        name="impulse",
        formula="J = F * t = delta_p",
        variables=("J", "F", "t", "delta_p"),
        description="Impulse-momentum theorem",
        category="momentum",
        keywords=("impulse", "force", "time", "momentum", "change")
    ),
    Equation(
        name="conservation_momentum",
        formula="p_initial = p_final",
        variables=("p_initial", "p_final"),
        description="Conservation of momentum",
        category="momentum",
        keywords=("conservation", "momentum", "collision", "isolated")
    ),
    
    # Circular Motion
    Equation(
        name="centripetal_acceleration",
        formula="a_c = v^2 / r",
        variables=("a_c", "v", "r"),
        description="Centripetal acceleration",
        category="circular_motion",
        keywords=("centripetal", "acceleration", "velocity", "radius", "circular")
    ),
    Equation(
        name="centripetal_force",
        formula="F_c = m * v^2 / r",
        variables=("F_c", "m", "v", "r"),
        description="Centripetal force",
        category="circular_motion",
        keywords=("centripetal", "force", "mass", "velocity", "radius", "circular")
    ),
    
    # Gravitation
    Equation(
        name="gravitational_force",
        formula="F = G * m1 * m2 / r^2",
        variables=("F", "G", "m1", "m2", "r"),
        description="Newton's law of universal gravitation",
        category="gravitation",
        keywords=("gravity", "gravitational", "force", "mass", "distance", "universal")
    ),
    
    # Springs
    Equation(
        name="hooke_law",
        formula="F = -k * x",
        variables=("F", "k", "x"),
        description="Hooke's law for springs",
        category="springs",
        keywords=("spring", "hooke", "force", "displacement", "constant")
    ),
    Equation(
        name="elastic_potential_energy",
        formula="PE_elastic = 0.5 * k * x^2",
        variables=("PE_elastic", "k", "x"),
        description="Elastic potential energy in a spring",
        category="springs",
        keywords=("elastic", "potential", "energy", "spring", "compression")
    ),
)


def search_equations(keywords: List[str], category: Optional[str] = None) -> List[Equation]:
    """
    Search equations by keywords with optional category filter.
    Returns sorted list by match confidence.
    """
    matches = []
    
    for equation in EQUATION_DATABASE:
        if category and equation.category != category:
            continue
            
        match_count = sum(1 for kw in keywords if equation.matches_keyword(kw))
        if match_count > 0:
            matches.append((equation, match_count))
    
    # Sort by match count (descending)
    matches.sort(key=lambda x: x[1], reverse=True)
    return [eq for eq, _ in matches]


def get_equation_by_name(name: str) -> Optional[Equation]:
    """Get equation by exact name match."""
    for equation in EQUATION_DATABASE:
        if equation.name == name:
            return equation
    return None


def get_equations_by_category(category: str) -> List[Equation]:
    """Get all equations in a category."""
    return [eq for eq in EQUATION_DATABASE if eq.category == category]


def get_all_categories() -> List[str]:
    """Get list of all unique categories."""
    return list(set(eq.category for eq in EQUATION_DATABASE))


def suggest_equation(variables: List[str], context_keywords: List[str]) -> Optional[Equation]:
    """
    Suggest best equation based on available variables and context.
    Prioritizes equations where all required variables are known except one.
    """
    candidates = search_equations(context_keywords)
    
    if not candidates:
        candidates = list(EQUATION_DATABASE)
    
    best_match = None
    best_score = -1
    
    for equation in candidates:
        # Count how many variables we have
        known_vars = sum(1 for var in equation.variables if any(var.lower() in v.lower() for v in variables))
        unknown_vars = len(equation.variables) - known_vars
        
        # Prefer equations with exactly one unknown (solvable)
        if unknown_vars == 1:
            score = known_vars * 2  # Bonus for solvable equations
        else:
            score = known_vars
        
        if score > best_score:
            best_score = score
            best_match = equation
    
    return best_match


__all__ = [
    'Equation',
    'EQUATION_DATABASE',
    'search_equations',
    'get_equation_by_name',
    'get_equations_by_category',
    'get_all_categories',
    'suggest_equation'
]
