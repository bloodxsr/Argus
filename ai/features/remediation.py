from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.request
import urllib.error
from typing import List, Dict, Any, Tuple, TYPE_CHECKING

from .scanners import Finding, scan_directory
from ..core.backends import HeuristicSecurityBackend
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
        backend = self.ai_engine.backend
        if isinstance(backend, HeuristicSecurityBackend):
            return ""

        prompt_text = (
            "Patch the vulnerable code snippet below. You must return a valid JSON object with a single key 'reasoning'. "
            "The value of 'reasoning' must contain ONLY the complete patched code snippet, "
            "with no markdown fences, no prose, and no threat analysis.\n\n"
            f"File: {finding.file_path}\n"
            f"Line: {finding.line_number}\n"
            f"Vulnerability: {finding.vulnerability_type}\n"
            f"Severity: {finding.severity}\n"
            f"Original code:\n{finding.code_snippet}"
        )

        incident = IncidentContext(
            incident_id="remediation",
            company="System",
            host="localhost",
            asset_id=finding.file_path,
            hour_of_day=12,
            risk_score=90,
            labels=("CODE_REMEDIATION", finding.vulnerability_type.upper().replace(" ", "_")),
            summary=f"Generate patched code for {finding.vulnerability_type} in {finding.file_path}",
        )

        bundle = SecurityPromptBundle(
            system_prompt="You are a secure code remediation engine. You must return a valid JSON object with a 'reasoning' key containing ONLY the patched source code.",
            user_prompt=prompt_text,
            messages=(
                {"role": "system", "content": "You must return a valid JSON object with a 'reasoning' key containing the patched code."},
                {"role": "user", "content": prompt_text},
            ),
            retrieved_context=(),
        )

        draft = backend.generate(bundle, incident)
        if "llm_inference" not in draft.reasoning_layers:
            return ""
        return draft.reasoning.strip()

    def create_pull_request(self, repo_path: str, findings: List[Finding]) -> str:
        """
        Creates a git branch, applies fixes, commits, pushes, and opens a PR.
        
        WARNING: This mutates the target repository in place by modifying files
        and running git commands.
        """
        if not findings:
            return "No vulnerabilities found."

        allowed_dirs = os.getenv("AGRUS_ALLOWED_REPOSITORIES_DIR", "/opt/agrus/repos")
        if not os.path.abspath(repo_path).startswith(os.path.abspath(allowed_dirs)):
            return "Error: Repository path is outside of allowed directories."

        branch_name = "agrus-security-remediation"
        
        
        try:
            subprocess.run(["git", "checkout", "-b", branch_name], cwd=repo_path, check=True, capture_output=True)
        except subprocess.CalledProcessError:
            subprocess.run(["git", "checkout", branch_name], cwd=repo_path, check=True, capture_output=True)

        for finding in findings:
            fix = self.generate_fix(finding)
            if not fix or fix == finding.code_snippet:
                continue
                
            
            try:
                with open(finding.file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                
                
                target_idx = finding.line_number - 1
                if 0 <= target_idx < len(lines):
                    
                    
                    
                    lines[target_idx] = lines[target_idx].replace(finding.code_snippet, fix)
                
                with open(finding.file_path, "w", encoding="utf-8") as f:
                    f.writelines(lines)
            except Exception as e:
                print(f"Failed to apply fix for {finding.file_path}: {e}")

        
        try:
            subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", "Security: Fix identified vulnerabilities [AGRUS AI]"], cwd=repo_path, check=True, capture_output=True)
            if os.getenv("AGRUS_REMEDIATION_AUTO_PUSH") == "true":
                
                subprocess.run(["git", "push", "-u", "origin", branch_name], cwd=repo_path, check=True, capture_output=True)
            else:
                return f"Fixes committed locally to branch {branch_name}. Set AGRUS_REMEDIATION_AUTO_PUSH=true to push automatically."
        except subprocess.CalledProcessError as e:
            return f"Git operation failed: {e.stderr.decode()}"

        
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            return f"Fixes committed to branch {branch_name}, but GITHUB_TOKEN not set so no PR was created."

        
        try:
            remote_url = subprocess.check_output(["git", "remote", "get-url", "origin"], cwd=repo_path).decode().strip()
            
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
            "base": "master", 
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
