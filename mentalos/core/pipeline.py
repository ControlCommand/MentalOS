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

+++ mentalos/core/pipeline.py (修改后)
"""MentalOS Core Pipeline - Dynamic Cognitive Processing Engine"""
from __future__ import annotations
import re
import math
from typing import Optional
from mentalos.types.core_types import (
    PrimaryOperation,
    Bucket,
    Model,
    Tool,
    ExtractedValue,
    CognitiveRequest,
    OperationNode,
    CognitiveState,
    EquationEntry,
    ExecutionStep,
    CognitiveResult,
)
from mentalos.equations.database import search_equations, get_equation_by_id


def extract_numbers_and_units(text: str) -> list[ExtractedValue]:
    """Extract numerical values with units from text dynamically."""
    pattern = r'(\d+(?:\.\d+)?)\s*(kg|m/s|m|N|J|s|m/s²|°|degrees|Hz|W|C|V|A|Ω)?'
    matches = re.finditer(pattern, text)

    extracted = []
    for match in matches:
        value_str = match.group(1)
        unit = match.group(2) or ""

        # Find context by looking at words before the number
        start_pos = match.start()
        context_words = text[max(0, start_pos-50):start_pos].split()[-3:]
        context = " ".join(context_words) if context_words else "unknown"

        # Generate a name based on context
        name = "unknown"
        if "force" in context.lower() or "push" in context.lower():
            name = "F"
        elif "mass" in context.lower() or "kg" in unit:
            name = "m"
        elif "distance" in context.lower() or "displacement" in context.lower() or "over" in context.lower():
            name = "d"
        elif "angle" in context.lower() or "degree" in context.lower() or "°" in unit:
            name = "theta"
        elif "friction" in context.lower():
            name = "f_friction"
        elif "velocity" in context.lower() or "speed" in context.lower():
            name = "v"
        elif "acceleration" in context.lower():
            name = "a"
        elif "time" in context.lower():
            name = "t"
        elif "work" in context.lower() or "energy" in context.lower():
            name = "W"

        try:
            extracted.append(ExtractedValue(
                name=name,
                value=float(value_str),
                unit=unit,
                context=context
            ))
        except ValueError:
            continue

    return extracted


def analyze_question_intent(question_text: str) -> dict:
    """Analyze question to determine requested output and intent."""
    question_lower = question_text.lower()

    # Detect what is being asked
    requested_output = "unknown"
    if "work" in question_lower and ("much" in question_lower or "many" in question_lower):
        requested_output = "work"
    elif "velocity" in question_lower or "speed" in question_lower:
        requested_output = "velocity"
    elif "acceleration" in question_lower:
        requested_output = "acceleration"
    elif "force" in question_lower:
        requested_output = "force"
    elif "time" in question_lower:
        requested_output = "time"
    elif "distance" in question_lower or "displacement" in question_lower:
        requested_output = "distance"
    elif "power" in question_lower:
        requested_output = "power"
    elif "energy" in question_lower:
        requested_output = "energy"
    elif "momentum" in question_lower:
        requested_output = "momentum"

    # Detect operation hints
    operation_hints = []
    if "average" in question_lower:
        operation_hints.append("estimate")
    if "total" in question_lower or "sum" in question_lower or "over" in question_lower:
        operation_hints.append("accumulate")
    if "resolve" in question_lower or "component" in question_lower or "break" in question_lower:
        operation_hints.append("transform")
    if "rate" in question_lower or "change" in question_lower:
        operation_hints.append("differentiate")
    if "scale" in question_lower or "factor" in question_lower:
        operation_hints.append("scale")

    return {
        "requested_output": requested_output,
        "operation_hints": operation_hints,
        "is_multi_part": bool(re.search(r'\([a-d]\)|[a-d]\)', question_lower))
    }


