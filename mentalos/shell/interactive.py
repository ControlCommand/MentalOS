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
- Sub-operation recursion via :defer command

Architecture notes:
- All I/O is isolated to this module for easy testing and replacement
- Pure functions from core.pipeline are imported and composed here
- The imperative shell pattern keeps side effects contained
"""

from datetime import datetime
import sys

from mentalos.core.models import Session, Stack, ProblemPart, GateLog, Variable, SubOperationResult
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
    get_formula_by_id,
    push_stack,
    pop_stack,
    is_stack_empty,
    get_current_gate_name,
    get_gate_prompt,
    is_execution_gate,
    is_primary_op_lock_gate,
    is_tool_gate,
    format_session_summary,
    create_sub_operation_session,
    complete_sub_operation,
    inject_sub_result,
    convert_unit,
    normalize_to_base_unit,
    search_formulas,
)
from mentalos.config.settings import Config, PHYSICAL_CONSTANTS, SMART_DEFAULTS


# =============================================================================
# BASIC I/O PRIMITIVES
# =============================================================================

def get_user_input(prompt: str = "") -> str:
    """
    Get input from the user via terminal.
    
    Pure wrapper around input() for easier testing and consistency.
    Handles EOFError gracefully (Ctrl+D).
    
    Args:
        prompt: Optional prompt string
    
    Returns:
        User input as string (empty string on EOF)
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
    
    Args:
        prompt: Prompt to display to user
    
    Returns:
        Tuple of (user answer, elapsed seconds)
    """
    print(prompt)
    start = datetime.now()
    answer = get_user_input("> ")
    end = datetime.now()
    elapsed = (end - start).total_seconds()
    return answer, elapsed


def clear_screen() -> None:
    """Clear terminal screen for better visual separation."""
    print("\n" * 2)


def print_separator(char: str = "=", length: int = 60) -> None:
    """Print a separator line for visual organization."""
    print(f"\n{char * length}\n")


# =============================================================================
# PROBLEM INGESTION
# =============================================================================

def collect_problem_parts() -> tuple[ProblemPart, ...]:
    """
    Interactively collect multi-part problem structure from user.
    
    First gets the full problem text, then asks for sub-question labels
    and their exact text. Returns an ordered tuple of ProblemParts.
    
    Returns:
        Tuple of ProblemPart objects in order
    """
    print_separator("=")
    print("MENTALOS - Cognitive Training Tool v2.0")
    print_separator("=")
    print("Paste the entire problem statement below.")
    print("(Press Enter twice on an empty line to finish)\n")
    
    # Collect full problem text
    lines = []
    while True:
        line = get_user_input("")
        if line == "":
            break
        lines.append(line)
    
    problem_text = "\n".join(lines)
    
    if not problem_text.strip():
        print("No problem text entered. Exiting.")
        return ()
    
    print(f"\n✓ Problem received ({len(lines)} lines).")
    print("\nNow define the sub-questions (parts a, b, c, etc.)")
    
    parts = []
    while True:
        label = get_user_input("\nEnter part label (e.g., 'a', 'b', 'c') or 'done' to finish: ")
        if label.lower() in ('done', 'exit', 'quit', 'd'):
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
            print(f"✓ Part ({label}) recorded.")
        else:
            print("Part text cannot be empty. Please try again.")
    
    if not parts:
        # If no parts defined, treat whole problem as single part 'a'
        print("\nNo sub-parts defined. Treating entire problem as part (a).")
        return (ProblemPart(label='a', text=problem_text),)
    
    return tuple(parts)


# =============================================================================
# FORMULA SELECTION UI
# =============================================================================

def display_physical_constants() -> None:
    """Display available physical constants for smart defaults."""
    print("\n" + "-" * 40)
    print("Available Physical Constants:")
    print("-" * 40)
    for const in PHYSICAL_CONSTANTS[:8]:  # Show first 8 most common
        print(f"  {const.symbol} = {const.value} {const.unit}  ({const.name})")
    if len(PHYSICAL_CONSTANTS) > 8:
        print(f"  ... and {len(PHYSICAL_CONSTANTS) - 8} more")


def display_formula_menu(formulas: tuple, operation: str = "") -> None:
    """
    Display available formulas in a numbered menu.
    
    Args:
        formulas: Tuple of Formula objects to display
        operation: Current operation type for context
    """
    print_separator("-", 50)
    if operation:
        print(f"Available Formulas for '{operation}':")
    else:
        print("Available Formulas:")
    print_separator("-", 50)
    
    for i, formula in enumerate(formulas, 1):
        print(f"  [{i:2}] {formula.name}")
        print(f"       Equation: {formula.equation}")
        print(f"       Requires: {', '.join(formula.required_vars)}")
        print()


def show_variable_catalog(session: Session) -> None:
    """Display current variable catalog in a formatted way."""
    if session.variable_catalog:
        print("\n📦 Variable Catalog:")
        for name, var in sorted(session.variable_catalog.items()):
            source_icon = "📥" if var.source == "given" else "🧮" if var.source == "calculated" else "🔄"
            print(f"  {source_icon} {name} = {var.value:.6g} {var.unit}  ({var.source})")
    else:
        print("\n📦 Variable Catalog: (empty)")


def select_formula_interactive(session: Session, operation: str) -> Session:
    """
    Interactive formula selection with dependency awareness.
    
    Shows available formulas, lets user pick one, then checks for missing variables.
    If variables are missing, prompts user to add them first.
    
    Args:
        session: Current session state
        operation: Operation type for filtering
    
    Returns:
        Updated Session with selected formula
    """
    formulas = get_formulas_for_operation(operation)
    
    while True:
        display_formula_menu(formulas, operation)
        show_variable_catalog(session)
        
        choice = get_user_input(
            "\nSelect formula number (or 'list' to see all, 'search' to find, 'skip' to skip): "
        )
        
        if choice.lower() == 'skip':
            print("Skipping formula selection.")
            return session
        
        if choice.lower() == 'list':
            formulas = get_all_formulas()
            continue
        
        if choice.lower() == 'search':
            query = get_user_input("Search term: ")
            results = search_formulas(query)
            if results:
                formulas = results
                print(f"Found {len(results)} matching formula(s).")
            else:
                print("No formulas found matching that query.")
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
                        
                        if value_str.lower() == 'cancel':
                            print("Variable addition cancelled.")
                            break
                        
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
            print("Please enter a valid number.")


# =============================================================================
# EXECUTION GATE WITH DEPENDENCY CHECKING
# =============================================================================

def run_execution_gate(session: Session) -> tuple[Session, str]:
    """
    Execute the Execution gate with dependency checking.
    
    Blocks calculation until all required variables are present.
    Shows formula, required variables, and current catalog status.
    Supports :defer command for sub-operations.
    
    Args:
        session: Current session state
    
    Returns:
        Tuple of (updated Session, answer string)
    """
    print("\n=== Execution ===")
    
    if session.selected_formula_id is None:
        print("No formula selected. Cannot execute.")
        answer = get_user_input("> ")
        return session, answer
    
    # Get formula info
    formula = get_formula_by_id(session.selected_formula_id)
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
        print("\nOptions:")
        print("  1. Enter missing variable values directly")
        print("  2. Type ':defer' to create a sub-operation for this")
        print("  3. Type ':return' to abort and return (if in sub-operation)")
        
        choice = get_user_input("\nChoose (1/2/3 or value to add): ")
        
        if choice.lower() == ':defer':
            return session, ":defer"
        
        if choice.lower() == ':return':
            return session, ":return"
        
        # Option 1: Enter value directly
        # Parse "varname = value unit" format or just value
        for var_name in missing:
            print(f"\n--- Resolve: {var_name} ---")
            value_str = get_user_input(f"Enter numeric value for {var_name}: ")
            
            if value_str.lower() in ('cancel', 'skip'):
                print("Skipping this variable.")
                continue
            
            unit = get_user_input(f"Enter unit for {var_name}: ")
            
            try:
                value = float(value_str)
                
                # Auto-convert to base unit if needed
                normalized_value, normalized_unit = normalize_to_base_unit(value, unit)
                if normalized_unit != unit:
                    print(f"  → Normalized: {normalized_value:.6g} {normalized_unit}")
                
                var = Variable(name=var_name, value=normalized_value, unit=normalized_unit, source="given")
                session = add_variable_to_catalog(session, var)
                print(f"✓ Added {var_name} = {normalized_value:.6g} {normalized_unit}")
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
    
    print(f"\n✓ Result: {formula.result_var} = {result:.6g}")
    
    # Show updated catalog
    show_variable_catalog(new_session)
    
    answer = f"{result:.6g}"
    return new_session, answer


# =============================================================================
# SINGLE GATE EXECUTION
# =============================================================================

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
    
    Args:
        session: Current session state
        operation: Operation type for filtering
    
    Returns:
        Tuple of (updated Session, answer string)
    """
    print("\n=== Tool ===")
    print("What method operates within that model? Select from formula database.")
    
    # Use interactive formula selector
    new_session = select_formula_interactive(session, operation)
    
    if new_session.selected_formula_id:
        formula = get_formula_by_id(new_session.selected_formula_id)
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


