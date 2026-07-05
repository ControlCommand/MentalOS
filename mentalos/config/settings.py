"""
MentalOS Configuration Module

This module contains all configurable aspects of the MentalOS pipeline.
Keeping configuration separate from logic allows easy customization
without touching core transformation functions.

Gate sequence and prompts are defined here rather than hard-coded
in the pipeline logic, fulfilling the requirement for configurable behavior.
"""

from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True)
class GateConfig:
    """Immutable configuration for a single gate."""
    name: str
    prompt: str


@dataclass(frozen=True)
class Config:
    """
    Master configuration for MentalOS.
    
    All fields are immutable (frozen dataclass) to prevent accidental mutation.
    This ensures configuration remains constant throughout program execution.
    """
    # Default gate sequence - order matters for pipeline flow
    gate_sequence: tuple[str, ...] = (
        "Scope Lock",
        "Intent",
        "Requested Output",
        "Domain Bucket",
        "Primary Operation Lock",
        "Model",
        "Tool",
        "Execution",
        "Interpretation",
    )
    
    # Prompts mapped by gate name for lookup during pipeline execution
    gate_prompts: Mapping[str, str] = field(default_factory=lambda: {
        "Scope Lock": "Define the constraints and boundaries of this problem. What is explicitly excluded?",
        "Intent": "What is the asker's true motivation? What deeper understanding are they seeking?",
        "Requested Output": "Specify the exact output type required (e.g., 'Work_app', numerical answer, derivation).",
        "Domain Bucket": "Categorize the problem domain (e.g., Classical Mechanics, Electromagnetism, Calculus).",
        "Primary Operation Lock": "Lock the single primary operation to perform. Winner-Takes-All selection.",
        "Model": "Identify the theorem, law, or conceptual model that applies.",
        "Tool": "Specify the formula, method, or algorithm to execute.",
        "Execution": "Perform the calculation or derivation. Type ':defer' to push a sub-operation.",
        "Interpretation": "Interpret the result in context. Does it make physical/mathematical sense?",
    })
    
    # Gate index where deferred operations should restart the pipeline
    # Typically "Intent" (index 1) or "Primary Operation Lock" (index 4)
    deferred_start_gate_idx: int = 1
    
    # LLM audit endpoint configuration
    llm_endpoint: str = "http://localhost:1234/v1/chat/completions"
    llm_model: str = "qwen2.5-math"
    
    # Audit system prompt
    audit_prompt: str = (
        "You are a MentalOS auditor. Point out any vague, incomplete, or incorrect gate answers. "
        "Do NOT provide solutions, only precise feedback."
    )
    
    # Shortened pipeline for sub-operations (indices into gate_sequence)
    sub_op_gates: tuple[str, ...] = (
        "Intent",
        "Primary Operation Lock",
        "Tool",
        "Execution",
    )


# Single instance for import throughout the application
DEFAULT_CONFIG = Config()
