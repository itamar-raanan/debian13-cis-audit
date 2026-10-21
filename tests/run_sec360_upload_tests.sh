#!/usr/bin/env bash
set -euo pipefail

test_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
test_tmp_dir="$(mktemp -d)"
port_file="${test_tmp_dir}/port"
request_log="${test_tmp_dir}/requests.jsonl"
ansible_log="${test_tmp_dir}/ansible.log"
report_file="${test_tmp_dir}/cis_report_test-host.json"

cleanup() {
  if [[ -n "${server_pid:-}" ]]; then
    kill "${server_pid}" 2>/dev/null || true
    wait "${server_pid}" 2>/dev/null || true
  fi
  rm -rf "${test_tmp_dir}"
}
trap cleanup EXIT

printf '%s\n' '{"schema_version":"1.1","host":"test-host","results":[]}' > "${report_file}"
python3 "${test_root}/tests/mock_sec360_server.py" \
  --port-file "${port_file}" \
  --log-file "${request_log}" &
server_pid=$!

for _attempt in {1..50}; do
  [[ -s "${port_file}" ]] && break
  sleep 0.1
done
[[ -s "${port_file}" ]]

if [[ -f /etc/ssl/certs/ca-certificates.crt ]]; then
  test_ca_path=/etc/ssl/certs/ca-certificates.crt
elif [[ -f /etc/ssl/cert.pem ]]; then
  test_ca_path=/etc/ssl/cert.pem
else
  echo "No system CA bundle is available for the custom-CA scenario." >&2
  exit 1
fi

export SEC360_TEST_BASE_URL="http://127.0.0.1:$(<"${port_file}")"
export SEC360_TEST_REPORT_PATH="${report_file}"
export SEC360_TEST_CA_PATH="${test_ca_path}"

ansible-playbook "${test_root}/tests/sec360_upload.yml" \
  -i localhost, \
  -c local \
  -vvv 2>&1 | tee "${ansible_log}"

for protected_token in \
  SEC360_TEST_SECRET_DO_NOT_PRINT \
  duplicate-token \
  retry-token \
  custom-ca-token \
  disabled-token \
  json-disabled-token \
  validation-token; do
  if grep -Fq "${protected_token}" "${ansible_log}"; then
    echo "Authorization token leaked into Ansible output." >&2
    exit 1
  fi
done

python3 "${test_root}/tests/assert_sec360_requests.py" "${request_log}"
