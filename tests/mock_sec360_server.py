#!/usr/bin/env python3
"""Minimal local SEC360 endpoint used by the Ansible integration scenarios."""

import argparse
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path


class Sec360Handler(BaseHTTPRequestHandler):
    request_counts = {}
    log_path = None

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length)
        authorization = self.headers.get("Authorization", "")
        token = authorization[7:] if authorization.startswith("Bearer ") else ""
        scenario = {
            "SEC360_TEST_SECRET_DO_NOT_PRINT": "created",
            "duplicate-token": "duplicate",
            "retry-token": "retry",
            "custom-ca-token": "custom_ca",
        }.get(token, "unknown")
        request_number = self.request_counts.get(scenario, 0) + 1
        self.request_counts[scenario] = request_number

        valid_json = True
        try:
            json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            valid_json = False

        valid_request = (
            self.path == "/api/linux-audits/ingest"
            and self.headers.get("Content-Type") == "application/json"
            and bool(self.headers.get("X-Report-Filename"))
            and authorization.startswith("Bearer ")
            and valid_json
        )

        if not valid_request:
            status = 422
        elif scenario == "duplicate":
            status = 200
        elif scenario == "retry" and request_number == 1:
            status = 503
        else:
            status = 201

        event = {
            "scenario": scenario,
            "request_number": request_number,
            "status": status,
            "path": self.path,
            "content_type": self.headers.get("Content-Type", ""),
            "filename": self.headers.get("X-Report-Filename", ""),
            "authorization_present": authorization.startswith("Bearer "),
            "body_sha256": hashlib.sha256(body).hexdigest(),
        }
        with self.log_path.open("a", encoding="utf-8") as log_file:
            log_file.write(json.dumps(event, sort_keys=True) + "\n")

        response = json.dumps({"accepted": status in (200, 201), "status": status}).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, _format, *_args):
        return


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port-file", required=True, type=Path)
    parser.add_argument("--log-file", required=True, type=Path)
    args = parser.parse_args()

    Sec360Handler.log_path = args.log_file
    server = ThreadingHTTPServer(("127.0.0.1", 0), Sec360Handler)
    args.port_file.write_text(str(server.server_port), encoding="utf-8")
    server.serve_forever()


if __name__ == "__main__":
    main()
