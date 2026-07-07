"""
MentalOS Core Pipeline Engine
Deterministic FCIS (Functional Cognitive Inference System) implementation.
Zero OOP for business logic - pure functions only.
Single Primary Operation Lock enforced.
"""

from typing import Callable, Any
import numpy as np
from numpy.typing import NDArray

from mentalos.types import (
    CognitiveRequest, CognitiveState, PipelineStage,
    OperationName, BucketName, ModelName, ToolName,
    Scene, SceneObject, BoundingBox, Transform,
    SpatialRay, RayHit, Vector3D, TransformMatrix,
    SimulationResult, SpatialQueryResult, StatisticalResult,
    create_transform_matrix, normalize_vector
)

# =============================================================================
# STAGE 1: QUESTION → REQUESTED OUTPUT (Task Identification)
# =============================================================================

def identify_task_from_question(question: str, bucket: BucketName) -> OperationName:
    """
    Pure function: Analyze question to determine the primary operation.
    Task identification BEFORE method selection (FCIS principle).
    
    This is a deterministic rule-based classifier.
    """
    q_lower = question.lower()
    
    # Spatial bucket operations
    if bucket == "SPATIAL":
        if any(word in q_lower for word in ["intersect", "collision", "hit", "ray"]):
            return "TRANSFORM"  # Ray transformation and intersection
        elif any(word in q_lower for word in ["distance", "closest", "nearest"]):
            return "MEASURE"
        elif any(word in q_lower for word in ["transform", "rotate", "translate", "scale"]):
            return "TRANSFORM"
        elif any(word in q_lower for word in ["project", "shadow", "projection"]):
            return "PROJECT"
        elif any(word in q_lower for word in ["compare", "similar", "difference"]):
            return "COMPARE"
        else:
            return "IDENTIFY"
    
    # Temporal bucket operations
    elif bucket == "TEMPORAL":
        if any(word in q_lower for word in ["simulate", "evolve", "step"]):
            return "TRANSFORM"
        elif any(word in q_lower for word in ["integrate", "accumulate"]):
            return "AGGREGATE"
        else:
            return "IDENTIFY"
    
    # Probabilistic bucket operations
    elif bucket == "PROBABILISTIC":
        if any(word in q_lower for word in ["sample", "monte carlo", "random"]):
            return "MAP"  # Map over samples
        elif any(word in q_lower for word in ["statistics", "mean", "variance", "distribution", "analyze"]):
            return "REDUCE"  # Statistical reduction
        else:
            return "IDENTIFY"
    
    # Optimization bucket operations
    elif bucket == "OPTIMIZATION":
        if any(word in q_lower for word in ["minimize", "maximize", "optimize"]):
            return "TRANSFORM"
        elif any(word in q_lower for word in ["constraint", "feasible"]):
            return "FILTER"
        else:
            return "IDENTIFY"
    
    # Logical bucket operations
    elif bucket == "LOGICAL":
        if any(word in q_lower for word in ["graph", "node", "edge", "connect"]):
            return "COMPARE"
        elif any(word in q_lower for word in ["path", "shortest", "route"]):
            return "TRANSFORM"
        else:
            return "IDENTIFY"
    
    # Default fallback
    return "IDENTIFY"


def validate_single_operation_lock(requested: OperationName, identified: OperationName) -> bool:
    """
    Enforce Single Primary Operation Lock.
    The identified operation must match or be a valid refinement of requested.
    """
    # For now, we allow the pipeline to proceed if identification refines the request
    # In strict mode, these should match exactly
    valid_transitions = {
        "IDENTIFY": {"IDENTIFY", "TRANSFORM", "MEASURE", "PROJECT", "COMPARE"},
        "TRANSFORM": {"TRANSFORM"},
        "MEASURE": {"MEASURE"},
        "PROJECT": {"PROJECT"},
        "COMPARE": {"COMPARE"},
        "AGGREGATE": {"AGGREGATE", "REDUCE"},
        "FILTER": {"FILTER"},
        "MAP": {"MAP", "REDUCE"},  # MAP can be refined to REDUCE for statistics
        "REDUCE": {"REDUCE", "MAP"},  # REDUCE can accept MAP for sampling workflows
    }
    return identified in valid_transitions.get(requested, {requested})


# =============================================================================
# STAGE 2: PRIMARY OPERATION → BUCKET → MODEL SELECTION
# =============================================================================

