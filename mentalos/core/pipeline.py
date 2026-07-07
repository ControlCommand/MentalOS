"""
MentalOS Cognitive Pipeline Engine

Implements the deterministic FCIS pipeline with DAG-based nested operation resolution.
Question → Requested Output → Constraint Lock → Operation Lock → Bucket → Model → Tool → Execution
"""
from __future__ import annotations
import re
import uuid
from typing import List, Dict, Optional, Any, Tuple, Set
from dataclasses import dataclass, field

from mentalos.types import (
    PrimaryOperation, Bucket, Model, Tool,
    QuestionAnalysis, RequestedOutput, ConstraintLock, OperationLock,
    BucketAssignment, ModelSelection, ToolSelection, NestedOperation,
    ExecutionPlan, StepResult, CognitiveResult, UserPrompt, UserResponse,
    CognitiveState, CognitiveRequest, CognitiveResponse,
    ExtractedValue, ExtractedVector, ProblemContext, EquationMatch,
    SpatialVisualization
)
from mentalos.equations.database import get_equation_database, Equation


# =============================================================================
# KEYWORD MAPS FOR INFERENCE
# =============================================================================

OPERATION_KEYWORDS: Dict[PrimaryOperation, List[str]] = {
    "accumulate": [
        "work", "energy", "total", "sum", "accumulated", "integral",
        "over a distance", "throughout", "combined", "net"
    ],
    "transform": [
        "resolve", "components", "break down", "decompose", "project",
        "x-component", "y-component", "horizontal", "vertical",
        "angle", "direction", "rotate", "convert"
    ],
    "scale": [
        "ratio", "proportion", "factor", "times", "multiplied",
        "divided", "per", "coefficient", "fraction", "percentage"
    ],
    "estimate": [
        "average", "mean", "approximate", "estimated", "typical",
        "roughly", "about", "around"
    ],
    "differentiate": [
        "rate", "change", "derivative", "slope", "instantaneous",
        "how fast", "velocity", "acceleration", "gradient"
    ]
}

BUCKET_KEYWORDS: Dict[Bucket, List[str]] = {
    "accumulation": ["work", "energy", "power", "impulse", "charge"],
    "transformation": ["vector", "components", "resolution", "coordinate", "rotation"],
    "geometry": ["distance", "angle", "triangle", "shape", "spatial"],
    "kinematics": ["velocity", "acceleration", "displacement", "motion", "speed"],
    "dynamics": ["force", "newton", "mass", "friction", "tension"],
    "conservation": ["conservation", "constant", "unchanged", "preserved"]
}

MODEL_KEYWORDS: Dict[Model, List[str]] = {
    "work_energy_theorem": ["work", "energy", "kinetic", "potential", "theorem"],
    "newtonian_mechanics": ["force", "newton", "mass", "acceleration", "f=ma"],
    "kinematics_constant_acceleration": ["constant acceleration", "uniform acceleration", "kinematics"],
    "equilibrium_statics": ["equilibrium", "static", "balanced", "stationary"],
    "conservation_of_energy": ["conservation energy", "mechanical energy", "total energy"],
    "conservation_of_momentum": ["conservation momentum", "collision", "impulse"]
}

OUTPUT_TYPE_KEYWORDS: Dict[str, List[str]] = {
    "instantaneous": ["instantaneous", "at this moment", "at t=", "when"],
    "average": ["average", "mean", "over the interval"],
    "total": ["total", "net", "overall", "combined"],
    "maximum": ["maximum", "max", "highest", "greatest"],
    "minimum": ["minimum", "min", "lowest", "least"]
}


# =============================================================================
# TEXT ANALYSIS UTILITIES
# =============================================================================

def extract_numbers_with_units(text: str) -> List[Dict[str, Any]]:
    """Extract numerical values with units from text."""
    pattern = r'(\d+(?:\.\d+)?)\s*(kg|m/s|N|J|m|s|deg|°|%|m/s²|W)?'
    matches = re.findall(pattern, text, re.IGNORECASE)
    
    results = []
    for value, unit in matches:
        # Clean up unit
        unit = unit.strip() if unit else ""
        unit = unit.replace("°", "deg")
        
        results.append({
            "value": float(value),
            "unit": unit
        })
    
    return results


