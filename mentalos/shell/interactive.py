"""
MentalOS Imperative Shell

This module contains all side-effecting operations for MentalOS.
Following the functional architecture, I/O is isolated here while
all transformations remain pure in the core module.

The shell handles:
- User input/output (terminal interaction)
- Timing measurements
- Coordination of the pipeline flow
- Sub-operation recursion via call stack
- Deferred operation processing
"""

from datetime import datetime

from mentalos.core.models import Session, Stack, ProblemPart, GateLog
from mentalos.core.pipeline import (
    initial_session,
    record_gate_answer,
    add_deferred_ops,
    pop_deferred_op,
    reset_session_to_gate,
    inject_sub_result,
    push_stack,
    pop_stack,
    is_stack_empty,
    get_current_gate_name,
    get_gate_prompt,
    is_execution_gate,
    is_primary_op_lock_gate,
    is_interpretation_gate,
    should_trigger_sub_operation,
    should_return_from_sub_op,
    format_session_summary,
)
from mentalos.config.settings import Config


def get_user_input(prompt: str) -> str:
    """
    Get input from the user via terminal.
    
    Pure wrapper around input() for easier testing and consistency.
    """
    try:
        return input(prompt).strip()
    except EOFError:
        # Handle Ctrl+D gracefully
        return ""


def measure_timed_input(prompt: str) -> tuple[str, float]:
    """
    Display prompt, start timer, wait for user input, return answer and elapsed time.
    
    This is the only place where timing occurs - keeping it isolated.
    """
    print(prompt)
    start = datetime.now()
    answer = get_user_input("> ")
    end = datetime.now()
    elapsed = (end - start).total_seconds()
    return answer, elapsed


def collect_problem_parts() -> tuple[ProblemPart, ...]:
    """
    Interactively collect multi-part problem structure from user.
    
    First gets the full problem text, then asks for sub-question labels
    and their exact text. Returns an ordered tuple of ProblemParts.
    """
    print("\n" + "=" * 60)
    print("MENTALOS - Cognitive Training Tool")
    print("=" * 60)
    print("\nPaste the entire problem statement below.")
    print("(Press Enter twice on an empty line to finish)\n")
    
    # Collect full problem text
    lines = []
    while True:
        line = get_user_input("")
        if line == "":
            break
        lines.append(line)
    
    problem_text = "\n".join(lines)
    
    print(f"\nProblem received ({len(lines)} lines).")
    print("\nNow define the sub-questions (parts a, b, c, etc.)")
    
    parts = []
    while True:
        label = get_user_input("\nEnter part label (e.g., 'a', 'b', 'c') or 'done' to finish: ")
        if label.lower() in ('done', 'exit', 'quit'):
            break
        if not label:
            print("Please enter a valid label.")
            continue
        
        print(f"\nEnter the exact text for part ({label}):")
        print("(Press Enter twice on empty line to finish this part)\n")
        
        part_lines = []
        while True:
            line = get_user_input("")
            if line == "":
                break
            part_lines.append(line)
        
        part_text = "\n".join(part_lines)
        if part_text:
            parts.append(ProblemPart(label=label, text=part_text))
            print(f"Part ({label}) recorded.")
        else:
            print("Part text cannot be empty. Please try again.")
    
    if not parts:
        # If no parts defined, treat whole problem as single part 'a'
        print("\nNo sub-parts defined. Treating entire problem as part (a).")
        return (ProblemPart(label='a', text=problem_text),)
    
    return tuple(parts)


def run_single_gate(
    session: Session,
    gate_name: str,
    config: Config
) -> tuple[Session, str]:
    """
    Execute a single gate interaction with the user.
    
    Displays the gate prompt, measures response time, and records the answer.
    Handles special commands like :defer during Execution gate.
    
    Args:
        session: Current session state
        gate_name: Name of the gate to execute
        config: Configuration settings
    
    Returns:
        Tuple of (updated Session, raw answer string)
    """
    prompt = get_gate_prompt(gate_name, config)
    print(f"\n=== {gate_name} ===")
    print(prompt)
    
    answer, elapsed = measure_timed_input("")
    updated_session = record_gate_answer(session, gate_name, answer, elapsed)
    
    return updated_session, answer


