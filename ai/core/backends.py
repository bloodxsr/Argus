from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Protocol
from urllib.error import URLError
from urllib.request import Request, urlopen

from .knowledge import SecurityKnowledgeBase
from .models import AIResult, IncidentContext
from .prompts import SecurityPromptBundle, SecurityPromptBuilder


@dataclass(frozen=True, slots=True)
class ModelDraft:
    classification: str
    confidence: float
    mitre_techniques: tuple[str, ...]
    recommended_action: str
    escalate_to_human: bool
    reasoning: str
    reasoning_layers: tuple[str, ...] = ()


class SecurityModelBackend(Protocol):
    name: str

    def generate(self, prompt: SecurityPromptBundle, incident: IncidentContext) -> ModelDraft:
        ...


class HeuristicSecurityBackend:
    name = "heuristic-analytical"

    
    THREAT_SIGNATURES: list[dict] = [
        {"pattern": r"(?:ignore previous instructions|override rules|system prompt)", "mitre": "", "weight": 0.9, "action": "observe", "label": "Prompt Injection Attempt", "escalate": True},
        {"pattern": r"(?=.*(?:c2|beacon|beaconing))(?=.*(?:/tmp/|spawned bash|mimikatz))", "mitre": "T1059.004", "weight": 0.98, "action": "kill_process", "label": "Remote Code Execution + C2 Beaconing"},
        {"pattern": r"(?:(?:/tmp/|/dev/shm/|/var/tmp/).*(?:bash|sh|python|perl|nc|ncat)|(?:bash|sh|python|perl|nc|ncat).*from\s+(?:/tmp/|/dev/shm/|/var/tmp/))", "mitre": "T1059.004", "weight": 0.9, "action": "kill_process", "label": "Remote Code Execution + C2 Beaconing"},
        {"pattern": r"(?:reverse.?shell|>?\s*&\s*/dev/tcp|mkfifo|nc\s+-[elp])", "mitre": "T1059.004", "weight": 0.95, "action": "kill_process", "label": "Remote Code Execution + C2 Beaconing"},
        {"pattern": r"(?:mimikatz|lsass.*dump|comsvcs\.dll.*MiniDump|sekurlsa)", "mitre": "T1003.001", "weight": 0.97, "action": "isolate_host", "label": "Credential dumping"},
        {"pattern": r"(?:nmap|masscan|zmap)\s+.*(?:-s[STUFN]|-p)|(?:broad|suspicious)?\s*network scan|unusual country", "mitre": "T1046", "weight": 0.72, "action": "recommend", "label": "Suspicious but Unconfirmed Activity", "escalate": True},
        {"pattern": r"(?:wget|curl)\s+.*(?:pastebin|raw\.githubusercontent|transfer\.sh)", "mitre": "T1105", "weight": 0.85, "action": "kill_process", "label": "Payload download from public host"},
        {"pattern": r"(?:chmod\s+[47][0-7]{2}|chmod\s+\+[sx])\s+/", "mitre": "T1222.002", "weight": 0.6, "action": "recommend", "label": "File permission modification"},
        {"pattern": r"(?:crontab\s+-[el]|/etc/cron|systemctl\s+enable)", "mitre": "T1053.003", "weight": 0.65, "action": "recommend", "label": "Persistence via scheduled task"},
        {"pattern": r"(?:base64\s+-d|python.*-c.*exec|eval\(|powershell.*-[Ee]nc)", "mitre": "T1140", "weight": 0.8, "action": "kill_process", "label": "Obfuscated payload execution"},
        {"pattern": r"(?:\/etc\/shadow|\/etc\/passwd|SAM\s+database|ntds\.dit)", "mitre": "T1003.002", "weight": 0.88, "action": "isolate_host", "label": "Sensitive credential file access"},
        {"pattern": r"(?:ssh\s+.*@|scp\s+|rsync\s+.*:)", "mitre": "T1021.004", "weight": 0.4, "action": "observe", "label": "SSH lateral movement candidate"},
        {"pattern": r"(?:iptables\s+-[FXZ]|ufw\s+disable|netsh\s+.*firewall.*off)", "mitre": "T1562.004", "weight": 0.92, "action": "isolate_host", "label": "Firewall tampering"},
        {"pattern": r"(?:scheduled\s+backup|maintenance\s+window|log\s+rotation|health.?check)", "mitre": "", "weight": 0.88, "action": "observe", "label": "Benign Operational Activity"},
    ]

    def __init__(self, knowledge_base: SecurityKnowledgeBase | None = None) -> None:
        self.knowledge_base = knowledge_base or SecurityKnowledgeBase()
        import re
        self._compiled = [(re.compile(sig["pattern"], re.IGNORECASE), sig) for sig in self.THREAT_SIGNATURES]

    def generate(self, prompt: SecurityPromptBundle, incident: IncidentContext) -> ModelDraft:
        import re

        text = f"{incident.summary} {incident.host} {incident.asset_id} {' '.join(incident.labels)}"
        
        
        matched_sigs = []
        for compiled_re, sig in self._compiled:
            if compiled_re.search(text):
                matched_sigs.append(sig)

        
        retrieved_titles = [s.title.lower() for s in prompt.retrieved_context]
        retrieved_content = " ".join(s.content if hasattr(s, 'content') else s.summary for s in prompt.retrieved_context).lower()
        kb_threat_score = sum(1 for word in ("malicious", "threat", "exploit", "attack", "vulnerability", "compromise") if word in retrieved_content) / 6.0

        
        if matched_sigs:
            
            matched_sigs.sort(key=lambda s: s["weight"], reverse=True)
            primary = matched_sigs[0]
            
            mitre_chain = tuple(dict.fromkeys(s["mitre"] for s in matched_sigs if s["mitre"]))
            
            
            raw_confidence = primary["weight"]
            risk_factor = min(incident.risk_score / 100.0, 1.0)
            kb_boost = kb_threat_score * 0.1
            confidence = min(round(raw_confidence * 0.7 + risk_factor * 0.2 + kb_boost + 0.05, 2), 0.99)
            if primary["label"] == "Benign Operational Activity":
                confidence = max(confidence, 0.88)
            
            reasoning_layers = ["signature_match", "risk_aggregation"]
            if kb_threat_score > 0:
                reasoning_layers.append("kb_corroboration")
            
            all_labels = [s["label"] for s in matched_sigs]
            reasoning = f"Matched {len(matched_sigs)} behavioral signature(s): {'; '.join(all_labels)}. Risk factor: {risk_factor:.2f}, KB threat signal: {kb_threat_score:.2f}."
            
            return ModelDraft(
                classification=primary["label"],
                confidence=confidence,
                mitre_techniques=mitre_chain,
                recommended_action=primary["action"],
                escalate_to_human=bool(primary.get("escalate", primary["action"] in ("isolate_host", "quarantine_container"))),
                reasoning=reasoning,
                reasoning_layers=tuple(reasoning_layers),
            )

        
        anomaly_score = 0.0
        anomaly_reasons = []
        
        if incident.risk_score >= 80:
            anomaly_score += 0.3
            anomaly_reasons.append("high_risk_score")
        if incident.hour_of_day < 6 or incident.hour_of_day > 22:
            anomaly_score += 0.15
            anomaly_reasons.append("off_hours_activity")
        if kb_threat_score > 0.3:
            anomaly_score += 0.2
            anomaly_reasons.append("kb_threat_context")
        if any(label in ("PROCESS_START", "NETWORK_CONNECTION") for label in incident.labels):
            anomaly_score += 0.1
            anomaly_reasons.append("kernel_event_type")

        if anomaly_score >= 0.4:
            return ModelDraft(
                classification="Anomalous Activity (No Signature Match)",
                confidence=round(0.5 + anomaly_score * 0.3, 2),
                mitre_techniques=(),
                recommended_action="recommend",
                escalate_to_human=True,
                reasoning=f"No direct signature match but anomaly score {anomaly_score:.2f} exceeds threshold. Factors: {', '.join(anomaly_reasons)}.",
                reasoning_layers=("signature_miss", "anomaly_scoring", "escalation"),
            )

        return ModelDraft(
            classification="Benign / No Threat Detected",
            confidence=round(0.65 + kb_threat_score * 0.1, 2),
            mitre_techniques=(),
            recommended_action="observe",
            escalate_to_human=False,
            reasoning=f"No behavioral signatures matched. Anomaly score {anomaly_score:.2f} is below threshold. KB threat signal: {kb_threat_score:.2f}.",
            reasoning_layers=("signature_miss", "anomaly_scoring", "benign_classification"),
        )


