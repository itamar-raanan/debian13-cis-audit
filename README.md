# CIS Debian Linux 13 Audit

Audit-only Ansible role targeting **CIS Debian Linux 13 Benchmark v1.0.0**.

## Current coverage

- Project framework and Debian 13 preflight validation
- Four CIS profiles
- JSON, CSV, and HTML reporting
- Documented control exceptions
- Section 1.1.1: controls 1.1.1.1 through 1.1.1.10
- Section 1.1.2: all 26 filesystem partition and mount-option controls

The role performs no remediation. Audit commands use `changed_when: false` and failures are captured in the report.

## Requirements

- Ansible Core 2.15+
- Target: Debian 13
- `findmnt`, `systemctl`, `modprobe`, and `lsmod` on the target
- Privilege escalation to root

## Run

```bash
ansible-playbook -i inventory.ini audit.yml -e cis_profile=level1_server
```

Run all current Section 1 checks:

```bash
ansible-playbook -i inventory.ini audit.yml --tags section_1
```

Run filesystem partition checks:

```bash
ansible-playbook -i inventory.ini audit.yml --tags section_1_1_2
```

Run one control:

```bash
ansible-playbook -i inventory.ini audit.yml --tags cis_1_1_2_1_1
```

Reports are written to `reports/` on the Ansible controller.

## Profiles

- `level1_server`
- `level2_server`
- `level1_workstation`
- `level2_workstation`

Level 2 profiles include applicable Level 1 checks.

## Result statuses

- `PASS`
- `FAIL`
- `ERROR`
- `EXCLUDED`
- `NOT_APPLICABLE`

All controls currently included by the role have an automated execution path.

## Exceptions

Add documented exceptions in `group_vars/all.yml`:

```yaml
cis_exceptions:
  '1.1.1.6': 'OverlayFS is required by the container platform.'
  '1.1.2.1.4': 'Application requires executable files under /tmp.'
```

An exception is reported as `EXCLUDED`; it is not counted as a pass.

## Policy-driven automated controls

Some CIS recommendations depend on an organization-approved value rather than
a universal value. For a single policy, configure the inputs in
`group_vars/all.yml`. For separate environments, copy the supplied example:

```bash
cp environments/example.yml environments/local.yml
ansible-playbook -i inventory.ini audit.yml \
  -e @environments/local.yml
```

`environments/local.yml` is ignored by Git. You can instead create and commit
named non-secret policies such as `environments/production.yml` when the same
policy should be shared by the team.

Use `cis_control_expectations` to replace the expected-state text displayed in
the report for any control:

```yaml
cis_control_expectations:
  '1.2.1.1': >-
    Every active APT repository uses the company Artifactory service and a
    repository-specific Signed-By key.
```

Expectation text documents the policy but does not by itself affect PASS/FAIL.
Set the corresponding policy variable to enforce it. Available policy inputs
include:

- `cis_unused_filesystem_modules` lists additional filesystem modules that the
  host does not need. Control `1.1.1.11` is `NOT_APPLICABLE` when the list is
  empty because the role cannot infer business use.
- `cis_approved_apt_repository_patterns` contains regular expressions for
  approved APT URIs. Control `1.2.1.1` requires every active repository to
  match one of these patterns and to use `Signed-By`. URI approval matching is
  disabled when the list is empty.
- `cis_approved_tcp_listening_ports` and
  `cis_approved_udp_listening_ports` define the non-loopback listeners allowed
  by control `2.1.23`.
- `cis_password_min_days` supplies the organization minimum for control
  `5.4.1.2`.
- `cis_journald_rotation_policy` supplies the required effective journald size
  and retention values for control `6.1.1.1.3`.
- `cis_suid_sgid_review_mode` selects package ownership or an explicit
  allowlist for control `7.1.13`. Use `cis_approved_suid_sgid_files` for locally
  approved binaries.

These checks are audit-only. They collect evidence and return PASS, FAIL,
NOT_APPLICABLE, or ERROR without changing the target.

## Audit behavior for mount controls

Mount-point checks use an exact `findmnt -M` lookup, so a directory inherited from `/` does not count as a separate filesystem. Mount-option checks inspect the active mount options. Control 1.1.2.1.1 also verifies that `tmp.mount` is not disabled or masked.

## Milestone 3 coverage

Milestone 3 adds CIS sections **1.2 Package Management** and **1.3 Mandatory Access Control**:

- 1.2.1.1 through 1.2.1.9
- 1.2.2.1
- 1.3.1.1 through 1.3.1.4

The Signed-By and pending-update recommendations are automated. The update
check uses the target's current APT metadata and never runs `apt update` or
modifies package metadata.

Run the new sections:

