"""
MentalOS Core Pipeline Transformations

This module contains all pure functional transformations for the MentalOS pipeline.
No I/O occurs here - all functions take immutable data and return new immutable data.
Side effects are isolated to the shell layer.

The pipeline is organized as a series of composable transformations that each
handle one aspect of session state evolution.

Pipeline enforces priority-based workflow from DEFINITIONS.md:
1. Requested Output (globally locked after first pass)
2. Primary Operation Lock (Winner-Takes-All, globally locked)  
3. Secondary Operations Queue
4. For each operation: Bucket → Model → Tool → Execution → Interpretation
5. Dependency resolution blocks execution until all required variables exist
"""

from datetime import datetime
import math

from mentalos.core.models import Session, GateLog, Stack, ProblemPart, Variable
from mentalos.config.settings import Config, FORMULA_DATABASE, Formula


def initial_session(part: ProblemPart) -> Session:
    """
    Create a fresh Session for a new problem part.
    
    This initializes all tracking fields to empty/default values.
    The session starts at gate index 0 (first gate in sequence).
    """
    return Session(
        part_id=part.label,
        question=part.text,
        logs=(),
        secondary_ops=(),
        current_gate_idx=0,
        is_primary_lock_complete=False,
        locked_requested_output=None,
        locked_primary_operation=None,
        variable_catalog={},
        selected_formula_id=None,
        pending_dependencies=(),
    )


def record_gate_answer(
    session: Session,
    gate_name: str,
    answer: str,
    elapsed_seconds: float
) -> Session:
    """
    Record a gate interaction by appending a new GateLog.
    
    This creates a new Session with the log entry added and advances
    the current gate index. The original session remains unchanged.
    
    For gates 0-1 (Requested Output, Primary Operation Lock), also stores
    the locked values that persist for all secondary operations.
    
    Args:
        session: Current session state
        gate_name: Name of the gate being recorded
        answer: User's response to the gate prompt
        elapsed_seconds: Time taken to respond
    
    Returns:
        New Session with updated logs and incremented gate index
    """
    new_log = GateLog(
        gate=gate_name,
        answer=answer,
        time_sec=elapsed_seconds
    )
    
    # Determine if we're completing the primary lock (after gate 1)
    new_gate_idx = session.current_gate_idx + 1
    is_lock_complete = session.is_primary_lock_complete or (new_gate_idx >= 2)
    
    # Store locked values for gates 0 and 1
    locked_req_output = session.locked_requested_output
    locked_prim_op = session.locked_primary_operation
    
    if session.current_gate_idx == 0:  # Requested Output gate
        locked_req_output = answer
    elif session.current_gate_idx == 1:  # Primary Operation Lock gate
        locked_prim_op = answer
    
    return Session(
        part_id=session.part_id,
        question=session.question,
        logs=(*session.logs, new_log),
        secondary_ops=session.secondary_ops,
        current_gate_idx=new_gate_idx,
        is_primary_lock_complete=is_lock_complete,
        locked_requested_output=locked_req_output,
        locked_primary_operation=locked_prim_op,
        variable_catalog=session.variable_catalog,
        selected_formula_id=session.selected_formula_id,
        pending_dependencies=session.pending_dependencies,
    )


def add_secondary_ops(session: Session, ops_string: str) -> Session:
    """
    Parse and add secondary operations from user input.
    
    Takes a comma-separated string of operations and appends them
    to the secondary_ops queue in the session.
    
    Args:
        session: Current session state
        ops_string: Comma-separated list of operation descriptions
    
    Returns:
        New Session with updated secondary_ops tuple
    """
    # Split by comma, strip whitespace, filter empty strings
    new_ops = tuple(
        op.strip() for op in ops_string.split(',')
        if op.strip()
    )
    return Session(
        part_id=session.part_id,
        question=session.question,
        logs=session.logs,
        secondary_ops=(*session.secondary_ops, *new_ops),
        current_gate_idx=session.current_gate_idx,
        is_primary_lock_complete=session.is_primary_lock_complete,
        locked_requested_output=session.locked_requested_output,
        locked_primary_operation=session.locked_primary_operation,
        variable_catalog=session.variable_catalog,
        selected_formula_id=session.selected_formula_id,
        pending_dependencies=session.pending_dependencies,
    )


