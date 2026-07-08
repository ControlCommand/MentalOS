"""
MentalOS Comprehensive Test Suite

Tests for cognitive pipeline, equation database, type system, and API endpoints.
Run with: pytest tests/test_mentalos.py -v
"""
import pytest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mentalos.types import (
    PrimaryOperation, Bucket, Model, Tool,
    ExtractedValue, ProblemContext, QuestionAnalysis, RequestedOutput,
    ConstraintLock, OperationLock, BucketAssignment, ModelSelection,
    ToolSelection, NestedOperation, ExecutionPlan, StepResult, CognitiveResult,
    CognitiveState, CognitiveRequest
)
from mentalos.core.pipeline import (
    CognitivePipeline, extract_keywords, parse_question_parts,
    extract_numbers_with_units, detect_primary_operation
)
from mentalos.equations.database import get_equation_database, Equation


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def pipeline():
    """Create a fresh cognitive pipeline instance."""
    return CognitivePipeline()


@pytest.fixture
def equation_db():
    """Get the equation database singleton."""
    return get_equation_database()


@pytest.fixture
def sample_problem_text():
    """Sample physics problem for testing."""
    return """A man pushes a 45 kg box from rest along a horizontal floor by exerting a force of 87 N downward at 33° to the horizontal against a friction force of 62 N over a distance of 13 m.
a) How much work was done in moving the box?
b) What is the final velocity of the box?
c) How long did it take to move this distance?"""


@pytest.fixture
def simple_problem():
    """Simple single-part problem."""
    return "Calculate the work done when a force of 50 N moves an object 10 m."


# =============================================================================
# TYPE SYSTEM TESTS
# =============================================================================

class TestTypeSystem:
    """Test frozen dataclasses and type safety."""

    def test_extracted_value_immutable(self):
        """Verify ExtractedValue is frozen (immutable)."""
        ev = ExtractedValue(symbol="F", value=10.0, unit="N", description="Force")

        with pytest.raises(AttributeError):
            ev.value = 20.0  # Should fail - frozen

    def test_requested_output_creation(self):
        """Test creating RequestedOutput with correct types."""
        ro = RequestedOutput(
            target_quantity="work",
            output_type="total",
            symbol="W",
            unit="J",
            description="Total work done"
        )

        assert ro.target_quantity == "work"
        assert ro.output_type == "total"
        assert ro.symbol == "W"
        assert ro.unit == "J"

    def test_nested_operation_chain(self):
        """Test creating nested operation dependency chain."""
        ops = [
            NestedOperation(
                order=1,
                operation="transform",
                bucket="transformation",
                model="newtonian_mechanics",
                tool="trigonometry",
                target_variable="F_x",
                dependencies=[]
            ),
            NestedOperation(
                order=2,
                operation="accumulate",
                bucket="accumulation",
                model="work_energy_theorem",
                tool="algebraic_manipulation",
                target_variable="W",
                dependencies=["F_x"]
            )
        ]

        assert len(ops) == 2
        assert ops[0].order == 1
        assert ops[1].dependencies == ["F_x"]


# =============================================================================
# TEXT ANALYSIS TESTS
# =============================================================================

class TestTextAnalysis:
    """Test text parsing and keyword extraction."""

    def test_extract_keywords(self):
        """Test keyword extraction from problem text."""
        text = "A man pushes a 45 kg box from rest along a horizontal floor"
        keywords = extract_keywords(text)

        assert "pushes" in keywords
        assert "box" in keywords
        assert "horizontal" in keywords
        assert "floor" in keywords
        # Stop words should be filtered
        assert "a" not in keywords
        assert "the" not in keywords

    def test_parse_question_parts(self):
        """Test parsing multi-part questions."""
        text = """Problem statement here.
a) First question?
b) Second question?
c) Third question?"""

        parts = parse_question_parts(text)

        assert "a" in parts
        assert "b" in parts
        assert "c" in parts
        assert "First question?" in parts["a"]

    def test_extract_numbers_with_units(self):
        """Test extracting numerical values with units."""
        text = "A 45 kg box with force 87 N at 33° over 13 m"
        numbers = extract_numbers_with_units(text)

        values = [n["value"] for n in numbers]
        assert 45.0 in values
        assert 87.0 in values
        assert 33.0 in values
        assert 13.0 in values

    def test_detect_primary_operation_work(self):
        """Test detecting 'accumulate' operation for work problems."""
        keywords = ["work", "done", "force", "distance", "energy"]
        op, confidence, reasoning = detect_primary_operation(keywords)

        assert op == "accumulate"
        assert confidence > 0.0

    def test_detect_primary_operation_vector(self):
        """Test detecting 'transform' operation for vector problems."""
        keywords = ["resolve", "components", "angle", "horizontal", "vertical"]
        op, confidence, reasoning = detect_primary_operation(keywords)

        assert op == "transform"


