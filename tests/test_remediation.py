from unittest import TestCase
from unittest.mock import patch, mock_open
import os
from ai.features.remediation import CodeRemediationEngine
from ai.features.scanners import Finding

class RemediationTests(TestCase):
    @patch('os.getenv')
    def test_remediation_blocks_unauthorized_paths(self, mock_getenv):
        mock_getenv.return_value = "/opt/agrus/repos"
        engine = CodeRemediationEngine()
        
        # Creating a finding to test the repo_path check
        findings = [
            Finding(file_path="/tmp/evil_repo/main.py", line_number=1, vulnerability_type="SQL Injection", severity="HIGH", code_snippet="")
        ]
        
        result = engine.create_pull_request("/tmp/evil_repo", findings)
        self.assertIn("Error: Repository path is outside of allowed directories", result)

    @patch('os.getenv')
    @patch('ai.features.remediation.CodeRemediationEngine.generate_fix')
    @patch('subprocess.run')
    def test_remediation_line_specific_replacement(self, mock_run, mock_generate_fix, mock_getenv):
        mock_getenv.return_value = "/opt/agrus/repos"
        mock_generate_fix.return_value = 'cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))'
        
        engine = CodeRemediationEngine()
        findings = [
            Finding(
                file_path="/opt/agrus/repos/test_repo/main.py", 
                line_number=2, 
                vulnerability_type="SQL Injection", 
                severity="HIGH", 
                code_snippet='cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")'
            )
        ]
        
        m_open = mock_open(read_data='import db\ncursor.execute(f"SELECT * FROM users WHERE id = {user_id}")\nprint("done")\n')
        with patch('builtins.open', m_open):
            # Also mock the return of write
            result = engine.create_pull_request("/opt/agrus/repos/test_repo", findings)
        
        # Verify that only the second line is replaced
        handle = m_open()
        written_lines = []
        for call in handle.writelines.call_args_list:
            written_lines.extend(call[0][0])
            
        if written_lines:
            self.assertIn('cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))', written_lines[1])
