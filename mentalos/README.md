# MentalOS

An interactive cognitive training tool for solving physics/math problems through a structured, timed 10-gate pipeline.

## Architecture

MentalOS follows a strict functional programming paradigm with these key principles:

- **No OOP**: No classes (except frozen dataclasses for immutable data), no inheritance, no mutable state
- **Pure Functions**: All transformations are pure functions that take immutable data and return new immutable data
- **Imperative Shell**: All side effects (I/O, timing, API calls) are isolated in the `shell/` module
- **Immutable Data**: Uses `frozen=True` dataclasses and tuples throughout

### Directory Structure

```
mentalos/
├── main.py              # Entry point and orchestration
├── config/
│   └── settings.py      # Immutable configuration (gate sequences, prompts, LLM settings)
├── core/
│   ├── models.py        # Immutable data structures (Session, GateLog, ProblemPart, etc.)
│   └── pipeline.py      # Pure functional transformations
├── shell/
│   └── interactive.py   # I/O layer (user input, timing, coordination)
└── audit/
    └── llm_audit.py     # LLM-powered audit functionality
```

### Why This Organization?

The codebase is organized by **concern separation** rather than technical layers:

1. **config/** - All configurable aspects live here. Changing gate prompts or sequences requires only editing this module.
2. **core/** - Contains pure business logic. These functions can be tested in isolation without mocking I/O.
3. **shell/** - The "dirty" layer that handles user interaction. This is the only place where `input()` and `print()` occur.
4. **audit/** - External service integration isolated to one module.

This decomposition allows:
- Easy testing of core logic without terminal interaction
- Swapping the I/O layer (e.g., for a web interface) without touching pipeline logic
- Modifying gate sequences/prompts without code changes
- Replacing the LLM audit with a different provider

## Requirements

- Python 3.12+
- `requests` library (`pip install requests`)
- Optional: Local LLM server (e.g., LM Studio, Ollama) at `http://localhost:1234`

## Installation

```bash
# Install the single external dependency
pip install requests

# Ensure you're using Python 3.12+
python --version
```

## Usage

```bash
cd mentalos
python main.py
```

### Workflow

1. **Problem Ingestion**: Paste the full problem statement, then define sub-parts (a, b, c...)
2. **Gate Pipeline**: For each part, walk through 10 gates:
   - Scope Lock → Intent → Requested Output → Domain Bucket → Primary Operation Lock → Model → Tool → Execution → Interpretation
3. **Deferred Operations**: After locking the primary operation, optionally queue secondary operations
4. **Sub-operations**: During Execution, type `:defer` to push a nested sub-task onto the call stack
5. **Audit**: After all parts complete, an LLM reviews your answers for vagueness or errors

### Special Commands

- `:defer` (during Execution gate): Push current session onto stack and start a sub-operation
- `:return`: Complete a sub-operation and return to parent session
- Press Enter on empty line: Finish multi-line input sections

## Configuration

Edit `config/settings.py` to customize:

- Gate sequence order
- Gate prompts
- Deferred operation starting gate
- LLM endpoint URL and model name
- Audit system prompt

## Example Session

```
$ python main.py

============================================================
MENTALOS - Cognitive Training Tool
============================================================

Paste the entire problem statement below.
(Press Enter twice on an empty line to finish)

A block of mass m slides down an inclined plane...

Now define the sub-questions (parts a, b, c, etc.)

Enter part label (e.g., 'a', 'b', 'c') or 'done' to finish: a

Enter the exact text for part (a):
Find the acceleration of the block.

Part (a) recorded.

Enter part label (e.g., 'a', 'b', 'c') or 'done' to finish: done

============================================================
Processing Part (a)
============================================================

=== Scope Lock ===
Define the constraints and boundaries of this problem...
> Frictionless surface, constant incline angle θ

=== Intent ===
What is the asker's true motivation?...
> Understand force decomposition on inclined planes

... (continues through all gates)

============================================================
FINAL AUDIT RESULTS
============================================================

Audit completed successfully.

LLM Feedback:
----------------------------------------
Your Scope Lock answer could be more specific about air resistance assumptions...
----------------------------------------
```

## Error Handling

- **Ctrl+C**: Graceful exit with cleanup message
- **LLM Unavailable**: Audit continues with error message but doesn't crash
- **Empty Input**: Prompts user to re-enter valid data
- **Stack Underflow**: Warns if `:return` used without active sub-operation

## Design Decisions

### Frozen Dataclasses

All data structures use `frozen=True` to prevent accidental mutation. This enforces the functional paradigm at runtime—any attempt to modify a field raises an error.

### Tuple-Based Stack

The sub-operation call stack is implemented as a tuple rather than a list. Each push/pop creates a new tuple, maintaining immutability.

### Type Hints

Full Python 3.12+ type hints are used throughout. This provides IDE support and enables static analysis tools like mypy.

### Match/Case

While not heavily used in this implementation (simple conditionals suffice), the code is structured to allow easy addition of `match`/`case` statements for gate-type dispatch if needed.

## License

MIT License
