"""AGRUS Security AI Service — modular AI-native security platform.

Directory structure:
    ai/
    ├── core/          ← Core engine: backends, models, knowledge, prompts, decision engine
    ├── features/      ← Feature modules: UEBA, APT correlation, container security, scanners, remediation
    ├── api.py         ← FastAPI application
    ├── nats_agent.py  ← NATS event bus subscriber
    └── scenarios/     ← Evaluation & replay
"""
from .core.backends import FineTunedLlamaBackend, HeuristicSecurityBackend, OllamaChatBackend
from .core.engine import HeuristicSecurityLLM, SecurityDecisionEngine
from .core.knowledge import KnowledgeSnippet, SecurityKnowledgeBase
from .core.models import AIResult, CompanyConstraints, Decision, IncidentContext, EvaluationCase
from .core.prompts import SecurityPromptBuilder

__all__ = [
    "AIResult",
    "CompanyConstraints",
    "Decision",
    "EvaluationCase",
    "FineTunedLlamaBackend",
    "HeuristicSecurityLLM",
    "IncidentContext",
    "KnowledgeSnippet",
    "HeuristicSecurityBackend",
    "OllamaChatBackend",
    "SecurityKnowledgeBase",
    "SecurityPromptBuilder",
    "SecurityDecisionEngine",
]