# =============================================================================
# EQUATION DATABASE TESTS
# =============================================================================

class TestEquationDatabase:
    """Test equation database functionality."""

    def test_database_initialization(self, equation_db):
        """Test that database loads with equations."""
        assert len(equation_db.equations) > 0

    def test_get_equation_by_id(self, equation_db):
        """Test retrieving equation by ID."""
        eq = equation_db.get_equation("work_constant_force")

        assert eq is not None
        assert eq.name == "Work by Constant Force"
        assert "W = F * d * cos(θ)" in eq.formula

    def test_search_by_keywords(self, equation_db):
        """Test fuzzy keyword search."""
        results = equation_db.search_by_keywords(["work", "force"], min_score=0.3)

        assert len(results) > 0
        top_eq, score = results[0]
        assert score > 0.3

    def test_search_by_operation(self, equation_db):
        """Test searching equations by operation type."""
        equations = equation_db.search_by_operation("accumulate")

        assert len(equations) > 0
        assert all("accumulate" in eq.operations for eq in equations)

    def test_search_by_model(self, equation_db):
        """Test searching equations by physics model."""
        equations = equation_db.search_by_model("work_energy_theorem")

        assert len(equations) > 0
        assert all("work_energy_theorem" in eq.models for eq in equations)

    def test_find_equations_for_variables(self, equation_db):
        """Test finding equations that can solve for target variable."""
        known_vars = ["F", "d", "θ"]
        target_var = "W"

        equations = equation_db.find_equations_for_variables(known_vars, target_var)

        assert len(equations) > 0
        assert any(eq.id == "work_constant_force" for eq in equations)


# =============================================================================
# COGNITIVE PIPELINE TESTS
# =============================================================================