```bash
ansible-playbook -i inventory.ini audit.yml -e cis_profile=level1_server --tags section_1_2
ansible-playbook -i inventory.ini audit.yml -e cis_profile=level2_server --tags section_1_3
```


## Milestone 4 additions

This cumulative release adds CIS sections **1.4 Configure Bootloader** and **1.5 Configure Additional Process Hardening**. It includes bootloader password and permissions checks, effective runtime/persistent sysctl evaluation, Apport, prelink, core limits, and systemd-coredump checks.

Run only these controls:

```bash
ansible-playbook -i inventory.ini audit.yml -e cis_profile=level1_server --tags section_1_4,section_1_5
```


## Milestone 5 coverage

This cumulative release adds CIS section **1.6 Configure Command Line Warning Banners** (`1.6.1` through `1.6.6`). Banner-content checks detect operating-system disclosure and preserve the benchmark-required local-policy review note in the evidence. File-access checks resolve symbolic links and verify root ownership plus mode `0644` or more restrictive.

Run this section only:

```bash
ansible-playbook -i inventory.ini audit.yml \
  -e cis_profile=level1_server \
  --tags section_1_6
```


## Milestone 7 coverage

Section 2.1 is implemented: controls 2.1.1 through 2.1.23. The service checks pass when the relevant package is absent, or when installed only as a dependency and every listed service/socket is disabled and inactive. Control 2.1.23 compares every non-loopback TCP/UDP listener with the approved port lists in `group_vars/all.yml`.

Run Section 2.1 only:

```bash
ansible-playbook -i inventory.ini audit.yml -e cis_profile=level1_server --tags section_2_1
```

## Milestone 8 coverage

This cumulative release adds CIS section **2.2 Configure Client Services**, controls `2.2.1` through `2.2.6`:

- NIS client
- rsh client
- talk client
- telnet client
- LDAP client utilities
- FTP clients (`ftp` and `tnftp`)

Every check is audit-only and passes only when all packages named by the benchmark are absent.

Run Section 2.2 only:

```bash
ansible-playbook -i inventory.ini audit.yml \
  -e cis_profile=level1_server \
  --tags section_2_2
```

## Milestone 9 coverage

This cumulative release completes CIS **Section 2** by adding:

- `2.3.1.1` through `2.3.3.3` — time synchronization daemon selection, timesyncd, and chrony
- `2.4.1.1` through `2.4.2.1` — cron and at access controls

Conditional recommendations return `NOT_APPLICABLE` when the relevant daemon or package is not in use. The authorized time-server checks verify that a non-empty effective source is configured; approval of the named servers remains governed by local policy.

Run the new controls:

```bash
ansible-playbook -i inventory.ini audit.yml \
  -e cis_profile=level1_server \
  --tags section_2_3,section_2_4
```

## Milestone 10 coverage

This cumulative release implements CIS **Section 3 - Network**:

- `3.1.1` through `3.1.3` - IPv6 status, wireless interfaces, and Bluetooth
- `3.2.1` through `3.2.6` - network protocol kernel modules
- `3.3.1.1` through `3.3.2.8` - IPv4 and IPv6 kernel parameters

Kernel-parameter checks validate both the live value and the effective persistent value resolved through systemd-sysctl configuration precedence. IPv6-only controls return `NOT_APPLICABLE` when IPv6 is disabled.

Run Section 3 only:

```bash
ansible-playbook -i inventory.ini audit.yml \
  -e cis_profile=level1_server \
  --tags section_3
```

## Milestone 11 coverage

This cumulative release implements CIS **Section 4 - Host Based Firewall**, controls `4.1.1` through `4.1.5`:

- UFW package installation
- UFW service enablement and active state
- UFW active status
- Incoming default deny or reject policy
- Outgoing default deny or reject policy for Level 2 profiles
- Routed default disabled or deny policy

All checks are audit-only and preserve the raw `ufw status verbose` output as evidence.

Run Section 4 only:

```bash
ansible-playbook -i inventory.ini audit.yml \
  -e cis_profile=level1_server \
  --tags section_4
```


## Milestone 13

Adds all 23 automated controls in CIS Section 5.1 (Configure SSH Server), including file access, host keys, effective sshd settings, crypto algorithms, post-quantum KEX, session limits, and PAM integration.

Run with:

```bash
ansible-playbook -i inventory.ini audit.yml -e cis_profile=level1_server --tags section_5_1
```


## Milestone 13 coverage

This cumulative release adds all seven automated controls in **Section 5.2 - Configure privilege escalation** (`5.2.1` through `5.2.7`), including sudo installation, pseudo-terminal use, custom logging, password and re-authentication requirements, timestamp timeout, and restricted `su` access.

Run only this subsection:

```bash
ansible-playbook -i inventory.ini audit.yml \
  -e cis_profile=level1_server \
  --tags section_5_2
```

## Milestone 14 coverage

This cumulative release implements **Section 5.3 - Pluggable Authentication Modules**, including PAM packages, module enablement, faillock, pwquality, password history, and pam_unix controls.

## Milestone 15 coverage

This cumulative release completes **Section 5.4 - User Accounts and Environment**:

- `5.4.1.1` through `5.4.1.6` - shadow password suite parameters
- `5.4.2.1` through `5.4.2.8` - root and system accounts and environment
- `5.4.3.1` through `5.4.3.3` - default user environment

Control `5.4.1.2` compares both `PASS_MIN_DAYS` and password-bearing local
accounts with `cis_password_min_days`. All Section 5.4 controls are automated
and audit-only.

Run the subsection:

```bash
ansible-playbook -i inventory.ini audit.yml \
  -e cis_profile=level1_server \
  --tags section_5_4
```


## Coverage update

This cumulative release includes all 333 recommendation IDs listed in CIS
Debian Linux 13 Benchmark v1.0.0. Recommendations classified as manual by the
benchmark now execute deterministic checks, using explicit site-policy inputs
where a local approval decision is required.

## Remediation guidance in reports

Each JSON, CSV, and HTML result now includes a `remediation` field. The HTML report displays it as a dedicated column beside the expected and actual states. Guidance is extracted from the CIS Debian Linux 13 Benchmark v1.0.0 where available.

Remediation text can include commands that alter packages, services, authentication, networking, boot settings, or file permissions. Review applicability, operational impact, backups, approved exceptions, and change-control requirements before applying any command. This role remains audit-only and does not automatically remediate the target.

### Remediation text safety

The remediation catalog is stored in `roles/cis_debian13_audit/vars/main.yml`.
Each remediation value is tagged with Ansible `!unsafe` so shell examples such as
`${#array[@]}` are treated as literal report text and are not parsed by Jinja.

---

# CIS Debian 13 remediation role

This archive now includes `roles/cis_debian13_remediate` and two playbooks:

- `remediate.yml` — remediation only
- `site.yml` — audit, remediation, then post-remediation audit

## Safety model

The role refuses to change a host unless both confirmation variables are true:

```bash
ansible-playbook -i inventory.ini remediate.yml \
  -e cis_remediation_enabled=true \
  -e cis_remediation_confirm=true
```

Potentially disruptive areas are disabled by default. Enable only after reviewing the target and maintaining console access:

```yaml
cis_allow_disruptive: false
cis_allow_partition_changes: false
cis_allow_bootloader_changes: false
cis_allow_pam_changes: false
cis_allow_ssh_changes: false
cis_allow_firewall_changes: false
cis_allow_network_changes: false
cis_allow_service_removal: false
cis_allow_updates: false
cis_allow_reboot: false
cis_allow_usb_storage_disable: false
cis_allow_overlay_disable: false
```

## Recommended first run

```bash
ansible-playbook -i inventory.ini remediate.yml \
  -e cis_remediation_enabled=true \
  -e cis_remediation_confirm=true \
  --check --diff
```

Then run a single section, for example:

```bash
ansible-playbook -i inventory.ini remediate.yml \
  -e cis_remediation_enabled=true \
  -e cis_remediation_confirm=true \
  --tags cis_section_1
```

Backups and the manual-action report are placed below `/var/backups/cis-debian13/<timestamp>/` on each target.

## Scope

The remediation role covers Sections 1–7 with idempotent package, permission, sysctl, service, AppArmor, sudo, SSH, password-policy, logging, auditing, and account-database tasks. Controls that require organization-specific decisions—partitioning, firewall policy, GRUB secrets, time sources, account deletion, and similar manual controls—are deliberately gated or reported rather than applied blindly.

This is intentional: automatically repartitioning disks, replacing a firewall ruleset, changing PAM/SSH authentication, or deleting accounts can make a host unavailable or destroy data.


## Profile inheritance

Profiles are cumulative. Selecting `level2_server` evaluates/remediates controls tagged for either `level1_server` or `level2_server`; `level2_workstation` similarly includes the Level 1 workstation baseline. The playbooks print both the selected profile and the effective profile list at startup. Known Level-2-only remediation groups are skipped during Level 1 runs.

## Enhanced HTML report

The HTML report includes a responsive dashboard, pass-rate indicator, summary cards, status filtering, full-text search, and an action-items view. Failed, error, and manual controls now show a concise **What you need to do** summary followed by three clear steps. The complete CIS remediation text remains available in an expandable **Detailed remediation guidance** panel so the report stays readable without removing technical detail.