# =============================================================================
# SUB-OPERATION FLOW (:defer COMMAND)
# =============================================================================

def handle_sub_operation_flow(
    session: Session,
    config: Config,
    parent_description: str = ""
) -> tuple[Session, SubOperationResult | None]:
    """
    Handle the complete sub-operation workflow when :defer is invoked.
    
    Creates a new sub-session, runs a shortened pipeline, and returns
    the result for injection into the parent.
    
    Args:
        session: Parent session (will be pushed to stack)
        config: Configuration
        parent_description: Optional description from parent
    
    Returns:
        Tuple of (restored parent session, sub-operation result or None)
    """
    print_separator("→")
    print("🔄 SUB-OPERATION MODE")
    print("Parent session saved to stack. Complete this sub-task to return.")
    print_separator("→")
    
    # Get description of sub-operation
    if not parent_description:
        description = get_user_input("Describe the sub-operation to defer: ")
    else:
        description = parent_description
    
    if not description:
        print("Sub-operation cancelled. Returning to parent.")
        return session, None
    
    # Create sub-operation session
    sub_session = create_sub_operation_session(session, description)
    
    print(f"\nStarting sub-operation: {description}")
    print(f"Depth: {sub_session.depth} | Inherited {len(sub_session.variable_catalog)} variables")
    
    # Run shortened pipeline for sub-operation (Intent → Primary Op → Tool → Execution)
    sub_session = run_sub_pipeline(sub_session, config)
    
    # Complete sub-operation and prepare result
    result_value = None
    result_unit = ""
    result_var_name = None
    
    # Extract result from variable catalog if a calculated variable exists
    for name, var in sub_session.variable_catalog.items():
        if var.source == "calculated":
            result_value = var.value
            result_unit = var.unit
            result_var_name = name
            break
    
    # Package result
    _, sub_result = complete_sub_operation(
        sub_session, 
        result_value, 
        result_unit, 
        result_var_name
    )
    
    print_separator("←")
    print(f"✓ Sub-operation complete: {description}")
    if sub_result and sub_result.result_value is not None:
        print(f"  Result: {sub_result.result_var_name} = {sub_result.result_value:.6g} {sub_result.result_unit}")
    print_separator("←")
    
    return session, sub_result


