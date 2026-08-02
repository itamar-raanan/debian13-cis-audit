# Debian 13 CIS Audit & Remediation

## Overview

This project provides a complete **CIS Debian Linux 13 Benchmark** audit
and optional remediation using Ansible.

### Features

-   Audit-only mode
-   Remediation-only mode
-   Audit → Remediate → Audit workflow
-   Level 1 and Level 2 profiles
-   Correct Level 2 profile inheritance (Level 2 includes Level 1)
-   HTML, CSV and JSON reports
-   Timestamped reports per host
-   Searchable HTML dashboard
-   Action-oriented remediation guidance
-   Manual action reporting
-   Safe defaults (potentially disruptive changes disabled unless
    explicitly enabled)

------------------------------------------------------------------------

# Requirements

-   macOS / Linux control node
-   Ansible Core 2.16+
-   Python 3
-   sshpass (only if using password authentication)

macOS:

``` bash
brew install ansible
brew install sshpass
```

------------------------------------------------------------------------

# Project layout

``` text
audit.yml
remediate.yml
site.yml
inventory.ini

roles/
  cis_debian13_audit/
  cis_debian13_remediate/

reports/
```

------------------------------------------------------------------------

# Inventory example

``` ini
[debian13]
server1 ansible_host=192.168.1.10

[debian13:vars]
ansible_user=user
ansible_password=USER_PASSWORD

ansible_become=true
ansible_become_method=su
ansible_become_user=root
ansible_become_password=ROOT_PASSWORD
```

------------------------------------------------------------------------

# Validate

``` bash
ansible-playbook -i inventory.ini audit.yml --syntax-check
```

Connectivity:

``` bash
ansible -i inventory.ini all -m command -a "whoami" --become
```

Expected:

``` text
root
```

------------------------------------------------------------------------

# Audit

Level 1:

``` bash
ansible-playbook -i inventory.ini audit.yml -e cis_profile=level1_server
```

Level 2 (includes Level 1 automatically):

``` bash
ansible-playbook -i inventory.ini audit.yml -e cis_profile=level2_server
```

------------------------------------------------------------------------

# Remediation

Preview only:

``` bash
ansible-playbook -i inventory.ini remediate.yml \
  -e cis_profile=level2_server \
  -e cis_remediation_enabled=true \
  -e cis_remediation_confirm=true \
  --check --diff
```

Apply:

``` bash
ansible-playbook -i inventory.ini remediate.yml \
  -e cis_profile=level2_server \
  -e cis_remediation_enabled=true \
  -e cis_remediation_confirm=true
```

Audit → Remediate → Audit:

``` bash
ansible-playbook -i inventory.ini site.yml \
  -e cis_profile=level2_server \
  -e cis_remediation_enabled=true \
  -e cis_remediation_confirm=true
```

------------------------------------------------------------------------

# Reports

Reports are generated under:

``` text
reports/<hostname>/
```

Example:

``` text
reports/web01/
├── cis_report_web01_20260802_113500.html
├── cis_report_web01_20260802_113500.csv
└── cis_report_web01_20260802_113500.json
```

The HTML report includes:

-   Dashboard summary
-   Pass/fail statistics
-   Search
-   Status filters
-   Action Items filter
-   Expected state
-   Evidence
-   "What You Need To Do"
-   Expandable detailed remediation

------------------------------------------------------------------------

# Safety

The following options are disabled by default because they may interrupt
access or services:

-   SSH configuration
-   PAM changes
-   Firewall policy
-   Network configuration
-   Bootloader changes
-   Partition changes
-   Package upgrades
-   Automatic reboot

Enable only after testing in a non-production environment.

------------------------------------------------------------------------

# Troubleshooting

## sshpass missing

``` bash
brew install sshpass
```

## Incorrect sudo password

If using a non-root SSH account with the root password:

``` ini
ansible_become=true
ansible_become_method=su
ansible_become_user=root
```

## Syntax check

``` bash
ansible-playbook -i inventory.ini audit.yml --syntax-check
```

------------------------------------------------------------------------

# Recommended workflow

1.  Run the audit.
2.  Review the HTML report.
3.  Filter to **Action Items**.
4.  Review each remediation.
5.  Run remediation in `--check --diff`.
6.  Apply remediation.
7.  Run the audit again and compare results.
