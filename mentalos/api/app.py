"""
MentalOS FastAPI Application

Secure, production-ready API with Pydantic V2 patterns.
Binds to 127.0.0.1 only for local security.
"""
from __future__ import annotations
import uvicorn
from fastapi import FastAPI, HTTPException, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Dict, Any, List
import os

from mentalos.core.pipeline import CognitivePipeline
from mentalos.types import (
    CognitiveRequest, CognitiveState, CognitiveResult,
    StepResult, UserPrompt, PrimaryOperation
)


# =============================================================================
# PYDANTIC V2 MODELS
# =============================================================================

class CognitiveRequestModel(BaseModel):
    """Pydantic V2 model for cognitive requests."""
    model_config = ConfigDict(
        arbitrary_types_allowed=False,
        json_schema_extra={"example": {"question_text": "A man pushes a 45 kg box..."}}
    )

    question_text: str = Field(..., description="The physics/math problem text")
    question_parts: Optional[Dict[str, str]] = Field(None, description="Multi-part questions {a: text, b: text}")
    selected_part: Optional[str] = Field(None, description="Which part to solve (a, b, c, d)")
    user_context: Optional[Dict[str, Any]] = Field(None, description="Additional user context")


class CognitiveResponseModel(BaseModel):
    """Pydantic V2 model for cognitive responses."""
    model_config = ConfigDict(
        arbitrary_types_allowed=False,
        json_schema_extra={"example": {
            "session_id": "abc12345",
            "stage": "complete",
            "requires_user_input": False
        }}
    )

    session_id: str
    stage: str
    requires_user_input: bool
    user_prompt: Optional[Dict[str, Any]] = None
    partial_result: Optional[Dict[str, Any]] = None
    final_result: Optional[Dict[str, Any]] = None
    state_summary: Dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    """Health check response."""
    model_config = ConfigDict(json_schema_extra={"example": {"status": "healthy", "version": "1.0.0"}})

    status: str
    version: str
    pipeline_ready: bool
    equations_loaded: int


class EquationSearchRequest(BaseModel):
    """Equation search request."""
    model_config = ConfigDict(json_schema_extra={"example": {"keywords": ["work", "force"]}})

    keywords: List[str]
    min_score: float = Field(default=0.3, ge=0.0, le=1.0)
    limit: int = Field(default=10, ge=1, le=50)


class ExecuteStepRequest(BaseModel):
    """Execute computation step request."""
    model_config = ConfigDict(json_schema_extra={"example": {
        "step_number": 1,
        "equation_id": "work_constant_force",
        "input_values": {"F": 87.0, "d": 13.0, "θ": 33.0}
    }})

    step_number: int = Field(..., ge=1)
    equation_id: str
    input_values: Dict[str, float]


# =============================================================================
# FASTAPI APPLICATION
# =============================================================================