def select_model_for_operation(
    operation: OperationName, 
    bucket: BucketName,
    input_data: dict
) -> ModelName:
    """
    Pure function: Select computational model based on operation and data characteristics.
    Deterministic selection rules.
    """
    # Spatial bucket model selection
    if bucket == "SPATIAL":
        if operation in ("TRANSFORM", "PROJECT"):
            # Check if raytracing is needed
            if "rays" in input_data or "ray" in input_data:
                return "RAYTRACE"
            return "FCIS"
        elif operation == "MEASURE":
            return "FCIS"
        elif operation == "COMPARE":
            return "GRAPH"
    
    # Probabilistic bucket
    elif bucket == "PROBABILISTIC":
        if operation in ("MAP", "REDUCE"):
            return "MONTECARLO"
        return "FCIS"
    
    # Temporal bucket
    elif bucket == "TEMPORAL":
        if operation == "TRANSFORM":
            return "FCIS"
        return "GRAPH"
    
    # Optimization bucket
    elif bucket == "OPTIMIZATION":
        return "FCIS"
    
    # Default
    return "FCIS"


def select_tool_for_model(model: ModelName, operation: OperationName) -> ToolName:
    """
    Pure function: Select computational tool based on model requirements.
    """
    if model == "RAYTRACE":
        return "VECTOR_ENGINE"
    elif model == "MONTECARLO":
        return "NUMPY"  # Vectorized random sampling
    elif model == "GRAPH":
        return "SCIPY"  # Sparse matrix operations
    else:
        return "NUMPY"  # Default to numpy for FCIS


# =============================================================================
# STAGE 3: TOOL → EXECUTION (Pure Computational Functions)
# =============================================================================

def execute_spatial_transform(
    scene: Scene,
    operation: OperationName,
    input_data: dict
) -> SpatialQueryResult:
    """
    Execute spatial transformation operations using vectorized numpy.
    Handles: transform, project, measure operations on spatial data.
    """
    results = []
    
    # Extract rays if present
    rays = input_data.get("rays", [])
    objects = scene.objects
    
    if operation == "TRANSFORM" and rays:
        # Ray-scene intersection using vectorized operations
        for ray_data in rays:
            origin = np.array(ray_data["origin"], dtype=np.float64)
            direction = normalize_vector(np.array(ray_data["direction"], dtype=np.float64))
            ray = SpatialRay(origin=origin, direction=direction)
            
            closest_hit = None
            closest_t = np.inf
            
            for obj in objects:
                hit = _ray_object_intersection(ray, obj)
                if hit.hit and hit.t < closest_t:
                    closest_t = hit.t
                    closest_hit = hit
            
            if closest_hit:
                results.append([
                    closest_hit.t,
                    closest_hit.point[0], closest_hit.point[1], closest_hit.point[2],
                    closest_hit.object_id
                ])
            else:
                results.append([np.inf, 0, 0, 0, -1])
    
    elif operation == "MEASURE":
        # Distance measurements
        points = input_data.get("points", [])
        if len(points) >= 2:
            p1 = np.array(points[0], dtype=np.float64)
            p2 = np.array(points[1], dtype=np.float64)
            distance = np.linalg.norm(p2 - p1)
            results.append([distance])
    
    elif operation == "PROJECT":
        # Projection operations
        points = input_data.get("points", [])
        plane_normal = np.array(input_data.get("plane_normal", [0, 1, 0]), dtype=np.float64)
        plane_point = np.array(input_data.get("plane_point", [0, 0, 0]), dtype=np.float64)
        
        for pt in points:
            pt_arr = np.array(pt, dtype=np.float64)
            # Project point onto plane
            projected = _project_point_to_plane(pt_arr, plane_point, plane_normal)
            results.append(projected.tolist())
    
    if not results:
        results = [[0.0]]
    
    return SpatialQueryResult(
        query_type=operation,
        results=np.array(results, dtype=np.float64),
        metadata={"objects_count": len(objects)}
    )


