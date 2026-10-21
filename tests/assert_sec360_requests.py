#!/usr/bin/env python3
"""Validate requests captured by the local SEC360 integration-test server."""

from collections import defaultdict
import json
from pathlib import Path
import sys


events = [json.loads(line) for line in Path(sys.argv[1]).read_text().splitlines()]
by_scenario = defaultdict(list)
for event in events:
    by_scenario[event["scenario"]].append(event)
    assert event["path"] == "/api/linux-audits/ingest"
    assert event["content_type"] == "application/json"
    assert event["filename"] == "cis_report_test-host.json"
    assert event["authorization_present"] is True
    assert len(event["body_sha256"]) == 64

assert [event["status"] for event in by_scenario["created"]] == [201]
assert [event["status"] for event in by_scenario["duplicate"]] == [200]
assert [event["status"] for event in by_scenario["retry"]] == [503, 201]
assert [event["status"] for event in by_scenario["custom_ca"]] == [201]
assert "unknown" not in by_scenario
assert len(events) == 5
