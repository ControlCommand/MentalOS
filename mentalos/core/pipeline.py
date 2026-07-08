"""
MentalOS Cognitive Pipeline Engine
Deterministic FCIS architecture with DAG-based operation chaining.
No OOP for business logic - pure functions only.
"""

from __future__ import annotations
import re
import math
from typing import List, Dict, Tuple, Optional, Any
import numpy as np

from mentalos.types import (
    PrimaryOperation, Bucket, Model, Tool, QuestionPart,
    ExtractedValue, OperationNode, CognitiveRequest, CognitiveState,
    PipelineResult
)
from mentalos.equations.database import (
    search_equations, get_equation_by_name, suggest_equation, Equation
)


# ============================================================================
# STAGE 1: QUESTION ANALYSIS
# ============================================================================

def parse_question_parts(question_text: str) -> Dict[QuestionPart, str]:
    """
    Parse multi-part questions (a), (b), (c), etc.
    Returns dict mapping part labels to their text.
    """
    parts: Dict[QuestionPart, str] = {}
    
    # Pattern to match (a), (b), etc.
    pattern = r'\(([a-h])\)\s*([^(\n]+)'
    matches = re.findall(pattern, question_text, re.IGNORECASE)
    
    if matches:
        for part_label, content in matches:
            if part_label.lower() in 'abcdefgh':
                parts[part_label.lower()] = content.strip()
    
    # If no parts found, treat entire text as part 'a'
    if not parts:
        parts['a'] = question_text.strip()
    
    return parts


def extract_numbers_and_units(text: str) -> List[ExtractedValue]:
    """
    Extract numerical values with units from text.
    Uses regex patterns for common physics quantities.
    """
    extracted: List[ExtractedValue] = []
    
    # Pattern: number followed by optional unit
    # Matches: "45 kg", "87 N", "33°", "62 N", "13 m"
    patterns = [
        (r'(\d+(?:\.\d+)?)\s*(kg|g|N|m|cm|mm|km|s|min|hr|h|J|W|Pa|Hz|V|A|Ω|C|F|T|H|eV|cal|BTU)\b', 'standard'),
        (r'(\d+(?:\.\d+)?)\s*degrees?\b', 'angle'),
        (r'(\d+(?:\.\d+)?)\s*°', 'angle'),
        (r'(\d+(?:\.\d+)?)\s*radians?\b', 'angle'),
        (r'(\d+(?:\.\d+)?)\s*m/s\b', 'velocity'),
        (r'(\d+(?:\.\d+)?)\s*m/s²', 'acceleration'),
    ]
    
    for pattern, ptype in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            value_str = match.group(1)
            unit = match.group(2) if match.lastindex >= 2 else ptype
            try:
                value = float(value_str)
                name = _infer_variable_name(ptype, unit, text)
                extracted.append(ExtractedValue(
                    name=name,
                    value=value,
                    unit=unit,
                    confidence=0.9
                ))
            except ValueError:
                continue
    
    return extracted


def _infer_variable_name(pattern_type: str, unit: str, context: str) -> str:
    """Infer variable name from context and unit."""
    context_lower = context.lower()
    
    # Force-related
    if unit == 'N':
        if 'friction' in context_lower:
            return 'f_friction'
        elif 'push' in context_lower or 'exert' in context_lower:
            return 'f_applied'
        elif 'weight' in context_lower:
            return 'f_weight'
        else:
            return 'f_force'
    
    # Mass
    if unit == 'kg' or unit == 'g':
        return 'm_mass'
    
    # Distance
    if unit in ['m', 'cm', 'mm', 'km']:
        if 'distance' in context_lower or 'displacement' in context_lower:
            return 'd_distance'
        elif 'height' in context_lower:
            return 'h_height'
        else:
            return 'd_distance'
    
    # Angle
    if pattern_type == 'angle':
        return 'theta_angle'
    
    # Velocity
    if unit == 'm/s':
        return 'v_velocity'
    
    # Acceleration
    if unit == 'm/s²':
        return 'a_acceleration'
    
    # Work/Energy
    if unit == 'J':
        return 'w_work'
    
    # Power
    if unit == 'W':
        return 'p_power'
    
    # Time
    if unit in ['s', 'min', 'hr', 'h']:
        return 't_time'
    
    return 'unknown'