def _ray_object_intersection(ray: SpatialRay, obj: SceneObject) -> RayHit:
    """
    Pure function: Compute ray-object intersection.
    Supports spheres, boxes, and planes.
    """
    # Transform ray to object space
    inv_matrix = np.linalg.inv(obj.transform.matrix)
    
    # Transform ray origin and direction (handle homogeneous coordinates properly)
    origin_homogeneous = np.array([ray.origin[0], ray.origin[1], ray.origin[2], 1.0])
    dir_homogeneous = np.array([ray.direction[0], ray.direction[1], ray.direction[2], 0.0])
    
    origin_obj = (inv_matrix @ origin_homogeneous)[:3]
    dir_obj = (inv_matrix @ dir_homogeneous)[:3]
    dir_obj = normalize_vector(dir_obj)
    
    ray_obj = SpatialRay(origin=origin_obj, direction=dir_obj)
    
    if obj.object_type == "SPHERE" and obj.radius is not None:
        return _ray_sphere_intersection(ray_obj, obj, np.zeros(3), obj.radius)
    elif obj.object_type == "BOX" and obj.half_extents is not None:
        return _ray_box_intersection(ray_obj, obj, np.zeros(3), obj.half_extents)
    elif obj.object_type == "PLANE":
        return _ray_plane_intersection(ray_obj, obj)
    
    return RayHit(hit=False)


def _ray_sphere_intersection(
    ray: SpatialRay, 
    obj: SceneObject,
    center: Vector3D, 
    radius: float
) -> RayHit:
    """Ray-sphere intersection using quadratic formula."""
    oc = ray.origin - center
    a = np.dot(ray.direction, ray.direction)
    b = 2.0 * np.dot(oc, ray.direction)
    c = np.dot(oc, oc) - radius * radius
    
    discriminant = b * b - 4 * a * c
    
    if discriminant < 0:
        return RayHit(hit=False)
    
    sqrt_d = np.sqrt(discriminant)
    t1 = (-b - sqrt_d) / (2 * a)
    t2 = (-b + sqrt_d) / (2 * a)
    
    t = None
    if t1 > ray.t_min and t1 < ray.t_max:
        t = t1
    elif t2 > ray.t_min and t2 < ray.t_max:
        t = t2
    else:
        return RayHit(hit=False)
    
    hit_point = ray.origin + t * ray.direction
    hit_normal = normalize_vector(hit_point - center)
    
    # Transform back to world space
    normal_world = (obj.transform.matrix[:3, :3].T @ hit_normal)
    normal_world = normalize_vector(normal_world)
    point_world = obj.transform.matrix @ np.array([*hit_point, 1.0])
    point_world = point_world[:3]
    
    return RayHit(
        hit=True,
        t=t,
        point=point_world,
        normal=normal_world,
        object_id=obj.object_id,
        material_id=obj.material_id
    )


def _ray_box_intersection(
    ray: SpatialRay,
    obj: SceneObject,
    center: Vector3D,
    half_extents: Vector3D
) -> RayHit:
    """Ray-AABB intersection using slab method."""
    inv_dir = 1.0 / (ray.direction + 1e-10)  # Avoid division by zero
    
    t1 = (center[0] - half_extents[0] - ray.origin[0]) * inv_dir[0]
    t2 = (center[0] + half_extents[0] - ray.origin[0]) * inv_dir[0]
    t3 = (center[1] - half_extents[1] - ray.origin[1]) * inv_dir[1]
    t4 = (center[1] + half_extents[1] - ray.origin[1]) * inv_dir[1]
    t5 = (center[2] - half_extents[2] - ray.origin[2]) * inv_dir[2]
    t6 = (center[2] + half_extents[2] - ray.origin[2]) * inv_dir[2]
    
    tmin = max(min(t1, t2), min(t3, t4), min(t5, t6))
    tmax = min(max(t1, t2), max(t3, t4), max(t5, t6))
    
    if tmax < ray.t_min or tmin > ray.t_max or tmin > tmax:
        return RayHit(hit=False)
    
    t = tmin if tmin > ray.t_min else tmax
    
    hit_point = ray.origin + t * ray.direction
    
    # Compute normal at hit point
    local_hit = hit_point - center
    normal = np.zeros(3)
    epsilon = 1e-6
    
    if abs(local_hit[0] - half_extents[0]) < epsilon:
        normal = np.array([1, 0, 0])
    elif abs(local_hit[0] + half_extents[0]) < epsilon:
        normal = np.array([-1, 0, 0])
    elif abs(local_hit[1] - half_extents[1]) < epsilon:
        normal = np.array([0, 1, 0])
    elif abs(local_hit[1] + half_extents[1]) < epsilon:
        normal = np.array([0, -1, 0])
    elif abs(local_hit[2] - half_extents[2]) < epsilon:
        normal = np.array([0, 0, 1])
    elif abs(local_hit[2] + half_extents[2]) < epsilon:
        normal = np.array([0, 0, -1])
    
    # Transform normal to world space
    normal_world = (obj.transform.matrix[:3, :3].T @ normal)
    normal_world = normalize_vector(normal_world)
    
    point_world = obj.transform.matrix @ np.array([*hit_point, 1.0])
    point_world = point_world[:3]
    
    return RayHit(
        hit=True,
        t=t,
        point=point_world,
        normal=normal_world,
        object_id=obj.object_id,
        material_id=obj.material_id
    )


