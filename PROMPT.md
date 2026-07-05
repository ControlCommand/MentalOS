<|im_start|>system
You are QWEN CODER - an elite software engineering AI assistant and master-level full-stack developer. You operate strictly within Functional, Data-Oriented, and Procedural paradigms (absolutely no OOP). 

You possess deep, polyglot expertise across the entire technology stack—including Python, C/C++, JavaScript/TypeScript (React, Vue, Node), and Go—writing clean, well-structured, production-grade code in any language requested.

**Core Execution Standards**
- Always produce complete, executable scripts with minimal dependencies and thorough inline comments.
- Follow best practices for interactive CLI tools, REST APIs, and frontend components, handling edge cases gracefully.
- Review every line of code as you write it in real-time. Never submit code until it reaches a state where any remaining bugs are superficial, easily locatable, and trivial to fix.
- Use only up-to-date language features (e.g., Python 3.12+, C++20, ES2022). Never use deprecated libraries, frameworks, or functions.
- Organize everything logically with source files, subfolders, modules, and common files to ensure seamless imports and avoid circular dependencies.

**Core Competencies**
- **Languages**: Python, C/C++
- **Frontend**: React, Vue, Angular, Svelte, Next.js, Tailwind CSS, WebGL, Three.js
- **Backend**: Node.js, FastAPI, Django, Flask, GraphQL, REST APIs
- **Databases**: PostgreSQL, MySQL, MongoDB, Redis, Elasticsearch, DynamoDB
- **DevOps**: Docker, CI/CD, GitHub Actions

**Your Approach & Paradigm Constraints**

- **Strictly NO OOP**: You absolutely do not use Object-Oriented Programming (OOP). Classes, inheritance, and object-state mutation are strictly forbidden because they are bug-prone. Use pure functions, immutable data structures (like Python `dataclasses` with `frozen=True`, or `NamedTuple`), and explicit data pipelines.
- Isolate state mutation to a single, tightly controlled "Imperative Shell" layer.

**SOLID Principles (Re-interpreted for Functional Programming)**

While SOLID originated in OOP, its core architectural tenets translate directly to FP. Apply them as follows:

- **SRP (Single Responsibility)**: A function does exactly one thing. Compose large programs from small, pure, single-purpose functions.
- **OCP (Open/Closed)**: Extend behavior using higher-order functions (functions taking functions as arguments) instead of rewriting existing logic.
- **LSP (Liskov Substitution)**: Any function matching a specific type signature must behave predictably when swapped. If a consumer expects a function of type `A -> B`, any substitute must not introduce unexpected side effects.
- **ISP (Interface Segregation)**: Instead of large, rigid type definitions, functions should demand only the exact, minimal data structure they need to execute.
- **DIP (Dependency Inversion)**: Pass dependencies explicitly as arguments (dependency injection) into functions, rather than hardcoding global state, imports, or external utility calls inside them.

**Security & Ethical Rigor**

- You are a highly conscientious, ethical, and security-focused engineer. Completely avoid malware-prone patterns, insecure functions (e.g., `eval()`, `exec()`, unvalidated subprocesses), and common CWE/OWASP vulnerabilities.
- Apply strict input validation, defensive error handling, and secure data sanitization by default, with proper memory management techniques that prevent memory leaks and common pitfalls.
- Real-Time Audit: Review every line of code as you write it. Since bugs are statistically unavoidable, your goal is to deliberately engineer code so that any remaining edge cases result in superficial, easily locatable, and trivial-to-fix bugs—never deep architectural flaws or silent data corruption.

**Code Execution Rules**

- Do not use placeholders, stubs, or "TODO" comments. Every script, module, and file must be completely implemented, syntactically correct, and production-ready.
- Use up-to-date Python 3.12+ functionalities (match-case, type hints, generics). Never use deprecated libraries, frameworks, or functions.
- Write thorough, explanatory inline comments documenting *why* a technical choice or data transformation was made.

**Architectural Self-Auditing Questions**

Before finalizing any response, mentally audit your code against these 10 core principles:
1. Does every module or function own exactly one single responsibility?
2. Does every module and file name perfectly describe its current contents?
3. Are there any hidden or implicit couplings between separate modules?
4. Are there duplicate sources of truth for data or configuration?
5. Can any module be pruned or deleted without breaking the conceptual model?
6. Does every state mutation flow through a single, explicit common source of truth?
7. Are any modules acting as massive, monolithic "God Modules"?
8. Does every data pipeline step remain a pure transformation without side effects?
9. Does the codebase strictly avoid OOP concepts while maintaining modularity?
10. Is the file layout organized logically for clean, intuitive import paths?

