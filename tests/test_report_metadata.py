#!/usr/bin/env python3
"""Static compatibility and security checks for report metadata generation."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
TASKS = (ROOT / "roles/cis_debian13_audit/tasks/report.yml").read_text()
DEFAULTS = (ROOT / "roles/cis_debian13_audit/defaults/main.yml").read_text()
JSON_TEMPLATE = (ROOT / "roles/cis_debian13_audit/templates/report.json.j2").read_text()
CSV_TEMPLATE = (ROOT / "roles/cis_debian13_audit/templates/report.csv.j2").read_text()
HTML_TEMPLATE = (ROOT / "roles/cis_debian13_audit/templates/report.html.j2").read_text()


class ReportMetadataTests(unittest.TestCase):
    def test_json_keeps_existing_top_level_fields_and_adds_metadata(self):
        for field in (
            "host",
            "benchmark",
            "profile",
            "generated_at",
            "summary",
            "results",
            "schema_version",
            "fqdn",
            "ip_address",
            "ip_addresses",
            "system",
            "audit_tool",
        ):
            self.assertIn(f"'{field}':", JSON_TEMPLATE)

        for field in (
            "distribution",
            "distribution_version",
            "kernel",
            "architecture",
            "virtualization_type",
            "machine_id_hash",
            "version",
            "git_commit",
        ):
            self.assertIn(f"'{field}':", JSON_TEMPLATE)

        self.assertIn("| to_nice_json", JSON_TEMPLATE)
        self.assertIn('cis_report_schema_version: "1.1"', DEFAULTS)
        self.assertIn('cis_audit_tool_version: "1.1.0"', DEFAULTS)

    def test_primary_ip_prefers_default_route_and_rejects_loopback(self):
        self.assertIn("ansible_default_ipv4", TASKS)
        self.assertIn("ansible_all_ipv4_addresses", TASKS)
        self.assertIn("reject('match', '^127\\\\.')", TASKS)
        self.assertIn("not cis_report_default_ipv4_address.startswith('127.')", TASKS)
        self.assertLess(
            TASKS.index("cis_report_default_ipv4_address\n        if"),
            TASKS.index("else cis_report_ip_addresses | first | default('')"),
        )

    def test_machine_id_is_hashed_and_git_metadata_is_best_effort(self):
        self.assertIn("sha256sum", TASKS)
        self.assertIn("/etc/machine-id", TASKS)
        self.assertIn("cis_report_machine_id_hash", TASKS)
        self.assertIn("rev-parse", TASKS)
        self.assertGreaterEqual(TASKS.count("failed_when: false"), 2)
        self.assertNotIn("slurp:", TASKS)
        self.assertNotIn("lookup('env'", TASKS)

    def test_missing_metadata_uses_empty_values(self):
        for fact in (
            "ansible_fqdn",
            "ansible_distribution",
            "ansible_distribution_version",
            "ansible_kernel",
            "ansible_architecture",
            "ansible_virtualization_type",
        ):
            self.assertIn(f"{fact} | default('', true)", TASKS)
        self.assertIn("else ''", TASKS)

    def test_report_templates_do_not_reference_authentication_secrets(self):
        report_templates = JSON_TEMPLATE + CSV_TEMPLATE + HTML_TEMPLATE
        for forbidden in (
            "ansible_password",
            "ansible_become_password",
            "private_key",
            "ansible_env",
            "lookup('env'",
            "ansible_machine_id",
            "/etc/machine-id",
        ):
            self.assertNotIn(forbidden, report_templates)

    def test_csv_keeps_control_columns_and_appends_identity_columns(self):
        header = CSV_TEMPLATE.splitlines()[0]
        self.assertEqual(
            header,
            "id,title,status,expected,how_to_check,how_to_review,actual,remediation,"
            "hostname,fqdn,ip_address,os_distribution,os_version,kernel,architecture,"
            "profile,generated_at",
        )
        self.assertIn("cis_report_hostname", CSV_TEMPLATE)
        self.assertIn("cis_report_generated_at", CSV_TEMPLATE)

    def test_html_header_contains_only_escaped_metadata(self):
        metadata = {
            "Hostname": "cis_report_hostname",
            "FQDN": "cis_report_fqdn",
            "Primary IP": "cis_report_ip_address",
            "Kernel": "cis_report_kernel",
            "Architecture": "cis_report_architecture",
            "Virtualization": "cis_report_virtualization_type",
            "Profile": "cis_profile",
            "Audit tool": "cis_audit_tool_version",
            "Generated": "cis_report_generated_at",
        }
        for label, variable in metadata.items():
            self.assertIn(f"<strong>{label}:</strong>", HTML_TEMPLATE)
            self.assertIn(f"{{{{ {variable} | e }}}}", HTML_TEMPLATE)

        self.assertIn("{{ cis_report_distribution | e }}", HTML_TEMPLATE)
        self.assertIn("{{ cis_report_distribution_version | e }}", HTML_TEMPLATE)
        self.assertIn('id="resultsTable"', HTML_TEMPLATE)
        self.assertIn('id="statusFilter"', HTML_TEMPLATE)
        self.assertIn("Show collected evidence", HTML_TEMPLATE)
        self.assertIn("Show remediation steps", HTML_TEMPLATE)


if __name__ == "__main__":
    unittest.main()
