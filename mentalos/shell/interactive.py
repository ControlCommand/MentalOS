"""
MentalOS Imperative Shell

This module contains all side-effecting operations for MentalOS.
Following the functional architecture, I/O is isolated here while
all transformations remain pure in the core module.

The shell handles:
- User input/output (terminal interaction)
- Timing measurements
- Coordination of the pipeline flow
- Secondary operation processing (restarts at Bucket gate, gates 0-1 remain locked)
"""

from datetime import datetime

from mentalos.core.models import Session, Stack, ProblemPart, GateLog
from mentalos.core.pipeline import (
    initial_session,
    record_gate_answer,
    add_secondary_ops,
    pop_secondary_op,
    reset_session_to_gate,
    push_stack,
    pop_stack,
    is_stack_empty,
    get_current_gate_name,
    get_gate_prompt,
    is_execution_gate,
    is_primary_op_lock_gate,
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


def process_secondary_operations(
    session: Session,
    config: Config
) -> Session:
    """
    Process the queue of secondary operations after primary execution completes.
    
    Prompts user whether to process each secondary operation. If yes,
    resets the session to the Bucket gate (index 2) and continues.
    Gates 0-1 (Requested Output, Primary Operation) remain globally locked.
    
    Args:
        session: Current session state
        config: Configuration settings
    
    Returns:
        Final session after all secondary ops processed (or skipped)
    """
    current_session = session
    
    while current_session.secondary_ops:
        print(f"\nSecondary operations remaining: {current_session.secondary_ops}")
        proceed = get_user_input("Process next secondary operation? (y/n): ")
        
        if proceed.lower() != 'y':
            print("Skipping remaining secondary operations.")
            break
        
        # Pop the next secondary operation
        current_session, next_op = pop_secondary_op(current_session)
        
        if next_op is None:
            break
        
        print(f"\nProcessing secondary operation: {next_op}")
        print(f"Note: Requested Output and Primary Operation remain locked.")
        
        # Reset session to Bucket gate (index 2) for secondary ops
        current_session = reset_session_to_gate(
            current_session,
            config.secondary_op_start_gate_idx
        )
        
        # Continue the main pipeline loop from the reset gate
        # Process this secondary op through remaining gates
        while True:
            gate_name = get_current_gate_name(current_session, config)
            
            if gate_name is None:
                break
            
            current_session, answer = run_single_gate(current_session, gate_name, config)
            
            # No nested sub-ops during secondary ops for now
            # Just continue through the gates
        
        # Loop back to check for more secondary ops
    
    return current_session


def run_part_pipeline(
    part: ProblemPart,
    config: Config
) -> Session:
    """
    Run the complete gate pipeline for a single problem part.
    
    This is the main orchestration function that walks through all gates,
    handles secondary operations queue after primary completion.
    
    Args:
        part: The problem part to process
        config: Configuration settings
    
    Returns:
        Completed Session with all gate logs
    """
    session = initial_session(part)
    
    while True:
        # Get current gate name
        gate_name = get_current_gate_name(session, config)
        
        # Check if all gates completed
        if gate_name is None:
            # Check for secondary operations after Interpretation
            if session.secondary_ops:
                session = process_secondary_operations(session, config)
            break
        
        # Execute the current gate
        session, answer = run_single_gate(session, gate_name, config)
        
        # Handle secondary ops collection after Primary Operation Lock (gate index 1)
        if is_primary_op_lock_gate(gate_name):
            deferred_input = get_user_input(
                "List secondary operations to process later (comma separated) or press Enter: "
            )
            if deferred_input:
                session = add_secondary_ops(session, deferred_input)
    
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