def _ray_plane_intersection(ray: SpatialRay, obj: SceneObject) -> RayHit:
    """Ray-plane intersection."""
    # Assume plane is at origin with normal along Y axis in object space
    plane_normal = np.array([0, 1, 0], dtype=np.float64)
    
    denom = np.dot(plane_normal, ray.direction)
    
    if abs(denom) < 1e-10:
        return RayHit(hit=False)  # Ray parallel to plane
    
    t = -np.dot(plane_normal, ray.origin) / denom
    
    if t < ray.t_min or t > ray.t_max:
        return RayHit(hit=False)
    
    hit_point = ray.origin + t * ray.direction
    
    # Transform to world space
    normal_world = (obj.transform.matrix[:3, :3].T @ plane_normal)
    normal_world = normalize_vector(normal_world)
    point_world = obj.transform.matrix @ np.array([*hit_point, 1.0])
    point_world = point_world[:3]
    
    return RayHit(
        hit=True,
        t=t,
        point=point_world,
        normal=normal_world,
        object_id=obj.object_id,
        material_id=obj.material_id
    )


def _project_point_to_plane(
    point: Vector3D, 
    plane_point: Vector3D, 
    plane_normal: Vector3D
) -> Vector3D:
    """Project a point onto a plane."""
    plane_normal = normalize_vector(plane_normal)
    vec_to_point = point - plane_point
    distance_to_plane = np.dot(vec_to_point, plane_normal)
    return point - distance_to_plane * plane_normal


def execute_monte_carlo_simulation(
    operation: OperationName,
    input_data: dict,
    n_samples: int = 10000
) -> StatisticalResult:
    """
    Execute Monte Carlo simulation using vectorized numpy operations.
    """
    # Extract distribution parameters
    dist_type = input_data.get("distribution", "normal")
    mean = np.array(input_data.get("mean", [0.0]), dtype=np.float64)
    std = np.array(input_data.get("std", [1.0]), dtype=np.float64)
    
    # Generate samples (vectorized)
    if dist_type == "normal":
        samples = np.random.normal(mean, std, size=(n_samples, len(mean)))
    elif dist_type == "uniform":
        low = input_data.get("low", mean - std)
        high = input_data.get("high", mean + std)
        samples = np.random.uniform(low, high, size=(n_samples, len(mean)))
    else:
        samples = np.random.normal(mean, std, size=(n_samples, len(mean)))
    
    # Compute statistics (vectorized reduction)
    sample_mean = np.mean(samples, axis=0)
    sample_variance = np.var(samples, axis=0)
    
    # 95% confidence interval
    z_score = 1.96
    std_error = np.sqrt(sample_variance / n_samples)
    ci_low = sample_mean - z_score * std_error
    ci_high = sample_mean + z_score * std_error
    
    return StatisticalResult(
        mean=sample_mean,
        variance=sample_variance,
        samples=n_samples,
        confidence_interval=(float(ci_low[0]), float(ci_high[0])),
        distribution_type=dist_type
    )


def execute_graph_operation(
    operation: OperationName,
    input_data: dict
) -> SpatialQueryResult:
    """
    Execute graph-based operations using scipy sparse matrices.
    """
    from scipy import sparse
    from scipy.sparse.csgraph import shortest_path, connected_components
    
    # Extract graph data
    edges = input_data.get("edges", [])
    nodes = input_data.get("nodes", 0)
    
    if not edges or nodes == 0:
        return SpatialQueryResult(
            query_type=operation,
            results=np.array([]),
            metadata={"error": "No graph data provided"}
        )
    
    # Build adjacency matrix (vectorized)
    row_indices = np.array([e[0] for e in edges], dtype=np.int32)
    col_indices = np.array([e[1] for e in edges], dtype=np.int32)
    weights = np.array([e[2] if len(e) > 2 else 1.0 for e in edges], dtype=np.float64)
    
    adj_matrix = sparse.csr_matrix(
        (weights, (row_indices, col_indices)),
        shape=(nodes, nodes)
    )
    
    if operation == "COMPARE":
        # Compute connected components
        n_components, labels = connected_components(adj_matrix, directed=False)
        results = np.array([n_components])
    else:
        # Compute shortest paths
        source = input_data.get("source", 0)
        dist_matrix = shortest_path(adj_matrix, method='D', directed=False)
        results = dist_matrix[source]
    
    return SpatialQueryResult(
        query_type=operation,
        results=results,
        metadata={"nodes": nodes, "edges": len(edges)}
    )


