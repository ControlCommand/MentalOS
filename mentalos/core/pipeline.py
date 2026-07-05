"""
MentalOS Core Pipeline Transformations

This module contains all pure functional transformations for the MentalOS pipeline.
No I/O occurs here - all functions take immutable data and return new immutable data.
Side effects are isolated to the shell layer.

The pipeline is organized as a series of composable transformations that each
handle one aspect of session state evolution.
"""

from datetime import datetime

from mentalos.core.models import Session, GateLog, Stack, ProblemPart
from mentalos.config.settings import Config


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
    )


def inject_sub_result(session: Session, result: str) -> Session:
    """
    Inject a sub-operation result into the parent session.
    
    Called when returning from a sub-operation. The result
    becomes the execution answer for the parent's Execution gate.
    
    Args:
        session: Parent session state
        result: Result string from the sub-operation
    
    Returns:
        New Session with sub_operation_result set
    """
    return Session(
        part_id=session.part_id,
        question=session.question,
        logs=session.logs,
        secondary_ops=session.secondary_ops,
        current_gate_idx=session.current_gate_idx,
        is_primary_lock_complete=session.is_primary_lock_complete,
        locked_requested_output=session.locked_requested_output,
        locked_primary_operation=session.locked_primary_operation,
    )


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


def should_trigger_sub_operation(answer: str) -> bool:
    """
    Check if the user's answer indicates a sub-operation trigger.
    
    The special command ':sub' signals that the current task requires
    a nested sub-operation to complete first.
    """
    return answer.strip().lower() == ":sub"


def should_return_from_sub_op(answer: str) -> bool:
    """
    Check if the user wants to return from a sub-operation.
    
    The special command ':return' completes the sub-operation and
    returns control to the parent session.
    """
    return answer.strip().lower() == ":return"


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
    
    return "\n".join(lines)
