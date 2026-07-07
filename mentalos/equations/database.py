"""
MentalOS Equation Database

Comprehensive physics and mathematics equation database with fuzzy matching.
Organized by model, tool, and operation type for intelligent retrieval.
"""
from __future__ import annotations
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
import re
import numpy as np


@dataclass(frozen=True)
class Equation:
    """Single equation entry in the database."""
    id: str
    name: str
    formula: str  # LaTeX-style or plain text formula
    description: str
    variables: Dict[str, Dict[str, Any]]  # {var_name: {unit, description, default}}
    models: List[str]
    tools: List[str]
    operations: List[str]
    buckets: List[str]
    tags: List[str] = field(default_factory=list)
    example_problem: Optional[str] = None
    
    def matches_keywords(self, keywords: List[str]) -> float:
        """Calculate match score based on keywords."""
        score = 0.0
        all_terms = self.tags + [self.name.lower()] + [self.description.lower()]
        all_terms_str = " ".join(all_terms)
        
        for keyword in keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in all_terms_str:
                score += 1.0
            # Fuzzy match - check for substring matches
            for term in all_terms:
                if keyword_lower in term or term in keyword_lower:
                    score += 0.3
        
        return score / max(len(keywords), 1)


class EquationDatabase:
    """
    Comprehensive equation database with intelligent search capabilities.
    Supports fuzzy matching, keyword extraction, and context-aware retrieval.
    """
    
    def __init__(self):
        self.equations: Dict[str, Equation] = {}
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize the equation database with physics and math equations."""
        
        # =====================================================================
        # WORK AND ENERGY EQUATIONS
        # =====================================================================
        
        self.add_equation(Equation(
            id="work_constant_force",
            name="Work by Constant Force",
            formula="W = F * d * cos(θ)",
            description="Work done by a constant force over a displacement",
            variables={
                "W": {"unit": "J", "description": "Work done"},
                "F": {"unit": "N", "description": "Magnitude of force"},
                "d": {"unit": "m", "description": "Displacement magnitude"},
                "θ": {"unit": "deg", "description": "Angle between force and displacement"}
            },
            models=["work_energy_theorem", "newtonian_mechanics"],
            tools=["trigonometry", "vector_algebra"],
            operations=["accumulate"],
            buckets=["accumulation"],
            tags=["work", "force", "displacement", "energy", "constant force"]
        ))
        
        self.add_equation(Equation(
            id="work_net",
            name="Net Work",
            formula="W_net = ΣW_i = W_1 + W_2 + ... + W_n",
            description="Total work done by all forces acting on an object",
            variables={
                "W_net": {"unit": "J", "description": "Net work"},
                "W_i": {"unit": "J", "description": "Individual work contributions"}
            },
            models=["work_energy_theorem"],
            tools=["algebraic_manipulation"],
            operations=["accumulate"],
            buckets=["accumulation"],
            tags=["net work", "total work", "sum", "multiple forces"]
        ))
        
        self.add_equation(Equation(
            id="kinetic_energy",
            name="Kinetic Energy",
            formula="KE = (1/2) * m * v²",
            description="Energy of motion",
            variables={
                "KE": {"unit": "J", "description": "Kinetic energy"},
                "m": {"unit": "kg", "description": "Mass"},
                "v": {"unit": "m/s", "description": "Velocity magnitude"}
            },
            models=["work_energy_theorem", "conservation_of_energy"],
            tools=["algebraic_manipulation"],
            operations=["accumulate", "scale"],
            buckets=["accumulation", "kinematics"],
            tags=["kinetic energy", "motion", "velocity", "mass"]
        ))
        
        self.add_equation(Equation(
            id="work_energy_theorem",
            name="Work-Energy Theorem",
            formula="W_net = ΔKE = KE_f - KE_i",
            description="Net work equals change in kinetic energy",
            variables={
                "W_net": {"unit": "J", "description": "Net work"},
                "KE_f": {"unit": "J", "description": "Final kinetic energy"},
                "KE_i": {"unit": "J", "description": "Initial kinetic energy"}
            },
            models=["work_energy_theorem"],
            tools=["algebraic_manipulation"],
            operations=["accumulate", "differentiate"],
            buckets=["accumulation", "conservation"],
            tags=["work-energy theorem", "change", "kinetic energy"]
        ))
        
        self.add_equation(Equation(
            id="gravitational_pe",
            name="Gravitational Potential Energy",
            formula="PE_g = m * g * h",
            description="Potential energy due to height in gravitational field",
            variables={
                "PE_g": {"unit": "J", "description": "Gravitational potential energy"},
                "m": {"unit": "kg", "description": "Mass"},
                "g": {"unit": "m/s²", "description": "Gravitational acceleration"},
                "h": {"unit": "m", "description": "Height above reference"}
            },
            models=["conservation_of_energy", "gravitation"],
            tools=["algebraic_manipulation"],
            operations=["accumulate"],
            buckets=["accumulation", "conservation"],
            tags=["potential energy", "gravity", "height", "conservation"]
        ))
        
        # =====================================================================
        # FORCE AND VECTOR EQUATIONS
        # =====================================================================
        
        self.add_equation(Equation(
            id="vector_components",
            name="Vector Resolution",
            formula="F_x = F * cos(θ), F_y = F * sin(θ)",
            description="Resolve a vector into x and y components",
            variables={
                "F_x": {"unit": "N", "description": "X-component of vector"},
                "F_y": {"unit": "N", "description": "Y-component of vector"},
                "F": {"unit": "N", "description": "Vector magnitude"},
                "θ": {"unit": "deg", "description": "Angle from positive x-axis"}
            },
            models=["newtonian_mechanics", "equilibrium_statics"],
            tools=["trigonometry", "vector_algebra"],
            operations=["transform"],
            buckets=["transformation", "geometry"],
            tags=["vector", "components", "resolution", "trig", "decompose"]
        ))
        
        self.add_equation(Equation(
            id="vector_magnitude",
            name="Vector Magnitude",
            formula="|F| = √(F_x² + F_y²)",
            description="Calculate magnitude from components",
            variables={
                "|F|": {"unit": "N", "description": "Vector magnitude"},
                "F_x": {"unit": "N", "description": "X-component"},
                "F_y": {"unit": "N", "description": "Y-component"}
            },
            models=["newtonian_mechanics"],
            tools=["trigonometry", "vector_algebra"],
            operations=["transform", "scale"],
            buckets=["transformation", "geometry"],
            tags=["magnitude", "vector", "pythagorean", "components"]
        ))
        
        self.add_equation(Equation(
            id="vector_angle",
            name="Vector Direction Angle",
            formula="θ = arctan(F_y / F_x)",
            description="Calculate direction angle from components",
            variables={
                "θ": {"unit": "deg", "description": "Direction angle"},
                "F_x": {"unit": "N", "description": "X-component"},
                "F_y": {"unit": "N", "description": "Y-component"}
            },
            models=["newtonian_mechanics"],
            tools=["trigonometry"],
            operations=["transform"],
            buckets=["transformation", "geometry"],
            tags=["angle", "direction", "vector", "arctan"]
        ))
        
        self.add_equation(Equation(
            id="newton_second_law",
            name="Newton's Second Law",
            formula="ΣF = m * a",
            description="Net force equals mass times acceleration",
            variables={
                "ΣF": {"unit": "N", "description": "Net force"},
                "m": {"unit": "kg", "description": "Mass"},
                "a": {"unit": "m/s²", "description": "Acceleration"}
            },
            models=["newtonian_mechanics", "dynamics"],
            tools=["algebraic_manipulation", "vector_algebra"],
            operations=["transform", "scale"],
            buckets=["dynamics"],
            tags=["newton", "force", "acceleration", "mass", "F=ma"]
        ))
        
        self.add_equation(Equation(
            id="friction_force",
            name="Friction Force",
            formula="f = μ * N",
            description="Friction force proportional to normal force",
            variables={
                "f": {"unit": "N", "description": "Friction force"},
                "μ": {"unit": "", "description": "Coefficient of friction"},
                "N": {"unit": "N", "description": "Normal force"}
            },
            models=["newtonian_mechanics", "dynamics"],
            tools=["algebraic_manipulation"],
            operations=["scale"],
            buckets=["dynamics"],
            tags=["friction", "normal force", "coefficient"]
        ))
        
        self.add_equation(Equation(
            id="weight_force",
            name="Weight Force",
            formula="W = m * g",
            description="Gravitational force on an object",
            variables={
                "W": {"unit": "N", "description": "Weight force"},
                "m": {"unit": "kg", "description": "Mass"},
                "g": {"unit": "m/s²", "description": "Gravitational acceleration"}
            },
            models=["newtonian_mechanics", "gravitation"],
            tools=["algebraic_manipulation"],
            operations=["scale"],
            buckets=["dynamics"],
            tags=["weight", "gravity", "mass", "force"]
        ))
        
        # =====================================================================
        # KINEMATICS EQUATIONS
        # =====================================================================
        
        self.add_equation(Equation(
            id="kinematic_velocity",
            name="Velocity with Constant Acceleration",
            formula="v = v₀ + a * t",
            description="Final velocity with constant acceleration",
            variables={
                "v": {"unit": "m/s", "description": "Final velocity"},
                "v₀": {"unit": "m/s", "description": "Initial velocity"},
                "a": {"unit": "m/s²", "description": "Acceleration"},
                "t": {"unit": "s", "description": "Time"}
            },
            models=["kinematics_constant_acceleration"],
            tools=["algebraic_manipulation"],
            operations=["accumulate", "scale"],
            buckets=["kinematics"],
            tags=["velocity", "acceleration", "time", "kinematics"]
        ))
        
        self.add_equation(Equation(
            id="kinematic_displacement",
            name="Displacement with Constant Acceleration",
            formula="Δx = v₀ * t + (1/2) * a * t²",
            description="Displacement with constant acceleration",
            variables={
                "Δx": {"unit": "m", "description": "Displacement"},
                "v₀": {"unit": "m/s", "description": "Initial velocity"},
                "t": {"unit": "s", "description": "Time"},
                "a": {"unit": "m/s²", "description": "Acceleration"}
            },
            models=["kinematics_constant_acceleration"],
            tools=["algebraic_manipulation"],
            operations=["accumulate"],
            buckets=["kinematics"],
            tags=["displacement", "position", "acceleration", "time"]
        ))
        
        self.add_equation(Equation(
            id="kinematic_v_squared",
            name="Velocity-Displacement Relation",
            formula="v² = v₀² + 2 * a * Δx",
            description="Relates velocity and displacement without time",
            variables={
                "v": {"unit": "m/s", "description": "Final velocity"},
                "v₀": {"unit": "m/s", "description": "Initial velocity"},
                "a": {"unit": "m/s²", "description": "Acceleration"},
                "Δx": {"unit": "m", "description": "Displacement"}
            },
            models=["kinematics_constant_acceleration"],
            tools=["algebraic_manipulation"],
            operations=["scale", "accumulate"],
            buckets=["kinematics"],
            tags=["velocity", "displacement", "acceleration", "no time"]
        ))
        
        self.add_equation(Equation(
            id="average_velocity",
            name="Average Velocity",
            formula="v_avg = Δx / Δt = (v₀ + v) / 2",
            description="Average velocity for constant acceleration",
            variables={
                "v_avg": {"unit": "m/s", "description": "Average velocity"},
                "Δx": {"unit": "m", "description": "Displacement"},
                "Δt": {"unit": "s", "description": "Time interval"},
                "v₀": {"unit": "m/s", "description": "Initial velocity"},
                "v": {"unit": "m/s", "description": "Final velocity"}
            },
            models=["kinematics_constant_acceleration"],
            tools=["algebraic_manipulation"],
            operations=["estimate"],
            buckets=["kinematics"],
            tags=["average", "velocity", "mean"]
        ))
        
        # =====================================================================
        # TRIGONOMETRY EQUATIONS
        # =====================================================================
        
        self.add_equation(Equation(
            id="cosine_definition",
            name="Cosine Function",
            formula="cos(θ) = adjacent / hypotenuse",
            description="Cosine ratio in right triangle",
            variables={
                "θ": {"unit": "deg", "description": "Angle"},
                "adjacent": {"unit": "any", "description": "Adjacent side"},
                "hypotenuse": {"unit": "any", "description": "Hypotenuse"}
            },
            models=["equilibrium_statics"],
            tools=["trigonometry"],
            operations=["scale"],
            buckets=["geometry"],
            tags=["cosine", "trig", "ratio", "triangle"]
        ))
        
        self.add_equation(Equation(
            id="sine_definition",
            name="Sine Function",
            formula="sin(θ) = opposite / hypotenuse",
            description="Sine ratio in right triangle",
            variables={
                "θ": {"unit": "deg", "description": "Angle"},
                "opposite": {"unit": "any", "description": "Opposite side"},
                "hypotenuse": {"unit": "any", "description": "Hypotenuse"}
            },
            models=["equilibrium_statics"],
            tools=["trigonometry"],
            operations=["scale"],
            buckets=["geometry"],
            tags=["sine", "trig", "ratio", "triangle"]
        ))
        
        self.add_equation(Equation(
            id="tangent_definition",
            name="Tangent Function",
            formula="tan(θ) = opposite / adjacent",
            description="Tangent ratio in right triangle",
            variables={
                "θ": {"unit": "deg", "description": "Angle"},
                "opposite": {"unit": "any", "description": "Opposite side"},
                "adjacent": {"unit": "any", "description": "Adjacent side"}
            },
            models=["equilibrium_statics"],
            tools=["trigonometry"],
            operations=["scale"],
            buckets=["geometry"],
            tags=["tangent", "trig", "ratio", "triangle"]
        ))
        
        self.add_equation(Equation(
            id="pythagorean_theorem",
            name="Pythagorean Theorem",
            formula="c² = a² + b²",
            description="Relation between sides of right triangle",
            variables={
                "c": {"unit": "any", "description": "Hypotenuse"},
                "a": {"unit": "any", "description": "Side a"},
                "b": {"unit": "any", "description": "Side b"}
            },
            models=[],
            tools=["trigonometry", "coordinate_geometry"],
            operations=["scale"],
            buckets=["geometry"],
            tags=["pythagorean", "triangle", "right angle", "distance"]
        ))
        
        # =====================================================================
        # POWER EQUATIONS
        # =====================================================================
        
        self.add_equation(Equation(
            id="power_average",
            name="Average Power",
            formula="P_avg = W / Δt",
            description="Average power as work per unit time",
            variables={
                "P_avg": {"unit": "W", "description": "Average power"},
                "W": {"unit": "J", "description": "Work done"},
                "Δt": {"unit": "s", "description": "Time interval"}
            },
            models=["work_energy_theorem"],
            tools=["algebraic_manipulation"],
            operations=["estimate", "scale"],
            buckets=["accumulation"],
            tags=["power", "work", "time", "rate"]
        ))
        
        self.add_equation(Equation(
            id="power_instantaneous",
            name="Instantaneous Power",
            formula="P = F * v * cos(θ)",
            description="Instantaneous power from force and velocity",
            variables={
                "P": {"unit": "W", "description": "Power"},
                "F": {"unit": "N", "description": "Force"},
                "v": {"unit": "m/s", "description": "Velocity"},
                "θ": {"unit": "deg", "description": "Angle between force and velocity"}
            },
            models=["work_energy_theorem"],
            tools=["trigonometry", "vector_algebra"],
            operations=["accumulate"],
            buckets=["accumulation"],
            tags=["power", "instantaneous", "force", "velocity"]
        ))
        
        # =====================================================================
        # MOMENTUM EQUATIONS
        # =====================================================================
        
        self.add_equation(Equation(
            id="momentum",
            name="Linear Momentum",
            formula="p = m * v",
            description="Linear momentum of an object",
            variables={
                "p": {"unit": "kg·m/s", "description": "Momentum"},
                "m": {"unit": "kg", "description": "Mass"},
                "v": {"unit": "m/s", "description": "Velocity"}
            },
            models=["conservation_of_momentum", "newtonian_mechanics"],
            tools=["algebraic_manipulation"],
            operations=["scale"],
            buckets=["dynamics", "conservation"],
            tags=["momentum", "mass", "velocity"]
        ))
        
        self.add_equation(Equation(
            id="impulse",
            name="Impulse-Momentum Theorem",
            formula="J = Δp = F_avg * Δt",
            description="Impulse equals change in momentum",
            variables={
                "J": {"unit": "N·s", "description": "Impulse"},
                "Δp": {"unit": "kg·m/s", "description": "Change in momentum"},
                "F_avg": {"unit": "N", "description": "Average force"},
                "Δt": {"unit": "s", "description": "Time interval"}
            },
            models=["conservation_of_momentum"],
            tools=["algebraic_manipulation"],
            operations=["accumulate"],
            buckets=["accumulation", "conservation"],
            tags=["impulse", "momentum", "force", "time"]
        ))
    
    def add_equation(self, equation: Equation):
        """Add an equation to the database."""
        self.equations[equation.id] = equation
    
    def get_equation(self, equation_id: str) -> Optional[Equation]:
        """Retrieve an equation by ID."""
        return self.equations.get(equation_id)
    
    def search_by_keywords(
        self, 
        keywords: List[str], 
        min_score: float = 0.3,
        limit: int = 10
    ) -> List[Tuple[Equation, float]]:
        """
        Search equations by keywords with fuzzy matching.
        Returns list of (equation, score) tuples sorted by score.
        """
        results = []
        
        for eq in self.equations.values():
            score = eq.matches_keywords(keywords)
            if score >= min_score:
                results.append((eq, score))
        
        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results[:limit]
    
    def search_by_model(self, model: str) -> List[Equation]:
        """Get all equations for a specific physics model."""
        return [eq for eq in self.equations.values() if model in eq.models]
    
    def search_by_tool(self, tool: str) -> List[Equation]:
        """Get all equations requiring a specific mathematical tool."""
        return [eq for eq in self.equations.values() if tool in eq.tools]
    
    def search_by_operation(self, operation: str) -> List[Equation]:
        """Get all equations for a specific primary operation."""
        return [eq for eq in self.equations.values() if operation in eq.operations]
    
    def search_by_bucket(self, bucket: str) -> List[Equation]:
        """Get all equations in a specific cognitive bucket."""
        return [eq for eq in self.equations.values() if bucket in eq.buckets]
    
    def get_variables_for_equation(self, equation_id: str) -> Optional[Dict[str, Dict[str, Any]]]:
        """Get variable definitions for an equation."""
        eq = self.get_equation(equation_id)
        return eq.variables if eq else None
    
    def find_equations_for_variables(
        self, 
        known_vars: List[str], 
        target_var: str
    ) -> List[Equation]:
        """
        Find equations that can solve for target variable given known variables.
        """
        candidates = []
        
        for eq in self.equations.values():
            eq_vars = set(eq.variables.keys())
            
            # Check if target variable is in equation
            if target_var not in eq_vars:
                continue
            
            # Check if we have enough known variables
            other_vars = eq_vars - {target_var}
            if other_vars.issubset(set(known_vars)):
                candidates.append(eq)
        
        return candidates
    
    def get_all_models(self) -> List[str]:
        """Get list of all unique models in database."""
        models = set()
        for eq in self.equations.values():
            models.update(eq.models)
        return sorted(list(models))
    
    def get_all_tools(self) -> List[str]:
        """Get list of all unique tools in database."""
        tools = set()
        for eq in self.equations.values():
            tools.update(eq.tools)
        return sorted(list(tools))
    
    def get_all_operations(self) -> List[str]:
        """Get list of all unique operations in database."""
        operations = set()
        for eq in self.equations.values():
            operations.update(eq.operations)
        return sorted(list(operations))


# Singleton instance
_equation_db: Optional[EquationDatabase] = None


def get_equation_database() -> EquationDatabase:
    """Get the singleton equation database instance."""
    global _equation_db
    if _equation_db is None:
        _equation_db = EquationDatabase()
    return _equation_db