def pop_secondary_op(session: Session) -> tuple[Session, str | None]:
    """
    Remove and return the next secondary operation from the queue.
    
    Uses FIFO ordering - first secondary operation is processed first.
    
    Args:
        session: Current session state
    
    Returns:
        Tuple of (new Session without the op, the popped operation or None if empty)
    """
    if not session.secondary_ops:
        return session, None
    
    next_op = session.secondary_ops[0]
    remaining = session.secondary_ops[1:]
    
    return Session(
        part_id=session.part_id,
        question=session.question,
        logs=session.logs,
        secondary_ops=remaining,
        current_gate_idx=session.current_gate_idx,
        is_primary_lock_complete=session.is_primary_lock_complete,
        locked_requested_output=session.locked_requested_output,
        locked_primary_operation=session.locked_primary_operation,
        variable_catalog=session.variable_catalog,
        selected_formula_id=session.selected_formula_id,
        pending_dependencies=session.pending_dependencies,
    ), next_op


def reset_session_to_gate(session: Session, gate_idx: int) -> Session:
    """
    Reset a session to restart from a specific gate index.
    
    Used when processing secondary operations to restart the pipeline
    at the Bucket gate (index 2). Gates 0-1 remain locked.
    
    Args:
        session: Current session state
        gate_idx: Index to reset to
    
    Returns:
        New Session with current_gate_idx set to gate_idx
    """
    return Session(
        part_id=session.part_id,
        question=session.question,
        logs=session.logs,
        secondary_ops=session.secondary_ops,
        current_gate_idx=gate_idx,
        is_primary_lock_complete=session.is_primary_lock_complete,
        locked_requested_output=session.locked_requested_output,
        locked_primary_operation=session.locked_primary_operation,
        variable_catalog=session.variable_catalog,
        selected_formula_id=None,  # Reset formula selection for new operation
        pending_dependencies=(),
    )


def select_formula_in_session(session: Session, formula_id: str) -> Session:
    """
    Pure function: Select a formula from the database for the current operation.
    
    This sets the formula that will be used for calculation and identifies
    which variables are required (pending dependencies).
    """
    formula = next((f for f in FORMULA_DATABASE if f.id == formula_id), None)
    if formula is None:
        raise ValueError(f"Formula '{formula_id}' not found in database")
    
    return Session(
        part_id=session.part_id,
        question=session.question,
        logs=session.logs,
        secondary_ops=session.secondary_ops,
        current_gate_idx=session.current_gate_idx,
        is_primary_lock_complete=session.is_primary_lock_complete,
        locked_requested_output=session.locked_requested_output,
        locked_primary_operation=session.locked_primary_operation,
        variable_catalog=session.variable_catalog,
        selected_formula_id=formula_id,
        pending_dependencies=formula.required_vars,
    )


def add_variable_to_catalog(session: Session, variable: Variable) -> Session:
    """
    Pure function: Add or update a variable in the catalog.
    
    The variable catalog is the single source of truth for all values.
    """
    new_catalog = {**session.variable_catalog, variable.name: variable}
    return Session(
        part_id=session.part_id,
        question=session.question,
        logs=session.logs,
        secondary_ops=session.secondary_ops,
        current_gate_idx=session.current_gate_idx,
        is_primary_lock_complete=session.is_primary_lock_complete,
        locked_requested_output=session.locked_requested_output,
        locked_primary_operation=session.locked_primary_operation,
        variable_catalog=new_catalog,
        selected_formula_id=session.selected_formula_id,
        pending_dependencies=session.pending_dependencies,
    )


def get_missing_dependencies(session: Session) -> tuple[str, ...]:
    """
    Pure function: Check which required variables are missing from the catalog.
    
    Returns tuple of variable names that must be calculated before execution can proceed.
    """
    if session.selected_formula_id is None:
        return ()
    
    formula = next((f for f in FORMULA_DATABASE if f.id == session.selected_formula_id), None)
    if formula is None:
        return ()
    
    missing = tuple(
        var for var in formula.required_vars 
        if var not in session.variable_catalog
    )
    return missing


def execute_calculation(session: Session) -> tuple[Session, float | None, str | None]:
    """
    Pure function: Execute the selected formula if all dependencies are met.
    
    Returns (new_session, result_value, error_message) where:
    - result_value is None if dependencies missing or error occurred
    - error_message contains description of what went wrong (if any)
    
    This is the computational core that evaluates the python expression safely.
    """
    if session.selected_formula_id is None:
        return session, None, "No formula selected"
    
    missing = get_missing_dependencies(session)
    if missing:
        # Cannot execute yet - dependencies missing
        return session, None, f"Missing dependencies: {', '.join(missing)}"
    
    formula = next((f for f in FORMULA_DATABASE if f.id == session.selected_formula_id), None)
    if formula is None:
        return session, None, "Formula not found"
    
    # Build evaluation context from variable catalog
    eval_context = {
        "math": math,
        **{name: var.value for name, var in session.variable_catalog.items()}
    }
    
    try:
        result = eval(formula.python_expr, {"__builtins__": {}}, eval_context)
        
        # Store result in catalog
        result_var = Variable(
            name=formula.result_var,
            value=float(result),
            unit="",  # Would need unit tracking system
            formula_id=formula.id,
            source="calculated",
        )
        
        new_session = add_variable_to_catalog(session, result_var)
        return new_session, float(result), None
        
    except Exception as e:
        # Return session unchanged, no result
        return session, None, f"Calculation error: {str(e)}"


