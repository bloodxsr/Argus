from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import List


@dataclass
class Finding:
    file_path: str
    line_number: int
    vulnerability_type: str
    severity: str
    code_snippet: str
    suggested_fix: str = ""


class ScannerProtocol:
    def scan(self, file_path: str) -> List[Finding]:
        raise NotImplementedError


class PythonScanner(ScannerProtocol):
    def scan(self, file_path: str) -> List[Finding]:
        findings = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception:
            return []

        for i, line in enumerate(lines):
            line_num = i + 1
            # Check for command injection
            if re.search(r'(os\.system|subprocess\.(Popen|run|call)).*shell\s*=\s*True', line) or re.search(r'os\.popen\(', line):
                findings.append(Finding(
                    file_path=file_path,
                    line_number=line_num,
                    vulnerability_type="Command Injection",
                    severity="CRITICAL",
                    code_snippet=line.strip()
                ))
            # Check for insecure deserialization
            if re.search(r'pickle\.loads\(', line):
                findings.append(Finding(
                    file_path=file_path,
                    line_number=line_num,
                    vulnerability_type="Insecure Deserialization",
                    severity="CRITICAL",
                    code_snippet=line.strip()
                ))
            # Check for hardcoded secrets
            if re.search(r'(api_key|password|secret|token)\s*=\s*["\'][A-Za-z0-9_\-]+["\']', line, re.IGNORECASE):
                findings.append(Finding(
                    file_path=file_path,
                    line_number=line_num,
                    vulnerability_type="Hardcoded Secret",
                    severity="HIGH",
                    code_snippet=line.strip()
                ))
            # Check for SQL injection (basic string formatting in execute)
            if re.search(r'\.execute\(.*(%s|\{.*\}|%|\+)', line):
                findings.append(Finding(
                    file_path=file_path,
                    line_number=line_num,
                    vulnerability_type="SQL Injection",
                    severity="HIGH",
                    code_snippet=line.strip()
                ))

        return findings


class JavaScriptScanner(ScannerProtocol):
    def scan(self, file_path: str) -> List[Finding]:
        findings = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception:
            return []

        for i, line in enumerate(lines):
            line_num = i + 1
            # Check for eval()
            if re.search(r'\beval\(', line):
                findings.append(Finding(
                    file_path=file_path,
                    line_number=line_num,
                    vulnerability_type="eval() Usage",
                    severity="CRITICAL",
                    code_snippet=line.strip()
                ))
            # Check for prototype pollution
            if re.search(r'__proto__|constructor\.prototype', line):
                findings.append(Finding(
                    file_path=file_path,
                    line_number=line_num,
                    vulnerability_type="Prototype Pollution",
                    severity="HIGH",
                    code_snippet=line.strip()
                ))
            # Check for path traversal
            if re.search(r'path\.join\(.*req\.', line) or re.search(r'fs\.readFile\(.*req\.', line):
                findings.append(Finding(
                    file_path=file_path,
                    line_number=line_num,
                    vulnerability_type="Path Traversal",
                    severity="HIGH",
                    code_snippet=line.strip()
                ))

        return findings


def scan_directory(directory_path: str) -> List[Finding]:
    all_findings = []
    py_scanner = PythonScanner()
    js_scanner = JavaScriptScanner()

    for root, _, files in os.walk(directory_path):
        for file in files:
            file_path = os.path.join(root, file)
            if file.endswith(".py"):
                all_findings.extend(py_scanner.scan(file_path))
            elif file.endswith((".js", ".jsx", ".ts", ".tsx")):
                all_findings.extend(js_scanner.scan(file_path))

    return all_findings
