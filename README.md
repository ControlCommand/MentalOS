# MentalOS - Cognitive Physics Engine

A deterministic physics/spatial inference engine that implements a DAG-based cognitive pipeline for solving physics and mathematics problems.

## 🧠 Architecture

MentalOS follows a strict **Data-Oriented Design** with immutable frozen dataclasses and a deterministic cognitive pipeline:

```
Question → Requested Output → Constraint Lock → Operation Lock → Bucket → Model → Tool → Execution
```

### Core Concepts

1. **Primary Operations (5 Verbs)**: `accumulate`, `transform`, `scale`, `estimate`, `differentiate`
2. **Cognitive Buckets (6)**: `accumulation`, `transformation`, `geometry`, `kinematics`, `dynamics`, `conservation`
3. **Physics Models**: Work-Energy Theorem, Newtonian Mechanics, Kinematics, etc.
4. **Mathematical Tools**: Trigonometry, Vector Algebra, Calculus, etc.
5. **Nested Operations**: DAG-based dependency resolution for multi-step problems

## 📁 Project Structure

```
mentalos/
├── types/           # Frozen dataclasses and type definitions
│   ├── core_types.py
│   └── __init__.py
├── core/            # Cognitive pipeline engine
│   └── pipeline.py
├── equations/       # Equation database with fuzzy search
│   └── database.py
├── api/             # FastAPI REST API
│   └── app.py
└── static/          # Web UI
    └── index.html

tests/
└── test_mentalos.py # Comprehensive test suite
```

## 🚀 Quick Start

### Installation

```bash
pip install fastapi uvicorn pydantic numpy typing-extensions
```

### Run the API Server

```bash
cd /workspace
python -m mentalos.api.app
```

The server will start at `http://127.0.0.1:8000`

### Access the Web UI

Open your browser to `http://127.0.0.1:8000`

### API Documentation

Interactive API docs available at:
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## 🧪 Running Tests

```bash
pytest tests/test_mentalos.py -v
```

All 26 tests should pass.

## 📖 Usage Example

### Via Web UI

1. Open `http://127.0.0.1:8000`
2. Enter a physics problem or use preset examples
3. Click "Analyze Problem"
4. Review the cognitive pipeline stages
5. Execute computation steps
6. Get final answer

### Via API

```python
import requests

# Process a problem
response = requests.post(
    "http://127.0.0.1:8000/cognitive/process",
    json={
        "question_text": "A force of 100 N at 30° pushes a box 5 m. Calculate work."
    }
)
data = response.json()
print(f"Session ID: {data['session_id']}")
print(f"Primary Operation: {data['state_summary']['primary_operation']}")
print(f"Model: {data['state_summary']['model']}")
```

### Via Python Code

```python
from mentalos.core.pipeline import CognitivePipeline
from mentalos.types import CognitiveRequest

# Initialize pipeline
pipeline = CognitivePipeline()

# Create request
request = CognitiveRequest(
    question_text="Calculate work done when 50 N moves an object 10 m."
)

# Run pipeline
state = pipeline.create_session(request)
state = pipeline.determine_requested_output(state.session_id)
state = pipeline.apply_constraint_lock(state.session_id)
state = pipeline.determine_operation_lock(state.session_id)
state = pipeline.assign_bucket(state.session_id)
state = pipeline.select_model(state.session_id)
state = pipeline.select_tool(state.session_id)
state = pipeline.discover_nested_operations(state.session_id)

# Execute
state, result = pipeline.execute_step(
    session_id=state.session_id,
    step_number=1,
    equation_id="work_constant_force",
    input_values={"F": 50.0, "d": 10.0, "θ": 0.0}
)

state = pipeline.finalize_result(state.session_id)
print(f"Answer: {state.final_result.final_value} {state.final_result.unit}")
```

## 🔍 Pipeline Stages

| Stage | Description |
|-------|-------------|
| 1. Question Analysis | Parse text, extract keywords, identify parts (a,b,c,d) |
| 2. Requested Output | Determine what quantity is being asked for |
| 3. Constraint Lock | Isolate relevant variables and constraints |
| 4. Operation Lock | Identify primary operation (Winner Takes All) |
| 5. Bucket Assignment | Assign cognitive bucket |
| 6. Model Selection | Select physics framework |
| 7. Tool Selection | Select mathematical tool |
| 8. Nested Operations | Discover dependent operations |
| 9. Execution | Compute results bottom-up through DAG |

## 📊 Features

- **Multi-part Questions**: Automatically detects and parses parts (a), (b), (c), etc.
- **Nested Operations**: Handles problems requiring multiple sequential calculations
- **Fuzzy Equation Search**: Find equations by keywords with intelligent matching
- **Spatial Visualization Ready**: Framework for vector triangles and diagrams
- **Immutable State**: Frozen dataclasses ensure deterministic behavior
- **Type Safety**: Comprehensive type hints throughout

## 🗄️ Equation Database

The built-in equation database includes:

- Work & Energy equations
- Force & Vector equations  
- Kinematics equations
- Trigonometry relations
- Power equations
- Momentum & Impulse

Each equation is tagged with applicable models, tools, operations, and buckets for intelligent retrieval.

## 🔒 Security

- API binds to `127.0.0.1` only (localhost)
- No external network exposure by default
- Pydantic V2 for input validation

## 📝 License

MIT License