app = FastAPI(
    title="MentalOS Cognitive Engine",
    description="Deterministic Physics/Spatial Inference Engine with DAG-based Operation Resolution",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Initialize pipeline
pipeline = CognitivePipeline()


# =============================================================================
# STATIC FILES & WEB UI
# =============================================================================

# Create static directory if not exists
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
os.makedirs(static_dir, exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", response_class=HTMLResponse, tags=["Web UI"])
async def serve_web_ui():
    """Serve the main web interface."""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)

    # Fallback minimal UI if index.html doesn't exist
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>MentalOS - Cognitive Physics Engine</title>
        <style>
            body { font-family: 'Segoe UI', sans-serif; background: #0f172a; color: #e2e8f0; margin: 0; padding: 20px; }
            .container { max-width: 1200px; margin: 0 auto; }
            h1 { color: #38bdf8; }
            .card { background: #1e293b; border-radius: 8px; padding: 20px; margin: 20px 0; }
            button { background: #38bdf8; color: #0f172a; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; font-weight: bold; }
            button:hover { background: #7dd3fc; }
            textarea { width: 100%; min-height: 150px; background: #0f172a; color: #e2e8f0; border: 1px solid #334155; border-radius: 6px; padding: 10px; }
            .result { background: #064e3b; padding: 15px; border-radius: 6px; margin-top: 20px; }
            .error { background: #7f1d1d; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🧠 MentalOS v1.0.0</h1>
            <p>Deterministic Physics/Spatial Inference Engine</p>

            <div class="card">
                <h2>Solve Physics Problem</h2>
                <textarea id="question" placeholder="Enter your physics problem here...&#10;&#10;Example: A man pushes a 45 kg box from rest along a horizontal floor by exerting a force of 87 N downward at 33° to the horizontal against a friction force of 62 N over a distance of 13 m.&#10;a) How much work was done in moving the box?"></textarea>
                <br><br>
                <button onclick="solveProblem()">Analyze Problem</button>
            </div>

            <div id="result" class="card" style="display:none;"></div>
        </div>

        <script>
            async function solveProblem() {
                const question = document.getElementById('question').value;
                const resultDiv = document.getElementById('result');

                try {
                    const response = await fetch('/cognitive/process', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({question_text: question})
                    });

                    const data = await response.json();
                    resultDiv.style.display = 'block';
                    resultDiv.className = 'card result';
                    resultDiv.innerHTML = '<h3>Analysis Result</h3><pre>' + JSON.stringify(data, null, 2) + '</pre>';
                } catch (error) {
                    resultDiv.style.display = 'block';
                    resultDiv.className = 'card error';
                    resultDiv.innerHTML = '<h3>Error</h3><p>' + error.message + '</p>';
                }
            }
        </script>
    </body>
    </html>
    """


# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Check system health and readiness."""
    eq_count = len(pipeline.equation_db.equations)
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        pipeline_ready=True,
        equations_loaded=eq_count
    )


@app.post("/cognitive/process", response_model=CognitiveResponseModel, tags=["Cognitive Pipeline"])
async def process_cognitive_request(request: CognitiveRequestModel):
    """
    Process a physics/math problem through the cognitive pipeline.

    This endpoint initiates the full pipeline:
    1. Question Analysis
    2. Requested Output Determination
    3. Constraint Lock
    4. Operation Lock (Winner Takes All)
    5. Bucket Assignment
    6. Model Selection
    7. Tool Selection
    8. Nested Operation Discovery
    """
    try:
        # Convert Pydantic model to internal type
        cognitive_request = CognitiveRequest(
            question_text=request.question_text,
            question_parts=request.question_parts,
            selected_part=request.selected_part,
            user_context=request.user_context
        )

        # Create session and run pipeline stages
        state = pipeline.create_session(cognitive_request)
        state = pipeline.determine_requested_output(state.session_id)
        state = pipeline.apply_constraint_lock(state.session_id)
        state = pipeline.determine_operation_lock(state.session_id)
        state = pipeline.assign_bucket(state.session_id)
        state = pipeline.select_model(state.session_id)
        state = pipeline.select_tool(state.session_id)
        state = pipeline.discover_nested_operations(state.session_id, user_confirms_secondary=True)

        # Check if nested operations exist
        requires_input = False
        user_prompt = None

        if state.execution_plan and state.execution_plan.nested_operations:
            requires_input = True
            user_prompt = {
                "prompt_type": "identify_secondary_operations",
                "message": f"Detected {len(state.execution_plan.nested_operations)} secondary operations needed before primary operation.",
                "options": ["Proceed with nested operations", "Skip secondary operations"],
                "nested_operations": [
                    {
                        "order": op.order,
                        "operation": op.operation,
                        "bucket": op.bucket,
                        "model": op.model,
                        "tool": op.tool,
                        "target_variable": op.target_variable
                    }
                    for op in state.execution_plan.nested_operations
                ]
            }

        # Build response
        state_summary = {
            "current_stage": state.current_stage,
            "primary_operation": state.operation_lock.primary_operation if state.operation_lock else None,
            "bucket": state.bucket_assignment.primary_bucket if state.bucket_assignment else None,
            "model": state.model_selection.primary_model if state.model_selection else None,
            "tool": state.tool_selection.primary_tool if state.tool_selection else None,
            "has_nested_operations": len(state.execution_plan.nested_operations) > 0 if state.execution_plan else False,
            "is_complete": state.is_complete
        }

        return CognitiveResponseModel(
            session_id=state.session_id,
            stage=state.current_stage,
            requires_user_input=requires_input,
            user_prompt=user_prompt,
            partial_result=None,
            final_result=None,
            state_summary=state_summary
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/cognitive/execute-step", response_model=CognitiveResponseModel, tags=["Cognitive Pipeline"])
async def execute_computation_step(
    session_id: str = Body(..., embed=True),
    step_number: int = Body(..., embed=True),
    equation_id: str = Body(..., embed=True),
    input_values: Dict[str, float] = Body(..., embed=True)
):
    """Execute a single computation step in the pipeline."""
    try:
        state, step_result = pipeline.execute_step(
            session_id=session_id,
            step_number=step_number,
            equation_id=equation_id,
            input_values=input_values
        )

        # Check if all steps complete
        if state.execution_plan and len(state.step_results) >= len(state.execution_plan.nested_operations):
            # Execute final step (primary operation)
            state = pipeline.finalize_result(session_id)

        state_summary = {
            "current_stage": state.current_stage,
            "steps_completed": len(state.step_results),
            "last_result": {
                "variable": step_result.variable_name,
                "value": step_result.value,
                "unit": step_result.unit,
                "formula": step_result.formula_used
            } if step_result else None,
            "is_complete": state.is_complete
        }

        return CognitiveResponseModel(
            session_id=session_id,
            stage=state.current_stage,
            requires_user_input=not state.is_complete,
            user_prompt=None,
            partial_result={
                "step_number": step_result.step_number,
                "operation": step_result.operation,
                "variable_name": step_result.variable_name,
                "value": step_result.value,
                "unit": step_result.unit,
                "formula_used": step_result.formula_used,
                "success": step_result.success
            } if step_result else None,
            final_result={
                "question_part": state.final_result.question_part,
                "final_value": state.final_result.final_value,
                "unit": state.final_result.unit,
                "significant_figures": state.final_result.significant_figures
            } if state.final_result else None,
            state_summary=state_summary
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/cognitive/equations/search", tags=["Equations"])
async def search_equations(request: EquationSearchRequest):
    """Search equations by keywords with fuzzy matching."""
    results = pipeline.equation_db.search_by_keywords(
        keywords=request.keywords,
        min_score=request.min_score,
        limit=request.limit
    )

    return {
        "query": request.keywords,
        "results": [
            {
                "id": eq.id,
                "name": eq.name,
                "formula": eq.formula,
                "description": eq.description,
                "variables": eq.variables,
                "score": score
            }
            for eq, score in results
        ],
        "count": len(results)
    }


@app.get("/cognitive/equations/{equation_id}", tags=["Equations"])
async def get_equation(equation_id: str):
    """Get a specific equation by ID."""
    equation = pipeline.equation_db.get_equation(equation_id)

    if not equation:
        raise HTTPException(status_code=404, detail=f"Equation '{equation_id}' not found")

    return {
        "id": equation.id,
        "name": equation.name,
        "formula": equation.formula,
        "description": equation.description,
        "variables": equation.variables,
        "models": equation.models,
        "tools": equation.tools,
        "operations": equation.operations,
        "buckets": equation.buckets,
        "tags": equation.tags
    }


@app.get("/cognitive/session/{session_id}", response_model=CognitiveResponseModel, tags=["Cognitive Pipeline"])
async def get_session_state(session_id: str):
    """Get current state of a cognitive session."""
    try:
        state = pipeline.get_state(session_id)

        state_summary = {
            "current_stage": state.current_stage,
            "primary_operation": state.operation_lock.primary_operation if state.operation_lock else None,
            "bucket": state.bucket_assignment.primary_bucket if state.bucket_assignment else None,
            "model": state.model_selection.primary_model if state.model_selection else None,
            "tool": state.tool_selection.primary_tool if state.tool_selection else None,
            "steps_completed": len(state.step_results),
            "is_complete": state.is_complete
        }

        return CognitiveResponseModel(
            session_id=session_id,
            stage=state.current_stage,
            requires_user_input=not state.is_complete,
            user_prompt=None,
            partial_result=None,
            final_result={
                "question_part": state.final_result.question_part,
                "final_value": state.final_result.final_value,
                "unit": state.final_result.unit
            } if state.final_result else None,
            state_summary=state_summary
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    """Run the MentalOS API server."""
    print("🧠 Starting MentalOS Cognitive Engine v1.0.0")
    print("🔒 Binding to 127.0.0.1:8000 (localhost only)")
    print("📚 Documentation: http://127.0.0.1:8000/docs")

    uvicorn.run(
        "mentalos.api.app:app",
        host="127.0.0.1",  # Secure: localhost only
        port=8000,
        reload=False,
        log_level="info"
    )


if __name__ == "__main__":
    main()

+++ mentalos/api/app.py (修改后)
"""MentalOS FastAPI Application - Secure Local Server"""
from __future__ import annotations
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel, ConfigDict
import os

from mentalos.types.core_types import (
    CognitiveRequest,
    PrimaryOperation,
    Bucket,
    Model,
    CognitiveResult,
)
from mentalos.core.pipeline import process_cognitive_request

app = FastAPI(title="MentalOS", version="1.0.0")

# Mount static files
static_path = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")


class CognitiveRequestModel(BaseModel):
    """Pydantic V2 compliant request model"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "question_text": "A man pushes a 45 kg box from rest along a horizontal floor by exerting a force of 87 N downward at 33° to the horizontal against a friction force of 62 N over a distance of 13 m. How much work was done in moving the box?",
                "part_label": "a",
                "user_values": {"F": 87, "theta": 33, "d": 13, "m": 45}
            }
        }
    )

    question_text: str
    part_label: Optional[str] = None
    custom_operation: Optional[str] = None
    custom_bucket: Optional[str] = None
    custom_model: Optional[str] = None
    user_notes: str = ""
    user_values: dict[str, float] = {}


class ExecutionStepModel(BaseModel):
    """Pydantic V2 compliant execution step model"""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    step_number: int
    operation_node_id: str
    equation_used: str
    inputs: dict[str, float]
    output_value: float
    output_unit: str
    explanation: str


class CognitiveResponseModel(BaseModel):
    """Pydantic V2 compliant response model"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "final_answer": 948.54,
                "final_unit": "J",
                "answer_explanation": "W = F * d * cos(θ) = 73.0 * 13 * cos(33°) = 948.54 J",
                "total_steps": 2,
                "warnings": [],
                "audit_summary": "Processed 2 operation(s). Primary operation: accumulate. Resolved 1 nested operation(s) first."
            }
        }
    )

    success: bool
    final_answer: Optional[float] = None
    final_unit: Optional[str] = None
    answer_explanation: str
    execution_steps: list[ExecutionStepModel]
    total_steps: int
    warnings: list[str]
    audit_summary: str


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main web UI"""
    static_path = os.path.join(os.path.dirname(__file__), "static")
    index_path = os.path.join(static_path, "index.html")

    if os.path.exists(index_path):
        with open(index_path, "r") as f:
            return HTMLResponse(content=f.read())
    else:
        return HTMLResponse(content="<h1>MentalOS API</h1><p>Visit /docs for API documentation</p>")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "engine": "MentalOS Cognitive Pipeline",
        "security": "localhost-only binding"
    }


@app.post("/cognitive/process", response_model=CognitiveResponseModel)
async def process_request(request: CognitiveRequestModel):
    """Process a cognitive physics problem dynamically"""
    try:
        # Convert string enums to actual enum types if provided
        custom_op = None
        if request.custom_operation:
            try:
                custom_op = PrimaryOperation(request.custom_operation)
            except ValueError:
                pass

        custom_bkt = None
        if request.custom_bucket:
            try:
                custom_bkt = Bucket(request.custom_bucket)
            except ValueError:
                pass

        custom_mdl = None
        if request.custom_model:
            try:
                custom_mdl = Model(request.custom_model)
            except ValueError:
                pass

        # Create cognitive request
        cognitive_request = CognitiveRequest(
            question_text=request.question_text,
            part_label=request.part_label,
            custom_operation=custom_op,
            custom_bucket=custom_bkt,
            custom_model=custom_mdl,
            user_notes=request.user_notes
        )

        # Process the request
        result = process_cognitive_request(cognitive_request, request.user_values or {})

        # Convert result to response model
        return CognitiveResponseModel(
            success=result.success,
            final_answer=result.final_answer,
            final_unit=result.final_unit,
            answer_explanation=result.answer_explanation,
            execution_steps=[
                ExecutionStepModel(
                    step_number=step.step_number,
                    operation_node_id=step.operation_node_id,
                    equation_used=step.equation_used,
                    inputs=step.inputs,
                    output_value=step.output_value,
                    output_unit=step.output_unit,
                    explanation=step.explanation
                )
                for step in result.execution_steps
            ],
            total_steps=result.total_steps,
            warnings=result.warnings,
            audit_summary=result.audit_summary
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/operations")
async def list_operations():
    """List available primary operations"""
    return {
        "operations": [op.value for op in PrimaryOperation],
        "buckets": [bucket.value for bucket in Bucket],
        "models": [model.value for model in Model],
        "tools": ["trigonometry", "vector_algebra", "calculus_derivative",
                 "calculus_integral", "linear_algebra", "algebraic_manipulation"]
    }


def main():
    """Run the server with secure localhost binding"""
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()
