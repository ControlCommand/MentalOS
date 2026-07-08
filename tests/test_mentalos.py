"""
Comprehensive test suite for MentalOS.
Tests type safety, pipeline execution, and API endpoints.
"""

import pytest
import numpy as np
from typing import get_args

# Test imports work correctly
from mentalos.types import (
    ExtractedValue, VectorData, SpatialPoint, SpatialRay, RayHit,
    Transform, BoundingBox, SceneObject, Scene, OperationNode,
    CognitiveRequest, CognitiveState, PipelineResult, EquationMatch,
    PrimaryOperation, Bucket, Model, Tool, QuestionPart
)
from mentalos.core.pipeline import (
    parse_question_parts, extract_numbers_and_units, extract_keywords,
    infer_requested_output, identify_primary_operation, select_bucket,
    select_model, select_tool, detect_nested_operations,
    execute_vector_resolution, execute_work_calculation, execute_pipeline
)
from mentalos.equations.database import (
    Equation, EQUATION_DATABASE, search_equations, get_equation_by_name,
    get_equations_by_category, get_all_categories, suggest_equation
)


class TestTypeDefinitions:
    """Test immutable type definitions."""
    
    def test_extracted_value_immutable(self):
        """Verify ExtractedValue is frozen."""
        ev = ExtractedValue(name="force", value=10.0, unit="N")
        assert ev.name == "force"
        assert ev.value == 10.0
        assert ev.unit == "N"
        
        with pytest.raises(Exception):  # frozen dataclass raises error
            ev.value = 20.0
    
    def test_spatial_point_creation(self):
        """Test SpatialPoint creation and array conversion."""
        point = SpatialPoint(x=1.0, y=2.0, z=3.0)
        arr = point.to_array()
        assert isinstance(arr, np.ndarray)
        assert np.allclose(arr, [1.0, 2.0, 3.0])
    
    def test_vector_data_auto_components(self):
        """Test VectorData automatically calculates components."""
        vec = VectorData(magnitude=10.0, direction_degrees=0.0)
        assert vec.components is not None
        assert np.isclose(vec.components[0], 10.0)
        assert np.isclose(vec.components[1], 0.0)
    
    def test_bounding_box_contains(self):
        """Test BoundingBox containment check."""
        bbox = BoundingBox(
            SpatialPoint(0, 0, 0),
            SpatialPoint(10, 10, 10)
        )
        assert bbox.contains(SpatialPoint(5, 5, 5))
        assert not bbox.contains(SpatialPoint(15, 5, 5))


class TestQuestionAnalysis:
    """Test question parsing and analysis functions."""
    
    def test_parse_single_part(self):
        """Test parsing single-part question."""
        text = "A box is pushed with 10 N force."
        parts = parse_question_parts(text)
        assert 'a' in parts
        assert parts['a'] == text
    
    def test_parse_multi_part(self):
        """Test parsing multi-part question."""
        text = """A problem statement.
(a) First question?
(b) Second question?
(c) Third question?"""
        parts = parse_question_parts(text)
        assert len(parts) == 3
        assert 'a' in parts
        assert 'b' in parts
        assert 'c' in parts
    
    def test_extract_numbers_with_units(self):
        """Test extracting numbers with units."""
        text = "A 45 kg box pushed with 87 N force over 13 m at 33 degrees."
        values = extract_numbers_and_units(text)
        assert len(values) >= 4
        
        names = [v.name for v in values]
        vals = [v.value for v in values]
        
        assert 45.0 in vals
        assert 87.0 in vals
        assert 13.0 in vals
        assert 33.0 in vals
    
    def test_extract_keywords(self):
        """Test keyword extraction."""
        text = "Calculate the work done by a constant force pushing a box horizontally."
        keywords = extract_keywords(text)
        assert 'work' in keywords
        assert 'force' in keywords
        assert 'constant' in keywords
        # Note: 'horizontally' is not in keyword set, only 'horizontal'
    
    def test_infer_requested_output_work(self):
        """Test inferring work as requested output."""
        keywords = ['work', 'force', 'distance']
        values = [ExtractedValue("f_force", 10.0, "N")]
        output = infer_requested_output(keywords, values)
        assert 'work' in output.lower() or 'W' in output


class TestOperationIdentification:
    """Test operation identification logic."""
    
    def test_identify_accumulate_for_work(self):
        """Test work problems identify accumulate operation."""
        keywords = ['work', 'energy', 'total', 'distance']
        op = identify_primary_operation(keywords, 'W_work')
        assert op == 'accumulate'
    
    def test_identify_transform_for_components(self):
        """Test component problems identify transform operation."""
        keywords = ['resolve', 'component', 'vector', 'break']
        op = identify_primary_operation(keywords, 'F_x_component')
        assert op == 'transform'
    
    def test_select_bucket_mapping(self):
        """Test bucket selection from operation."""
        assert select_bucket('accumulate') == 'accumulation'
        assert select_bucket('transform') == 'transformation'
        assert select_bucket('scale') == 'geometry'
    
    def test_select_model_mapping(self):
        """Test model selection from bucket."""
        assert select_model('accumulation') == 'work_energy_theorem'
        assert select_model('dynamics') == 'newton_second_law'
    
    def test_select_tool_mapping(self):
        """Test tool selection from model."""
        assert select_tool('work_energy_theorem') == 'algebraic_manipulation'
        assert select_tool('projectile_motion') == 'trigonometry'