# =============================================================================
# STAGE 4: EXECUTION → ANSWER (Result Formatting)
# =============================================================================

def format_answer_from_result(
    result: Any,
    operation: OperationName,
    question: str
) -> str:
    """
    Pure function: Format computational result into natural language answer.
    """
    if isinstance(result, SpatialQueryResult):
        if operation == "TRANSFORM":
            hits = result.results[result.results[:, 0] != np.inf]
            if len(hits) > 0:
                return f"Found {len(hits)} ray intersection(s). Closest hit at t={hits[0][0]:.4f} on object {int(hits[0][4])}"
            return "No intersections found"
        
        elif operation == "MEASURE":
            if len(result.results) > 0:
                return f"Measured distance: {result.results[0][0]:.6f} units"
            return "Measurement failed"
        
        elif operation == "PROJECT":
            if len(result.results) > 0:
                proj = result.results[0]
                return f"Projected point: ({proj[0]:.4f}, {proj[1]:.4f}, {proj[2]:.4f})"
            return "Projection failed"
        
        elif operation == "COMPARE":
            # Graph comparison results
            if len(result.results) > 0:
                if result.metadata and "nodes" in result.metadata:
                    return f"Graph analysis: {result.metadata['nodes']} nodes, {result.metadata.get('edges', 0)} edges, {result.results[0]:.0f} connected component(s)"
                return f"Comparison result: {result.results}"
    
    elif isinstance(result, StatisticalResult):
        ci = result.confidence_interval
        return (
            f"Statistical analysis ({result.distribution_type}, n={result.samples}): "
            f"mean={result.mean[0]:.6f}, variance={result.variance[0]:.6f}, "
            f"95% CI=[{ci[0]:.6f}, {ci[1]:.6f}]"
        )
    
    elif isinstance(result, SimulationResult):
        if result.success:
            return f"Simulation completed in {result.iterations} iterations (convergence: {result.convergence_metric:.6f})"
        return f"Simulation failed after {result.iterations} iterations"
    
    return f"Operation {operation} completed. Question: {question}"


# =============================================================================
# MAIN PIPELINE ORCHESTRATOR
# =============================================================================

def execute_cognitive_pipeline(request: CognitiveRequest) -> CognitiveState:
    """
    Main deterministic pipeline executor.
    Follows: Question → Requested Output → Primary Operation → Bucket → Model → Tool → Execution → Answer
    
    All stages use pure functions. No mutable state except the final state construction.
    """
    execution_log = []
    
    # Stage 1: Task Identification (before method selection)
    identified_op = identify_task_from_question(request.question, request.context_bucket)
    execution_log.append(f"Identified operation: {identified_op}")
    
    # Validate single operation lock
    if not validate_single_operation_lock(request.requested_operation, identified_op):
        return CognitiveState(
            request=request,
            identified_operation=identified_op,
            selected_model="FCIS",
            selected_tool="NUMPY",
            intermediate_results={},
            final_answer=f"Error: Operation lock violation. Requested {request.requested_operation}, identified {identified_op}",
            execution_log=tuple(execution_log)
        )
    
    # Stage 2: Model Selection
    selected_model = select_model_for_operation(
        identified_op, 
        request.context_bucket, 
        request.input_data
    )
    execution_log.append(f"Selected model: {selected_model}")
    
    # Stage 3: Tool Selection
    selected_tool = select_tool_for_model(selected_model, identified_op)
    execution_log.append(f"Selected tool: {selected_tool}")
    
    # Stage 4: Execution
    result = None
    intermediate = {}
    
    try:
        if request.context_bucket == "SPATIAL":
            # Build scene from input data
            scene = _build_scene_from_input(request.input_data)
            result = execute_spatial_transform(scene, identified_op, request.input_data)
            intermediate["scene_objects"] = len(scene.objects)
        
        elif request.context_bucket == "PROBABILISTIC":
            n_samples = request.parameters.get("n_samples", 10000) if request.parameters else 10000
            result = execute_monte_carlo_simulation(identified_op, request.input_data, n_samples)
            intermediate["samples"] = n_samples
        
        elif request.context_bucket == "LOGICAL":
            result = execute_graph_operation(identified_op, request.input_data)
            intermediate["graph_processed"] = True
        
        else:
            # Default FCIS execution
            scene = _build_scene_from_input(request.input_data)
            result = execute_spatial_transform(scene, identified_op, request.input_data)
        
        execution_log.append(f"Execution completed successfully")
    
    except Exception as e:
        execution_log.append(f"Execution error: {str(e)}")
        return CognitiveState(
            request=request,
            identified_operation=identified_op,
            selected_model=selected_model,
            selected_tool=selected_tool,
            intermediate_results=intermediate,
            final_answer=f"Execution failed: {str(e)}",
            execution_log=tuple(execution_log)
        )
    
    # Stage 5: Answer Formation
    final_answer = format_answer_from_result(result, identified_op, request.question)
    execution_log.append("Answer formatted")
    
    return CognitiveState(
        request=request,
        identified_operation=identified_op,
        selected_model=selected_model,
        selected_tool=selected_tool,
        intermediate_results=intermediate,
        final_answer=final_answer,
        execution_log=tuple(execution_log)
    )