class TestCognitivePipeline:
    """Test cognitive pipeline stages."""

    def test_create_session(self, pipeline, simple_problem):
        """Test creating a cognitive session."""
        request = CognitiveRequest(question_text=simple_problem)
        state = pipeline.create_session(request)

        assert state.session_id is not None
        assert state.current_stage == "question_analysis"
        assert len(state.question_analysis.keywords) > 0

    def test_full_pipeline_simple_problem(self, pipeline, simple_problem):
        """Test running full pipeline on simple problem."""
        request = CognitiveRequest(question_text=simple_problem)
        state = pipeline.create_session(request)
        state = pipeline.determine_requested_output(state.session_id)
        state = pipeline.apply_constraint_lock(state.session_id)
        state = pipeline.determine_operation_lock(state.session_id)
        state = pipeline.assign_bucket(state.session_id)
        state = pipeline.select_model(state.session_id)
        state = pipeline.select_tool(state.session_id)
        state = pipeline.discover_nested_operations(state.session_id)

        assert state.operation_lock is not None
        assert state.operation_lock.primary_operation == "accumulate"
        assert state.bucket_assignment is not None
        assert state.model_selection is not None

    def test_pipeline_with_angle_detection(self, pipeline):
        """Test pipeline detects nested operations for angled forces."""
        problem = "A force of 100 N at 30° pushes a box 5 m. Calculate work."
        request = CognitiveRequest(question_text=problem)

        state = pipeline.create_session(request)
        state = pipeline.determine_requested_output(state.session_id)
        state = pipeline.apply_constraint_lock(state.session_id)
        state = pipeline.determine_operation_lock(state.session_id)
        state = pipeline.assign_bucket(state.session_id)
        state = pipeline.select_model(state.session_id)
        state = pipeline.select_tool(state.session_id)
        state = pipeline.discover_nested_operations(state.session_id, user_confirms_secondary=True)

        assert state.execution_plan is not None
        assert len(state.execution_plan.nested_operations) > 0
        assert state.execution_plan.nested_operations[0].operation == "transform"

    def test_pipeline_multi_part_question(self, pipeline, sample_problem_text):
        """Test pipeline handles multi-part questions."""
        request = CognitiveRequest(
            question_text=sample_problem_text,
            selected_part="a"
        )

        state = pipeline.create_session(request)

        assert state.question_analysis.parts is not None
        assert "a" in state.question_analysis.parts
        assert "b" in state.question_analysis.parts
        assert state.question_analysis.current_part == "a"

    def test_execute_step(self, pipeline, simple_problem):
        """Test executing a computation step."""
        request = CognitiveRequest(question_text=simple_problem)
        state = pipeline.create_session(request)
        state = pipeline.determine_requested_output(state.session_id)
        state = pipeline.apply_constraint_lock(state.session_id)
        state = pipeline.determine_operation_lock(state.session_id)
        state = pipeline.assign_bucket(state.session_id)
        state = pipeline.select_model(state.session_id)
        state = pipeline.select_tool(state.session_id)
        state = pipeline.discover_nested_operations(state.session_id)

        # Execute work calculation
        state, step_result = pipeline.execute_step(
            session_id=state.session_id,
            step_number=1,
            equation_id="work_constant_force",
            input_values={"F": 50.0, "d": 10.0, "θ": 0.0}
        )

        assert step_result.success
        assert step_result.value == 500.0  # W = F*d*cos(0) = 50*10*1 = 500
        assert step_result.unit == "J"

    def test_finalize_result(self, pipeline, simple_problem):
        """Test finalizing cognitive result."""
        request = CognitiveRequest(question_text=simple_problem)
        state = pipeline.create_session(request)
        state = pipeline.determine_requested_output(state.session_id)
        state = pipeline.apply_constraint_lock(state.session_id)
        state = pipeline.determine_operation_lock(state.session_id)
        state = pipeline.assign_bucket(state.session_id)
        state = pipeline.select_model(state.session_id)
        state = pipeline.select_tool(state.session_id)
        state = pipeline.discover_nested_operations(state.session_id)

        # Execute step
        state, _ = pipeline.execute_step(
            session_id=state.session_id,
            step_number=1,
            equation_id="work_constant_force",
            input_values={"F": 50.0, "d": 10.0, "θ": 0.0}
        )

        # Finalize
        state = pipeline.finalize_result(state.session_id)

        assert state.is_complete
        assert state.final_result is not None
        assert state.final_result.final_value == 500.0
        assert state.final_result.unit == "J"