def extract_keywords(text: str) -> List[str]:
    """Extract meaningful keywords from problem statement."""
    # Common physics keywords
    physics_keywords = {
        'work', 'energy', 'force', 'mass', 'acceleration', 'velocity',
        'speed', 'distance', 'displacement', 'time', 'power', 'momentum',
        'friction', 'gravity', 'weight', 'normal', 'tension', 'spring',
        'kinetic', 'potential', 'elastic', 'thermal', 'heat', 'temperature',
        'pressure', 'volume', 'density', 'frequency', 'wavelength',
        'electric', 'magnetic', 'field', 'charge', 'current', 'voltage',
        'resistance', 'capacitance', 'inductance', 'flux',
        'push', 'pull', 'lift', 'drop', 'throw', 'slide', 'roll',
        'horizontal', 'vertical', 'inclined', 'angled', 'parallel',
        'rest', 'constant', 'uniform', 'instantaneous', 'average',
        'initial', 'final', 'maximum', 'minimum', 'equilibrium',
        'clockwise', 'counterclockwise', 'rotation', 'revolution',
        'component', 'resolve', 'vector', 'scalar', 'magnitude', 'direction'
    }
    
    words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
    return [w for w in words if w in physics_keywords]


def infer_requested_output(keywords: List[str], extracted_values: List[ExtractedValue]) -> str:
    """
    Infer what the question is asking for based on keywords and context.
    Returns the expected output variable name.
    """
    keyword_set = set(keywords)
    
    # Direct question word patterns
    if 'work' in keyword_set:
        return 'W_work'
    elif any(w in keyword_set for w in ['velocity', 'speed']):
        if 'average' in keyword_set:
            return 'v_avg_velocity'
        elif 'initial' in keyword_set:
            return 'v_initial_velocity'
        elif 'final' in keyword_set:
            return 'v_final_velocity'
        else:
            return 'v_velocity'
    elif 'acceleration' in keyword_set:
        return 'a_acceleration'
    elif 'force' in keyword_set:
        return 'f_force'
    elif 'power' in keyword_set:
        return 'p_power'
    elif 'energy' in keyword_set:
        if 'kinetic' in keyword_set:
            return 'KE_kinetic_energy'
        elif 'potential' in keyword_set:
            return 'PE_potential_energy'
        else:
            return 'E_energy'
    elif 'momentum' in keyword_set:
        return 'p_momentum'
    elif 'time' in keyword_set:
        return 't_time'
    elif 'distance' in keyword_set or 'displacement' in keyword_set:
        return 'd_distance'
    elif 'height' in keyword_set:
        return 'h_height'
    elif 'angle' in keyword_set or 'direction' in keyword_set:
        return 'theta_angle'
    elif 'mass' in keyword_set:
        return 'm_mass'
    else:
        return 'unknown'


# ============================================================================
# STAGE 2: OPERATION IDENTIFICATION (Winner-Takes-All)
# ============================================================================

OPERATION_KEYWORDS: Dict[PrimaryOperation, List[str]] = {
    'accumulate': ['total', 'sum', 'work', 'energy', 'distance', 'displacement', 
                   'accumulated', 'combined', 'overall', 'net'],
    'transform': ['convert', 'change', 'resolve', 'decompose', 'rotate', 
                  'translate', 'transform', 'component', 'break'],
    'scale': ['ratio', 'proportion', 'scale', 'factor', 'multiply', 'divide',
              'per', 'rate', 'slope', 'gradient'],
    'estimate': ['approximate', 'average', 'mean', 'estimate', 'roughly',
                 'about', 'approximately', 'typical'],
    'differentiate': ['derivative', 'rate', 'instantaneous', 'change',
                      'slope', 'gradient', 'velocity', 'acceleration']
}

BUCKET_MAPPING: Dict[PrimaryOperation, Bucket] = {
    'accumulate': 'accumulation',
    'transform': 'transformation',
    'scale': 'geometry',
    'estimate': 'kinematics',
    'differentiate': 'dynamics'
}

MODEL_MAPPING: Dict[Bucket, Model] = {
    'accumulation': 'work_energy_theorem',
    'transformation': 'newton_second_law',
    'geometry': 'kinematics_equations',
    'kinematics': 'kinematics_equations',
    'dynamics': 'newton_second_law',
    'conservation': 'conservation_energy'
}

