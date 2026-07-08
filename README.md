# MentalOS v1.0.0 - Deterministic Cognitive Physics Engine

A production-ready cognitive control system implementing the FCIS (Functional Cognitive Inference System) architecture for deterministic physics/math problem solving.

## Architecture

### Core Pipeline (Question → Answer)
```
Question → Requested Output → Constraint Lock → Operation Lock → Bucket → Model → Tool → Execution → Answer
```

### 5 Primary Operations (Verbs)
- **accumulate**: Total, sum, work, energy, distance
- **transform**: Convert, resolve, decompose, rotate, components
- **scale**: Ratio, proportion, factor, multiply, divide
- **estimate**: Approximate, average, mean, roughly
- **differentiate**: Derivative, rate, instantaneous, change

### 6 Cognitive Buckets
- accumulation, transformation, geometry, kinematics, dynamics, conservation

### Winner-Takes-All Strategy
The pipeline identifies the dominant primary operation using keyword scoring. Secondary operations are nested in a DAG structure and executed bottom-up through the dependency chain.

## Installation

```bash
pip install fastapi uvicorn pydantic numpy typing_extensions pytest
```

## Usage

### Start Server
```bash
python -m mentalos.api.app
```

Server binds to `127.0.0.1:8000` by default (secure localhost-only access).

### Web Interface
Access at: http://127.0.0.1:8000

Features:
- Problem input with multi-part question support
- Preset problems (work, kinematics, forces, vectors)
- Real-time results display
- Operation DAG visualization
- Audit log tracking
- Metrics dashboard

### API Endpoints

#### Health Check
```bash
curl http://127.0.0.1:8000/health
```

#### Process Question
```bash
curl -X POST http://127.0.0.1:8000/cognitive/process \
  -H "Content-Type: application/json" \
  -d '{"question_text": "A force of 87 N at 33 degrees pushes a box 13 m. Calculate work."}'
```

#### Get Question Parts
```bash
curl "http://127.0.0.1:8000/cognitive/parts?question_text=A%20problem.%0Aa)%20First?%0Ab)%20Second?"
```

API Documentation: http://127.0.0.1:8000/docs

### Example

**Input:**
```
A man pushes a 45 kg box from rest along a horizontal floor by exerting a force 
of 87 N downward at 33° to the horizontal against a friction force of 62 N over 
a distance of 13 m.
a) How much work was done in moving the box?
```

**Pipeline Execution:**
1. **Extracted Values**: f_applied=87N, theta=33°, d=13m, f_friction=62N, m=45kg
2. **Keywords**: work, force, push, horizontal, distance
3. **Requested Output**: W_work (Joules)
4. **Primary Operation**: accumulate (winner-takes-all)
5. **Bucket**: accumulation
6. **Model**: work_energy_theorem
7. **Tool**: algebraic_manipulation + trigonometry
8. **Operation DAG**: 
   - Order 0: transform (vector resolution)
   - Order 1: scale (trig ratios)
   - Order 2: accumulate (work calculation) ← primary
9. **Execution**: W = F·d·cos(θ) = 87·13·cos(33°) = 948.54 J

**Output:**
```json
{
  "success": true,
  "answer": 948.5364,
  "unit": "J",
  "explanation": "Solved using accumulate operation in accumulation bucket..."
}
```

## Running Tests

```bash
cd /workspace
python -m pytest tests/test_mentalos.py -v
```

All 30 tests pass covering:
- Type definitions & immutability
- Question analysis (parsing, extraction)
- Operation identification
- DAG construction
- Execution engine
- Full pipeline integration
- Equation database
- Edge cases

## Project Structure

```
/workspace/
├── mentalos/
│   ├── __init__.py              # Package marker
│   ├── types/
│   │   ├── __init__.py          # Clean router (exports only)
│   │   └── core_types.py        # Frozen dataclasses, type aliases
│   ├── core/
│   │   ├── __init__.py
│   │   └── pipeline.py          # FCIS pipeline engine
│   ├── equations/
│   │   ├── __init__.py
│   │   └── database.py          # 30+ physics equations
│   ├── api/
│   │   ├── __init__.py
│   │   └── app.py               # FastAPI server
│   └── static/
│       └── index.html           # Modern web UI
├── tests/
│   └── test_mentalos.py         # Comprehensive test suite
└── README.md
```

## Key Design Principles

### 1. Data-Oriented Design
- Zero OOP for business logic
- Frozen dataclasses for immutability
- Pure functions throughout

### 2. Strict Typing
- NewType-style aliases
- Annotated arrays for numpy vectors/matrices
- Literal types for operations, buckets, models, tools

### 3. Security
- Binds to 127.0.0.1 only (no network exposure)
- Pydantic V2 for input validation
- No eval/exec usage

### 4. Memory Safety
- Immutable state prevents accidental mutations
- No circular references
- Proper resource cleanup via Python GC

### 5. Module Separation
- `__init__.py` files are clean routers only
- Heavy dependencies load on-demand
- Clear separation of concerns

## Equation Database

Includes 30+ equations across categories:
- Work & Energy (5 equations)
- Forces & Newton's Laws (5 equations)
- Vectors (4 equations)
- Kinematics (5 equations)
- Power (2 equations)
- Momentum (3 equations)
- Circular Motion (2 equations)
- Gravitation (1 equation)
- Springs (2 equations)

Supports fuzzy keyword search and variable-based suggestion.

## Multi-Part Questions

Automatically detects and parses questions with parts (a), (b), (c), etc.
Users can solve parts sequentially through the web UI.

## Next Steps (Recommendations)

1. **Expand Equation Database**: Add more equations for thermodynamics, waves, electromagnetism
2. **Add BVH/Octree Acceleration**: For large scene spatial queries
3. **Implement Temporal Bucket**: Time-stepping physics simulation
4. **Add Unit Conversion**: Automatic unit normalization and conversion
5. **CI/CD Pipeline**: GitHub Actions for automated testing
6. **Enhanced Spatial Visualization**: Interactive vector diagrams, force triangles

## License

MIT License - See LICENSE file for details.

## Version

1.0.0 - Production Ready