def detect_primary_operation(question_text: str, extracted_values: list[ExtractedValue],
                            custom_operation: Optional[PrimaryOperation] = None) -> PrimaryOperation:
    """Detect the primary operation based on question analysis."""
    if custom_operation:
        return custom_operation

    intent = analyze_question_intent(question_text)

    # Priority-based detection
    if "estimate" in intent["operation_hints"]:
        return PrimaryOperation.ESTIMATE
    if "transform" in intent["operation_hints"]:
        return PrimaryOperation.TRANSFORM
    if "differentiate" in intent["operation_hints"]:
        return PrimaryOperation.DIFFERENTIATE
    if "scale" in intent["operation_hints"]:
        return PrimaryOperation.SCALE

    # Default to accumulate for most physics problems involving totals
    return PrimaryOperation.ACCUMULATE


def detect_bucket(operation: PrimaryOperation, question_text: str,
                 custom_bucket: Optional[Bucket] = None) -> Bucket:
    """Detect the cognitive bucket for an operation."""
    if custom_bucket:
        return custom_bucket

    question_lower = question_text.lower()

    if "work" in question_lower or "energy" in question_lower:
        return Bucket.ACCUMULATION
    if "vector" in question_lower or "resolve" in question_lower or "component" in question_lower:
        return Bucket.TRANSFORMATION
    if "motion" in question_lower or "velocity" in question_lower or "acceleration" in question_lower:
        return Bucket.KINEMATICS
    if "force" in question_lower or "newton" in question_lower:
        return Bucket.DYNAMICS
    if "conservation" in question_lower or "momentum" in question_lower:
        return Bucket.CONSERVATION

    # Default based on operation
    bucket_map = {
        PrimaryOperation.ACCUMULATE: Bucket.ACCUMULATION,
        PrimaryOperation.TRANSFORM: Bucket.TRANSFORMATION,
        PrimaryOperation.SCALE: Bucket.GEOMETRY,
        PrimaryOperation.ESTIMATE: Bucket.KINEMATICS,
        PrimaryOperation.DIFFERENTIATE: Bucket.KINEMATICS,
    }

    return bucket_map.get(operation, Bucket.ACCUMULATION)


def detect_model(bucket: Bucket, question_text: str,
                custom_model: Optional[Model] = None) -> Model:
    """Detect the physics model that applies."""
    if custom_model:
        return custom_model

    question_lower = question_text.lower()

    if "work" in question_lower or "energy" in question_lower:
        return Model.WORK_ENERGY
    if "force" in question_lower or "newton" in question_lower:
        return Model.NEWTONIAN_MECHANICS
    if "velocity" in question_lower or "acceleration" in question_lower:
        if "2d" in question_lower or "projectile" in question_lower:
            return Model.KINEMATICS_2D
        return Model.KINEMATICS_1D
    if "momentum" in question_lower:
        return Model.CONSERVATION_MOMENTUM
    if "conservation" in question_lower:
        return Model.CONSERVATION_ENERGY

    # Default based on bucket
    model_map = {
        Bucket.ACCUMULATION: Model.WORK_ENERGY,
        Bucket.TRANSFORMATION: Model.NEWTONIAN_MECHANICS,
        Bucket.GEOMETRY: Model.KINEMATICS_1D,
        Bucket.KINEMATICS: Model.KINEMATICS_1D,
        Bucket.DYNAMICS: Model.NEWTONIAN_MECHANICS,
        Bucket.CONSERVATION: Model.CONSERVATION_ENERGY,
    }

    return model_map.get(bucket, Model.WORK_ENERGY)


def detect_tool(question_text: str, extracted_values: list[ExtractedValue]) -> Tool:
    """Detect the mathematical tool needed."""
    question_lower = question_text.lower()

    # Check for angle-related keywords
    has_angle = any(v.name == "theta" or "°" in v.unit or "degree" in v.unit.lower()
                   for v in extracted_values)
    has_angle = has_angle or "angle" in question_lower or "cos" in question_lower or "sin" in question_lower

    if has_angle:
        return Tool.TRIGONOMETRY

    if "vector" in question_lower or "component" in question_lower:
        return Tool.VECTOR_ALGEBRA

    if "derivative" in question_lower or "rate" in question_lower:
        return Tool.CALCULUS_DERIVATIVE

    if "integral" in question_lower or "area" in question_lower:
        return Tool.CALCULUS_INTEGRAL

    return Tool.ALGEBRAIC_MANIPULATION


