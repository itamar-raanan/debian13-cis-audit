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
- `MANUAL` (used as manual controls are added)

## Exceptions

Add documented exceptions in `group_vars/all.yml`:

```yaml
cis_exceptions:
  '1.1.1.6': 'OverlayFS is required by the container platform.'
  '1.1.2.1.4': 'Application requires executable files under /tmp.'
```

An exception is reported as `EXCLUDED`; it is not counted as a pass.

## Audit behavior for mount controls

Mount-point checks use an exact `findmnt -M` lookup, so a directory inherited from `/` does not count as a separate filesystem. Mount-option checks inspect the active mount options. Control 1.1.2.1.1 also verifies that `tmp.mount` is not disabled or masked.

## Milestone 3 coverage

Milestone 3 adds CIS sections **1.2 Package Management** and **1.3 Mandatory Access Control**:

- 1.2.1.1 through 1.2.1.9
- 1.2.2.1
- 1.3.1.1 through 1.3.1.4

The project now contains **63 automated checks** and **2 manual checks**. Manual controls are reported as `MANUAL`; the audit never runs `apt update` or modifies package metadata.

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

Section 2.1 is implemented: controls 2.1.1 through 2.1.23. The service checks pass when the relevant package is absent, or when installed only as a dependency and every listed service/socket is disabled and inactive. Control 2.1.23 is reported as MANUAL with listener-review guidance.

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

Control `5.4.1.2` remains a manual assessment because the acceptable minimum password age is determined by organizational policy. All other controls are automated and audit-only.

Run the subsection:

```bash
ansible-playbook -i inventory.ini audit.yml \
  -e cis_profile=level1_server \
  --tags section_5_4
```


## Coverage update

This cumulative release includes all 333 recommendation IDs listed in CIS Debian Linux 13 Benchmark v1.0.0. Manual recommendations are reported as `MANUAL`; automated recommendations execute audit-only checks.
