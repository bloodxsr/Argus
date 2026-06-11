from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.request
import urllib.error
from typing import List, Dict, Any, Tuple, TYPE_CHECKING

from .scanners import Finding, scan_directory
from ..core.models import IncidentContext
from ..core.prompts import SecurityPromptBundle

if TYPE_CHECKING:
    from ..core.engine import HeuristicSecurityLLM


class CodeRemediationEngine:
    def __init__(self, ai_engine: "HeuristicSecurityLLM" | None = None) -> None:
        if ai_engine is None:
            from ..core.engine import HeuristicSecurityLLM
            self.ai_engine = HeuristicSecurityLLM()
        else:
            self.ai_engine = ai_engine

    def scan_repo(self, repo_path: str) -> List[Finding]:
        """Scan a repository for vulnerabilities."""
        return scan_directory(repo_path)

    def generate_fix(self, finding: Finding) -> str:
        """Use the AI backend to generate a code patch for a finding."""
        # For simplicity, we are going to formulate a prompt for the AI backend.
        # Since our models are tuned for incident triage, we'll format the finding as an incident
        # and ask it to provide a fixed code snippet.
        
        prompt_text = (
            f"Vulnerability found in {finding.file_path} at line {finding.line_number}.\n"
            f"Type: {finding.vulnerability_type}\n"
            f"Severity: {finding.severity}\n"
            f"Code:\n```\n{finding.code_snippet}\n```\n"
            "Please provide ONLY the fixed code snippet without markdown formatting."
        )

        incident = IncidentContext(
            incident_id="remediation",
            company="System",
            host="localhost",
            asset_id=finding.file_path,
            hour_of_day=12,
            risk_score=90,
            labels=["VULNERABILITY", finding.vulnerability_type.upper().replace(" ", "_")],
            summary=f"Fixing {finding.vulnerability_type} in {finding.file_path}"
        )
        
        bundle = SecurityPromptBundle(
            system_prompt="You are an expert security engineer. You must provide ONLY the fixed code for the vulnerability shown. No explanations, no markdown blocks.",
            user_prompt=prompt_text,
            messages=(),
            retrieved_context=()
        )
        
        # We invoke generate directly on the backend to avoid the structured JSON response logic
        backend = self.ai_engine._default_backend()
        draft = backend.generate(bundle, incident)
        
        # We will assume the reasoning contains the code, as the draft classification might not be right for code.
        return draft.reasoning.strip()

    def create_pull_request(self, repo_path: str, findings: List[Finding]) -> str:
        """Creates a git branch, applies fixes, commits, pushes, and opens a PR."""
        if not findings:
            return "No vulnerabilities found."

        branch_name = "agrus-security-remediation"
        
        # Git operations
        try:
            subprocess.run(["git", "checkout", "-b", branch_name], cwd=repo_path, check=True, capture_output=True)
        except subprocess.CalledProcessError:
            subprocess.run(["git", "checkout", branch_name], cwd=repo_path, check=True, capture_output=True)

        for finding in findings:
            fix = self.generate_fix(finding)
            if not fix or fix == finding.code_snippet:
                continue
                
            # Apply fix (very naive string replacement for now)
            try:
                with open(finding.file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                content = content.replace(finding.code_snippet, fix)
                
                with open(finding.file_path, "w", encoding="utf-8") as f:
                    f.write(content)
            except Exception as e:
                print(f"Failed to apply fix for {finding.file_path}: {e}")

        # Commit and push
        try:
            subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", "Security: Fix identified vulnerabilities [AGRUS AI]"], cwd=repo_path, check=True, capture_output=True)
            # Assuming origin exists
            subprocess.run(["git", "push", "-u", "origin", branch_name], cwd=repo_path, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            return f"Git operation failed: {e.stderr.decode()}"

        # Create PR via GitHub API
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            return f"Fixes committed to branch {branch_name}, but GITHUB_TOKEN not set so no PR was created."

        # Try to infer owner/repo from git remote
        try:
            remote_url = subprocess.check_output(["git", "remote", "get-url", "origin"], cwd=repo_path).decode().strip()
            # e.g. git@github.com:owner/repo.git or https://github.com/owner/repo.git
            match = re.search(r'github\.com[:/](.+)/(.+?)(\.git)?$', remote_url)
            if not match:
                return f"Could not infer GitHub repo from remote: {remote_url}"
            owner, repo = match.group(1), match.group(2)
        except Exception:
            return "Could not determine git remote."

        url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        data = {
            "title": "Security: Auto-remediation by AGRUS AI",
            "head": branch_name,
            "base": "main", # hardcoded base for now
            "body": "This PR was automatically generated by AGRUS Security AI to fix identified vulnerabilities."
        }
        
        req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers, method='POST')
        try:
            with urllib.request.urlopen(req) as response:
                res_data = json.loads(response.read().decode())
                return res_data.get("html_url", "PR created successfully.")
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode()
            return f"GitHub API Error: {e.code} - {err_msg}"
        except Exception as e:
            return f"Error creating PR: {str(e)}"
