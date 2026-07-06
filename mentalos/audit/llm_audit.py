"""
MentalOS Audit Module

This module handles the LLM-powered audit phase that occurs after all
problem parts have been processed. It compiles session data into a
structured summary and communicates with a local LLM endpoint for feedback.

The audit function is pure except for the HTTP request, which is isolated
here in keeping with the imperative shell pattern.

Architecture notes:
- HTTP communication is isolated to send_audit_request()
- All other functions are pure transformations
- Error handling is comprehensive for network failures
- Response parsing is defensive against malformed JSON
"""

import json
from typing import Any

import requests

from mentalos.core.models import Session, AuditResult, PipelineResult
from mentalos.config.settings import Config


def compile_audit_summary(
    problem_text: str,
    sessions: tuple[Session, ...]
) -> str:
    """
    Compile all session data into a formatted summary for LLM audit.
    
    Creates a structured text representation including the original problem,
    each part's question, and all gate logs with timing information.
    
    Args:
        problem_text: The full original problem statement
        sessions: Tuple of all completed session states
    
    Returns:
        Formatted string suitable for sending to LLM
    """
    lines = [
        "MENTALOS AUDIT SUMMARY",
        "=" * 60,
        "",
        "ORIGINAL PROBLEM:",
        problem_text,
        "",
        "-" * 60,
        "",
    ]
    
    for session in sessions:
        lines.append(f"PART {session.part_id} (Depth: {session.depth})")
        lines.append(f"Question: {session.question}")
        lines.append("")
        lines.append("Gate Logs:")
        
        for log in session.logs:
            lines.append(
                f"  [{log.gate}] ({log.time_sec:.2f}s): {log.answer}"
            )
        
        # Show variable catalog if populated
        if session.variable_catalog:
            lines.append("")
            lines.append("Variable Catalog:")
            for name, var in session.variable_catalog.items():
                lines.append(f"  {name} = {var.value} {var.unit} ({var.source})")
        
        # Show locked values
        if session.locked_requested_output:
            lines.append("")
            lines.append(f"Locked Requested Output: {session.locked_requested_output}")
        
        if session.locked_primary_operation:
            lines.append(f"Locked Primary Operation: {session.locked_primary_operation}")
        
        lines.append("")
        lines.append("-" * 60)
        lines.append("")
    
    return "\n".join(lines)


def build_audit_request(
    summary: str,
    config: Config
) -> dict[str, Any]:
    """
    Build the JSON payload for the LLM audit request.
    
    Constructs a properly formatted chat completion request with
    the system prompt and user summary.
    
    Args:
        summary: Compiled audit summary text
        config: Configuration with endpoint and model settings
    
    Returns:
        Dictionary ready for JSON serialization
    """
    from mentalos.config.settings import Config
    
    return {
        "model": config.llm_model,
        "messages": [
            {
                "role": "system",
                "content": config.audit_prompt
            },
            {
                "role": "user",
                "content": summary
            }
        ],
        "temperature": 0.3,  # Lower temperature for more focused feedback
        "max_tokens": 2000
    }


def send_audit_request(
    summary: str,
    config: Config
) -> AuditResult:
    """
    Send the audit summary to the LLM and parse the response.
    
    This is the only function in the audit module that performs I/O.
    It handles HTTP communication, error handling, and response parsing.
    
    Args:
        summary: Compiled audit summary text
        config: Configuration with endpoint settings
    
    Returns:
        AuditResult containing feedback or error information
    """
    from mentalos.config.settings import Config
    
    payload = build_audit_request(summary, config)
    
    try:
        response = requests.post(
            config.llm_endpoint,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60  # 60 second timeout for LLM response
        )
        response.raise_for_status()
        
        result_data = response.json()
        
        # Extract the assistant's message from the response
        if "choices" in result_data and len(result_data["choices"]) > 0:
            feedback = result_data["choices"][0].get("message", {}).get("content", "")
            return AuditResult(
                feedback=feedback,
                success=True,
                error_message=None
            )
        else:
            return AuditResult(
                feedback="",
                success=False,
                error_message="Unexpected response format from LLM"
            )
    
    except requests.exceptions.ConnectionError as e:
        return AuditResult(
            feedback="",
            success=False,
            error_message=f"Connection failed: {str(e)}. Is the LLM server running?"
        )
    except requests.exceptions.Timeout as e:
        return AuditResult(
            feedback="",
            success=False,
            error_message=f"Request timed out: {str(e)}"
        )
    except requests.exceptions.HTTPError as e:
        return AuditResult(
            feedback="",
            success=False,
            error_message=f"HTTP error: {str(e)}"
        )
    except requests.exceptions.RequestException as e:
        return AuditResult(
            feedback="",
            success=False,
            error_message=f"Request failed: {str(e)}"
        )
    except json.JSONDecodeError as e:
        return AuditResult(
            feedback="",
            success=False,
            error_message=f"Failed to parse LLM response: {str(e)}"
        )


def perform_audit(
    problem_text: str,
    sessions: tuple[Session, ...],
    config: Config
) -> AuditResult:
    """
    Main entry point for the audit phase.
    
    Compiles the session data into a summary and sends it to the LLM
    for feedback. Returns the audit result for display.
    
    Args:
        problem_text: The full original problem statement
        sessions: Tuple of all completed session states
        config: Configuration settings
    
    Returns:
        AuditResult with feedback or error information
    """
    from mentalos.config.settings import Config
    
    summary = compile_audit_summary(problem_text, sessions)
    return send_audit_request(summary, config)


def format_audit_display(audit_result: AuditResult) -> str:
    """
    Format the audit result for terminal display.
    
    Creates a nicely formatted output showing whether the audit
    succeeded and displaying the feedback or error message.
    
    Args:
        audit_result: Result from perform_audit
    
    Returns:
        Formatted string for display
    """
    lines = ["", "=" * 60, "FINAL AUDIT RESULTS", "=" * 60, ""]
    
    if audit_result.success:
        lines.append("✓ Audit completed successfully.")
        lines.append("")
        lines.append("LLM Feedback:")
        lines.append("-" * 40)
        lines.append(audit_result.feedback)
        lines.append("-" * 40)
    else:
        lines.append("⚠ Audit failed.")
        lines.append(f"Error: {audit_result.error_message}")
        lines.append("")
        lines.append("Note: The LLM server may not be running.")
        lines.append("Expected endpoint: http://localhost:1234/v1/chat/completions")
        lines.append("To run MentalOS without LLM audit, the application will continue normally.")
    
    return "\n".join(lines)
