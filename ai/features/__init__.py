"""Feature modules — UEBA baselines, APT correlation, container security, vulnerability scanning, and code remediation."""
from .baselines import BaselineEngine, EntityBaseline
from .container import list_containers, quarantine_container, kill_container, get_container_for_pid
from .correlation import CorrelationEngine, CorrelatedIncident
from .scanners import PythonScanner, JavaScriptScanner, Finding, scan_directory
from .remediation import CodeRemediationEngine