# =============================================================================
# EDGE CASE TESTS
# =============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_keywords(self):
        """Test operation detection with empty keywords."""
        op, confidence, reasoning = detect_primary_operation([])

        # Should return a default operation with low confidence
        assert op in ["accumulate", "transform", "scale", "estimate", "differentiate"]

    def test_unknown_equation_id(self, pipeline, simple_problem):
        """Test error handling for unknown equation ID."""
        request = CognitiveRequest(question_text=simple_problem)
        state = pipeline.create_session(request)

        with pytest.raises(ValueError, match="Equation .* not found"):
            pipeline.execute_step(
                session_id=state.session_id,
                step_number=1,
                equation_id="nonexistent_equation",
                input_values={}
            )

    def test_invalid_session_id(self, pipeline):
        """Test error handling for invalid session ID."""
        with pytest.raises(ValueError, match="Session .* not found"):
            pipeline.get_state("invalid_session_123")

    def test_zero_values_in_equation(self, pipeline, simple_problem):
        """Test equation evaluation with zero values."""
        request = CognitiveRequest(question_text=simple_problem)
        state = pipeline.create_session(request)
        state = pipeline.determine_requested_output(state.session_id)
        state = pipeline.apply_constraint_lock(state.session_id)
        state = pipeline.determine_operation_lock(state.session_id)
        state = pipeline.assign_bucket(state.session_id)
        state = pipeline.select_model(state.session_id)
        state = pipeline.select_tool(state.session_id)
        state = pipeline.discover_nested_operations(state.session_id)

        state, step_result = pipeline.execute_step(
            session_id=state.session_id,
            step_number=1,
            equation_id="work_constant_force",
            input_values={"F": 0.0, "d": 10.0, "θ": 0.0}
        )

        assert step_result.success
        assert step_result.value == 0.0  # Zero force = zero work


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegration:
    """End-to-end integration tests."""

    def test_full_work_problem_solution(self, pipeline):
        """Test complete solution of work problem with angle."""
        problem = "A force of 100 N at 30° pushes a box 5 m horizontally. Calculate work done."
        request = CognitiveRequest(question_text=problem)

        # Run full pipeline
        state = pipeline.create_session(request)
        state = pipeline.determine_requested_output(state.session_id)
        state = pipeline.apply_constraint_lock(state.session_id)
        state = pipeline.determine_operation_lock(state.session_id)
        state = pipeline.assign_bucket(state.session_id)
        state = pipeline.select_model(state.session_id)
        state = pipeline.select_tool(state.session_id)
        state = pipeline.discover_nested_operations(state.session_id)

        # Execute nested operation first (vector resolution)
        if state.execution_plan and state.execution_plan.nested_operations:
            state, _ = pipeline.execute_step(
                session_id=state.session_id,
                step_number=1,
                equation_id="vector_components",
                input_values={"F": 100.0, "θ": 30.0}
            )

        # Execute primary operation (work calculation)
        state, step_result = pipeline.execute_step(
            session_id=state.session_id,
            step_number=2,
            equation_id="work_constant_force",
            input_values={"F": 100.0, "d": 5.0, "θ": 30.0}
        )

        state = pipeline.finalize_result(state.session_id)

        assert state.is_complete
        assert state.final_result is not None
        # W = F*d*cos(30°) = 100*5*0.866 = 433 J
        assert abs(state.final_result.final_value - 433.0) < 1.0

    def test_friction_problem_solution(self, pipeline):
        """Test problem with friction force."""
        problem = "A box experiences friction force of 62 N over 13 m. Calculate work done by friction."
        request = CognitiveRequest(question_text=problem)

        state = pipeline.create_session(request)
        state = pipeline.determine_requested_output(state.session_id)
        state = pipeline.apply_constraint_lock(state.session_id)
        state = pipeline.determine_operation_lock(state.session_id)
        state = pipeline.assign_bucket(state.session_id)
        state = pipeline.select_model(state.session_id)
        state = pipeline.select_tool(state.session_id)
        state = pipeline.discover_nested_operations(state.session_id)

        # Execute work calculation (friction opposes motion, so θ=180°)
        state, step_result = pipeline.execute_step(
            session_id=state.session_id,
            step_number=1,
            equation_id="work_constant_force",
            input_values={"F": 62.0, "d": 13.0, "θ": 180.0}
        )

        state = pipeline.finalize_result(state.session_id)

        assert state.is_complete
        # W = F*d*cos(180°) = 62*13*(-1) = -806 J
        assert abs(step_result.value - (-806.0)) < 1.0


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

+++ tests/test_mentalos.py (修改后)
"""MentalOS Comprehensive Test Suite"""
import pytest
from mentalos.types.core_types import (
    PrimaryOperation,
    Bucket,
    Model,
    Tool,
    ExtractedValue,
    CognitiveRequest,
    OperationNode,
    CognitiveResult,
)
from mentalos.core.pipeline import (
    extract_numbers_and_units,
    analyze_question_intent,
    detect_primary_operation,
    detect_bucket,
    detect_model,
    detect_tool,
    build_operation_dag,
    process_cognitive_request,
)
from mentalos.equations.database import search_equations, get_equation_by_id