def extract_keywords(text: str) -> List[str]:
    """Extract meaningful keywords from problem text."""
    # Remove common stop words and punctuation
    stop_words = {
        "a", "an", "the", "is", "are", "was", "were", "be", "been",
        "by", "from", "to", "of", "in", "on", "at", "for", "with",
        "this", "that", "these", "those", "it", "its", "and", "or",
        "but", "if", "then", "else", "when", "where", "how", "what"
    }
    
    # Tokenize
    tokens = re.findall(r'\b[a-zA-Z][a-zA-Z-]+\b', text.lower())
    
    # Filter stop words and short words
    keywords = [t for t in tokens if t not in stop_words and len(t) > 2]
    
    return keywords


def parse_question_parts(text: str) -> Dict[str, str]:
    """Parse multi-part questions (a, b, c, d)."""
    parts = {}
    
    # Pattern for part labels like "a)", "a.", "(a)", etc.
    pattern = r'(?:^|\n)\s*([a-d])[\).\)]\s*(.*?)(?=\n\s*[a-d][\).\)]|\Z)'
    
    matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
    
    for label, content in matches:
        parts[label.lower()] = content.strip()
    
    return parts


def detect_primary_operation(keywords: List[str]) -> Tuple[PrimaryOperation, float, str]:
    """Detect primary operation using keyword matching (Winner Takes All)."""
    scores: Dict[PrimaryOperation, float] = {op: 0.0 for op in OPERATION_KEYWORDS.keys()}
    
    for keyword in keywords:
        kw_lower = keyword.lower()
        for operation, op_keywords in OPERATION_KEYWORDS.items():
            for op_kw in op_keywords:
                if op_kw in kw_lower or kw_lower in op_kw:
                    scores[operation] += 1.0
    
    # Winner takes all
    best_op = max(scores, key=scores.get)
    best_score = scores[best_op]
    
    # Normalize score
    confidence = min(best_score / max(len(keywords), 1), 1.0)
    
    reasoning = f"Detected '{best_op}' based on keywords: {[k for k in keywords if any(op_kw in k.lower() for op_kw in OPERATION_KEYWORDS[best_op])]}"
    
    return best_op, confidence, reasoning


def detect_bucket(keywords: List[str], operation: PrimaryOperation) -> Tuple[Bucket, float, str]:
    """Detect cognitive bucket based on keywords and operation."""
    scores: Dict[Bucket, float] = {bucket: 0.0 for bucket in BUCKET_KEYWORDS.keys()}
    
    # Operation-to-bucket mapping hints
    operation_bucket_hints = {
        "accumulate": ["accumulation", "conservation"],
        "transform": ["transformation", "geometry"],
        "scale": ["geometry", "dynamics"],
        "estimate": ["kinematics", "dynamics"],
        "differentiate": ["kinematics", "dynamics"]
    }
    
    for keyword in keywords:
        kw_lower = keyword.lower()
        for bucket, bucket_keywords in BUCKET_KEYWORDS.items():
            for bk in bucket_keywords:
                if bk in kw_lower or kw_lower in bk:
                    scores[bucket] += 1.5  # Boost for direct matches
            
            # Bonus for operation-hinted buckets
            if bucket in operation_bucket_hints.get(operation, []):
                scores[bucket] += 0.3
    
    best_bucket = max(scores, key=scores.get)
    confidence = min(scores[best_bucket] / max(len(keywords), 1), 1.0)
    
    reasoning = f"Bucket '{best_bucket}' selected based on domain keywords and operation '{operation}'"
    
    return best_bucket, confidence, reasoning