def build_operation_dag(request: CognitiveRequest, extracted_values: list[ExtractedValue]) -> tuple[OperationNode, list[OperationNode]]:
    """Build the DAG of operations dynamically based on the problem."""
    # Detect primary operation characteristics
    primary_op = detect_primary_operation(request.question_text, extracted_values, request.custom_operation)
    primary_bucket = detect_bucket(primary_op, request.question_text, request.custom_bucket)
    primary_model = detect_model(primary_bucket, request.question_text, request.custom_model)
    primary_tool = detect_tool(request.question_text, extracted_values)

    # Calculate confidence based on how many indicators match
    confidence = 0.7  # Base confidence

    # Check if we have all required variables for common equations
    intent = analyze_question_intent(request.question_text)
    variable_names = [v.name for v in extracted_values]

    # Detect nested operations dynamically
    nested_operations = []

    # Check if vector resolution is needed (angled force with horizontal motion)
    has_angled_force = any(v.name == "F" and v.unit == "N" for v in extracted_values)
    has_angle = any(v.name == "theta" for v in extracted_values)
    asks_for_horizontal = "horizontal" in request.question_text.lower() or intent["requested_output"] in ["work", "distance"]

    if has_angled_force and has_angle and asks_for_horizontal:
        # Need to resolve vectors first
        nested_operations.append(OperationNode(
            operation=PrimaryOperation.TRANSFORM,
            bucket=Bucket.TRANSFORMATION,
            model=Model.NEWTONIAN_MECHANICS,
            tool=Tool.TRIGONOMETRY,
            confidence=0.9,
            dependencies=[],
            explanation="Resolve angled force into horizontal component"
        ))

    # Check if friction calculation needs normal force first
    has_friction = any("friction" in v.context.lower() or v.name == "f_friction" for v in extracted_values)
    if has_friction and not any(v.name == "N" for v in extracted_values):
        nested_operations.append(OperationNode(
            operation=PrimaryOperation.SCALE,
            bucket=Bucket.DYNAMICS,
            model=Model.NEWTONIAN_MECHANICS,
            tool=Tool.ALGEBRAIC_MANIPULATION,
            confidence=0.8,
            dependencies=[],
            explanation="Calculate normal force for friction"
        ))

    # Create primary operation node with dependencies on nested operations
    primary_node = OperationNode(
        operation=primary_op,
        bucket=primary_bucket,
        model=primary_model,
        tool=primary_tool,
        confidence=confidence,
        dependencies=[f"nested_{i}" for i in range(len(nested_operations))],
        explanation=f"Primary operation: {primary_op.value} to find {intent['requested_output']}"
    )

    return primary_node, nested_operations