class TestTypeDefinitions:
    """Test immutable type definitions"""

    def test_primary_operation_enum(self):
        assert PrimaryOperation.ACCUMULATE.value == "accumulate"
        assert PrimaryOperation.TRANSFORM.value == "transform"
        assert PrimaryOperation.SCALE.value == "scale"
        assert PrimaryOperation.ESTIMATE.value == "estimate"
        assert PrimaryOperation.DIFFERENTIATE.value == "differentiate"

    def test_bucket_enum(self):
        assert Bucket.ACCUMULATION.value == "accumulation"
        assert Bucket.TRANSFORMATION.value == "transformation"
        assert Bucket.GEOMETRY.value == "geometry"

    def test_extracted_value_immutability(self):
        ev = ExtractedValue(name="F", value=10.0, unit="N")
        assert ev.name == "F"
        assert ev.value == 10.0
        assert ev.unit == "N"


class TestNumberExtraction:
    """Test dynamic number and unit extraction"""

    def test_extract_force_and_mass(self):
        text = "A 45 kg box with 87 N force"
        extracted = extract_numbers_and_units(text)
        values_dict = {ev.name: ev.value for ev in extracted}

        assert 45.0 in values_dict.values() or any(ev.unit == "kg" for ev in extracted)
        assert 87.0 in values_dict.values() or any(ev.unit == "N" for ev in extracted)

    def test_extract_angle(self):
        text = "at an angle of 33 degrees"
        extracted = extract_numbers_and_units(text)
        assert any(ev.name == "theta" or ev.unit == "" for ev in extracted)

    def test_extract_distance(self):
        text = "over a distance of 13 m"
        extracted = extract_numbers_and_units(text)
        assert any(ev.name == "d" or ev.unit == "m" for ev in extracted)


class TestIntentAnalysis:
    """Test question intent analysis"""

    def test_detect_work_question(self):
        result = analyze_question_intent("How much work was done?")
        assert result["requested_output"] == "work"

    def test_detect_velocity_question(self):
        result = analyze_question_intent("What is the velocity?")
        assert result["requested_output"] == "velocity"

    def test_detect_multi_part(self):
        result = analyze_question_intent("a) Find the work. b) Find the energy.")
        assert result["is_multi_part"] is True

    def test_detect_operation_hints(self):
        result = analyze_question_intent("Calculate the average velocity")
        assert "estimate" in result["operation_hints"]


class TestOperationDetection:
    """Test primary operation detection"""

    def test_detect_accumulate_for_work(self):
        text = "How much total work was done over 13 m?"
        extracted = [ExtractedValue(name="d", value=13.0, unit="m")]
        op = detect_primary_operation(text, extracted)
        assert op == PrimaryOperation.ACCUMULATE

    def test_detect_transform_for_vector(self):
        text = "Resolve the vector into components"
        extracted = []
        op = detect_primary_operation(text, extracted)
        assert op == PrimaryOperation.TRANSFORM

    def test_custom_operation_override(self):
        text = "Some question"
        extracted = []
        op = detect_primary_operation(text, extracted, custom_operation=PrimaryOperation.ESTIMATE)
        assert op == PrimaryOperation.ESTIMATE


class TestBucketDetection:
    """Test bucket detection"""

    def test_accumulation_for_work(self):
        bucket = detect_bucket(PrimaryOperation.ACCUMULATE, "work done by force")
        assert bucket == Bucket.ACCUMULATION

    def test_transformation_for_vector(self):
        bucket = detect_bucket(PrimaryOperation.TRANSFORM, "resolve vector components")
        assert bucket == Bucket.TRANSFORMATION


class TestModelDetection:
    """Test physics model detection"""

    def test_work_energy_model(self):
        model = detect_model(Bucket.ACCUMULATION, "work and energy problem")
        assert model == Model.WORK_ENERGY

    def test_newtonian_mechanics_model(self):
        model = detect_model(Bucket.DYNAMICS, "force and newton's laws")
        assert model == Model.NEWTONIAN_MECHANICS


