# Remediation coverage

The remediation role is intentionally policy-driven. A control is not considered
silently covered merely because the audit has a remediation paragraph.

| Control area | Implementation | Safety policy |
|---|---|---|
| 1.1.1 kernel modules | Automated; optional and unused modules use explicit allowlists | `cis_allow_disruptive`, module-specific gates |
| 1.1.2 mounts | Automated only for explicit device/source definitions | `cis_allow_partition_changes`, `cis_managed_mounts` |
| 1.2 APT | Permissions and weak dependencies automatic; source and upgrades gated | `cis_allow_apt_source_changes`, `cis_allow_updates` |
| 1.3 AppArmor | Package/service automatic; enforcing loaded profiles gated | `cis_allow_disruptive` |
| 1.4 GRUB | Permissions automatic; kernel arguments and password changes are independently gated | `cis_allow_bootloader_changes`; `cis_allow_grub_password_changes` plus PBKDF2 policy |
| 1.5 process hardening | Sysctl and core limits automated | none |
| 1.6 banners | Automated | none |
| 2 services and clients | Explicit removal lists only | `cis_allow_service_removal` |
| 2 time synchronization | Automated when approved sources are supplied | `cis_chrony_servers` |
| 2 cron and at | Automated | none |
| 3 network modules/sysctl | Automated | `cis_allow_network_changes` |
| 4 UFW | Automated with an explicit port allowlist | `cis_allow_firewall_changes` |
| 5 SSH | Automated including host-key permissions | `cis_allow_ssh_changes` |
| 5 sudo and su | Automated | none |
| 5 PAM | Pwquality, faillock, pwhistory, pam_unix and nullok controls automated | `cis_allow_pam_changes` |
| 5 password aging | Defaults automatic; existing accounts gated | `cis_allow_password_age_changes` |
| 5 shell policy | UMASK and TMOUT automated | none |
| 6 journald/rsyslog | Local logging automatic; authenticated remote logging policy-driven | `cis_logging_mode`, `cis_allow_remote_logging_changes` |
| 6 auditd | Packages, storage policy, rules and tool permissions automated | Level 2 profile; immutable mode is explicit |
| 6 AIDE | Package, audit-tool hashes and daily schedule automated | `cis_allow_aide_changes` |
| 7 file permissions | Core account files and sticky-bit remediation automated | none |
| 7 ownership and SUID/SGID | Evidence only; ownership and privilege bits require review | manual approval |

The following controls always remain review or policy-input controls because the
role cannot infer the correct organization decision: 1.1.1.11, storage layout,
2.1.23, 3.1.1, journal-upload certificate identity, rsyslog destinations and CA
trust, log retention, account ownership, and SUID/SGID authorization.

Always run remediation in check mode first and keep console access when enabling
partition, bootloader, PAM, SSH, network, firewall, immutable-audit, or remote
logging changes.