def run_sub_operation_pipeline(
    sub_op_desc: str,
    parent_session: Session,
    stack: Stack,
    config: Config
) -> tuple[Session, Stack]:
    """
    Run a shortened pipeline for a sub-operation.
    
    Creates a new session for the sub-task, runs through the abbreviated
    gate sequence (Intent → Primary Op → Tool → Execution), and returns
    the result. Supports nested :defer commands recursively.
    
    Args:
        sub_op_desc: Description of the sub-operation to perform
        parent_session: The parent session that triggered this sub-op
        stack: Current call stack
        config: Configuration settings
    
    Returns:
        Tuple of (parent session with injected result, updated stack)
    """
    # Create a sub-operation session using parent's question context
    sub_session = Session(
        part_id=f"{parent_session.part_id}.sub",
        question=f"Sub-operation: {sub_op_desc}",
        logs=(),
        deferred_ops=(),
        current_gate_idx=0,
        sub_operation_result=None,
        parent_execution_answer=None,
    )
    
    # Push parent onto stack
    new_stack = push_stack(stack, parent_session)
    
    # Run the sub-operation gates
    sub_op_gate_names = config.sub_op_gates
    
    for gate_name in sub_op_gate_names:
        # Check if we've completed all gates
        current_gate = get_current_gate_name(sub_session, config)
        if current_gate is None:
            break
        
        # Execute the gate
        sub_session, answer = run_single_gate(sub_session, gate_name, config)
        
        # Handle :defer recursively
        if is_execution_gate(gate_name) and should_trigger_sub_operation(answer):
            nested_desc = get_user_input("Describe nested sub-operation: ")
            sub_session, new_stack = run_sub_operation_pipeline(
                nested_desc, sub_session, new_stack, config
            )
            # Inject the nested result
            sub_session = inject_sub_result(sub_session, sub_session.sub_operation_result)
        
        # Handle :return command
        if should_return_from_sub_op(answer):
            # Pop parent from stack and return
            popped_parent, remaining_stack = pop_stack(new_stack)
            result_text = format_session_summary(sub_session)
            popped_parent = inject_sub_result(popped_parent, result_text)
            return popped_parent, remaining_stack
    
    # Sub-operation completed normally - extract result from Execution log
    execution_result = "Sub-operation completed"
    for log in reversed(sub_session.logs):
        if log.gate == "Execution":
            execution_result = log.answer
            break
    
    # Pop parent from stack
    popped_parent, remaining_stack = pop_stack(new_stack)
    
    # Inject result into parent
    popped_parent = inject_sub_result(popped_parent, execution_result)
    
    return popped_parent, remaining_stack


def process_deferred_operations(
    session: Session,
    stack: Stack,
    config: Config
) -> tuple[Session, Stack]:
    """
    Process the queue of deferred operations after primary execution completes.
    
    Prompts user whether to process each deferred operation. If yes,
    resets the session to the configured start gate and continues.
    
    Args:
        session: Current session state
        stack: Current call stack
        config: Configuration settings
    
    Returns:
        Tuple of (final session, unchanged stack)
    """
    current_session = session
    
    while current_session.deferred_ops:
        print(f"\nDeferred operations remaining: {current_session.deferred_ops}")
        proceed = get_user_input("Process next deferred operation? (y/n): ")
        
        if proceed.lower() != 'y':
            print("Skipping remaining deferred operations.")
            break
        
        # Pop the next deferred operation
        current_session, next_op = pop_deferred_op(current_session)
        
        if next_op is None:
            break
        
        print(f"\nProcessing deferred operation: {next_op}")
        
        # Reset session to the configured start gate for deferred ops
        current_session = reset_session_to_gate(
            current_session,
            config.deferred_start_gate_idx
        )
        
        # Continue the main pipeline loop from the reset gate
        # This is handled by returning to the caller which continues the loop
        return current_session, stack
    
    return current_session, stack


