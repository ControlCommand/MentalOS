"""
MentalOS FastAPI Shell Layer
Production-ready API boundary following industry standards.
"""

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, Any, Union
import numpy as np

from mentalos.core.pipeline import execute_cognitive_pipeline
from mentalos.types import (
    CognitiveRequest, CognitiveState, OperationName, BucketName
)

# =============================================================================
# PYDANTIC MODELS FOR API REQUEST/RESPONSE
# =============================================================================

class CognitiveRequestModel(BaseModel):
    """API request model for cognitive pipeline."""
    question: str = Field(..., description="The question to process")
    context_bucket: BucketName = Field(..., description="Context bucket category")
    requested_operation: OperationName = Field(..., description="Requested operation type")
    input_data: dict = Field(default_factory=dict, description="Input data for processing")
    parameters: Optional[dict] = Field(default=None, description="Optional parameters")
    
    class Config:
        json_schema_extra = {
            "example": {
                "question": "Find where a ray from origin hits a sphere",
                "context_bucket": "SPATIAL",
                "requested_operation": "TRANSFORM",
                "input_data": {
                    "objects": [
                        {
                            "type": "SPHERE",
                            "translation": [0, 0, 5],
                            "radius": 1.0
                        }
                    ],
                    "rays": [
                        {
                            "origin": [0, 0, 0],
                            "direction": [0, 0, 1]
                        }
                    ]
                },
                "parameters": {}
            }
        }


class CognitiveResponseModel(BaseModel):
    """API response model for cognitive pipeline results."""
    success: bool
    identified_operation: OperationName
    selected_model: str
    selected_tool: str
    final_answer: str
    execution_log: list[str]
    intermediate_results: dict
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "identified_operation": "TRANSFORM",
                "selected_model": "RAYTRACE",
                "selected_tool": "VECTOR_ENGINE",
                "final_answer": "Found 1 ray intersection(s). Closest hit at t=4.0000 on object 0",
                "execution_log": [
                    "Identified operation: TRANSFORM",
                    "Selected model: RAYTRACE",
                    "Selected tool: VECTOR_ENGINE",
                    "Execution completed successfully",
                    "Answer formatted"
                ],
                "intermediate_results": {"scene_objects": 1}
            }
        }


class HealthResponseModel(BaseModel):
    """Health check response model."""
    status: str
    version: str
    components: dict


# =============================================================================
# FASTAPI APPLICATION
# =============================================================================

app = FastAPI(
    title="MentalOS Cognitive Engine API",
    description="Deterministic FCIS (Functional Cognitive Inference System) API for Physics/Spatial inference",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)


@app.get("/health", response_model=HealthResponseModel, tags=["System"])
async def health_check():
    """
    Health check endpoint to verify system status.
    """
    return HealthResponseModel(
        status="healthy",
        version="1.0.0",
        components={
            "pipeline": "operational",
            "spatial_engine": "operational",
            "monte_carlo": "operational",
            "graph_engine": "operational"
        }
    )


@app.post(
    "/cognitive/process",
    response_model=CognitiveResponseModel,
    responses={
        200: {"description": "Successful processing"},
        400: {"description": "Invalid request"},
        500: {"description": "Processing error"}
    },
    tags=["Cognitive Pipeline"]
)
async def process_cognitive_request(request: CognitiveRequestModel):
    """
    Process a cognitive request through the deterministic FCIS pipeline.
    
    This endpoint executes the full pipeline:
    Question → Requested Output → Primary Operation → Bucket → Model → Tool → Execution → Answer
    
    - **question**: Natural language question describing the task
    - **context_bucket**: The cognitive domain (SPATIAL, TEMPORAL, LOGICAL, etc.)
    - **requested_operation**: The operation type (IDENTIFY, TRANSFORM, MEASURE, etc.)
    - **input_data**: Structured data for the operation
    - **parameters**: Optional configuration parameters
    """
    try:
        # Convert Pydantic model to internal CognitiveRequest
        cognitive_request = CognitiveRequest(
            question=request.question,
            context_bucket=request.context_bucket,
            requested_operation=request.requested_operation,
            input_data=request.input_data,
            parameters=request.parameters
        )
        
        # Execute the deterministic pipeline
        result: CognitiveState = execute_cognitive_pipeline(cognitive_request)
        
        # Check for errors in the result
        if result.final_answer.startswith("Error:") or result.final_answer.startswith("Execution failed:"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.final_answer
            )
        
        # Build response
        return CognitiveResponseModel(
            success=True,
            identified_operation=result.identified_operation,
            selected_model=result.selected_model,
            selected_tool=result.selected_tool,
            final_answer=result.final_answer,
            execution_log=list(result.execution_log),
            intermediate_results=result.intermediate_results
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pipeline execution failed: {str(e)}"
        )