TOOL_MAPPING: Dict[Model, Tool] = {
    'work_energy_theorem': 'algebraic_manipulation',
    'newton_second_law': 'vector_algebra',
    'kinematics_equations': 'algebraic_manipulation',
    'conservation_momentum': 'algebraic_manipulation',
    'conservation_energy': 'algebraic_manipulation',
    'thermodynamics_first_law': 'algebraic_manipulation',
    'thermodynamics_second_law': 'calculus_derivative',
    'wave_equation': 'differential_equations',
    'coulomb_law': 'vector_algebra',
    'ohm_law': 'algebraic_manipulation',
    'gravitation_law': 'vector_algebra',
    'projectile_motion': 'trigonometry',
    'circular_motion': 'trigonometry',
    'simple_harmonic_motion': 'differential_equations'
}


def identify_primary_operation(keywords: List[str], requested_output: str) -> PrimaryOperation:
    """
    Identify the primary operation using winner-takes-all strategy.
    Scores each operation based on keyword matches.
    """
    scores: Dict[PrimaryOperation, int] = {op: 0 for op in ['accumulate', 'transform', 'scale', 'estimate', 'differentiate']}
    
    for keyword in keywords:
        for operation, op_keywords in OPERATION_KEYWORDS.items():
            if keyword in op_keywords:
                scores[operation] += 1
    
    # Bonus for specific requested outputs
    if 'work' in requested_output.lower() or 'energy' in requested_output.lower():
        scores['accumulate'] += 2
    elif 'component' in requested_output.lower() or 'resolve' in requested_output.lower():
        scores['transform'] += 2
    elif 'average' in requested_output.lower():
        scores['estimate'] += 2
    elif 'rate' in requested_output.lower() or 'derivative' in requested_output.lower():
        scores['differentiate'] += 2
    
    # Winner takes all - return operation with highest score
    max_score = -1
    winner: PrimaryOperation = 'accumulate'  # Default
    
    for operation, score in scores.items():
        if score > max_score:
            max_score = score
            winner = operation
    
    return winner


def select_bucket(operation: PrimaryOperation) -> Bucket:
    """Select cognitive bucket based on primary operation."""
    return BUCKET_MAPPING[operation]


def select_model(bucket: Bucket) -> Model:
    """Select physics model based on bucket."""
    return MODEL_MAPPING[bucket]


def select_tool(model: Model) -> Tool:
    """Select mathematical tool based on model."""
    return TOOL_MAPPING[model]


# ============================================================================
# STAGE 3: DAG CONSTRUCTION (Nested Operations)
# ============================================================================

def detect_nested_operations(
    extracted_values: List[ExtractedValue],
    primary_operation: PrimaryOperation,
    keywords: List[str]
) -> List[OperationNode]:
    """
    Detect if nested operations are needed.
    For example, if calculating work with angled force, need vector resolution first.
    Returns list of operation nodes in dependency order.
    """
    nodes: List[OperationNode] = []
    
    # Check if we have an angle but need horizontal component
    has_angle = any('theta' in v.name or 'angle' in v.name for v in extracted_values)
    has_force = any('f_' in v.name for v in extracted_values)
    needs_work = primary_operation == 'accumulate' and any('work' in kw for kw in keywords)
    
    order = 0
    
    # If we need work but force is at an angle, we need to resolve vectors first
    if has_angle and has_force and needs_work:
        # Tertiary: Transform (vector resolution)
        nodes.append(OperationNode(
            operation='transform',
            bucket='transformation',
            model='newton_second_law',
            tool='trigonometry',
            dependencies=(),
            order=order
        ))
        order += 1
        
        # Secondary: Scale (apply trig ratios)
        nodes.append(OperationNode(
            operation='scale',
            bucket='geometry',
            model='kinematics_equations',
            tool='trigonometry',
            dependencies=('transform',),
            order=order
        ))
        order += 1
    
    # Add primary operation last
    deps = tuple(node.operation.value if hasattr(node.operation, 'value') else str(node.operation) for node in nodes)
    nodes.append(OperationNode(
        operation=primary_operation,
        bucket=select_bucket(primary_operation),
        model=select_model(select_bucket(primary_operation)),
        tool=select_tool(MODEL_MAPPING[select_bucket(primary_operation)]),
        dependencies=deps,
        order=order
    ))
    
    return nodes


# ============================================================================
# STAGE 4: EXECUTION ENGINE
# ============================================================================

