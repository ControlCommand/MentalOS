# MentalOS Config Package
"""
Immutable configuration for gate sequences, prompts, formulas, and LLM settings.
All configuration is frozen to prevent accidental mutation at runtime.
"""

from mentalos.config.settings import (
    GateConfig,
    Config,
    Formula,
    FORMULA_DATABASE,
    DEFAULT_CONFIG,
    PHYSICAL_CONSTANTS,
    UNIT_CONVERSIONS,
    SMART_DEFAULTS,
)

# Backwards compatibility alias - UNITS is now organized by dimension in UNIT_CONVERSIONS
UNITS = {}

__all__ = [
    "GateConfig",
    "Config",
    "Formula",
    "FORMULA_DATABASE",
    "UNITS",
    "DEFAULT_CONFIG",
    "PHYSICAL_CONSTANTS",
    "UNIT_CONVERSIONS",
]