def run_sub_pipeline(session: Session, config: Config) -> Session:
    """
    Run a shortened pipeline for sub-operations.
    
    Sub-operations use a reduced gate sequence:
    Intent/Bucket → Model → Tool → Execution → Interpretation
    
    Args:
        session: Sub-operation session
        config: Configuration
    
    Returns:
        Completed sub-operation session
    """
    # For sub-operations, we start from a reasonable gate
    # Skip Requested Output and Primary Operation Lock since those are inherited
    session = reset_session_to_gate(session, 2)  # Start at Bucket
    
    while True:
        gate_name = get_current_gate_name(session, config)
        
        if gate_name is None:
            break
        
        # Check for special commands
        if is_tool_gate(gate_name):
            session, answer = run_tool_gate_with_formula(
                session,
                session.locked_primary_operation or "Accumulate"
            )
        elif is_execution_gate(gate_name):
            session, answer = run_execution_gate(session)
            
            # Check for nested :defer
            if answer.lower() == ':defer':
                session, sub_result = handle_sub_operation_flow(session, config)
                if sub_result:
                    session = inject_sub_result(session, sub_result)
                    print("Sub-operation result injected. Continuing...")
                    continue
        else:
            session, answer = run_single_gate(session, gate_name, config)
    
    return session


# =============================================================================
# SECONDARY OPERATIONS PROCESSING
# =============================================================================

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
            if is_tool_gate(gate_name):
                current_session, answer = run_tool_gate_with_formula(
                    current_session, 
                    next_op  # Use current secondary op for filtering
                )
            elif is_execution_gate(gate_name):
                current_session, answer = run_execution_gate(current_session)
                
                # Handle :defer in secondary operations too
                if answer.lower() == ':defer':
                    current_session, sub_result = handle_sub_operation_flow(
                        current_session, config
                    )
                    if sub_result:
                        current_session = inject_sub_result(current_session, sub_result)
            else:
                current_session, answer = run_single_gate(current_session, gate_name, config)
        
        # Loop back to check for more secondary ops
    
    return current_session