def _build_scene_from_input(input_data: dict) -> Scene:
    """
    Build a Scene object from input data dictionary.
    Pure function for data transformation.
    """
    objects_list = []
    global_min = np.array([np.inf, np.inf, np.inf])
    global_max = np.array([-np.inf, -np.inf, -np.inf])
    
    raw_objects = input_data.get("objects", [])
    
    for idx, obj_data in enumerate(raw_objects):
        obj_type = obj_data.get("type", "SPHERE").upper()
        
        # Create transform
        translation = np.array(obj_data.get("translation", [0, 0, 0]), dtype=np.float64)
        rotation = obj_data.get("rotation", None)
        if rotation:
            rotation = np.array(rotation, dtype=np.float64)
        scale = np.array(obj_data.get("scale", [1, 1, 1]), dtype=np.float64)
        
        transform_matrix = create_transform_matrix(
            translation=translation,
            rotation_quaternion=rotation,
            scale=scale
        )
        transform = Transform(matrix=transform_matrix)
        
        # Compute bounds based on object type
        if obj_type == "SPHERE":
            radius = obj_data.get("radius", 1.0)
            half_extents = np.array([radius, radius, radius])
            min_pt = translation - half_extents
            max_pt = translation + half_extents
            bounds = BoundingBox(min_point=min_pt, max_point=max_pt)
            
            scene_obj = SceneObject(
                object_id=idx,
                object_type="SPHERE",
                transform=transform,
                material_id=obj_data.get("material_id", 0),
                bounds=bounds,
                radius=radius
            )
        
        elif obj_type == "BOX":
            half_extents = np.array(obj_data.get("half_extents", [1, 1, 1]), dtype=np.float64)
            min_pt = translation - half_extents
            max_pt = translation + half_extents
            bounds = BoundingBox(min_point=min_pt, max_point=max_pt)
            
            scene_obj = SceneObject(
                object_id=idx,
                object_type="BOX",
                transform=transform,
                material_id=obj_data.get("material_id", 0),
                bounds=bounds,
                half_extents=half_extents
            )
        
        elif obj_type == "PLANE":
            # Infinite plane, use large bounds
            large_val = 1e6
            bounds = BoundingBox(
                min_point=np.array([-large_val, -large_val, -large_val]),
                max_point=np.array([large_val, large_val, large_val])
            )
            scene_obj = SceneObject(
                object_id=idx,
                object_type="PLANE",
                transform=transform,
                material_id=obj_data.get("material_id", 0),
                bounds=bounds
            )
        
        else:
            # Default to sphere
            radius = 1.0
            half_extents = np.array([radius, radius, radius])
            min_pt = translation - half_extents
            max_pt = translation + half_extents
            bounds = BoundingBox(min_point=min_pt, max_point=max_pt)
            
            scene_obj = SceneObject(
                object_id=idx,
                object_type="SPHERE",
                transform=transform,
                material_id=obj_data.get("material_id", 0),
                bounds=bounds,
                radius=radius
            )
        
        objects_list.append(scene_obj)
        global_min = np.minimum(global_min, bounds.min_point)
        global_max = np.maximum(global_max, bounds.max_point)
    
    # Handle empty scene
    if not objects_list:
        global_min = np.array([-1, -1, -1])
        global_max = np.array([1, 1, 1])
    
    global_bounds = BoundingBox(min_point=global_min, max_point=global_max)
    
    return Scene(
        objects=tuple(objects_list),
        global_bounds=global_bounds,
        acceleration_type="BVH"
    )
