"""
MentalOS Core Data Models

This module defines all immutable data structures used throughout MentalOS.
Using frozen dataclasses and NamedTuple ensures no accidental mutation occurs
in the pure functional layers. All state changes happen via creating new instances.

The architecture groups related data into cohesive units that flow through
the pipeline transformations.
"""

from dataclasses import dataclass, field
from typing import NamedTuple
from datetime import datetime


@dataclass(frozen=True)
class GateLog:
    """
    Immutable record of a single gate interaction.
    
    Captures the gate name, user's answer, and elapsed time for audit purposes.
    """
    gate: str
    answer: str
    time_sec: float


@dataclass(frozen=True)
class Variable:
    """
    Immutable record of a calculated or given variable.
    
    Single source of truth for all variables in the catalog.
    """
    name: str  # e.g., "F_parallel", "d", "W"
    value: float
    unit: str
    formula_id: str | None = None  # Which formula produced this (if calculated)
    source: str = "given"  # "given", "calculated", "derived"


@dataclass(frozen=True)
class ProblemPart:
    """
    Represents a single sub-question (a, b, c, etc.) of a multi-part problem.
    
    The label identifies the part (e.g., 'a', 'b'), and text contains the
    exact question content.
    """
    label: str
    text: str


@dataclass(frozen=True)
class Session:
    """
    Complete immutable state of a processing session for one problem part.
    
    This is the primary data structure that flows through the pipeline.
    Each transformation returns a new Session instance rather than mutating.
    
    Fields:
        part_id: Label of the current problem part (e.g., 'a', 'b')
        question: The full text of this part's question
        logs: Tuple of GateLog entries accumulated so far
        secondary_ops: Queue of secondary operations to process after primary completes
        current_gate_idx: Index into the gate_sequence for next gate to process
        is_primary_lock_complete: Whether Primary Operation Lock has been completed (gates 0-1 are globally locked)
        locked_requested_output: The locked Requested Output value (None until gate 0 complete)
        locked_primary_operation: The locked Primary Operation value (None until gate 1 complete)
        variable_catalog: Dict of variable name -> Variable (single source of truth)
        selected_formula_id: ID of formula selected for current operation (if any)
        pending_dependencies: Tuple of variable names still needed before execution
    """
    part_id: str
    question: str
    logs: tuple[GateLog, ...] = ()
    secondary_ops: tuple[str, ...] = ()
    current_gate_idx: int = 0
    is_primary_lock_complete: bool = False
    locked_requested_output: str | None = None
    locked_primary_operation: str | None = None
    variable_catalog: dict[str, Variable] = field(default_factory=dict)
    selected_formula_id: str | None = None
    pending_dependencies: tuple[str, ...] = ()


# Type alias for the immutable call stack
# Stack is a tuple of Sessions, with newest at index 0 (top of stack)
Stack = tuple[Session, ...]


@dataclass(frozen=True)
class AuditResult:
    """
    Result from the LLM-powered audit phase.
    
    Contains both the raw LLM feedback and a formatted summary.
    """
    feedback: str
    success: bool
    error_message: str | None = None


@dataclass(frozen=True)
class PipelineResult:
    """
    Final result after processing all parts of a problem.
    
    Aggregates all session data and audit results for display.
    """
    problem_text: str
    sessions: tuple[Session, ...]
    audit_result: AuditResult | None

