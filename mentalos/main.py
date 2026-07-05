"""
MentalOS - Interactive Cognitive Training Tool

Main entry point for the MentalOS application. Orchestrates the complete
workflow from problem ingestion through gate pipeline execution to final
LLM-powered audit.

Architecture:
- config/: Immutable configuration (gate sequences, prompts, LLM settings)
- core/: Pure functional transformations (no I/O)
  - models.py: Immutable data structures (frozen dataclasses)
  - pipeline.py: State transformation functions
- shell/: Imperative I/O layer (user interaction, timing)
- audit/: LLM audit functionality

Usage:
    python main.py

Requirements:
    - Python 3.12+
    - requests library (pip install requests)
    - Optional: Local LLM server running at http://localhost:1234
"""

import signal
import sys

from mentalos.config.settings import DEFAULT_CONFIG
from mentalos.shell.interactive import (
    collect_problem_parts,
    run_part_pipeline,
    display_results,
)
from mentalos.audit.llm_audit import perform_audit, format_audit_display


def handle_interrupt(signum, frame):
    """
    Graceful handler for Ctrl+C interrupts.
    
    Ensures clean exit with appropriate message rather than stack trace.
    """
    print("\n\nInterrupt received. Exiting MentalOS gracefully...")
    sys.exit(0)


def main() -> None:
    """
    Main orchestration function for MentalOS.
    
    Coordinates the complete workflow:
    1. Collect multi-part problem from user
    2. Process each part through the gate pipeline
    3. Perform LLM audit on completed sessions
    4. Display results and feedback
    """
    # Register interrupt handler for graceful shutdown
    signal.signal(signal.SIGINT, handle_interrupt)
    
    try:
        # Step 1: Collect problem structure from user
        parts = collect_problem_parts()
        
        if not parts:
            print("No problem parts provided. Exiting.")
            return
        
        # Reconstruct full problem text from parts for audit
        problem_text = "\n".join(
            f"Part ({p.label}): {p.text}" for p in parts
        )
        
        # Step 2: Process each part through the complete gate pipeline
        sessions = []
        for part in parts:
            print(f"\n{'=' * 60}")
            print(f"Processing Part ({part.label})")
            print(f"{'=' * 60}")
            
            session = run_part_pipeline(part, DEFAULT_CONFIG)
            sessions.append(session)
            
            print(f"\nPart ({part.label}) complete.")
        
        # Convert to tuple for immutability
        sessions_tuple = tuple(sessions)
        
        # Step 3: Perform LLM-powered audit
        print("\nPerforming automated audit...")
        audit_result = perform_audit(problem_text, sessions_tuple, DEFAULT_CONFIG)
        audit_display = format_audit_display(audit_result)
        
        # Step 4: Display all results
        display_results(sessions_tuple, audit_display)
        
    except KeyboardInterrupt:
        # Extra safety for interrupt handling
        print("\n\nSession interrupted. Goodbye.")
        sys.exit(0)
    except Exception as e:
        # Catch any unexpected errors and display gracefully
        print(f"\nAn error occurred: {e}")
        print("Please report this issue if it persists.")
        sys.exit(1)


if __name__ == "__main__":
    main()
