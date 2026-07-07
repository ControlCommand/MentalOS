# MentalOS Core Specification

## MentalOS is a cognitive control system.

Its purpose is NOT to solve problems.
###
Its purpose is to control the order in which reasoning expands.

- Always identify the task before selecting methods.
- Always select methods before computation.
- Never reason about explanations before the task has been locked.

###
## Primary Pipeline

Question
↓
Requested Output
↓
Primary Operation
↓
Bucket
↓
Model
↓
Tool
↓
Execution
↓
Answer
###
Everything after Execution (interpretation, inference, decision making) is outside the current scope unless explicitly requested.
###
## Definitions
>>> Requested Output

What must be produced?

Examples

- Velocity
- Coordinate
- Area
- Classification
- Decision
###
>>> Primary Operation
What single action is fundamentally required to produce the requested output?

Examples

- Estimate
- Compare
- Change
- Accumulate
- Transform
- Convert
- Decide
- Classify

Only ONE operation may be selected.
###
>>> Bucket

The behavioral domain in which the operation occurs.

- A Geometry
- B Change
- C Accumulation
- D Estimation
- E Transformation
- F Decision

Buckets constrain valid models and tools.
###
>>> Model
The governing assumptions describing how the system behaves.

Examples

- Newtonian Mechanics
- Probability
- Least Squares
- Coordinate Geometry
- Linear Algebra

Models select tools.

Never the reverse.
###
>>> Tool

The concrete computational procedure.

Examples

- Derivative
- Integral
- Rotation Matrix
- Least Squares
- Kalman Filter
- Pythagorean Theorem
- v=d/t
- Priority Recognition

Question
↓
Requested Output
↓
Primary Operation
↓
Secondary Operations
↓
Context
↓
Noise

Only the Primary Operation determines the lock.
###
Everything else is subordinate.
###
Winner-Takes-All Lock Rule
###
Before reasoning begins:
###
Select exactly ONE Primary Operation.
###

##If multiple operations compete:##

-Best matches requested output.
-Prefer structural over interpretive actions.
-Prefer computation over explanation.
-Prefer narrower semantic scope.
-If unresolved, use predefined priority ordering.
###
##Once locked:##

- No relabeling.
- No dual operations.
- No retroactive justification.

Log conflicts instead of changing the lock.
###
Bucket-Neutral Operations
###
##Some operations do not own a bucket.##

- Compare
- Classify
- Represent
- Describe
- Organize

Determine their bucket from the thing being acted upon.

Example

Compare uncertain measurements
→ D Estimation

Compare coordinate systems
→ E Transformation

Compare candidate designs
→ F Decision
Golden Rule
The question determines the bucket.

Not the object.

Not the wording.

Not the tool.
###
## MentalOS Objective

##MentalOS exists to reduce:##

-premature computation
-causal-chain expansion
-tool-first reasoning
-multi-operation activation
-delayed commitment

##by enforcing deterministic recognition before computation.##