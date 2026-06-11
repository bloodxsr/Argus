# Dataset Schema for fine-tuning the Security AI

Each training example should be a JSON object with these top-level keys. For supervised fine-tuning / instruction tuning we use an "instruction" + "response" style where the response is the structured JSON the model must return.

Example JSONL line:

{
  "instruction": "Analyze incident: nginx spawned bash from /tmp and connected to 185.1.2.3",
  "response": {
    "classification": "Remote Code Execution + C2 Beaconing",
    "confidence": 0.93,
    "mitre_techniques": ["T1059.004","T1071.001"],
    "recommended_action": "kill_process",
    "escalate_to_human": false,
    "reasoning": "Execution from /tmp combined with external IP and beaconing matches webshell/C2 patterns."
  }
}

Fields:
- `instruction` (string): natural language incident description and context.
- `response` (object): structured output the model should emit.
  - `classification` (string)
  - `confidence` (float, 0.0-1.0)
  - `mitre_techniques` (array of strings)
  - `recommended_action` (string)
  - `escalate_to_human` (bool)
  - `reasoning` (string)

Prefer deterministic responses (temperature=0) during fine-tuning and evaluation. Include adversarial examples (prompt injection, partial info, label flips) and company-constraint cases.
