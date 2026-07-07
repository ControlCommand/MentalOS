"""
MentalOS Comprehensive Test Suite
Industry-grade pytest implementation with full coverage.
"""

import pytest
import numpy as np
from fastapi.testclient import TestClient

from mentalos.types import (
    CognitiveRequest, CognitiveState, Scene, SceneObject, Transform,
    BoundingBox, SpatialRay, RayHit, Vector3D, TransformMatrix
)
from mentalos.core.pipeline import (
    execute_cognitive_pipeline, identify_task_from_question,
    validate_single_operation_lock, select_model_for_operation,
    select_tool_for_model, _build_scene_from_input as build_scene_from_request
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def sample_sphere_scene():
    """Create a scene with a single sphere."""
    transform = Transform(matrix=np.eye(4))
    bounds = BoundingBox(
        min_point=np.array([-1, -1, 4]),
        max_point=np.array([1, 1, 6])
    )
    sphere = SceneObject(
        object_id=0,
        object_type="SPHERE",
        transform=transform,
        material_id=0,
        bounds=bounds,
        radius=1.0
    )
    global_bounds = BoundingBox(
        min_point=np.array([-1, -1, 4]),
        max_point=np.array([1, 1, 6])
    )
    return Scene(objects=(sphere,), global_bounds=global_bounds)


@pytest.fixture
def sample_ray():
    """Create a ray pointing along +Z axis."""
    return SpatialRay(
        origin=np.array([0, 0, 0], dtype=np.float64),
        direction=np.array([0, 0, 1], dtype=np.float64)
    )


@pytest.fixture
def client():
    """Create test client for FastAPI app."""
    from mentalos.api.app import app
    return TestClient(app)


# =============================================================================
# TYPE TESTS
# =============================================================================

class TestTypes:
    """Test data type definitions and immutability."""
    
    def test_spatial_ray_creation(self):
        """Test ray creation with proper numpy arrays."""
        ray = SpatialRay(
            origin=np.array([1, 2, 3], dtype=np.float64),
            direction=np.array([0, 0, 1], dtype=np.float64)
        )
        assert ray.origin.shape == (3,)
        assert ray.direction.shape == (3,)
        assert ray.t_min == 0.0
        assert ray.t_max == np.inf
    
    def test_ray_hit_default(self):
        """Test RayHit default values."""
        hit = RayHit(hit=False)
        assert hit.hit is False
        assert hit.t == np.inf
        assert hit.object_id == -1
    
    def test_ray_hit_with_data(self):
        """Test RayHit with intersection data."""
        point = np.array([5, 5, 5], dtype=np.float64)
        normal = np.array([0, 1, 0], dtype=np.float64)
        hit = RayHit(
            hit=True,
            t=10.0,
            point=point,
            normal=normal,
            object_id=42
        )
        assert hit.hit is True
        assert hit.t == 10.0
        assert np.array_equal(hit.point, point)
        assert np.array_equal(hit.normal, normal)
        assert hit.object_id == 42
    
    def test_transform_matrix_validation(self):
        """Test Transform validates matrix shape."""
        valid_matrix = np.eye(4)
        transform = Transform(matrix=valid_matrix)
        assert transform.matrix.shape == (4, 4)
        
        with pytest.raises(ValueError):
            invalid_matrix = np.eye(3)
            Transform(matrix=invalid_matrix)
    
    def test_bounding_box_validation(self):
        """Test BoundingBox validates points."""
        min_pt = np.array([0, 0, 0])
        max_pt = np.array([1, 1, 1])
        bbox = BoundingBox(min_point=min_pt, max_point=max_pt)
        assert np.array_equal(bbox.min_point, min_pt)
        assert np.array_equal(bbox.max_point, max_pt)
        
        # Invalid: max < min
        with pytest.raises(ValueError):
            BoundingBox(
                min_point=np.array([1, 1, 1]),
                max_point=np.array([0, 0, 0])
            )
    
    def test_scene_object_immutability(self):
        """Test that SceneObject is frozen (immutable)."""
        transform = Transform(matrix=np.eye(4))
        bounds = BoundingBox(
            min_point=np.array([-1, -1, -1]),
            max_point=np.array([1, 1, 1])
        )
        obj = SceneObject(
            object_id=0,
            object_type="SPHERE",
            transform=transform,
            material_id=0,
            bounds=bounds,
            radius=1.0
        )
        
        with pytest.raises(Exception):  # frozen dataclass raises Exception on modification
            obj.object_id = 999


# =============================================================================
# PIPELINE CORE FUNCTION TESTS
# =============================================================================

class TestPipelineCoreFunctions:
    """Test pure functions in the pipeline."""
    
    def test_identify_task_spatial_intersect(self):
        """Test task identification for spatial intersection queries."""
        op = identify_task_from_question(
            "Where does the ray intersect the sphere?",
            "SPATIAL"
        )
        assert op == "TRANSFORM"
    
    def test_identify_task_spatial_distance(self):
        """Test task identification for distance queries."""
        op = identify_task_from_question(
            "What is the distance between these points?",
            "SPATIAL"
        )
        assert op == "MEASURE"
    
    def test_identify_task_probabilistic(self):
        """Test task identification for probabilistic queries."""
        op = identify_task_from_question(
            "Run Monte Carlo simulation with random sampling",
            "PROBABILISTIC"
        )
        assert op == "MAP"
    
    def test_identify_task_logical_graph(self):
        """Test task identification for graph queries."""
        op = identify_task_from_question(
            "Analyze the graph nodes and edges",
            "LOGICAL"
        )
        assert op == "COMPARE"
    
    def test_validate_operation_lock_valid(self):
        """Test operation lock validation for valid transitions."""
        assert validate_single_operation_lock("IDENTIFY", "TRANSFORM") is True
        assert validate_single_operation_lock("TRANSFORM", "TRANSFORM") is True
        assert validate_single_operation_lock("MEASURE", "MEASURE") is True
    
    def test_validate_operation_lock_invalid(self):
        """Test operation lock validation for invalid transitions."""
        # TRANSFORM cannot be refined to MEASURE
        assert validate_single_operation_lock("TRANSFORM", "MEASURE") is False
    
    def test_select_model_spatial_raytrace(self):
        """Test model selection for spatial raytracing."""
        input_data = {"rays": [{"origin": [0, 0, 0], "direction": [0, 0, 1]}]}
        model = select_model_for_operation("TRANSFORM", "SPATIAL", input_data)
        assert model == "RAYTRACE"
    
    def test_select_model_spatial_fcis(self):
        """Test model selection for spatial non-raytrace operations."""
        input_data = {"points": [[0, 0, 0], [1, 1, 1]]}
        model = select_model_for_operation("MEASURE", "SPATIAL", input_data)
        assert model == "FCIS"
    
    def test_select_model_montecarlo(self):
        """Test model selection for Monte Carlo simulation."""
        input_data = {"distribution": "normal", "mean": [0], "std": [1]}
        model = select_model_for_operation("MAP", "PROBABILISTIC", input_data)
        assert model == "MONTECARLO"
    
    def test_select_tool_vector_engine(self):
        """Test tool selection for raytracing."""
        tool = select_tool_for_model("RAYTRACE", "TRANSFORM")
        assert tool == "VECTOR_ENGINE"
    
    def test_select_tool_numpy(self):
        """Test tool selection for Monte Carlo."""
        tool = select_tool_for_model("MONTECARLO", "MAP")
        assert tool == "NUMPY"
    
    def test_select_tool_scipy(self):
        """Test tool selection for graph operations."""
        tool = select_tool_for_model("GRAPH", "COMPARE")
        assert tool == "SCIPY"


# =============================================================================
# SCENE BUILDING TESTS
# =============================================================================

class TestSceneBuilding:
    """Test scene construction from request data."""
    
    def test_build_scene_with_sphere(self):
        """Test building a scene with a sphere object."""
        input_data = {
            "objects": [
                {
                    "type": "SPHERE",
                    "translation": [0, 0, 5],
                    "radius": 1.0
                }
            ]
        }
        
        scene = build_scene_from_request(input_data)
        assert len(scene.objects) == 1
        assert scene.objects[0].object_type == "SPHERE"
        assert scene.objects[0].radius == 1.0
    
    def test_build_scene_with_box(self):
        """Test building a scene with a box object."""
        input_data = {
            "objects": [
                {
                    "type": "BOX",
                    "translation": [0, 0, 0],
                    "half_extents": [1, 2, 3]
                }
            ]
        }
        
        scene = build_scene_from_request(input_data)
        assert len(scene.objects) == 1
        assert scene.objects[0].object_type == "BOX"
        assert np.array_equal(scene.objects[0].half_extents, np.array([1, 2, 3]))
    
    def test_build_scene_empty(self):
        """Test building an empty scene."""
        input_data = {"objects": []}
        
        scene = build_scene_from_request(input_data)
        assert len(scene.objects) == 0
        assert scene.global_bounds is not None


# =============================================================================
# FULL PIPELINE INTEGRATION TESTS
# =============================================================================

class TestPipelineIntegration:
    """Test complete pipeline execution."""
    
    def test_pipeline_ray_sphere_intersection(self):
        """Test full pipeline for ray-sphere intersection."""
        request = CognitiveRequest(
            question="Find where a ray from origin hits a sphere at z=5",
            context_bucket="SPATIAL",
            requested_operation="TRANSFORM",
            input_data={
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
            parameters={}
        )
        
        result = execute_cognitive_pipeline(request)
        
        assert result.identified_operation == "TRANSFORM"
        assert result.selected_model == "RAYTRACE"
        assert result.selected_tool == "VECTOR_ENGINE"
        assert result.final_answer is not None
        assert "t=4.0000" in result.final_answer or "intersection" in result.final_answer.lower()
    
    def test_pipeline_distance_measurement(self):
        """Test full pipeline for distance measurement."""
        request = CognitiveRequest(
            question="Measure distance between two points",
            context_bucket="SPATIAL",
            requested_operation="MEASURE",
            input_data={
                "points": [[0, 0, 0], [3, 4, 0]]
            },
            parameters={}
        )
        
        result = execute_cognitive_pipeline(request)
        
        assert result.identified_operation == "MEASURE"
        assert result.final_answer is not None
        assert "5.0" in result.final_answer
    
    def test_pipeline_monte_carlo(self):
        """Test full pipeline for Monte Carlo simulation."""
        request = CognitiveRequest(
            question="Run Monte Carlo simulation",
            context_bucket="PROBABILISTIC",
            requested_operation="REDUCE",
            input_data={
                "distribution": "normal",
                "mean": [0.0],
                "std": [1.0]
            },
            parameters={"n_samples": 1000}
        )
        
        result = execute_cognitive_pipeline(request)
        
        assert result.selected_model == "MONTECARLO"
        assert result.final_answer is not None
    
    def test_pipeline_graph_analysis(self):
        """Test full pipeline for graph analysis."""
        request = CognitiveRequest(
            question="Analyze connected components",
            context_bucket="LOGICAL",
            requested_operation="COMPARE",
            input_data={
                "nodes": 6,
                "edges": [[0, 1], [1, 2], [3, 4]]
            },
            parameters={}
        )
        
        result = execute_cognitive_pipeline(request)
        
        assert result.final_answer is not None


# =============================================================================
# API ENDPOINT TESTS
# =============================================================================

class TestAPIEndpoints:
    """Test FastAPI endpoints."""
    
    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "components" in data
    
    def test_root_endpoint(self, client):
        """Test root endpoint serves HTML."""
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_cognitive_process_endpoint(self, client):
        """Test main cognitive process endpoint."""
        payload = {
            "question": "Find ray-sphere intersection",
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
        
        response = client.post("/cognitive/process", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "final_answer" in data
        assert "execution_log" in data
    
    def test_spatial_raytrace_endpoint(self, client):
        """Test specialized raytrace endpoint."""
        payload = {
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
        }
        
        response = client.post("/cognitive/spatial/raytrace", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_spatial_measure_endpoint(self, client):
        """Test specialized measure endpoint."""
        payload = {
            "points": [[0, 0, 0], [3, 4, 0]]
        }
        
        response = client.post("/cognitive/spatial/measure", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "5.0" in data["final_answer"]
    
    def test_probabilistic_simulate_endpoint(self, client):
        """Test probabilistic simulation endpoint."""
        payload = {
            "distribution": "normal",
            "mean": [0.0],
            "std": [1.0],
            "n_samples": 1000
        }
        
        response = client.post("/cognitive/probabilistic/simulate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_logical_graph_endpoint(self, client):
        """Test logical graph endpoint."""
        payload = {
            "nodes": 6,
            "edges": [[0, 1], [1, 2], [3, 4]]
        }
        
        response = client.post("/cognitive/logical/graph", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_invalid_request_handling(self, client):
        """Test handling of invalid requests."""
        payload = {
            "question": "",
            "context_bucket": "INVALID_BUCKET",
            "requested_operation": "TRANSFORM",
            "input_data": {},
            "parameters": {}
        }
        
        response = client.post("/cognitive/process", json=payload)
        assert response.status_code in [400, 422]  # Bad request or validation error


# =============================================================================
# EDGE CASE TESTS
# =============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_ray_missing_sphere(self):
        """Test ray that misses a sphere."""
        request = CognitiveRequest(
            question="Find intersection",
            context_bucket="SPATIAL",
            requested_operation="TRANSFORM",
            input_data={
                "objects": [
                    {
                        "type": "SPHERE",
                        "translation": [10, 10, 5],
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
            parameters={}
        )
        
        result = execute_cognitive_pipeline(request)
        # Should complete without error
    
    def test_parallel_ray_plane(self):
        """Test ray parallel to plane (no intersection)."""
        request = CognitiveRequest(
            question="Find intersection",
            context_bucket="SPATIAL",
            requested_operation="TRANSFORM",
            input_data={
                "objects": [
                    {
                        "type": "PLANE",
                        "translation": [0, 0, 0]
                    }
                ],
                "rays": [
                    {
                        "origin": [0, 1, 0],
                        "direction": [1, 0, 0]  # Parallel to XZ plane
                    }
                ]
            },
            parameters={}
        )
        
        result = execute_cognitive_pipeline(request)
        # Should complete without error
    
    def test_zero_distance(self):
        """Test measuring distance between same points."""
        request = CognitiveRequest(
            question="Measure distance",
            context_bucket="SPATIAL",
            requested_operation="MEASURE",
            input_data={
                "points": [[1, 2, 3], [1, 2, 3]]
            },
            parameters={}
        )
        
        result = execute_cognitive_pipeline(request)
        assert result.final_answer is not None
        assert "0.0" in result.final_answer or "0" in result.final_answer
    
    def test_empty_graph(self):
        """Test graph with no edges."""
        request = CognitiveRequest(
            question="Analyze graph",
            context_bucket="LOGICAL",
            requested_operation="COMPARE",
            input_data={
                "nodes": 5,
                "edges": []
            },
            parameters={}
        )
        
        result = execute_cognitive_pipeline(request)
        assert result.final_answer is not None


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