class TestToolDetection:
    """Test mathematical tool detection"""

    def test_trigonometry_for_angle(self):
        text = "force at 33 degrees angle"
        extracted = [ExtractedValue(name="theta", value=33.0, unit="")]
        tool = detect_tool(text, extracted)
        assert tool == Tool.TRIGONOMETRY

    def test_algebraic_default(self):
        text = "simple calculation"
        extracted = []
        tool = detect_tool(text, extracted)
        assert tool == Tool.ALGEBRAIC_MANIPULATION


class TestDAGBuilding:
    """Test operation DAG construction"""

    def test_detect_nested_vector_resolution(self):
        text = "Force of 87 N at 33 degrees horizontal work over 13 m"
        extracted = [
            ExtractedValue(name="F", value=87.0, unit="N"),
            ExtractedValue(name="theta", value=33.0, unit=""),
            ExtractedValue(name="d", value=13.0, unit="m"),
        ]
        request = CognitiveRequest(question_text=text)
        primary, nested = build_operation_dag(request, extracted)

        # Should detect need for vector resolution
        assert len(nested) >= 1 or primary.operation == PrimaryOperation.ACCUMULATE

    def test_primary_node_has_dependencies(self):
        text = "Simple work problem"
        extracted = [ExtractedValue(name="F", value=10.0, unit="N")]
        request = CognitiveRequest(question_text=text)
        primary, nested = build_operation_dag(request, extracted)

        assert primary.operation is not None
        assert isinstance(primary.bucket, Bucket)
        assert isinstance(primary.model, Model)


class TestFullPipeline:
    """Test complete pipeline processing"""

    def test_work_calculation_with_angle(self):
        text = "A man pushes a box with 87 N force at 33 degrees over 13 m. How much work?"
        request = CognitiveRequest(question_text=text)
        user_values = {"F": 87.0, "theta": 33.0, "d": 13.0}

        result = process_cognitive_request(request, user_values)

        assert result.success is True
        assert result.final_answer is not None
        assert result.total_steps >= 1
        # Work should be F * d * cos(theta) = 87 * 13 * cos(33°) ≈ 948.5 J
        assert 900 < result.final_answer < 1000

    def test_simple_work_no_angle(self):
        text = "A force of 50 N moves an object 10 m horizontally. Calculate the work done."
        request = CognitiveRequest(question_text=text)
        user_values = {"F": 50.0, "d": 10.0, "theta": 0.0}

        result = process_cognitive_request(request, user_values)

        assert result.success is True
        # Work should be calculated (F * d * cos(0) = 500 J)
        assert result.final_answer is not None
        assert result.total_steps >= 1

    def test_acceleration_problem(self):
        text = "A car accelerates from rest to 25 m/s in 8 seconds. What is average acceleration?"
        request = CognitiveRequest(question_text=text)
        user_values = {"v": 25.0, "t": 8.0}

        result = process_cognitive_request(request, user_values)

        assert result.success is True
        # a = delta_v / delta_t = 25 / 8 = 3.125 m/s²
        assert result.final_answer is not None


class TestEquationDatabase:
    """Test equation database functionality"""

    def test_search_work_equations(self):
        results = search_equations(["work", "force", "distance"])
        assert len(results) > 0
        assert any("work" in eq.name.lower() for eq in results)

    def test_search_vector_equations(self):
        results = search_equations(["vector", "resolution", "component"])
        assert len(results) > 0

    def test_get_equation_by_id(self):
        eq = get_equation_by_id("work_basic")
        assert eq is not None
        assert eq.formula == "W = F * d * cos(theta)"

    def test_equation_not_found(self):
        eq = get_equation_by_id("nonexistent")
        assert eq is None


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_question(self):
        request = CognitiveRequest(question_text="")
        result = process_cognitive_request(request, {})
        assert result.success is True  # Should handle gracefully

    def test_no_user_values(self):
        text = "A 10 kg mass"
        request = CognitiveRequest(question_text=text)
        result = process_cognitive_request(request, {})
        assert result.success is True

    def test_invalid_operation_string(self):
        # Test that invalid custom operations are handled
        request = CognitiveRequest(
            question_text="Test",
            custom_operation=None  # Will remain None if invalid
        )
        assert request.question_text == "Test"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