def detect_model(keywords: List[str], bucket: Bucket) -> Tuple[Model, float, str]:
    """Detect physics model based on keywords and bucket."""
    scores: Dict[Model, float] = {model: 0.0 for model in MODEL_KEYWORDS.keys()}
    
    # Bucket-to-model hints
    bucket_model_hints = {
        "accumulation": ["work_energy_theorem", "conservation_of_energy"],
        "transformation": ["newtonian_mechanics", "equilibrium_statics"],
        "geometry": ["equilibrium_statics"],
        "kinematics": ["kinematics_constant_acceleration"],
        "dynamics": ["newtonian_mechanics"],
        "conservation": ["conservation_of_energy", "conservation_of_momentum"]
    }
    
    for keyword in keywords:
        kw_lower = keyword.lower()
        for model, model_keywords in MODEL_KEYWORDS.items():
            for mk in model_keywords:
                if mk in kw_lower or kw_lower in mk:
                    scores[model] += 1.5
            
            # Bonus for bucket-hinted models
            if model in bucket_model_hints.get(bucket, []):
                scores[model] += 0.3
    
    best_model = max(scores, key=scores.get)
    confidence = min(scores[best_model] / max(len(keywords), 1), 1.0)
    
    reasoning = f"Model '{best_model}' identified from problem context and bucket '{bucket}'"
    
    return best_model, confidence, reasoning


def detect_tool(model: Model, operation: PrimaryOperation) -> Tuple[Tool, float, str]:
    """Determine mathematical tool based on model and operation."""
    # Heuristic mapping
    tool_mapping: Dict[Tuple[Model, PrimaryOperation], Tool] = {
        ("work_energy_theorem", "accumulate"): "algebraic_manipulation",
        ("newtonian_mechanics", "transform"): "trigonometry",
        ("newtonian_mechanics", "scale"): "algebraic_manipulation",
        ("kinematics_constant_acceleration", "accumulate"): "algebraic_manipulation",
        ("kinematics_constant_acceleration", "estimate"): "algebraic_manipulation",
        ("equilibrium_statics", "transform"): "trigonometry",
    }
    
    # Default tools by operation
    operation_defaults = {
        "accumulate": "algebraic_manipulation",
        "transform": "trigonometry",
        "scale": "algebraic_manipulation",
        "estimate": "statistics",
        "differentiate": "calculus_derivative"
    }
    
    key = (model, operation)
    if key in tool_mapping:
        tool = tool_mapping[key]
        confidence = 0.9
        reasoning = f"Tool '{tool}' selected based on model '{model}' and operation '{operation}'"
    else:
        tool = operation_defaults.get(operation, "algebraic_manipulation")
        confidence = 0.6
        reasoning = f"Default tool '{tool}' for operation '{operation}'"
    
    return tool, confidence, reasoning


def infer_requested_output(question_text: str, keywords: List[str]) -> RequestedOutput:
    """Infer what the question is asking for."""
    question_lower = question_text.lower()
    
    # Target quantity detection
    quantity_map = {
        "work": (["work done", "work was done", "much work"], "W", "J"),
        "velocity": (["velocity", "speed", "how fast"], "v", "m/s"),
        "acceleration": (["acceleration", "accelerating"], "a", "m/s²"),
        "force": (["force", "forces"], "F", "N"),
        "displacement": (["displacement", "distance moved"], "Δx", "m"),
        "time": (["time", "how long", "duration"], "t", "s"),
        "power": (["power", "power output"], "P", "W"),
        "energy": (["energy", "kinetic energy", "potential energy"], "E", "J"),
        "momentum": (["momentum"], "p", "kg·m/s"),
        "height": (["height", "how high"], "h", "m")
    }
    
    target_quantity = "unknown"
    symbol = "?"
    unit = "?"
    
    for quantity, (kw_list, sym, unt) in quantity_map.items():
        for kw in kw_list:
            if kw in question_lower:
                target_quantity = quantity
                symbol = sym
                unit = unt
                break
        if target_quantity != "unknown":
            break
    
    # Output type detection
    output_type = "total"  # default
    for out_type, type_keywords in OUTPUT_TYPE_KEYWORDS.items():
        for tk in type_keywords:
            if tk in question_lower:
                output_type = out_type
                break
    
    description = f"Calculate the {output_type} {target_quantity}"
    
    return RequestedOutput(
        target_quantity=target_quantity,
        output_type=output_type,  # type: ignore
        symbol=symbol,
        unit=unit,
        description=description
    )


