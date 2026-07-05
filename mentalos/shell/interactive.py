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
- Variable catalog management and formula selection
- Dependency-aware execution blocking
"""

from datetime import datetime

from mentalos.core.models import Session, Stack, ProblemPart, GateLog, Variable
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
    get_all_formulas,
    get_formulas_for_operation,
    push_stack,
    pop_stack,
    is_stack_empty,
    get_current_gate_name,
    get_gate_prompt,
    is_execution_gate,
    is_primary_op_lock_gate,
    format_session_summary,
)
from mentalos.config.settings import Config, UNITS


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


def display_formula_menu(formulas, operation: str = "") -> None:
    """Display available formulas in a numbered menu."""
    print(f"\n{'='*50}")
    if operation:
        print(f"Available Formulas for '{operation}':")
    else:
        print("Available Formulas:")
    print(f"{'='*50}")
    
    for i, formula in enumerate(formulas, 1):
        print(f"  [{i}] {formula.name}")
        print(f"      Equation: {formula.equation}")
        print(f"      Requires: {', '.join(formula.required_vars)}")
        print()


def select_formula_interactive(session: Session, operation: str) -> Session:
    """
    Interactive formula selection with dependency awareness.
    
    Shows available formulas, lets user pick one, then checks for missing variables.
    If variables are missing, prompts user to add them first.
    """
    formulas = get_formulas_for_operation(operation)
    
    while True:
        display_formula_menu(formulas, operation)
        
        # Show current variable catalog
        if session.variable_catalog:
            print("\nCurrent Variables in Catalog:")
            for name, var in session.variable_catalog.items():
                print(f"  {name} = {var.value} {var.unit}")
        else:
            print("\nVariable Catalog: (empty)")
        
        choice = get_user_input("\nSelect formula number (or 'list' to see all, 'skip' to skip): ")
        
        if choice.lower() == 'skip':
            print("Skipping formula selection.")
            return session
        
        if choice.lower() == 'list':
            formulas = get_all_formulas()
            continue
        
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(formulas):
                selected_formula = formulas[idx]
                session = select_formula_in_session(session, selected_formula.id)
                
                # Check for missing dependencies
                missing = get_missing_dependencies(session)
                if missing:
                    print(f"\n⚠️  Missing dependencies: {', '.join(missing)}")
                    print("You must add these variables before execution.")
                    
                    # Prompt to add missing variables
                    for var_name in missing:
                        print(f"\n--- Add Variable: {var_name} ---")
                        value_str = get_user_input(f"Enter numeric value for {var_name}: ")
                        unit = get_user_input(f"Enter unit for {var_name} (e.g., N, m, kg): ")
                        
                        try:
                            value = float(value_str)
                            var = Variable(name=var_name, value=value, unit=unit, source="given")
                            session = add_variable_to_catalog(session, var)
                            print(f"✓ Added {var_name} = {value} {unit}")
                        except ValueError:
                            print(f"Invalid value for {var_name}. Skipping.")
                
                return session
            else:
                print("Invalid selection. Try again.")
        except ValueError:
            print("Please enter a number.")


def run_execution_gate(session: Session) -> tuple[Session, str]:
    """
    Execute the Execution gate with dependency checking.
    
    Blocks calculation until all required variables are present.
    Shows formula, required variables, and current catalog status.
    """
    print("\n=== Execution ===")
    
    if session.selected_formula_id is None:
        print("No formula selected. Cannot execute.")
        answer = get_user_input("> ")
        return session, answer
    
    # Get formula info
    formula = next((f for f in get_all_formulas() if f.id == session.selected_formula_id), None)
    if formula is None:
        print("Formula not found.")
        answer = get_user_input("> ")
        return session, answer
    
    print(f"Formula: {formula.equation}")
    print(f"Required variables: {', '.join(formula.required_vars)}")
    
    # Check dependencies
    missing = get_missing_dependencies(session)
    
    if missing:
        print(f"\n❌ BLOCKED: Missing dependencies: {', '.join(missing)}")
        print("\nYou must resolve these variables first:")
        
        for var_name in missing:
            print(f"\n--- Resolve: {var_name} ---")
            print("Options:")
            print("  1. Enter value directly (if given in problem)")
            print("  2. Calculate from another formula (select 'defer')")
            
            choice = get_user_input("\nChoose (1/2/defer): ")
            
            if choice.lower() == 'defer':
                print("Deferring execution. Please process secondary operations first.")
                return session, ":defer"
            
            # Option 1: Enter value directly
            value_str = get_user_input(f"Enter numeric value for {var_name}: ")
            unit = get_user_input(f"Enter unit for {var_name}: ")
            
            try:
                value = float(value_str)
                var = Variable(name=var_name, value=value, unit=unit, source="given")
                session = add_variable_to_catalog(session, var)
                print(f"✓ Added {var_name} = {value} {unit}")
            except ValueError:
                print("Invalid value. Aborting execution.")
                return session, "error: invalid input"
        
        # Re-check after adding variables
        missing = get_missing_dependencies(session)
        if missing:
            print("\nStill missing variables. Deferring execution.")
            return session, ":defer"
    
    # All dependencies met - proceed with calculation
    print("\n✓ All dependencies satisfied. Executing calculation...")
    
    new_session, result, error = execute_calculation(session)
    
    if error:
        print(f"❌ Error: {error}")
        answer = get_user_input("> ")
        return session, answer
    
    print(f"\n✓ Result: {formula.result_var} = {result}")
    
    # Show updated catalog
    print("\nUpdated Variable Catalog:")
    for name, var in new_session.variable_catalog.items():
        print(f"  {name} = {var.value} {var.unit} ({var.source})")
    
    answer = str(result)
    return new_session, answer


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


def run_tool_gate_with_formula(session: Session, operation: str) -> tuple[Session, str]:
    """
    Special handling for Tool gate: select formula from database.
    
    Shows formula menu filtered by operation type, handles dependency checking.
    """
    print("\n=== Tool ===")
    print("What method operates within that model? Select from formula database.")
    
    # Use interactive formula selector
    new_session = select_formula_interactive(session, operation)
    
    if new_session.selected_formula_id:
        formula = next((f for f in get_all_formulas() if f.id == new_session.selected_formula_id), None)
        if formula:
            answer = formula.equation
        else:
            answer = "Formula selected"
    else:
        answer = get_user_input("> Enter custom formula: ")
    
    # Record the answer but keep the session with formula selection
    start = datetime.now()
    end = datetime.now()
    elapsed = (end - start).total_seconds()
    recorded_session = record_gate_answer(new_session, "Tool", answer, elapsed)
    
    return recorded_session, answer


def process_secondary_operations(
    session: Session,
    config: Config,
    primary_operation: str
) -> Session:
    """
    Process the queue of secondary operations after primary execution completes.
    
    Prompts user whether to process each secondary operation. If yes,
    resets the session to the Bucket gate (index 2) and continues.
    Gates 0-1 (Requested Output, Primary Operation) remain globally locked.
    
    Args:
        session: Current session state
        config: Configuration settings
        primary_operation: The locked primary operation (for formula filtering)
    
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
            
            # Special handling for Tool gate with formula selection
            if gate_name == "Tool":
                current_session, answer = run_tool_gate_with_formula(
                    current_session, 
                    next_op  # Use current secondary op for filtering
                )
            elif gate_name == "Execution":
                current_session, answer = run_execution_gate(current_session)
            else:
                current_session, answer = run_single_gate(current_session, gate_name, config)
        
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
    locked_primary_operation = None
    
    while True:
        # Get current gate name
        gate_name = get_current_gate_name(session, config)
        
        # Check if all gates completed
        if gate_name is None:
            # Check for secondary operations after Interpretation
            if session.secondary_ops:
                session = process_secondary_operations(session, config, locked_primary_operation or "Accumulate")
            break
        
        # Special handling for Tool gate with formula selection
        if gate_name == "Tool":
            session, answer = run_tool_gate_with_formula(
                session, 
                locked_primary_operation or "Accumulate"
            )
        # Special handling for Execution gate with dependency checking
        elif gate_name == "Execution":
            session, answer = run_execution_gate(session)
        else:
            # Execute the current gate normally
            session, answer = run_single_gate(session, gate_name, config)
        
        # Store locked primary operation for later use
        if is_primary_op_lock_gate(gate_name):
            locked_primary_operation = answer
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
