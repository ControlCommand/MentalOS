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
        deferred_ops: Queue of operations deferred for later processing
        current_gate_idx: Index into the gate_sequence for next gate to process
        sub_operation_result: Result from a sub-operation if this session was a sub-task
        parent_execution_answer: Answer from parent session when returning from :defer
    """
    part_id: str
    question: str
    logs: tuple[GateLog, ...] = ()
    deferred_ops: tuple[str, ...] = ()
    current_gate_idx: int = 0
    sub_operation_result: str | None = None
    parent_execution_answer: str | None = None


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
