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
- `REVIEW` (current state was collected successfully and requires a human decision)

## Exceptions

Add documented exceptions in `group_vars/all.yml`:

```yaml
cis_exceptions:
  '1.1.1.6': 'OverlayFS is required by the container platform.'
  '1.1.2.1.4': 'Application requires executable files under /tmp.'
```

An exception is reported as `EXCLUDED`; it is not counted as a pass.

## Automated policy and evidence-only review controls

Nine recommendations that CIS classifies as manual now use explicit local
PASS/FAIL criteria. The exact criterion appears in the HTML report under
**Expected state**, so a reviewer can see why the result passed or failed:

- `1.1.1.11`: known-risk filesystem modules are absent, actively used, or
  unloaded and disabled with both blacklist and install-block rules.
- `1.2.1.1`: the only active binary APT source is the approved Artifactory
  `trixie main non-free-firmware` source.
- `1.2.2.1`: APT metadata is at most 24 hours old, a simulated full upgrade has
  no pending packages, no packages are held, and no reboot is pending.
- `5.3.3.2.3`: `pam_pwquality` is active and requires all four character
  classes through `minclass >= 4` or four negative credit settings; positive
  credits fail.
- `5.4.1.2`: `PASS_MIN_DAYS` and every local password-bearing account use a
  minimum password age of at least one day.
- `6.1.1.1.2`: existing journal files are root-owned, belong to `root` or
  `systemd-journal`, and use mode `0640` or more restrictive.
- `6.1.1.1.3`: effective journald limits match `SystemMaxUse=1G`,
  `SystemKeepFree=500M`, `RuntimeMaxUse=200M`, `RuntimeKeepFree=50M`, and
  `MaxFileSec=1month`.
- `6.2.3.37`: `augenrules --check` succeeds and normalized running watch/syscall
  rules match `/etc/audit/audit.rules`.
- `7.1.13`: every SUID/SGID file is owned by an installed Debian package,
  root-owned, and not writable by group or other.

The remaining seven recommendations (`2.1.23`, `3.1.1`, `6.1.1.2.2`,
`6.1.2.5`, `6.1.2.6`, `6.1.2.8`, and `6.1.2.11`) retain `REVIEW` because the
correct result depends on an organization-approved service, network, logging,
retention, or certificate policy. Their read-only collectors show the current
state plus control-specific review instructions. Collection failures return
`ERROR`.

> **APT Signed-By note:** the approved source value requested for `1.2.1.1` is
> `deb http://artifactory.dmz.internal/artifactory/prod-remote-debian-debian trixie main non-free-firmware`.
> It does not contain a `signed-by=` option even though the CIS control title
> calls for one. The audit intentionally follows the configured local PASS
> value. For true Signed-By enforcement, add an approved Artifactory keyring to
> the source entry and update the expected value in
> `roles/cis_debian13_audit/vars/package_management.yml`.

## Audit behavior for mount controls

Mount-point checks use an exact `findmnt -M` lookup, so a directory inherited from `/` does not count as a separate filesystem. Mount-option checks inspect the active mount options. Control 1.1.2.1.1 also verifies that `tmp.mount` is not disabled or masked.

## Milestone 3 coverage

Milestone 3 adds CIS sections **1.2 Package Management** and **1.3 Mandatory Access Control**:

- 1.2.1.1 through 1.2.1.9
- 1.2.2.1
- 1.3.1.1 through 1.3.1.4

The approved APT-source and pending-update recommendations now return
deterministic PASS/FAIL results. The audit never runs `apt update`, installs
packages, or modifies package metadata.

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

Section 2.1 is implemented: controls 2.1.1 through 2.1.23. The service checks pass when the relevant package is absent, or when installed only as a dependency and every listed service/socket is disabled and inactive. Control 2.1.23 collects every TCP/UDP listener and returns `REVIEW` with instructions for comparing it to the approved-service inventory.

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

Control `5.4.1.2` uses a fixed best-practice minimum of one day for
`PASS_MIN_DAYS` and every password-bearing local account. The expected state is
shown directly in the report. All checks remain audit-only.

Run the subsection:

```bash
ansible-playbook -i inventory.ini audit.yml \
  -e cis_profile=level1_server \
  --tags section_5_4
```


## Coverage update

This cumulative release includes all 333 recommendation IDs listed in CIS
Debian Linux 13 Benchmark v1.0.0. Manual recommendations collect their current
state and return `REVIEW`; automatically scorable recommendations execute their
audit-only PASS/FAIL checks.

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

The HTML report includes a responsive dashboard, pass-rate indicator, summary
cards, status filtering, full-text search, and an action-items view. Failed and
error controls show corrective steps. Evidence-only controls show the current
state and a dedicated **How to review this evidence** panel with control-specific
decision criteria. The complete CIS remediation text remains available in an
expandable guidance panel.