def execute_vector_resolution(
    magnitude: float,
    angle_degrees: float,
    component: str = 'x'
) -> float:
    """Resolve a vector into x or y component."""
    angle_rad = math.radians(angle_degrees)
    if component.lower() == 'x':
        return magnitude * math.cos(angle_rad)
    else:
        return magnitude * math.sin(angle_rad)


def execute_work_calculation(
    force: float,
    distance: float,
    angle_degrees: Optional[float] = None
) -> float:
    """Calculate work done by force."""
    if angle_degrees is not None:
        angle_rad = math.radians(angle_degrees)
        return force * distance * math.cos(angle_rad)
    else:
        return force * distance


def execute_pipeline(request: CognitiveRequest) -> PipelineResult:
    """
    Main pipeline execution function.
    Implements the full FCIS workflow.
    """
    audit_log: List[str] = []
    
    try:
        # Stage 1: Analyze question
        text_to_analyze = request.question_text
        if request.part:
            parts = parse_question_parts(request.question_text)
            if request.part in parts:
                text_to_analyze = parts[request.part]
        
        audit_log.append(f"Analyzing part {request.part or 'a'}: {text_to_analyze[:100]}...")
        
        # Extract data
        extracted_values = extract_numbers_and_units(text_to_analyze)
        keywords = extract_keywords(text_to_analyze)
        requested_output = infer_requested_output(keywords, extracted_values)
        
        audit_log.append(f"Extracted {len(extracted_values)} values: {[v.name for v in extracted_values]}")
        audit_log.append(f"Keywords: {keywords}")
        audit_log.append(f"Requested output: {requested_output}")
        
        # Stage 2: Identify primary operation
        primary_op = identify_primary_operation(keywords, requested_output)
        bucket = select_bucket(primary_op)
        model = select_model(bucket)
        tool = select_tool(model)
        
        audit_log.append(f"Primary operation: {primary_op}")
        audit_log.append(f"Bucket: {bucket}")
        audit_log.append(f"Model: {model}")
        audit_log.append(f"Tool: {tool}")
        
        # Stage 3: Build operation DAG
        operation_dag = detect_nested_operations(extracted_values, primary_op, keywords)
        audit_log.append(f"Operation DAG: {[node.operation for node in operation_dag]}")
        
        # Stage 4: Execute operations
        intermediate_results: Dict[str, float] = {}
        final_answer: Optional[float] = None
        
        # Find relevant values
        force_val = next((v.value for v in extracted_values if 'f_' in v.name), None)
        distance_val = next((v.value for v in extracted_values if 'd_' in v.name), None)
        angle_val = next((v.value for v in extracted_values if 'theta' in v.name or 'angle' in v.name), None)
        
        # Execute based on operation type
        if primary_op == 'accumulate' and 'work' in requested_output.lower():
            if force_val is not None and distance_val is not None:
                final_answer = execute_work_calculation(force_val, distance_val, angle_val)
                audit_log.append(f"Calculated work: {final_answer:.4f} J")
            else:
                raise ValueError(f"Missing required values for work calculation. Got: force={force_val}, distance={distance_val}")
        
        # Build state
        state = CognitiveState(
            extracted_values=tuple(extracted_values),
            identified_operation=primary_op,
            selected_bucket=bucket,
            selected_model=model,
            selected_tool=tool,
            operation_dag=tuple(operation_dag),
            intermediate_results=intermediate_results,
            final_answer=final_answer,
            answer_unit="J" if final_answer is not None and 'work' in requested_output.lower() else None,
            audit_log=tuple(audit_log)
        )
        
        return PipelineResult(
            success=final_answer is not None,
            state=state,
            answer=final_answer,
            unit=state.answer_unit,
            explanation=f"Solved using {primary_op} operation in {bucket} bucket with {model} model.",
            error_message=None
        )
        
    except Exception as e:
        return PipelineResult(
            success=False,
            state=CognitiveState(audit_log=tuple(audit_log)),
            answer=None,
            unit=None,
            explanation="",
            error_message=str(e)
        )


__all__ = [
    'parse_question_parts',
    'extract_numbers_and_units',
    'extract_keywords',
    'infer_requested_output',
    'identify_primary_operation',
    'select_bucket',
    'select_model',
    'select_tool',
    'detect_nested_operations',
    'execute_vector_resolution',
    'execute_work_calculation',
    'execute_pipeline'
]