def run_part_pipeline(
    part: ProblemPart,
    config: Config
) -> Session:
    """
    Run the complete gate pipeline for a single problem part.
    
    This is the main orchestration function that walks through all gates,
    handles :defer sub-operations, and processes deferred operations queue.
    
    Args:
        part: The problem part to process
        config: Configuration settings
    
    Returns:
        Completed Session with all gate logs
    """
    session = initial_session(part)
    stack: Stack = ()
    
    while True:
        # Get current gate name
        gate_name = get_current_gate_name(session, config)
        
        # Check if all gates completed
        if gate_name is None:
            # Check for deferred operations after Interpretation
            if session.deferred_ops:
                session, stack = process_deferred_operations(session, stack, config)
                # If we reset for deferred ops, continue the loop
                if session.current_gate_idx < len(config.gate_sequence):
                    continue
            break
        
        # Execute the current gate
        session, answer = run_single_gate(session, gate_name, config)
        
        # Handle :defer command during Execution gate
        if is_execution_gate(gate_name) and should_trigger_sub_operation(answer):
            sub_op_desc = get_user_input("Describe sub-operation: ")
            session, stack = run_sub_operation_pipeline(
                sub_op_desc, session, stack, config
            )
            # After returning, we need to record the sub-result as the execution answer
            # Find the elapsed time from the original Execution gate attempt
            exec_log = None
            for log in reversed(session.logs):
                if log.gate == "Execution":
                    exec_log = log
                    break
            
            if exec_log:
                # Update the execution log with the sub-operation result
                # We need to replace the last log entry
                old_logs = session.logs[:-1]
                new_log = GateLog(
                    gate="Execution",
                    answer=f"[Sub-operation result]: {session.sub_operation_result}",
                    time_sec=exec_log.time_sec
                )
                session = Session(
                    part_id=session.part_id,
                    question=session.question,
                    logs=(*old_logs, new_log),
                    deferred_ops=session.deferred_ops,
                    current_gate_idx=session.current_gate_idx,
                    sub_operation_result=None,  # Clear after injecting
                    parent_execution_answer=session.parent_execution_answer,
                )
        
        # Handle deferred ops collection after Primary Operation Lock
        if is_primary_op_lock_gate(gate_name):
            deferred_input = get_user_input(
                "List secondary operations to defer (comma separated) or press Enter: "
            )
            if deferred_input:
                session = add_deferred_ops(session, deferred_input)
        
        # Handle :return command (for sub-operations)
        if should_return_from_sub_op(answer):
            if not is_stack_empty(stack):
                parent_session, stack = pop_stack(stack)
                parent_session = inject_sub_result(
                    parent_session,
                    f"Returned from sub-operation at {gate_name}"
                )
                return parent_session
            else:
                print("Warning: :return used but no parent session exists.")
    
    return session


def display_results(sessions: tuple[Session, ...], audit_feedback: str | None) -> None:
    """
    Display final results including all session logs and audit feedback.
    
    Formats output in a readable table-like structure for review.
    """
    print("\n" + "=" * 60)
    print("MENTALOS SESSION COMPLETE")
    print("=" * 60)
    
    # Display audit feedback first if available
    if audit_feedback:
        print("\n" + audit_feedback)
    
    # Display detailed logs for each part
    print("\n" + "=" * 60)
    print("DETAILED GATE LOGS")
    print("=" * 60)
    
    for session in sessions:
        print(format_session_summary(session))
        print("-" * 40)
    
    print("\nSession complete. Thank you for using MentalOS.")