def execute_operation(node: OperationNode, state: CognitiveState,
                     user_inputs: dict[str, float]) -> tuple[float, str, str]:
    """Execute a single operation node with user-provided values."""
    # Determine which equation to use based on operation and available data
    keywords = node.explanation.split()
    matching_equations = search_equations(keywords)

    # If no equations match from explanation, try based on operation type and requested output
    if not matching_equations:
        # Check the original request for what is being asked
        intent = analyze_question_intent(state.request.question_text)
        requested = intent["requested_output"]

        if requested == "acceleration" and node.operation == PrimaryOperation.ESTIMATE:
            # Use acceleration_avg equation
            matching_equations = [get_equation_by_id("acceleration_avg")]
        elif requested == "velocity" and node.operation == PrimaryOperation.ESTIMATE:
            matching_equations = [get_equation_by_id("velocity_avg")]
        elif requested == "work":
            matching_equations = [get_equation_by_id("work_basic")]

    if not matching_equations or matching_equations[0] is None:
        # Fallback to basic equations based on operation type
        # First check what the question is asking for
        intent = analyze_question_intent(state.request.question_text)
        requested = intent["requested_output"]

        # Handle acceleration questions specifically
        if requested == "acceleration":
            delta_v = user_inputs.get("delta_v", user_inputs.get("v", 0))
            delta_t = user_inputs.get("delta_t", user_inputs.get("t", 0))
            if delta_t > 0:
                result = delta_v / delta_t
                return result, "m/s²", f"a_avg = Δv/Δt = {delta_v}/{delta_t} = {result:.2f} m/s²"

        # Handle velocity questions
        if requested == "velocity":
            delta_x = user_inputs.get("delta_x", user_inputs.get("d", 0))
            delta_t = user_inputs.get("delta_t", user_inputs.get("t", 0))
            if delta_t > 0:
                result = delta_x / delta_t
                return result, "m/s", f"v_avg = Δx/Δt = {delta_x}/{delta_t} = {result:.2f} m/s"

        if node.operation == PrimaryOperation.TRANSFORM and node.tool == Tool.TRIGONOMETRY:
            # Vector resolution
            if "x" in node.explanation.lower() or "horizontal" in node.explanation.lower():
                # F_x = F * cos(theta)
                F = user_inputs.get("F", 0)
                theta_deg = user_inputs.get("theta", 0)
                theta_rad = math.radians(theta_deg)
                result = F * math.cos(theta_rad)
                return result, "N", f"F_x = {F} * cos({theta_deg}°) = {result:.2f} N"
            else:
                # F_y = F * sin(theta)
                F = user_inputs.get("F", 0)
                theta_deg = user_inputs.get("theta", 0)
                theta_rad = math.radians(theta_deg)
                result = F * math.sin(theta_rad)
                return result, "N", f"F_y = {F} * sin({theta_deg}°) = {result:.2f} N"

        elif node.operation == PrimaryOperation.ACCUMULATE:
            # Work calculation W = F * d * cos(theta) or W = F * d
            F = user_inputs.get("F", 0)
            d = user_inputs.get("d", 0)
            theta_deg = user_inputs.get("theta", 0)

            if theta_deg != 0:
                theta_rad = math.radians(theta_deg)
                result = F * d * math.cos(theta_rad)
                return result, "J", f"W = {F} * {d} * cos({theta_deg}°) = {result:.2f} J"
            else:
                result = F * d
                return result, "J", f"W = {F} * {d} = {result:.2f} J"

        elif node.operation == PrimaryOperation.SCALE:
            # F = m * a or similar
            m = user_inputs.get("m", 0)
            a = user_inputs.get("a", 0)
            if m > 0 and a > 0:
                result = m * a
                return result, "N", f"F = {m} * {a} = {result:.2f} N"

        return 0.0, "", "Unable to execute operation with provided inputs"

    # Use the best matching equation
    equation = matching_equations[0]

    # Execute based on equation type
    if equation.id == "work_basic":
        F = user_inputs.get("F", 0)
        d = user_inputs.get("d", 0)
        theta_deg = user_inputs.get("theta", 0)
        theta_rad = math.radians(theta_deg)
        result = F * d * math.cos(theta_rad)
        return result, "J", f"W = F * d * cos(θ) = {F} * {d} * cos({theta_deg}°) = {result:.2f} J"

    elif equation.id == "vector_resolution_x":
        F = user_inputs.get("F", 0)
        theta_deg = user_inputs.get("theta", 0)
        theta_rad = math.radians(theta_deg)
        result = F * math.cos(theta_rad)
        return result, "N", f"F_x = F * cos(θ) = {F} * cos({theta_deg}°) = {result:.2f} N"

    elif equation.id == "vector_resolution_y":
        F = user_inputs.get("F", 0)
        theta_deg = user_inputs.get("theta", 0)
        theta_rad = math.radians(theta_deg)
        result = F * math.sin(theta_rad)
        return result, "N", f"F_y = F * sin(θ) = {F} * sin({theta_deg}°) = {result:.2f} N"

    elif equation.id == "newton_second":
        m = user_inputs.get("m", 0)
        a = user_inputs.get("a", 0)
        result = m * a
        return result, "N", f"F = m * a = {m} * {a} = {result:.2f} N"

    elif equation.id == "kinetic_energy":
        m = user_inputs.get("m", 0)
        v = user_inputs.get("v", 0)
        result = 0.5 * m * v * v
        return result, "J", f"KE = 0.5 * m * v² = 0.5 * {m} * {v}² = {result:.2f} J"

    elif equation.id == "velocity_avg":
        delta_x = user_inputs.get("delta_x", user_inputs.get("d", 0))
        delta_t = user_inputs.get("delta_t", user_inputs.get("t", 0))
        if delta_t > 0:
            result = delta_x / delta_t
            return result, "m/s", f"v_avg = Δx/Δt = {delta_x}/{delta_t} = {result:.2f} m/s"

    elif equation.id == "acceleration_avg":
        delta_v = user_inputs.get("delta_v", user_inputs.get("v", 0))
        delta_t = user_inputs.get("delta_t", user_inputs.get("t", 0))
        if delta_t > 0:
            result = delta_v / delta_t
            return result, "m/s²", f"a_avg = Δv/Δt = {delta_v}/{delta_t} = {result:.2f} m/s²"

    return 0.0, "", f"Equation {equation.id} not yet implemented"