**Response Style**
- Provide complete, production-ready code solutions.
- Explain complex concepts clearly with examples.
- Offer multiple approaches when appropriate.
- Include error handling and edge cases.
- Add helpful comments for complex logic.
- Suggest improvements and optimizations proactively.
- 
<|im_end|>
<|im_start|>user
Write a complete, modular Python (3.12+) program for MentalOS – an interactive cognitive training tool that walks the user through a strict, timed, 10‑gate pipeline for solving physics/math problems, supports multi‑part questions, a Winner‑Takes‑All lock with deferred operations, and a recursive sub‑operation stack, ending with an LLM‑powered audit.

**Paradigm & Quality Bar (inherited from system prompt):**
- Purely functional, data‑oriented, no OOP (no classes, inheritance, mutable objects except inside a single imperative I/O shell).
- Use immutable data structures (`frozen=True` dataclasses, `NamedTuple`, `MappingProxyType`).
- Pure functions only; side‑effects isolated to the imperative shell.
- Full Python 3.12+ features, exhaustive type hints, `match`/`case` where sensible.
- Complete, production‑ready, zero placeholders. Critical thinking applied – don't just transliterate specs; propose better structure if it improves clarity, maintainability, or correctness.

**Your Architectural Freedom:**
You are the architect. Design the directory layout and module boundaries from scratch. Create subdirectories freely to group related concerns (e.g., a `core/` package for pure transformations, `shell/` for I/O, `gates/` for gate logic, `audit/`, etc.). The only hard rules:
1. The entry point is `main.py` at the root of the project directory.
2. Imports must be clean and avoid circular dependencies.
3. The codebase must remain a cohesive whole – a human should be able to understand the data flow without tracing through a maze of files.
4. Choose the **best** organisation, not the most obvious one. If a different decomposition is better (e.g., grouping by pipeline stages rather than technical layers), do that and explain why briefly in comments.

**Functional Requirements (the “what”):**
Implement the full MentalOS workflow:

1. **Multi‑part problem ingestion:**  
   User pastes entire problem. Program asks for sub‑question labels (a, b, c) and their exact text. These are stored as an ordered queue. Each part is processed independently.

2. **Gate pipeline (sequential, interactive):**  
   For each part, the program walks through these gates (order and prompts defined in configuration, not hard‑coded):
   - Scope Lock (constraints)
   - Intent (asker’s motivation)
   - Requested Output (precise output type, e.g., “Work_app”)
   - Domain Bucket
   - Primary Operation Lock (Winner‑Takes‑All: user locks one operation)
   - Model (theorem/concept)
   - Tool (formula/method)
   - Execution (final answer or triggers sub‑operation)
   - Interpretation
   - Deferred operations prompt (after primary lock)

   At each gate:
   - Print prompt (from config).
   - Start a hidden timer.
   - Wait for user input.
   - Record answer and elapsed seconds in an immutable log entry.
   - Update session state immutably.
   - Proceed.

3. **Winner‑Takes‑All Lock & deferred operations:**  
   After the primary operation is locked, ask: “List secondary operations to defer (comma separated) or press Enter.” Store them.  
   When the primary execution and interpretation finish, if deferred ops remain, ask: “Process next deferred operation? (y/n)”. If yes, reset the pipeline to a configurable start gate (e.g., Intent or Primary Op Lock) and process that deferred operation. Continue until queue empty or user stops.

4. **Recursive sub‑operation stack:**  
   During the Execution gate, a special command `:defer` triggers sub‑operation mode.  
   - Push the current session (including logs, deferred queue, gate position) onto an immutable call stack.  
   - Ask for a description of the sub‑operation.  
   - Run a shortened pipeline (Intent → Primary Op → Tool → Execution) for that sub‑task.  
   - Nested `:defer` commands are supported (multi‑level recursion).  
   - When sub‑operation finishes (user provides an answer or `:return`), capture the result, pop the stack, restore the parent session, and inject the sub‑operation’s result into the parent’s Execution answer (or a designated field).  

   The stack must be an immutable list (tuple), managed by pure functions that return a new stack.

5. **Timing & logging:**  
   Every gate interaction produces an immutable `GateLog` with `gate: str, answer: str, time_sec: float`. Logs are stored per‑part and per‑sub‑operation in nested structures (but still immutable – use frozen dataclasses that contain tuples of logs, etc.). The imperative shell is responsible for capturing timestamps via `datetime`.

6. **Final audit via local LLM:**  
   After all parts complete, compile a summary (question, per‑part gate logs with timings, final answers). Send this to a local LLM (configurable endpoint, default `http://localhost:1234/v1/chat/completions`, model `qwen2.5‑math`) with a strict prompt:  
   *“You are a MentalOS auditor. Point out any vague, incomplete, or incorrect gate answers. Do NOT provide solutions, only precise feedback.”*  
   Display the LLM’s response alongside a formatted table of the user’s logs.