class OllamaChatBackend:
    name = "ollama-chat"

    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
        timeout_seconds: float = 20.0,
        fallback: SecurityModelBackend | None = None,
    ) -> None:
        self.model = model or os.getenv("SECURITY_AI_OLLAMA_MODEL", "Foundation-Sec-8B-Reasoning")
        self.base_url = (base_url or os.getenv("SECURITY_AI_OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.fallback = fallback or HeuristicSecurityBackend()

    def generate(self, prompt: SecurityPromptBundle, incident: IncidentContext) -> ModelDraft:
        payload = {
            "model": self.model,
            "messages": list(prompt.messages),
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0,
            },
        }
        request = Request(
            f"{self.base_url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:  
                body = json.loads(response.read().decode("utf-8"))
        except (URLError, TimeoutError, ValueError, json.JSONDecodeError):
            return self.fallback.generate(prompt, incident)

        content = self._extract_message_content(body)
        if not content:
            return self.fallback.generate(prompt, incident)

        parsed = self._parse_draft(content)
        if parsed is None:
            return self.fallback.generate(prompt, incident)
        return parsed

    def _parse_draft(self, content: str) -> ModelDraft | None:
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return None

        try:
            return ModelDraft(
                classification=str(data.get("classification", "Unknown")),
                confidence=float(data.get("confidence", 0.5)),
                mitre_techniques=tuple(str(item) for item in data.get("mitre_techniques", ())),
                recommended_action=str(data.get("recommended_action", "observe")),
                escalate_to_human=bool(data.get("escalate_to_human", True)),
                reasoning=str(data.get("reasoning", "")),
                reasoning_layers=tuple(str(item) for item in data.get("reasoning_layers", ())),
            )
        except (KeyError, TypeError, ValueError):
            return None

    @staticmethod
    def _extract_message_content(body: dict[str, object]) -> str:
        message = body.get("message")
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, str):
                return content.strip()
        return ""


class LocalTransformersBackend:
    """Backend that loads local Transformers models for real GPU inference."""

    name = "foundation-sec-8b"

    def __init__(
        self,
        base_model: str = "Foundation-Sec-8B-Reasoning",
        fallback: SecurityModelBackend | None = None,
        max_new_tokens: int = 512,
    ) -> None:
        self.base_model_name = base_model
        self.max_new_tokens = max_new_tokens
        self.fallback = fallback or HeuristicSecurityBackend()
        self._model = None
        self._tokenizer = None
        self._loaded = False

    def _load_model(self) -> bool:
        """Lazy-load the model on first inference call to avoid blocking startup."""
        if self._loaded:
            return True

        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
        except ImportError:
            return False

        try:
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.bfloat16,
            )

            self._tokenizer = AutoTokenizer.from_pretrained(self.base_model_name)
            if self._tokenizer.pad_token is None:
                self._tokenizer.pad_token = self._tokenizer.eos_token

            self._model = AutoModelForCausalLM.from_pretrained(
                self.base_model_name,
                quantization_config=bnb_config,
                device_map="auto",
            )
            self._model.eval()
            self._loaded = True
            return True
        except Exception:
            self._model = None
            self._tokenizer = None
            return False

    def generate(self, prompt: SecurityPromptBundle, incident: IncidentContext) -> ModelDraft:
        if not self._load_model():
            return self.fallback.generate(prompt, incident)

        import torch

        
        if incident.incident_id == "remediation":
            input_text = f"Instruction: {prompt.user_prompt}\nAssessment:\n"
        else:
            input_text = f"Instruction: Analyze the following security event and provide a SOC assessment:\n{prompt.user_prompt}\nAssessment:\n"

        inputs = self._tokenizer(input_text, return_tensors="pt", truncation=True, max_length=1024)
        inputs = {k: v.to(self._model.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self._model.generate(
                **inputs,
                max_new_tokens=self.max_new_tokens,
                do_sample=True,
                temperature=0.3,
                top_p=0.9,
                repetition_penalty=1.1,
                pad_token_id=self._tokenizer.pad_token_id,
            )

        generated_ids = outputs[0][inputs["input_ids"].shape[-1]:]
        raw_output = self._tokenizer.decode(generated_ids, skip_special_tokens=True).strip()

        return self._parse_output(raw_output, incident)

    def _parse_output(self, raw_output: str, incident: IncidentContext) -> ModelDraft:
        """Attempt to parse model output as JSON, with structured fallback extraction."""
        
        try:
            data = json.loads(raw_output)
            return ModelDraft(
                classification=str(data.get("classification", "Unknown")),
                confidence=float(data.get("confidence", 0.5)),
                mitre_techniques=tuple(str(t) for t in data.get("mitre_techniques", ())),
                recommended_action=str(data.get("recommended_action", "observe")),
                escalate_to_human=bool(data.get("escalate_to_human", True)),
                reasoning=str(data.get("reasoning", raw_output[:200])),
                reasoning_layers=("llm_inference",),
            )
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            pass

        
        import re
        json_match = re.search(r'\{[^{}]*\}', raw_output, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
                return ModelDraft(
                    classification=str(data.get("classification", "Unknown")),
                    confidence=float(data.get("confidence", 0.5)),
                    mitre_techniques=tuple(str(t) for t in data.get("mitre_techniques", ())),
                    recommended_action=str(data.get("recommended_action", "observe")),
                    escalate_to_human=bool(data.get("escalate_to_human", True)),
                    reasoning=str(data.get("reasoning", raw_output[:200])),
                    reasoning_layers=("llm_inference", "json_extraction"),
                )
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                pass

        
        output_lower = raw_output.lower()
        is_threat = any(w in output_lower for w in ("malicious", "threat", "attack", "exploit", "critical", "kill"))
        
        return ModelDraft(
            classification="LLM Threat Assessment" if is_threat else "LLM Benign Assessment",
            confidence=0.72 if is_threat else 0.6,
            mitre_techniques=(),
            recommended_action="recommend" if is_threat else "observe",
            escalate_to_human=is_threat,
            reasoning=raw_output[:500],
            reasoning_layers=("llm_inference", "freetext_fallback"),
        )
