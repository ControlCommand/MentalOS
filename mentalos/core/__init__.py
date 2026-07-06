# MentalOS Core Package
"""
Pure functional transformations and immutable data models.
No I/O occurs in this module - all side effects are isolated to the shell.
"""

from mentalos.core.models import (
    GateLog,
    Variable,
    ProblemPart,
    Session,
    Stack,
    AuditResult,
    PipelineResult,
    SubOperationResult,
)
from mentalos.core.pipeline import (
    initial_session,
    record_gate_answer,
    add_secondary_ops,
    pop_secondary_op,
    reset_session_to_gate,
    select_formula_in_session,
    add_variable_to_catalog,
    get_missing_dependencies,
    execute_calculation,
    push_stack,
    pop_stack,
    is_stack_empty,
    get_current_gate_name,
    get_gate_prompt,
    format_session_summary,
    get_all_formulas,
    get_formulas_for_operation,
    create_sub_operation_session,
    complete_sub_operation,
    inject_sub_result,
)

__all__ = [
    # Models
    "GateLog",
    "Variable",
    "ProblemPart",
    "Session",
    "Stack",
    "AuditResult",
    "PipelineResult",
    "SubOperationResult",
    # Pipeline functions
    "initial_session",
    "record_gate_answer",
    "add_secondary_ops",
    "pop_secondary_op",
    "reset_session_to_gate",
    "select_formula_in_session",
    "add_variable_to_catalog",
    "get_missing_dependencies",
    "execute_calculation",
    "push_stack",
    "pop_stack",
    "is_stack_empty",
    "get_current_gate_name",
    "get_gate_prompt",
    "format_session_summary",
    "get_all_formulas",
    "get_formulas_for_operation",
    "create_sub_operation_session",
    "complete_sub_operation",
    "inject_sub_result",
]