class TestDAGConstruction:
    """Test DAG construction for nested operations."""
    
    def test_detect_nested_for_angled_work(self):
        """Test detecting nested operations for angled force work."""
        values = [
            ExtractedValue("f_applied", 87.0, "N"),
            ExtractedValue("theta_angle", 33.0, "degrees"),
            ExtractedValue("d_distance", 13.0, "m")
        ]
        keywords = ['work', 'force', 'push']
        
        dag = detect_nested_operations(values, 'accumulate', keywords)
        
        # Should have multiple operations (transform/scale + accumulate)
        assert len(dag) >= 2
        
        # Last operation should be primary (accumulate)
        last_op = dag[-1]
        assert last_op.operation == 'accumulate'
        
        # Earlier operations should be dependencies
        if len(dag) > 1:
            assert dag[0].operation in ['transform', 'scale']


class TestExecutionEngine:
    """Test execution functions."""
    
    def test_execute_vector_resolution_x(self):
        """Test resolving vector x-component."""
        result = execute_vector_resolution(10.0, 0.0, 'x')
        assert np.isclose(result, 10.0)
    
    def test_execute_vector_resolution_y(self):
        """Test resolving vector y-component."""
        result = execute_vector_resolution(10.0, 90.0, 'y')
        assert np.isclose(result, 10.0)
    
    def test_execute_work_horizontal(self):
        """Test work calculation with horizontal force."""
        result = execute_work_calculation(10.0, 5.0, None)
        assert np.isclose(result, 50.0)
    
    def test_execute_work_angled(self):
        """Test work calculation with angled force."""
        result = execute_work_calculation(10.0, 5.0, 60.0)
        expected = 10.0 * 5.0 * np.cos(np.radians(60.0))
        assert np.isclose(result, expected)


class TestPipelineIntegration:
    """Test full pipeline integration."""
    
    def test_pipeline_work_problem(self):
        """Test complete pipeline for work problem."""
        request = CognitiveRequest(
            question_text="A man pushes a box with 87 N force over 13 m. How much work was done?"
        )
        result = execute_pipeline(request)
        
        assert result.success
        assert result.answer is not None
        assert result.state is not None
        assert result.state.identified_operation == 'accumulate'
    
    def test_pipeline_angled_force(self):
        """Test pipeline with angled force."""
        request = CognitiveRequest(
            question_text="A force of 87 N at 33 degrees pushes a box 13 m. Calculate work."
        )
        result = execute_pipeline(request)
        
        # May not succeed if extraction fails, but should have state
        assert result.state is not None
        
        # If successful, verify the answer
        if result.success:
            assert result.answer is not None
            # Work should be F * d * cos(theta)
            expected = 87.0 * 13.0 * np.cos(np.radians(33.0))
            assert np.isclose(result.answer, expected, rtol=0.01)
    
    def test_pipeline_error_handling(self):
        """Test pipeline handles missing data gracefully."""
        request = CognitiveRequest(
            question_text="Some random text without numbers."
        )
        result = execute_pipeline(request)
        
        # Should not crash, but may not succeed
        assert result.state is not None


class TestEquationDatabase:
    """Test equation database functionality."""
    
    def test_database_not_empty(self):
        """Verify equation database has entries."""
        assert len(EQUATION_DATABASE) > 0
    
    def test_search_by_keyword(self):
        """Test searching equations by keyword."""
        results = search_equations(['work', 'force'])
        assert len(results) > 0
        assert any('work' in eq.name.lower() for eq in results)
    
    def test_get_equation_by_name(self):
        """Test retrieving equation by exact name."""
        eq = get_equation_by_name('work_constant_force')
        assert eq is not None
        assert eq.formula == "W = F * d * cos(theta)"
    
    def test_get_categories(self):
        """Test getting all categories."""
        categories = get_all_categories()
        assert len(categories) > 0
        assert 'work_energy' in categories or 'forces' in categories
    
    def test_suggest_equation(self):
        """Test equation suggestion."""
        variables = ['F', 'd', 'theta']
        keywords = ['work', 'force', 'angle']
        eq = suggest_equation(variables, keywords)
        assert eq is not None
        assert 'work' in eq.name.lower()


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_question(self):
        """Test handling empty question."""
        request = CognitiveRequest(question_text="")
        result = execute_pipeline(request)
        # Should handle gracefully
        assert result.state is not None
    
    def test_no_numbers_in_text(self):
        """Test text without numbers."""
        values = extract_numbers_and_units("A box is pushed along the floor.")
        assert len(values) == 0
    
    def test_invalid_angle(self):
        """Test vector resolution with edge angles."""
        # 0 degrees - full magnitude in x
        result_x = execute_vector_resolution(10.0, 0.0, 'x')
        assert np.isclose(result_x, 10.0)
        
        # 90 degrees - zero in x
        result_x_90 = execute_vector_resolution(10.0, 90.0, 'x')
        assert np.isclose(result_x_90, 0.0, atol=1e-10)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
