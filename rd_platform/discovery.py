"""Deterministic, baseline requirement discovery for trusted hosts.

This module deliberately does not claim to be an autonomous model.  It makes a
small, explainable first-pass structure from the operator's idea; a host can
later replace or enrich that structure with an approved model adapter.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


_SCHEMA_VERSION = "discovery-v1"
_QUESTION_IDS = ("Q-001", "Q-002", "Q-003")


def discover(idea: str) -> dict[str, Any]:
    """Return an explainable first-pass discovery model for a non-empty idea."""
    if not isinstance(idea, str) or not idea.strip():
        raise ValueError("idea must be a non-empty string")

    normalized_idea = idea.strip()
    questions = [
        {
            "id": "Q-001",
            "question": "Who is the accountable operator and who are the primary users?",
            "suggestion": "Name one accountable operator and one primary user group.",
            "why": "Roles determine permissions, hand-offs, and acceptance responsibility.",
            "required": True,
        },
        {
            "id": "Q-002",
            "question": "What is the smallest successful end-to-end outcome?",
            "suggestion": "Describe one input, one decision or action, and one observable output.",
            "why": "A bounded flow prevents the initial scope from becoming an untestable wish list.",
            "required": True,
        },
        {
            "id": "Q-003",
            "question": "Which data is sensitive and what retention or access limits apply?",
            "suggestion": "Classify personal, confidential, and regulated data before implementation.",
            "why": "Data classification drives the minimum security and operational requirements.",
            "required": True,
        },
    ]
    return {
        "idea": normalized_idea,
        "schema_version": _SCHEMA_VERSION,
        "discovery_mode": "baseline_no_model",
        "host_enhancement": "supported_later",
        "facts": [
            {
                "statement": normalized_idea,
                "source": "operator_idea",
            }
        ],
        "inferences": [
            {
                "statement": "The idea needs a bounded user outcome before implementation planning.",
                "basis": "baseline discovery heuristic; requires user confirmation",
            }
        ],
        "unknowns": [
            "Accountable operator and primary user group",
            "Minimum successful end-to-end flow",
            "Data classification, access, and retention constraints",
        ],
        "business_flow": [
            "User provides an input",
            "Authorized operator or service evaluates it",
            "System records an observable outcome",
        ],
        "permissions": [
            "Role ownership and least-privilege access require confirmation",
        ],
        "data": [
            "Data categories, sources, retention, and export constraints require confirmation",
        ],
        "nfr": [
            "Availability, performance, auditability, and recovery targets require confirmation",
        ],
        "questions": questions,
        "approval_status": "NOT_APPROVED",
    }


def freeze(model: Mapping[str, Any], answers: Mapping[str, str]) -> dict[str, Any]:
    """Validate required answers and export a DRAFT SRS and PARTIAL RTM.

    Freezing captures the supplied answers for downstream work.  It does not
    create a human approval, baseline, or acceptance decision.
    """
    if not isinstance(model, Mapping):
        raise ValueError("model must be a discovery mapping")
    if not isinstance(answers, Mapping):
        raise ValueError("answers must be a mapping")
    if model.get("schema_version") != _SCHEMA_VERSION:
        raise ValueError("unsupported discovery schema version")
    if not isinstance(model.get("idea"), str) or not model["idea"].strip():
        raise ValueError("model idea must be a non-empty string")
    _validate_evidence_list(model, "facts", ("statement", "source"))
    _validate_evidence_list(model, "inferences", ("statement", "basis"))
    _validate_string_list(model, "unknowns")
    questions = model.get("questions")
    if not isinstance(questions, list):
        raise ValueError("model questions must be a list")

    normalized_answers: dict[str, str] = {}
    seen_question_ids: set[str] = set()
    required_question_ids: set[str] = set()
    for question in questions:
        if not isinstance(question, Mapping) or any(
            not isinstance(question.get(field), str) or not question[field].strip()
            for field in ("id", "question", "suggestion", "why")
        ) or not isinstance(question.get("required"), bool):
            raise ValueError("each discovery question must have valid fields")
        question_id = question["id"]
        seen_question_ids.add(question_id)
        if question["required"]:
            required_question_ids.add(question_id)
        answer = answers.get(question_id)
        if question.get("required", False) and (not isinstance(answer, str) or not answer.strip()):
            raise ValueError(f"missing required answer: {question_id}")
        if isinstance(answer, str) and answer.strip():
            normalized_answers[question_id] = answer.strip()
    if seen_question_ids != set(_QUESTION_IDS) or required_question_ids != set(_QUESTION_IDS):
        raise ValueError("model must contain the expected required question ids")

    requirements = [
        {
            "id": "REQ-DISC-001",
            "statement": "The system shall support the confirmed minimum end-to-end business flow.",
            "source_question": "Q-002",
            "confirmation": normalized_answers.get("Q-002", ""),
        },
        {
            "id": "REQ-DISC-002",
            "statement": "The system shall enforce confirmed role and access boundaries.",
            "source_question": "Q-001",
            "confirmation": normalized_answers.get("Q-001", ""),
        },
        {
            "id": "REQ-DISC-003",
            "statement": "The system shall handle confirmed data classifications and constraints.",
            "source_question": "Q-003",
            "confirmation": normalized_answers.get("Q-003", ""),
        },
    ]
    rows = [
        {
            "requirement_id": requirement["id"],
            "source_question": requirement["source_question"],
            "design": "PENDING",
            "task": "PENDING",
            "test": "PENDING",
            "traceability_status": "PARTIAL",
        }
        for requirement in requirements
    ]
    return {
        "model": dict(model),
        "answers": normalized_answers,
        "srs": {
            "document_state": "DRAFT",
            "requirements": requirements,
            "facts": list(model.get("facts", [])),
            "inferences": list(model.get("inferences", [])),
            "unknowns": list(model.get("unknowns", [])),
        },
        "rtm": {
            "traceability_status": "PARTIAL",
            "rows": rows,
        },
        "approval_status": "NOT_APPROVED",
    }


def _validate_evidence_list(model: Mapping[str, Any], name: str, fields: tuple[str, ...]) -> None:
    value = model.get(name)
    if not isinstance(value, list) or not value:
        raise ValueError(f"model {name} must be a non-empty list")
    for item in value:
        if not isinstance(item, Mapping) or any(
            not isinstance(item.get(field), str) or not item[field].strip() for field in fields
        ):
            raise ValueError(f"model {name} has invalid item fields")


def _validate_string_list(model: Mapping[str, Any], name: str) -> None:
    value = model.get(name)
    if not isinstance(value, list) or not value or any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f"model {name} must be a non-empty string list")
