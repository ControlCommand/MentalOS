"""
MentalOS FastAPI Application
Secure, production-ready API with Pydantic V2 compliance.
Bound to 127.0.0.1 for local-only access.
"""

from __future__ import annotations
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict, Field
import os

from mentalos.types import CognitiveRequest, PipelineResult, QuestionPart
from mentalos.core.pipeline import execute_pipeline, parse_question_parts


# ============================================================================
# PYDANTIC V2 MODELS
# ============================================================================

class CognitiveRequestModel(BaseModel):
    """Pydantic V2 model for cognitive requests."""
    model_config = ConfigDict(extra='forbid')
    
    question_text: str = Field(..., min_length=1, description="The physics/math problem text")
    part: Optional[QuestionPart] = Field(None, description="Specific part to solve (a, b, c, etc.)")
    context: Optional[str] = Field(None, description="Additional context")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Additional parameters")


class OperationNodeModel(BaseModel):
    """Pydantic V2 model for operation nodes."""
    model_config = ConfigDict(extra='forbid')
    
    operation: str
    bucket: str
    model: str
    tool: str
    dependencies: List[str]
    order: int


class ExtractedValueModel(BaseModel):
    """Pydantic V2 model for extracted values."""
    model_config = ConfigDict(extra='forbid')
    
    name: str
    value: float
    unit: str
    confidence: float


class CognitiveStateModel(BaseModel):
    """Pydantic V2 model for cognitive state."""
    model_config = ConfigDict(extra='forbid')
    
    extracted_values: List[ExtractedValueModel]
    identified_operation: Optional[str]
    selected_bucket: Optional[str]
    selected_model: Optional[str]
    selected_tool: Optional[str]
    operation_dag: List[OperationNodeModel]
    intermediate_results: Dict[str, float]
    final_answer: Optional[float]
    answer_unit: Optional[str]
    audit_log: List[str]


class CognitiveResponseModel(BaseModel):
    """Pydantic V2 model for cognitive responses."""
    model_config = ConfigDict(extra='forbid')
    
    success: bool
    answer: Optional[float]
    unit: Optional[str]
    explanation: str
    error_message: Optional[str]
    state: Optional[CognitiveStateModel] = None


class HealthResponse(BaseModel):
    """Pydantic V2 model for health check."""
    model_config = ConfigDict(extra='forbid')
    
    status: str
    version: str
    operations: List[str]
    buckets: List[str]


# ============================================================================
# FASTAPI APPLICATION
# ============================================================================

app = FastAPI(
    title="MentalOS",
    description="Deterministic Cognitive Physics Engine",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)


# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/", response_class=HTMLResponse, tags=["UI"])
async def root():
    """Serve the main web UI."""
    static_path = os.path.join(os.path.dirname(__file__), '..', 'static')
    index_path = os.path.join(static_path, 'index.html')
    
    if os.path.exists(index_path):
        with open(index_path, 'r', encoding='utf-8') as f:
            return HTMLResponse(content=f.read(), status_code=200)
    else:
        return HTMLResponse(
            content="<h1>MentalOS API</h1><p>Visit <a href='/docs'>/docs</a> for API documentation.</p>",
            status_code=200
        )


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """System health check endpoint."""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        operations=["accumulate", "transform", "scale", "estimate", "differentiate"],
        buckets=["accumulation", "transformation", "geometry", "kinematics", "dynamics", "conservation"]
    )


@app.post("/cognitive/process", response_model=CognitiveResponseModel, tags=["Cognitive"])
async def process_cognitive_request(request: CognitiveRequestModel):
    """
    Process a cognitive physics/math problem.
    
    Implements the full FCIS pipeline:
    1. Question Analysis
    2. Requested Output Inference
    3. Primary Operation Identification (Winner-Takes-All)
    4. Bucket Selection
    5. Model Selection
    6. Tool Selection
    7. DAG Construction (Nested Operations)
    8. Execution
    """
    try:
        # Convert Pydantic model to domain model
        cognitive_request = CognitiveRequest(
            question_text=request.question_text,
            part=request.part,
            context=request.context,
            parameters=request.parameters or {}
        )
        
        # Execute pipeline
        result = execute_pipeline(cognitive_request)
        
        # Convert result to response model
        if result.state:
            state_model = CognitiveStateModel(
                extracted_values=[
                    ExtractedValueModel(
                        name=v.name,
                        value=v.value,
                        unit=v.unit,
                        confidence=v.confidence
                    )
                    for v in result.state.extracted_values
                ],
                identified_operation=result.state.identified_operation,
                selected_bucket=result.state.selected_bucket,
                selected_model=result.state.selected_model,
                selected_tool=result.state.selected_tool,
                operation_dag=[
                    OperationNodeModel(
                        operation=node.operation,
                        bucket=node.bucket,
                        model=node.model,
                        tool=node.tool,
                        dependencies=list(node.dependencies),
                        order=node.order
                    )
                    for node in result.state.operation_dag
                ],
                intermediate_results=result.state.intermediate_results,
                final_answer=result.state.final_answer,
                answer_unit=result.state.answer_unit,
                audit_log=list(result.state.audit_log)
            )
        else:
            state_model = None
        
        return CognitiveResponseModel(
            success=result.success,
            answer=result.answer,
            unit=result.unit,
            explanation=result.explanation,
            error_message=result.error_message,
            state=state_model
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/cognitive/parts", tags=["Cognitive"])
async def get_question_parts(question_text: str):
    """
    Parse and return all parts of a multi-part question.
    """
    try:
        parts = parse_question_parts(question_text)
        return {
            "success": True,
            "parts": parts
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# STATIC FILES
# ============================================================================

# Mount static files directory
static_path = os.path.join(os.path.dirname(__file__), '..', 'static')
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def run_server(host: str = "127.0.0.1", port: int = 8000, reload: bool = False):
    """
    Run the MentalOS server.
    
    Security: Binds to 127.0.0.1 by default to prevent network exposure.
    """
    import uvicorn
    
    uvicorn.run(
        "mentalos.api.app:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )


if __name__ == "__main__":
    # Production: bind to localhost only for security
    run_server(host="127.0.0.1", port=8000, reload=False)