**Logic Guidance (Pseudocode) – Illustrative, not prescriptive:**

Below are conceptual snippets to convey the intended data‑flow patterns. Adapt as needed while keeping the functional purity and immutable updates.

*Session update pattern (all pure):*
```python
@dataclass(frozen=True)
class Session:
    part_id: str
    question: str
    logs: tuple[GateLog, ...]
    deferred_ops: tuple[str, ...]
    current_gate: int  # index into gate_sequence

def record_gate(s: Session, gate: str, answer: str, elapsed: float) -> Session:
    new_log = GateLog(gate=gate, answer=answer, time_sec=elapsed)
    return Session(
        part_id=s.part_id,
        question=s.question,
        logs=(*s.logs, new_log),
        deferred_ops=s.deferred_ops,
        current_gate=s.current_gate + 1,
    )
```
*Imperative shell gate loop (simplified):*

```python
def run_part(question: str, config: Config) -> Session:
    s = initial_session(question)
    for gate_idx, gate_name in enumerate(config.gate_sequence):
        if gate_idx != s.current_gate:
            continue  # skip if already advanced (e.g., after deferred ops)
        prompt = config.gate_prompts[gate_name]
        print(f"=== {gate_name} ===")
        print(prompt)
        start = datetime.now()
        answer = input("> ").strip()
        elapsed = (datetime.now() - start).total_seconds()
        # Handle special commands
        if gate_name == "Execution" and answer == ":defer":
            sub_op_desc = input("Describe sub-operation: ")
            # Push current session onto stack, create sub-session
            stack = push(stack, s)
            s = run_sub_operation(sub_op_desc, stack, config)
            stack, sub_result = pop(stack)
            # Inject result back into parent Execution answer
            s = record_gate(s, "Execution", sub_result, elapsed)  # simplified
        else:
            s = record_gate(s, gate_name, answer, elapsed)
        # After primary lock, handle deferred ops collection
        if gate_name == "Primary Operation Lock":
            deferred = input("Secondary ops (comma separated) or Enter: ")
            if deferred:
                s = add_deferred_ops(s, deferred)
        # After Interpretation, process deferred ops queue
        if gate_name == "Interpretation" and s.deferred_ops:
            s = process_deferred_ops(s, config)
    return s
```

*Stack management (pure, immutable):*

```python
Stack = tuple  # immutable stack of sessions

def push(stack: Stack, session: Session) -> Stack:
    return (session, *stack)

def pop(stack: Stack) -> tuple[Session, Stack]:
    return stack[0], stack[1:]
Deferred ops loop:

python
def process_deferred_ops(s: Session, config: Config) -> Session:
    while s.deferred_ops:
        print(f"Deferred ops remaining: {s.deferred_ops}")
        ans = input("Process next deferred operation? (y/n): ").lower()
        if ans != 'y':
            break
        next_op = s.deferred_ops[0]
        s = s._replace(deferred_ops=s.deferred_ops[1:])
        # Reset to a suitable start gate, e.g., Intent, and reuse same part question
        s = s._replace(current_gate=config.deferred_start_gate_idx)
        # Insert next_op into session (maybe as an implicit override)
        s = set_current_operation(s, next_op)
        # Run gates from that point onward (loop will continue from current_gate)
        s = run_part_from_gate(s, config)
    return s
```

*Main orchestration:*
```python
def main():
    problem = input("Paste the entire problem:\n")
    parts = get_parts_from_user()  # interactive
    all_sessions = []
    for part in parts:
        session = run_part(part.text, config)
        all_sessions.append(session)
    audit_result = perform_audit(all_sessions, problem, config)
    print("\n=== FINAL AUDIT ===")
    print(audit_result)
    print("\nDetailed logs:")
    for session in all_sessions:
        print(format_session_log(session))
```
These snippets are mere sketches. You are free to improve the decomposition, error handling, and flow control—provided the final result remains functionally pure and fully implements the requirements above.

**Technical Constraints:**

Language: Python 3.12+.

**Dependencies: requests for API call; everything else from standard library.**

No eval(), exec(), or insecure subprocess.

Handle Ctrl+C gracefully.

All pure functions must have docstrings; comments explain why, not what.

**Deliverable:**

- The complete project directory with all files fully implemented and ready to run. Include a brief README.md explaining how to run and the high‑level architecture.
- Exercise your architectural judgment – if a better decomposition exists than the one outlined in this request, adopt it and document the rationale.
- Do not leave any TODO or placeholder. Every line of code must be production‑clean.
<|im_end|>
<|im_start|>assistant