# =============================================================================
# COGNITIVE PIPELINE ENGINE
# =============================================================================

class CognitivePipeline:
    """
    Main cognitive pipeline engine implementing the DAG-based approach.
    
    Pipeline stages:
    1. Question Analysis - Parse and extract context
    2. Requested Output - Determine what's being asked
    3. Constraint Lock - Isolate relevant variables
    4. Operation Lock - Identify primary operation (Winner Takes All)
    5. Bucket Assignment - Determine cognitive bucket
    6. Model Selection - Select physics framework
    7. Tool Selection - Select mathematical tool
    8. Nested Operation Discovery - Find dependent operations
    9. Execution Planning - Order operations for execution
    10. Execution - Compute results bottom-up
    """
    
    def __init__(self):
        self.equation_db = get_equation_database()
        self.sessions: Dict[str, CognitiveState] = {}
    
    def create_session(self, request: CognitiveRequest) -> CognitiveState:
        """Create a new cognitive session."""
        session_id = str(uuid.uuid4())[:8]
        
        # Stage 1: Question Analysis
        keywords = extract_keywords(request.question_text)
        parts = parse_question_parts(request.question_text)
        
        # Extract known values
        numbers = extract_numbers_with_units(request.question_text)
        known_values: List[Any] = []
        for num in numbers:
            known_values.append(ExtractedValue(
                symbol="unknown",
                value=num["value"],
                unit=num["unit"],
                description="Extracted from problem"
            ))
        
        context = ProblemContext(
            objects=[],
            conditions=[],
            constraints=[],
            assumptions=[],
            known_values=known_values
        )
        
        question_analysis = QuestionAnalysis(
            raw_text=request.question_text,
            parts=parts,
            current_part=request.selected_part,
            context=context,
            keywords=keywords,
            tokens=keywords
        )
        
        state = CognitiveState(
            session_id=session_id,
            question_analysis=question_analysis,
            current_stage="question_analysis"
        )
        
        self.sessions[session_id] = state
        return state
    
    def analyze_question(self, session_id: str) -> CognitiveState:
        """Stage 1: Complete question analysis."""
        state = self.sessions.get(session_id)
        if not state:
            raise ValueError(f"Session {session_id} not found")
        
        # Already done in create_session, but can be refined
        return state
    
    def determine_requested_output(self, session_id: str) -> CognitiveState:
        """Stage 2: Determine what the question wants."""
        state = self.sessions.get(session_id)
        if not state:
            raise ValueError(f"Session {session_id} not found")
        
        question_text = state.question_analysis.raw_text
        if state.question_analysis.current_part and state.question_analysis.parts:
            part_text = state.question_analysis.parts.get(state.question_analysis.current_part, "")
            if part_text:
                question_text = part_text
        
        keywords = state.question_analysis.keywords
        requested_output = infer_requested_output(question_text, keywords)
        
        # Create immutable new state
        state = CognitiveState(
            session_id=state.session_id,
            question_analysis=state.question_analysis,
            requested_output=requested_output,
            constraint_lock=state.constraint_lock,
            operation_lock=state.operation_lock,
            bucket_assignment=state.bucket_assignment,
            model_selection=state.model_selection,
            tool_selection=state.tool_selection,
            execution_plan=state.execution_plan,
            step_results=state.step_results,
            final_result=state.final_result,
            audit_feedback=state.audit_feedback,
            user_prompts=state.user_prompts,
            user_responses=state.user_responses,
            current_stage="requested_output",
            is_complete=state.is_complete,
            has_errors=state.has_errors,
            error_messages=state.error_messages
        )
        
        self.sessions[session_id] = state
        return state
    
    def apply_constraint_lock(self, session_id: str, user_values: Optional[Dict[str, float]] = None) -> CognitiveState:
        """Stage 3: Isolate variables and constraints."""
        state = self.sessions.get(session_id)
        if not state:
            raise ValueError(f"Session {session_id} not found")
        
        # Extract relevant variables based on requested output
        relevant_vars = []
        fixed_params = {}
        variable_params = {}
        
        # Simple heuristic: numbers in problem are fixed parameters
        for kv in state.question_analysis.context.known_values:
            if isinstance(kv, ExtractedValue):
                fixed_params[kv.symbol] = kv
        
        constraint_lock = ConstraintLock(
            relevant_variables=relevant_vars,
            ignored_variables=[],
            fixed_parameters=fixed_params,
            variable_parameters=variable_params,
            boundary_conditions=["horizontal floor", "from rest"] if "rest" in state.question_analysis.raw_text.lower() else [],
            scope_keywords=state.question_analysis.keywords
        )
        
        state = CognitiveState(
            session_id=state.session_id,
            question_analysis=state.question_analysis,
            requested_output=state.requested_output,
            constraint_lock=constraint_lock,
            operation_lock=state.operation_lock,
            bucket_assignment=state.bucket_assignment,
            model_selection=state.model_selection,
            tool_selection=state.tool_selection,
            execution_plan=state.execution_plan,
            step_results=state.step_results,
            final_result=state.final_result,
            audit_feedback=state.audit_feedback,
            user_prompts=state.user_prompts,
            user_responses=state.user_responses,
            current_stage="constraint_lock",
            is_complete=state.is_complete,
            has_errors=state.has_errors,
            error_messages=state.error_messages
        )
        
        self.sessions[session_id] = state
        return state
    
    def determine_operation_lock(self, session_id: str) -> CognitiveState:
        """Stage 4: Determine primary operation (Winner Takes All)."""
        state = self.sessions.get(session_id)
        if not state:
            raise ValueError(f"Session {session_id} not found")
        
        keywords = state.question_analysis.keywords
        primary_op, confidence, reasoning = detect_primary_operation(keywords)
        
        # Detect secondary operations
        secondary_ops = []
        if "angle" in " ".join(keywords) or "°" in state.question_analysis.raw_text:
            secondary_ops.append("transform")
        if "from rest" in state.question_analysis.raw_text.lower():
            secondary_ops.append("estimate")
        
        operation_lock = OperationLock(
            primary_operation=primary_op,
            confidence=confidence,
            reasoning=reasoning,
            secondary_operations=secondary_ops,
            operation_order=[primary_op] + secondary_ops
        )
        
        state = CognitiveState(
            session_id=state.session_id,
            question_analysis=state.question_analysis,
            requested_output=state.requested_output,
            constraint_lock=state.constraint_lock,
            operation_lock=operation_lock,
            bucket_assignment=state.bucket_assignment,
            model_selection=state.model_selection,
            tool_selection=state.tool_selection,
            execution_plan=state.execution_plan,
            step_results=state.step_results,
            final_result=state.final_result,
            audit_feedback=state.audit_feedback,
            user_prompts=state.user_prompts,
            user_responses=state.user_responses,
            current_stage="operation_lock",
            is_complete=state.is_complete,
            has_errors=state.has_errors,
            error_messages=state.error_messages
        )
        
        self.sessions[session_id] = state
        return state
    
    def assign_bucket(self, session_id: str) -> CognitiveState:
        """Stage 5: Assign cognitive bucket."""
        state = self.sessions.get(session_id)
        if not state:
            raise ValueError(f"Session {session_id} not found")
        
        if not state.operation_lock:
            raise ValueError("Operation lock must be determined first")
        
        keywords = state.question_analysis.keywords
        operation = state.operation_lock.primary_operation
        
        bucket, confidence, reasoning = detect_bucket(keywords, operation)
        
        bucket_assignment = BucketAssignment(
            primary_bucket=bucket,
            confidence=confidence,
            reasoning=reasoning,
            alternative_buckets=[]
        )
        
        state = CognitiveState(
            session_id=state.session_id,
            question_analysis=state.question_analysis,
            requested_output=state.requested_output,
            constraint_lock=state.constraint_lock,
            operation_lock=state.operation_lock,
            bucket_assignment=bucket_assignment,
            model_selection=state.model_selection,
            tool_selection=state.tool_selection,
            execution_plan=state.execution_plan,
            step_results=state.step_results,
            final_result=state.final_result,
            audit_feedback=state.audit_feedback,
            user_prompts=state.user_prompts,
            user_responses=state.user_responses,
            current_stage="bucket_assignment",
            is_complete=state.is_complete,
            has_errors=state.has_errors,
            error_messages=state.error_messages
        )
        
        self.sessions[session_id] = state
        return state
    
    def select_model(self, session_id: str) -> CognitiveState:
        """Stage 6: Select physics model."""
        state = self.sessions.get(session_id)
        if not state:
            raise ValueError(f"Session {session_id} not found")
        
        if not state.bucket_assignment:
            raise ValueError("Bucket assignment must be determined first")
        
        keywords = state.question_analysis.keywords
        bucket = state.bucket_assignment.primary_bucket
        
        model, confidence, reasoning = detect_model(keywords, bucket)
        
        model_selection = ModelSelection(
            primary_model=model,
            confidence=confidence,
            reasoning=reasoning,
            supporting_principles=[]
        )
        
        state = CognitiveState(
            session_id=state.session_id,
            question_analysis=state.question_analysis,
            requested_output=state.requested_output,
            constraint_lock=state.constraint_lock,
            operation_lock=state.operation_lock,
            bucket_assignment=state.bucket_assignment,
            model_selection=model_selection,
            tool_selection=state.tool_selection,
            execution_plan=state.execution_plan,
            step_results=state.step_results,
            final_result=state.final_result,
            audit_feedback=state.audit_feedback,
            user_prompts=state.user_prompts,
            user_responses=state.user_responses,
            current_stage="model_selection",
            is_complete=state.is_complete,
            has_errors=state.has_errors,
            error_messages=state.error_messages
        )
        
        self.sessions[session_id] = state
        return state
    
    def select_tool(self, session_id: str) -> CognitiveState:
        """Stage 7: Select mathematical tool."""
        state = self.sessions.get(session_id)
        if not state:
            raise ValueError(f"Session {session_id} not found")
        
        if not state.operation_lock or not state.model_selection:
            raise ValueError("Operation and model must be determined first")
        
        operation = state.operation_lock.primary_operation
        model = state.model_selection.primary_model
        
        tool, confidence, reasoning = detect_tool(model, operation)
        
        # Get required formulas from equation database
        equations = self.equation_db.search_by_operation(operation.value if hasattr(operation, 'value') else operation)
        required_formulas = [eq.formula for eq in equations[:3]]
        
        tool_selection = ToolSelection(
            primary_tool=tool,
            confidence=confidence,
            reasoning=reasoning,
            required_formulas=required_formulas
        )
        
        state = CognitiveState(
            session_id=state.session_id,
            question_analysis=state.question_analysis,
            requested_output=state.requested_output,
            constraint_lock=state.constraint_lock,
            operation_lock=state.operation_lock,
            bucket_assignment=state.bucket_assignment,
            model_selection=state.model_selection,
            tool_selection=tool_selection,
            execution_plan=state.execution_plan,
            step_results=state.step_results,
            final_result=state.final_result,
            audit_feedback=state.audit_feedback,
            user_prompts=state.user_prompts,
            user_responses=state.user_responses,
            current_stage="tool_selection",
            is_complete=state.is_complete,
            has_errors=state.has_errors,
            error_messages=state.error_messages
        )
        
        self.sessions[session_id] = state
        return state
    
    def discover_nested_operations(self, session_id: str, user_confirms_secondary: bool = True) -> CognitiveState:
        """Stage 8: Discover nested/sub-operations in dependency chain."""
        state = self.sessions.get(session_id)
        if not state:
            raise ValueError(f"Session {session_id} not found")
        
        if not state.operation_lock or not state.bucket_assignment or not state.model_selection or not state.tool_selection:
            raise ValueError("All previous stages must be complete")
        
        nested_ops: List[NestedOperation] = []
        order_counter = 1
        
        # Check for vector resolution needs (angles in problem)
        raw_text = state.question_analysis.raw_text.lower()
        if ("angle" in raw_text or "°" in raw_text or "deg" in raw_text) and user_confirms_secondary:
            nested_ops.append(NestedOperation(
                order=order_counter,
                operation="transform",
                bucket="transformation",
                model="newtonian_mechanics",
                tool="trigonometry",
                target_variable="F_x",
                dependencies=[]
            ))
            order_counter += 1
        
        # Check for equilibrium needs (normal force, friction)
        if ("friction" in raw_text or "normal" in raw_text) and user_confirms_secondary:
            nested_ops.append(NestedOperation(
                order=order_counter,
                operation="scale",
                bucket="dynamics",
                model="newtonian_mechanics",
                tool="algebraic_manipulation",
                target_variable="f_friction",
                dependencies=[]
            ))
            order_counter += 1
        
        # Build execution plan
        primary_op_lock = state.operation_lock
        
        # Determine execution order (reverse dependency order)
        execution_order = list(range(len(nested_ops), 0, -1))  # Execute nested first, then primary
        
        # Determine final formula based on primary operation
        final_formula = ""
        if primary_op_lock.primary_operation == "accumulate":
            final_formula = "W = F * d * cos(θ)"
        elif primary_op_lock.primary_operation == "transform":
            final_formula = "F_x = F * cos(θ), F_y = F * sin(θ)"
        elif primary_op_lock.primary_operation == "scale":
            final_formula = "F = m * a"
        elif primary_op_lock.primary_operation == "estimate":
            final_formula = "v_avg = Δx / Δt"
        elif primary_op_lock.primary_operation == "differentiate":
            final_formula = "a = dv/dt"
        
        execution_plan = ExecutionPlan(
            primary_operation=primary_op_lock,
            nested_operations=nested_ops,
            execution_order=execution_order,
            final_formula=final_formula,
            intermediate_results={}
        )
        
        state = CognitiveState(
            session_id=state.session_id,
            question_analysis=state.question_analysis,
            requested_output=state.requested_output,
            constraint_lock=state.constraint_lock,
            operation_lock=state.operation_lock,
            bucket_assignment=state.bucket_assignment,
            model_selection=state.model_selection,
            tool_selection=state.tool_selection,
            execution_plan=execution_plan,
            step_results=state.step_results,
            final_result=state.final_result,
            audit_feedback=state.audit_feedback,
            user_prompts=state.user_prompts,
            user_responses=state.user_responses,
            current_stage="execution_plan",
            is_complete=False,
            has_errors=state.has_errors,
            error_messages=state.error_messages
        )
        
        self.sessions[session_id] = state
        return state
    
    def execute_step(
        self, 
        session_id: str, 
        step_number: int, 
        equation_id: str, 
        input_values: Dict[str, float]
    ) -> Tuple[CognitiveState, StepResult]:
        """Execute a single computation step."""
        state = self.sessions.get(session_id)
        if not state:
            raise ValueError(f"Session {session_id} not found")
        
        equation = self.equation_db.get_equation(equation_id)
        if not equation:
            raise ValueError(f"Equation {equation_id} not found")
        
        # Determine operation and variable name
        if state.execution_plan and step_number <= len(state.execution_plan.nested_operations):
            nested_op = state.execution_plan.nested_operations[step_number - 1]
            operation = nested_op.operation
            var_name = nested_op.target_variable
        else:
            operation = state.operation_lock.primary_operation if state.operation_lock else "accumulate"
            var_name = state.requested_output.symbol if state.requested_output else "result"
        
        # Simple equation evaluation (expand this for production)
        try:
            result_value = self._evaluate_equation(equation, input_values)
            success = True
            error_msg = None
        except Exception as e:
            result_value = 0.0
            success = False
            error_msg = str(e)
        
        step_result = StepResult(
            step_number=step_number,
            operation=operation,
            variable_name=var_name,
            value=result_value,
            unit=equation.variables.get(list(equation.variables.keys())[0], {}).get("unit", ""),
            formula_used=equation.formula,
            inputs=input_values,
            success=success,
            error_message=error_msg
        )
        
        # Update state with new step result
        updated_results = list(state.step_results) + [step_result]
        
        state = CognitiveState(
            session_id=state.session_id,
            question_analysis=state.question_analysis,
            requested_output=state.requested_output,
            constraint_lock=state.constraint_lock,
            operation_lock=state.operation_lock,
            bucket_assignment=state.bucket_assignment,
            model_selection=state.model_selection,
            tool_selection=state.tool_selection,
            execution_plan=state.execution_plan,
            step_results=updated_results,
            final_result=state.final_result,
            audit_feedback=state.audit_feedback,
            user_prompts=state.user_prompts,
            user_responses=state.user_responses,
            current_stage="executing",
            is_complete=False,
            has_errors=not success,
            error_messages=[error_msg] if error_msg else state.error_messages
        )
        
        self.sessions[session_id] = state
        return state, step_result
    
    def _evaluate_equation(self, equation: Equation, input_values: Dict[str, float]) -> float:
        """Evaluate an equation with given input values."""
        # This is a simplified evaluator - expand for production
        eq_id = equation.id
        
        if eq_id == "work_constant_force":
            F = input_values.get("F", 0)
            d = input_values.get("d", 0)
            theta_deg = input_values.get("θ", 0)
            import math
            theta_rad = math.radians(theta_deg)
            return F * d * math.cos(theta_rad)
        
        elif eq_id == "vector_components":
            F = input_values.get("F", 0)
            theta_deg = input_values.get("θ", 0)
            import math
            theta_rad = math.radians(theta_deg)
            # Return F_x component
            return F * math.cos(theta_rad)
        
        elif eq_id == "friction_force":
            mu = input_values.get("μ", 0)
            N = input_values.get("N", 0)
            return mu * N
        
        # Default: return sum of inputs (placeholder)
        return sum(input_values.values())
    
    def finalize_result(self, session_id: str) -> CognitiveState:
        """Finalize the cognitive result after all steps executed."""
        state = self.sessions.get(session_id)
        if not state:
            raise ValueError(f"Session {session_id} not found")
        
        if not state.requested_output:
            raise ValueError("Requested output not determined")
        
        # Get final value from last successful step
        final_value = 0.0
        final_unit = state.requested_output.unit
        
        if state.step_results:
            last_successful = next((sr for sr in reversed(state.step_results) if sr.success), None)
            if last_successful:
                final_value = last_successful.value
                final_unit = last_successful.unit
        
        cognitive_result = CognitiveResult(
            question_part=state.question_analysis.current_part or "main",
            requested_output=state.requested_output,
            final_value=final_value,
            unit=final_unit,
            significant_figures=3,
            step_results=state.step_results,
            audit_feedback=None  # Would be filled by LLM audit
        )
        
        state = CognitiveState(
            session_id=state.session_id,
            question_analysis=state.question_analysis,
            requested_output=state.requested_output,
            constraint_lock=state.constraint_lock,
            operation_lock=state.operation_lock,
            bucket_assignment=state.bucket_assignment,
            model_selection=state.model_selection,
            tool_selection=state.tool_selection,
            execution_plan=state.execution_plan,
            step_results=state.step_results,
            final_result=cognitive_result,
            audit_feedback=state.audit_feedback,
            user_prompts=state.user_prompts,
            user_responses=state.user_responses,
            current_stage="complete",
            is_complete=True,
            has_errors=state.has_errors,
            error_messages=state.error_messages
        )
        
        self.sessions[session_id] = state
        return state
    
    def get_state(self, session_id: str) -> CognitiveState:
        """Get current state of a session."""
        state = self.sessions.get(session_id)
        if not state:
            raise ValueError(f"Session {session_id} not found")
        return state