# =============================================================================
# MAIN PIPELINE ORCHESTRATION
# =============================================================================

def run_part_pipeline(
    part: ProblemPart,
    config: Config
) -> Session:
    """
    Run the complete gate pipeline for a single problem part.
    
    This is the main orchestration function that walks through all gates,
    handles secondary operations queue after primary completion,
    and manages sub-operation recursion via :defer.
    
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
                session = process_secondary_operations(
                    session, config, 
                    locked_primary_operation or "Accumulate"
                )
            break
        
        # Special handling for Tool gate with formula selection
        if is_tool_gate(gate_name):
            session, answer = run_tool_gate_with_formula(
                session, 
                locked_primary_operation or "Accumulate"
            )
        # Special handling for Execution gate with dependency checking and :defer
        elif is_execution_gate(gate_name):
            session, answer = run_execution_gate(session)
            
            # Handle :defer command for recursive sub-operations
            if answer.lower() == ':defer':
                session, sub_result = handle_sub_operation_flow(session, config)
                if sub_result:
                    session = inject_sub_result(session, sub_result)
                    print("Sub-operation result injected. Continuing with parent...")
                    # Don't advance gate - let user re-enter Execution with new data
                    continue
            elif answer.lower() == ':return':
                # User wants to abort this operation
                print("Aborting current operation. Moving to Interpretation.")
                # Skip to end
                session = Session(
                    part_id=session.part_id,
                    question=session.question,
                    logs=session.logs,
                    secondary_ops=session.secondary_ops,
                    current_gate_idx=len(config.gate_sequence),  # Skip to end
                    is_primary_lock_complete=session.is_primary_lock_complete,
                    locked_requested_output=session.locked_requested_output,
                    locked_primary_operation=session.locked_primary_operation,
                    variable_catalog=session.variable_catalog,
                    selected_formula_id=session.selected_formula_id,
                    pending_dependencies=session.pending_dependencies,
                    sub_stack=session.sub_stack,
                    sub_result=session.sub_result,
                    depth=session.depth,
                )
                continue
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


# =============================================================================
# RESULTS DISPLAY
# =============================================================================

def display_results(sessions: tuple[Session, ...], audit_feedback: str | None) -> None:
    """
    Display final results including all session logs and audit feedback.
    
    Formats output in a readable table-like structure for review.
    
    Args:
        sessions: Tuple of completed sessions
        audit_feedback: Formatted audit feedback string
    """
    print_separator("=")
    print("MENTALOS SESSION COMPLETE")
    print_separator("=")
    
    # Display audit feedback first if available
    if audit_feedback:
        print(audit_feedback)
    
    # Display detailed logs for each part
    print_separator("=")
    print("DETAILED GATE LOGS")
    print_separator("=")
    
    for session in sessions:
        print(format_session_summary(session))
        print("-" * 40)
    
    # Summary statistics
    total_gates = sum(len(s.logs) for s in sessions)
    total_time = sum(log.time_sec for s in sessions for log in s.logs)
    total_vars = sum(len(s.variable_catalog) for s in sessions)
    
    print("\n📊 Session Statistics:")
    print(f"  Total Parts: {len(sessions)}")
    print(f"  Total Gates Completed: {total_gates}")
    print(f"  Total Time: {total_time:.1f}s ({total_time/60:.1f} min)")
    print(f"  Variables Calculated: {total_vars}")
    print(f"  Avg Time per Gate: {total_time/max(total_gates,1):.2f}s")
    
    print("\n✓ Session complete. Thank you for using MentalOS.")