# Stack management functions - pure, immutable operations

def push_stack(stack: Stack, session: Session) -> Stack:
    """
    Push a session onto the call stack.
    
    The new session becomes the top of stack (index 0).
    
    Args:
        stack: Current stack (tuple of Sessions)
        session: Session to push
    
    Returns:
        New stack with session prepended
    """
    return (session, *stack)


def pop_stack(stack: Stack) -> tuple[Session, Stack]:
    """
    Pop the top session from the call stack.
    
    Args:
        stack: Current stack (must not be empty)
    
    Returns:
        Tuple of (top session, remaining stack)
    
    Raises:
        IndexError: If stack is empty
    """
    if not stack:
        raise IndexError("Cannot pop from empty stack")
    return stack[0], stack[1:]


def is_stack_empty(stack: Stack) -> bool:
    """Check if the call stack is empty."""
    return len(stack) == 0


def get_current_gate_name(session: Session, config: Config) -> str | None:
    """
    Get the name of the current gate based on session's gate index.
    
    Returns None if the index is out of bounds (all gates completed).
    
    Args:
        session: Current session state
        config: Configuration containing gate sequence
    
    Returns:
        Gate name string or None if complete
    """
    if session.current_gate_idx >= len(config.gate_sequence):
        return None
    return config.gate_sequence[session.current_gate_idx]


def get_gate_prompt(gate_name: str, config: Config) -> str:
    """
    Retrieve the prompt text for a specific gate.
    
    Args:
        gate_name: Name of the gate
        config: Configuration containing gate prompts
    
    Returns:
        Prompt string for the gate
    
    Raises:
        KeyError: If gate_name not found in config
    """
    return config.gate_prompts[gate_name]


def is_execution_gate(gate_name: str) -> bool:
    """Check if the given gate is the Execution gate."""
    return gate_name == "Execution"


def is_primary_op_lock_gate(gate_name: str) -> bool:
    """Check if the given gate is the Primary Operation Lock gate."""
    return gate_name == "Primary Operation Lock"


def is_interpretation_gate(gate_name: str) -> bool:
    """Check if the given gate is the Interpretation gate."""
    return gate_name == "Interpretation"


def format_session_summary(session: Session) -> str:
    """
    Create a human-readable summary of a session for audit purposes.
    
    Includes part ID, question, and all gate logs with timings.
    """
    lines = [
        f"=== Part {session.part_id} ===",
        f"Question: {session.question}",
        "",
        "Gate Logs:",
    ]
    
    for log in session.logs:
        lines.append(f"  [{log.gate}] ({log.time_sec:.2f}s): {log.answer}")
    
    if session.locked_requested_output:
        lines.append(f"\nLocked Requested Output: {session.locked_requested_output}")
    
    if session.locked_primary_operation:
        lines.append(f"Locked Primary Operation: {session.locked_primary_operation}")
    
    if session.secondary_ops:
        lines.append(f"\nPending Secondary Ops: {', '.join(session.secondary_ops)}")
    
    if session.variable_catalog:
        lines.append("\nVariable Catalog:")
        for name, var in session.variable_catalog.items():
            lines.append(f"  {name} = {var.value} {var.unit} ({var.source})")
    
    return "\n".join(lines)


def get_all_formulas() -> tuple[Formula, ...]:
    """Pure function: Return all available formulas."""
    return FORMULA_DATABASE


def get_formulas_for_operation(operation: str) -> tuple[Formula, ...]:
    """
    Filter formulas relevant to a specific operation type.
    
    Maps operations to likely formula categories.
    """
    op_to_category = {
        "Accumulate": ["Mechanics", "Energy"],
        "Transform": ["Vectors"],
        "Change": ["Kinematics", "Mechanics"],
        "Estimate": ["Energy"],
    }
    
    relevant_categories = op_to_category.get(operation, [])
    if not relevant_categories:
        return FORMULA_DATABASE
    
    return tuple(f for f in FORMULA_DATABASE if f.category in relevant_categories)
