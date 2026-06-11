from unittest import TestCase
import os
import tempfile
from ai.features.scanners import PythonScanner

class ScannerTests(TestCase):
    def test_sql_injection_false_positives(self):
        scanner = PythonScanner()
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))\n')
            f.write('cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")\n')
            filepath = f.name
        
        try:
            findings = scanner.scan(filepath)
            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0].vulnerability_type, "SQL Injection")
            self.assertIn("f\"SELECT", findings[0].code_snippet)
        finally:
            os.remove(filepath)

    def test_hardcoded_secrets_false_positives(self):
        scanner = PythonScanner()
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('api_key = "AIzaSyB_dummy_key_here_for_testing"\n')
            f.write('print(f"The api_key is missing")\n')
            f.write('logger.info("Found secret token")\n')
            filepath = f.name
        
        try:
            findings = scanner.scan(filepath)
            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0].vulnerability_type, "Hardcoded Secret")
            self.assertIn("AIzaSyB", findings[0].code_snippet)
        finally:
            os.remove(filepath)
