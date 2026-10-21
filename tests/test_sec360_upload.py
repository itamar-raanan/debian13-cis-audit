#!/usr/bin/env python3
"""Static compatibility and security checks for optional SEC360 upload."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
DEFAULTS = (ROOT / "roles/cis_debian13_audit/defaults/main.yml").read_text()
REPORT_TASKS = (ROOT / "roles/cis_debian13_audit/tasks/report.yml").read_text()
UPLOAD_TASKS = (ROOT / "roles/cis_debian13_audit/tasks/sec360_upload.yml").read_text()


class Sec360UploadTests(unittest.TestCase):
    def test_safe_defaults(self):
        expected = (
            "cis_sec360_upload_enabled: false",
            'cis_sec360_url: ""',
            'cis_sec360_token: ""',
            "cis_sec360_validate_certs: true",
            'cis_sec360_ca_path: ""',
        )
        for setting in expected:
            self.assertIn(setting, DEFAULTS)

    def test_json_writer_and_uploader_share_one_path(self):
        self.assertIn("cis_report_json_path:", REPORT_TASKS)
        self.assertIn('dest: "{{ cis_report_json_path }}"', REPORT_TASKS)
        self.assertIn('src: "{{ cis_report_json_path }}"', UPLOAD_TASKS)
        self.assertEqual(REPORT_TASKS.count("cis_report_json_path }}"), 1)

    def test_upload_is_guarded_by_enable_format_and_generation_success(self):
        for condition in (
            "cis_sec360_upload_enabled | bool",
            "'json' in cis_report_formats",
            "cis_json_report is defined",
            "cis_json_report is succeeded",
            "not (cis_json_report.skipped | default(false))",
        ):
            self.assertIn(condition, UPLOAD_TASKS)
        self.assertIn("register: cis_json_report", REPORT_TASKS)

    def test_raw_json_request_contract(self):
        for setting in (
            "ansible.builtin.uri:",
            "method: POST",
            "/api/linux-audits/ingest",
            "Content-Type: application/json",
            "X-Report-Filename:",
            "Authorization: \"Bearer {{ cis_sec360_token }}\"",
            "status_code:",
            "- 200",
            "- 201",
            "retries: 3",
            "delay: 5",
            "delegate_to: localhost",
            "become: false",
        ):
            self.assertIn(setting, UPLOAD_TASKS)
        self.assertNotIn("body_format:", UPLOAD_TASKS)
        self.assertNotIn("multipart", UPLOAD_TASKS.lower())

    def test_optional_ca_and_certificate_validation(self):
        self.assertIn("validate_certs: \"{{ cis_sec360_validate_certs | bool }}\"", UPLOAD_TASKS)
        self.assertIn("cis_sec360_ca_path", UPLOAD_TASKS)
        self.assertIn("else omit", UPLOAD_TASKS)

    def test_token_is_protected_and_not_hardcoded(self):
        self.assertIn("no_log: true", UPLOAD_TASKS)
        self.assertNotIn("cis_sec360_token: Bearer", DEFAULTS)
        self.assertNotIn("SEC360_LINUX_AUDIT_TOKEN", DEFAULTS)

    def test_missing_url_and_token_have_clear_validation_errors(self):
        self.assertIn("cis_sec360_url is empty", UPLOAD_TASKS)
        self.assertIn("cis_sec360_token is empty", UPLOAD_TASKS)
        self.assertGreaterEqual(UPLOAD_TASKS.count("ansible.builtin.assert:"), 2)


if __name__ == "__main__":
    unittest.main()