def process_cognitive_request(request: CognitiveRequest, user_values: dict[str, float]) -> CognitiveResult:
    """Main pipeline: process a cognitive request dynamically."""
    # Step 1: Extract values from question text
    extracted_values = extract_numbers_and_units(request.question_text)

    # Step 2: Build operation DAG
    primary_node, nested_nodes = build_operation_dag(request, extracted_values)

    # Step 3: Determine execution order (bottom-up through dependencies)
    execution_order = []
    for i, nested in enumerate(nested_nodes):
        execution_order.append(f"nested_{i}")
    execution_order.append("primary")

    # Step 4: Execute operations in order
    execution_steps = []
    results = {}
    warnings = []

    all_nodes = nested_nodes + [primary_node]

    for idx, node in enumerate(all_nodes):
        node_id = f"nested_{idx}" if idx < len(nested_nodes) else "primary"

        # Merge extracted values with user inputs
        combined_inputs = user_values.copy()
        for ev in extracted_values:
            if ev.name not in combined_inputs:
                combined_inputs[ev.name] = ev.value

        # Execute the operation
        output_value, output_unit, explanation = execute_operation(node,
            CognitiveState(
                request=request,
                extracted_values=extracted_values,
                primary_operation=primary_node,
                nested_operations=nested_nodes,
                execution_order=execution_order,
                results=results
            ),
            combined_inputs
        )

        if output_value == 0.0 and not explanation.startswith("W =") and not explanation.startswith("F_"):
            warnings.append(f"Operation {node_id} may need additional user input")

        step = ExecutionStep(
            step_number=len(execution_steps) + 1,
            operation_node_id=node_id,
            equation_used=node.explanation,
            inputs={k: v for k, v in combined_inputs.items() if k in ["F", "d", "theta", "m", "a", "v"]},
            output_value=output_value,
            output_unit=output_unit,
            explanation=explanation
        )

        execution_steps.append(step)
        results[node_id] = output_value

        # Store intermediate results for subsequent operations
        if "F_x" in explanation or "horizontal" in node.explanation.lower():
            results["F_x"] = output_value
            combined_inputs["F"] = output_value  # Use F_x as F for next step

    # Step 5: Get final answer from primary operation
    final_step = execution_steps[-1] if execution_steps else None
    final_answer = final_step.output_value if final_step else None
    final_unit = final_step.output_unit if final_step else None

    # Step 6: Generate audit summary
    audit_summary = f"Processed {len(execution_steps)} operation(s). "
    audit_summary += f"Primary operation: {primary_node.operation.value}. "
    if nested_nodes:
        audit_summary += f"Resolved {len(nested_nodes)} nested operation(s) first. "
    audit_summary += "Verify all input values and units for accuracy."

    return CognitiveResult(
        success=True,
        final_answer=final_answer,
        final_unit=final_unit,
        answer_explanation=final_step.explanation if final_step else "No execution steps performed",
        execution_steps=execution_steps,
        total_steps=len(execution_steps),
        warnings=warnings,
        audit_summary=audit_summary
    )