@app.post(
    "/cognitive/spatial/raytrace",
    response_model=CognitiveResponseModel,
    tags=["Spatial Operations"]
)
async def spatial_raytrace(
    request_data: dict,
    question: Optional[str] = None
):
    """
    Specialized endpoint for raytracing operations.
    
    Performs ray-scene intersection tests using vectorized computation.
    
    Request body should contain:
    - objects: List of scene objects
    - rays: List of rays to trace
    """
    objects = request_data.get("objects", [])
    rays = request_data.get("rays", [])
    
    req = CognitiveRequestModel(
        question=question or "Perform raytracing",
        context_bucket="SPATIAL",
        requested_operation="TRANSFORM",
        input_data={
            "objects": objects,
            "rays": rays
        }
    )
    
    return await process_cognitive_request(req)


@app.post(
    "/cognitive/spatial/measure",
    response_model=CognitiveResponseModel,
    tags=["Spatial Operations"]
)
async def spatial_measure(
    request_data: dict,
    question: Optional[str] = None
):
    """
    Specialized endpoint for spatial measurements.
    
    Computes distances between points in 3D space.
    
    Request body should contain:
    - points: List of points to measure between
    """
    points = request_data.get("points", [])
    
    req = CognitiveRequestModel(
        question=question or "Measure distance",
        context_bucket="SPATIAL",
        requested_operation="MEASURE",
        input_data={
            "points": points
        }
    )
    
    return await process_cognitive_request(req)


@app.post(
    "/cognitive/probabilistic/simulate",
    response_model=CognitiveResponseModel,
    tags=["Probabilistic Operations"]
)
async def probabilistic_simulation(
    request_data: dict,
    question: Optional[str] = None
):
    """
    Specialized endpoint for Monte Carlo simulations.
    
    Performs statistical analysis using vectorized random sampling.
    
    Request body should contain:
    - distribution: Distribution type (normal, uniform)
    - mean: Mean values
    - std: Standard deviation values
    - n_samples: Number of samples (default: 10000)
    """
    distribution = request_data.get("distribution", "normal")
    mean = request_data.get("mean", [0.0])
    std = request_data.get("std", [1.0])
    n_samples = request_data.get("n_samples", 10000)
    
    req = CognitiveRequestModel(
        question=question or "Run Monte Carlo simulation",
        context_bucket="PROBABILISTIC",
        requested_operation="MAP",
        input_data={
            "distribution": distribution,
            "mean": mean,
            "std": std
        },
        parameters={"n_samples": n_samples}
    )
    
    return await process_cognitive_request(req)


@app.post(
    "/cognitive/logical/graph",
    response_model=CognitiveResponseModel,
    tags=["Logical Operations"]
)
async def logical_graph_analysis(
    request_data: dict,
    question: Optional[str] = None
):
    """
    Specialized endpoint for graph-based logical operations.
    
    Performs connected component analysis and shortest path computation.
    
    Request body should contain:
    - nodes: Number of nodes
    - edges: Edge list with optional weights
    - source: Source node for path finding (optional)
    """
    nodes = request_data.get("nodes", 0)
    edges = request_data.get("edges", [])
    source = request_data.get("source", 0)
    
    req = CognitiveRequestModel(
        question=question or "Analyze graph",
        context_bucket="LOGICAL",
        requested_operation="COMPARE",
        input_data={
            "nodes": nodes,
            "edges": edges,
            "source": source
        }
    )
    
    return await process_cognitive_request(req)


# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    return {
        "success": False,
        "error": "validation_error",
        "detail": str(exc)
    }


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return {
        "success": False,
        "error": "internal_error",
        "detail": str(exc)
    }


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
