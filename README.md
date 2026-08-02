# SharePoint Mirror Sync Service

One-way SharePoint Online to local NTFS mirror service for Symantec DLP Discover scanning.

## What It Does

- Reads SharePoint Online content through Microsoft Graph only.
- Mirrors document library files to a local Windows path.
- Preserves site, library, and folder hierarchy.
- Uses Microsoft Graph delta links for full and incremental sync.
- Stores site, drive, folder, file, hash, and sync-run metadata in SQLite.
- Streams downloads to disk and stores SHA256 hashes for integrity checks.
- Handles new, modified, deleted, renamed, and moved files.
- Propagates folder deletions: when a folder is removed in SharePoint, the local directory tree and the metadata records for its descendants are removed.
- Configures **independent mirrors**, each targeting one SharePoint site (by Graph site ID or site URL) with its own local repository, sync schedule, and folder filter, all sharing one metadata database.
- Restricts each mirror to specific folders within the site, or syncs everything.
- Uses bounded download concurrency, tenant-wide Graph request pacing shared across all mirrors, and Graph retry/backoff handling.
- Runs each mirror on its own sync schedule, in parallel.
- **Re-reads `appsettings.json` before every sync cycle** — add, remove, or modify mirrors without restarting the service. Falls back to the last-known-good configuration if the file is broken.
- Includes a **standalone configuration validator tool** (`SharePointMirror.ConfigValidator`) for pre-deployment checks.
- Emits logs in three formats: RFC 5424 text to console and file (human-readable), structured JSON to file (machine-parseable). Configurable log levels via `appsettings.json`.

## Projects

- `src/SharePointMirror.Core`: sync engine, Graph adapter, SQLite metadata, path mapping, retry, hashing, downloads.
- `src/SharePointMirror.SyncService`: Windows Service host and configuration.
- `src/SharePointMirror.ConfigValidator`: standalone configuration validation tool.
- `tests/SharePointMirror.Core.Tests`: local tests for sync behavior, metadata, retry, hashing, paths, and downloads.

## Prerequisites

- **Build machine:** the .NET 10 SDK.
- **Target server:** nothing — the publish is **self-contained**, so no .NET Runtime is required on the server. Supported platforms: Windows x64 and Linux x64.

This repository targets `.NET 10`.

## Azure App Registration

Create an app registration with application permissions:

- `Sites.Read.All`
- `Files.Read.All`

Then complete these steps, all of which are required before the service can read content:

1. **Create the authentication certificate** (see below).
2. **Grant admin consent** for the two application permissions. Without tenant admin consent the permissions are not effective and Graph calls fail with authorization errors.
3. **Upload the certificate's public key** (the `.cer`) to the app registration under *Certificates & secrets → Certificates → Upload certificate*.
4. Point the service at the certificate via the `Graph` configuration section (see [Configuration](#configuration)). The service supports either:
   - a certificate file path plus password (`CertificatePath` + `CertificatePassword`), or
   - a certificate thumbprint resolved from the Windows certificate store (`CertificateThumbprint` + `CertificateStoreName` + `CertificateStoreLocation`).

No Graph write permissions are required.

### Create the authentication certificate

Use a certificate the tenant trusts. For most deployments a self-signed certificate is acceptable for app-only Graph auth; use a CA-issued certificate if your organization requires it. The example below creates a self-signed certificate in the local machine store and exports both the public key (to upload to Azure) and a password-protected PFX (for backup or for the file-based auth mode).

Run from an **elevated** PowerShell prompt on the server that will run the service:

```powershell
# 1. Create a self-signed certificate in LocalMachine\My (2-year lifetime).
$cert = New-SelfSignedCertificate `
    -Subject "CN=SharePointMirrorSync" `
    -CertStoreLocation "Cert:\LocalMachine\My" `
    -KeyExportPolicy Exportable `
    -KeySpec Signature `
    -KeyLength 2048 `
    -HashAlgorithm SHA256 `
    -NotAfter (Get-Date).AddYears(2)

# 2. Export the PUBLIC key (.cer) — this is what you upload to the app registration.
Export-Certificate -Cert $cert -FilePath "C:\Services\SharePointMirror\SharePointMirrorSync.cer"

# 3. Export a password-protected PFX (private key) — keep this secret; needed for file-based auth and for backup.
$pfxPassword = Read-Host -AsSecureString "PFX export password"
Export-PfxCertificate -Cert $cert -FilePath "C:\Services\SharePointMirror\SharePointMirrorSync.pfx" -Password $pfxPassword

# 4. Note the thumbprint for the configuration (thumbprint-based auth).
$cert.Thumbprint
```

Then choose one of the two authentication modes:

- **Thumbprint mode (recommended on the server):** the certificate created above already lives in `LocalMachine\My`. Set `CertificateThumbprint` to the value from step 4, leave `CertificatePath`/`CertificatePassword` empty, and keep `CertificateStoreName = "My"` and `CertificateStoreLocation = "LocalMachine"`. The service account must be granted read access to the certificate's private key (see [Service account](#service-account)).
- **File mode:** set `CertificatePath` to the exported `.pfx` and `CertificatePassword` to the PFX password; leave `CertificateThumbprint` empty.

In both cases, upload only the `.cer` (public key) to Azure — never the `.pfx`.

## Configuration

Edit `src/SharePointMirror.SyncService/appsettings.json` or provide equivalent production configuration. The configuration has three top-level sections:

- `Service` — instance-wide settings shared by every mirror, including the **single metadata database** used by all of them.
- `Graph` — the single app registration / certificate used for all Graph access.
- `Mirrors` — an array of **independent mirrors**. Each entry targets **one** SharePoint site with its own local repository, sync schedule, and folder filter. Mirrors run in parallel, each on its own loop, and all share the one metadata database.

```json
{
  "Service": {
    "LogsPath": "D:\\SharePointMirror\\Logs",
    "DatabasePath": "D:\\SharePointMirror\\Metadata\\mirror.db",
    "MaxGraphRequestsPerSecond": 5,
    "MaxConcurrentDownloads": 10,
    "SyncInterval": "00:15:00"
  },
  "Graph": {
    "TenantId": "<tenant-id>",
    "ClientId": "<client-id>",
    "CertificatePath": "",
    "CertificatePassword": "",
    "CertificateThumbprint": "<thumbprint>",
    "CertificateStoreName": "My",
    "CertificateStoreLocation": "LocalMachine"
  },
  "Mirrors": [
    {
      "Name": "HR",
      "MirrorRoot": "D:\\SharePointMirror\\HR",
      "SiteId": "contoso.sharepoint.com,11111111-1111-1111-1111-111111111111,22222222-2222-2222-2222-222222222222",
      "IncludedFolders": [ "*" ],
      "ExcludedFolders": [ "Archive" ]
    },
    {
      "Name": "Legal-Contracts",
      "MirrorRoot": "E:\\SharePointMirror\\Legal",
      "MaxConcurrentDownloads": 4,
      "SyncInterval": "01:00:00",
      "SiteId": "contoso.sharepoint.com,2c6ad3f6-1a2b-4c3d-9e8f-0123456789ab,6e3f4a1b-5c6d-7e8f-9a0b-1c2d3e4f5a6b",
      "IncludedFolders": [ "Contracts", "Templates/NDA" ],
      "ExcludedFolders": [ "Contracts/Drafts" ]
    }
  ]
}
```

In the example above, the HR mirror inherits the global `MaxConcurrentDownloads` (10) and `SyncInterval` (15 minutes) from `Service`, while Legal-Contracts overrides both with its own values (4 concurrent downloads, 1-hour interval).

Each mirror is identified by its **Microsoft Graph site ID** (`SiteId`). Site display names are intentionally **not** accepted as a selector — titles can be duplicated across a tenant or renamed, either of which would silently send a mirror to the wrong site or nowhere. The site ID is immutable, so it always resolves to exactly one site. (The display name is still used internally for the local folder layout; it is read from the resolved site, not from config.)

### `Service` fields

- `LogsPath`: absolute Windows path for the service's operational JSON logs (shared by all mirrors; created on startup).
- `DatabasePath`: absolute path to the **single** SQLite metadata database used by every mirror. **Must include a directory component** (a bare filename is rejected). Records are keyed by site, drive, and item IDs, so all sites coexist in one database without collision. The directory is created on startup.
- `MaxGraphRequestsPerSecond`: tenant-wide Graph API **rate limiter** for the whole service — caps how many API calls per second are started across every mirror combined (site/drive discovery, delta queries, retries, downloads). This prevents hitting Microsoft's throttling limits regardless of how many mirrors run concurrently. A value of `0` disables pacing entirely. Cannot be negative.
- `MaxConcurrentDownloads`: the default number of parallel file downloads per mirror. Each mirror can override this in its own entry. This controls **parallelism within a single mirror** — how many files download simultaneously — while `MaxGraphRequestsPerSecond` controls the **overall API rate** across all mirrors. Default: `10`.
- `SyncInterval`: the default wait between the end of one sync run and the start of the next for each mirror (`hh:mm:ss`). Each mirror can override this in its own entry. Default: `00:15:00` (15 minutes).

### `Mirrors[]` fields

Each object is one independent mirror:

- `Name`: a friendly label used in logs to identify the mirror. Optional but recommended.
- `MirrorRoot`: absolute path for this mirror's local file repository. Layout is `{MirrorRoot}\{SiteName}\{LibraryName}\{folders...}`. Created on startup. Mirrors may share a root (the site-name segment keeps them separate) or use separate roots/drives.
- `MaxConcurrentDownloads` *(optional)*: overrides the global `Service.MaxConcurrentDownloads` for this mirror. Omit to inherit the service default. (This is per-mirror parallelism; overall Graph load is still bounded by the shared `MaxGraphRequestsPerSecond`.)
- `SyncInterval` *(optional)*: overrides the global `Service.SyncInterval` for this mirror (`hh:mm:ss`). Omit to inherit the service default. This is the wait between the end of one run and the start of the next, not a fixed wall-clock schedule.
- `SiteId`: the single site this mirror syncs, as its full **Microsoft Graph site ID** — a composite of three comma-separated parts, `{hostname},{siteCollectionId},{webId}`, **not** a bare GUID. Matched whole-string and case-insensitively against the discovered site's ID. Retrieve it via `GET https://graph.microsoft.com/v1.0/sites/contoso.sharepoint.com:/sites/HR` and read the returned `id` field.

  ```json
  "SiteId": "contoso.sharepoint.com,2c6ad3f6-1a2b-4c3d-9e8f-0123456789ab,6e3f4a1b-5c6d-7e8f-9a0b-1c2d3e4f5a6b"
  ```

- `SiteUrl`: alternative to `SiteId` — the full SharePoint site URL. When set, the site is looked up directly via Graph instead of searching all sites by ID. Either `SiteId` or `SiteUrl` is required; if both are set, `SiteUrl` is tried first.

  ```json
  "SiteUrl": "https://contoso.sharepoint.com/sites/HR"
  ```

  If a mirror has neither `SiteId` nor `SiteUrl`, or the value matches no accessible site, that mirror logs a warning and syncs nothing (other mirrors are unaffected).
- `IncludedFolders`: restricts which **folders** are mirrored within each document library of this mirror's site.
  - `[ "*" ]` or `[]` syncs **every** folder — the full library content.
  - Listing folder paths syncs **only** those folders and everything beneath them. Paths are relative to the **document library root** (they do not include the site or library name), use `/` separators, and are matched **whole-segment and case-insensitively**. A listed folder matches itself and all descendants. A file at the library root is **not** synced when a specific list is set; if any entry is `*`, everything is synced.

    ```json
    "IncludedFolders": ["Reports"]                 // only the Reports folder (and subfolders)
    "IncludedFolders": ["Reports", "HR/Policies"]  // multiple folders; nested paths allowed
    ```
- `ExcludedFolders`: folders to **skip**, matched exactly like `IncludedFolders` (library-relative paths, whole-segment, case-insensitive, folder + all descendants). **Exclusion wins over inclusion**, which makes it useful in two ways:
  - To carve folders out of a full sync — `"IncludedFolders": ["*"]` with `"ExcludedFolders": ["Archive", "Personal"]` mirrors everything except those folders.
  - To carve a subfolder out of an included folder — `"IncludedFolders": ["Reports"]` with `"ExcludedFolders": ["Reports/Drafts"]` mirrors `Reports` except `Reports/Drafts`.

    Empty (`[]`) excludes nothing. Note: changing the lists does not retroactively delete already-mirrored content for a folder you newly exclude — it only stops syncing it going forward; remove such content manually if required.

### `Graph` fields

- `TenantId` / `ClientId`: **required**; the service fails fast if missing.
- `CertificatePath` + `CertificatePassword`, **or** `CertificateThumbprint` + `CertificateStoreName` + `CertificateStoreLocation` (see [Create the authentication certificate](#create-the-authentication-certificate)).
- `CertificateStoreName`: a `System.Security.Cryptography.X509Certificates.StoreName` value (e.g. `My`, `Root`).
- `CertificateStoreLocation`: `LocalMachine` or `CurrentUser`. Use `LocalMachine` when the service runs under a machine/service account.

To sync **multiple sites**, add one `Mirrors[]` entry per site, each with its own `SiteId`. Give **each mirror a distinct site**: because all mirrors share one database (records keyed by site/drive/item ID), two mirrors pointed at the same `SiteId` would fight over the same records. Use separate sites per mirror (the normal case); mirroring one site to two destinations is not currently supported in a single database.

### Configuration validation

The service validates the entire configuration at startup **and before every sync cycle**. The configuration file (`appsettings.json`) is re-read on each cycle, so you can add, remove, or modify mirrors without restarting the service.

Validation runs in three layers:

1. **JSON syntax** — the raw file is parsed first. If the JSON is malformed (missing commas, unclosed braces, etc.), the error is logged with line and position, and the service falls back to the last-known-good configuration.
2. **Required sections** — the `Service`, `Graph`, and `Mirrors` sections must all be present. Missing sections are flagged immediately.
3. **Config rules** — field values are validated (see below).

**Fatal — on startup the service exits; at runtime it falls back to the last valid configuration:**
  - `Graph.TenantId`, `Graph.ClientId`, or a certificate (`CertificatePath` or `CertificateThumbprint`) missing.
  - `Service.LogsPath` blank.
  - `Service.DatabasePath` blank, or without a directory component (a bare filename is rejected).
  - `Service.MaxGraphRequestsPerSecond` is negative.
  - `Service.MaxConcurrentDownloads` is zero or less.
  - `Service.SyncInterval` is zero or less.
  - the same site configured on more than one mirror (they would collide in the shared database).
  - no valid mirrors remain — an empty `Mirrors` array, or every mirror skipped.

**Skipped — that mirror is dropped, the rest keep running:**
  - blank `SiteId` and `SiteUrl`.
  - `SiteUrl` is not a valid https URL.
  - blank `MirrorRoot`.

  Note: mirrors that omit `MaxConcurrentDownloads` or `SyncInterval` (or set them to `0`) inherit the global defaults from `Service` — this is normal, not an error.

**Warning — advisory only, nothing is disabled:**
  - two mirrors sharing the same `Name` (their log entries become ambiguous).
  - `MaxGraphRequestsPerSecond` is 0 (Graph request throttling disabled).

**Last-known-good fallback:** if the configuration file is broken or invalid while the service is running, the service continues syncing with the last valid configuration. The last-known-good config is also persisted to the metadata database, so even a service restart with a broken file can recover.

Note: the shipped `appsettings.json` has empty `"SiteId": ""` and `"SiteUrl": ""`, so the bundled mirror is skipped and the service exits with a "No valid mirrors" fatal until you set a real site — this is the intended fail-fast behavior, not a bug.

### Configuration validator tool

A standalone tool is included in the release under `tools/`. Use it to validate `appsettings.json` **before** deploying or editing the production file:

```powershell
# Windows
tools\SharePointMirror.ConfigValidator.exe appsettings.json

# Linux
tools/SharePointMirror.ConfigValidator appsettings.json
```

The tool checks JSON syntax, required sections, and all configuration rules. It prints a color-coded report and exits with code `0` (valid) or `1` (invalid). If no path is given, it looks for `appsettings.json` in the current directory.

Example output for a valid configuration:

```
Validating: D:\SharePointMirror\appsettings.json
────────────────────────────────────────────────────────────

  OK   JSON syntax is valid

Valid mirrors:
    +  "HR"
       Site:     https://contoso.sharepoint.com/sites/HR
       Root:     D:\SharePointMirror\HR
       Interval: 00:15:00
    +  "Finance"
       Site:     https://contoso.sharepoint.com/sites/Finance
       Root:     D:\SharePointMirror\Finance
       Interval: 00:30:00

  RESULT   Configuration is VALID — 2 mirror(s) ready to sync.
```

## Build And Test

```powershell
dotnet restore SharePointMirror.sln
dotnet build SharePointMirror.sln --no-restore
dotnet test SharePointMirror.sln --no-build
```

There is no separate database migration step; the SQLite schema is created automatically on first run.

## Publish And Install

Publish as a self-contained trimmed build (no .NET Runtime required on the server):

```powershell
# Sync service
dotnet publish .\src\SharePointMirror.SyncService\SharePointMirror.SyncService.csproj -c Release -r win-x64 --self-contained -o C:\Services\SharePointMirror

# Config validator tool
dotnet publish .\src\SharePointMirror.ConfigValidator\SharePointMirror.ConfigValidator.csproj -c Release -r win-x64 --self-contained -o C:\Services\SharePointMirror\tools
```

For Linux, replace `-r win-x64` with `-r linux-x64`.

Install as a Windows Service from an elevated PowerShell prompt:

```powershell
sc.exe create SharePointMirrorSync binPath= "C:\Services\SharePointMirror\SharePointMirror.SyncService.exe" start= delayed-auto
sc.exe description SharePointMirrorSync "One-way SharePoint Online to NTFS mirror sync for Symantec DLP Discover"
sc.exe start SharePointMirrorSync
```

### Service account

`sc.exe create` runs the service as `LocalSystem` by default. Whichever account the service runs under must have:

- **read access to the certificate's private key** (for thumbprint auth, the certificate with its private key must be installed in the configured store — e.g. `LocalMachine\My` — and the service account granted private-key read access via *Manage Private Keys*). This is the most common cause of startup auth failures.
- **write access** to `Service.LogsPath`, the `Service.DatabasePath` directory, and every mirror's `MirrorRoot`.

To run under a dedicated account, set it with `sc.exe config SharePointMirrorSync obj= "DOMAIN\svc-account" password= "..."`.

### Upgrade and uninstall

```powershell
# Upgrade: stop, republish over the folder, start.
sc.exe stop SharePointMirrorSync
dotnet publish .\src\SharePointMirror.SyncService\SharePointMirror.SyncService.csproj -c Release -r win-x64 --self-contained -o C:\Services\SharePointMirror
dotnet publish .\src\SharePointMirror.ConfigValidator\SharePointMirror.ConfigValidator.csproj -c Release -r win-x64 --self-contained -o C:\Services\SharePointMirror\tools
sc.exe start SharePointMirrorSync

# Uninstall:
sc.exe stop SharePointMirrorSync
sc.exe delete SharePointMirrorSync
```

## Logging

The service writes logs to three destinations simultaneously:

| Sink | Format | File pattern | Purpose |
|------|--------|-------------|---------|
| **Console** | RFC 5424 syslog | — | Real-time monitoring when running interactively |
| **Text file** | RFC 5424 syslog | `sharepointmirror-YYYYMMDD.log` | Human-readable log file, syslog-compatible |
| **JSON file** | Structured JSON | `sharepointmirror-YYYYMMDD.json` | Machine-parseable for log aggregation tools |

Both file sinks write to `Service.LogsPath`, roll daily, and retain 31 files.

### Log format

The console and text file produce fully RFC 5424-compliant syslog messages:

```
<PRI>VERSION TIMESTAMP HOSTNAME APP-NAME PROCID MSGID SD MSG
```

| Field | Value |
|-------|-------|
| PRI | Facility `local0` (16) combined with syslog severity |
| VERSION | `1` |
| TIMESTAMP | ISO 8601 UTC (`yyyy-MM-ddTHH:mm:ss.fffZ`) |
| HOSTNAME | Machine name |
| APP-NAME | `SharePointMirror` |
| PROCID | OS process ID |
| MSGID | Source component (e.g. `Worker`, `SyncAuditLogger`) or `-` |
| SD | `-` (nil) |

Serilog log levels map to syslog severity: Debug → 7, Information → 6, Warning → 4, Error → 3, Fatal → 2.

Example output:

```
<134>1 2026-06-30T14:22:01.123Z SERVER1 SharePointMirror 16296 Worker - [sync] Mirror "HR" — completed in 4.2s: 5 added, 2 updated, 1 deleted
<132>1 2026-06-30T14:22:01.456Z SERVER1 SharePointMirror 16296 Worker - [config] Site "Legal" removed — no longer synced (local files left in place)
<131>1 2026-06-30T14:22:01.789Z SERVER1 SharePointMirror 16296 Worker - [sync] Mirror "HR" — failed after 12.3s. Check network connectivity and Graph API permissions
```

The `.log` files can be fed directly into any syslog-compatible log aggregation tool (Splunk, Graylog, rsyslog, etc.).

Each message is prefixed with a category tag for easy filtering:

| Tag | Meaning |
|-----|---------|
| `[startup]` | Service lifecycle (starting, mirror count) |
| `[config]` | Configuration reload, validation, change detection |
| `[sync]` | Per-mirror sync runs (start, complete, failed, next interval) |
| `[discovery]` | SharePoint site lookup via Graph |
| `[audit]` | Per-file operations (download, skip, move, delete) |

### Log levels

Log levels are configured in the `Logging` section of `appsettings.json`:

```json
{
  "Logging": {
    "LogLevel": {
      "Default": "Information",
      "Microsoft.Hosting.Lifetime": "Information"
    }
  }
}
```

Available levels (from most to least verbose):

| Level | What it shows |
|-------|--------------|
| `Debug` | All of the below, plus internal Graph responses, site-matching details, delta page counts |
| `Information` | Sync start/complete, duration, file counts, config baseline, site discovery, next-sync schedule |
| `Warning` | Skipped mirrors, removed sites/folders, config changes that reduce scope, throttling |
| `Error` | Sync failures, JSON parse errors, missing config sections, invalid configuration values |
| `Fatal` | Startup-blocking config errors (missing Graph credentials, no valid mirrors) |

**Recommended levels:**
- **Production:** `Information` (default) — shows sync activity and config changes without noise.
- **Troubleshooting:** `Debug` — adds Graph API detail and site-matching diagnostics.
- **Quiet/alerting:** `Warning` — only logs problems and scope changes.

You can also set levels per namespace to control verbosity of specific components:

```json
{
  "Logging": {
    "LogLevel": {
      "Default": "Information",
      "Microsoft.Hosting.Lifetime": "Warning",
      "SharePointMirror.Core": "Debug"
    }
  }
}
```

Since the service re-reads `appsettings.json` before every sync cycle, log level changes take effect without a restart.

### Sync duration

Every sync run logs its elapsed time. When no files changed, a short summary is logged:

```
<134>1 2026-06-30T14:22:01.123Z SERVER1 SharePointMirror 16296 Worker - [sync] Mirror "HR" — no changes detected (1.2s)
```

When files were synced, the counts and duration are included:

```
<134>1 2026-06-30T14:22:05.456Z SERVER1 SharePointMirror 16296 Worker - [sync] Mirror "HR" — completed in 4.2s: 5 added, 2 updated, 1 deleted
```

After each sync, the next scheduled sync time is logged:

```
<134>1 2026-06-30T14:22:05.789Z SERVER1 SharePointMirror 16296 Worker - [sync] Mirror "HR" — next sync in 15m 0s
```

### Configuration change auditing

Before every sync cycle the service compares the current configuration against the previous snapshot (persisted in the metadata database) and logs what changed, so scope reductions are never silent:

- **Site removed** from `Mirrors[]` → **Warning**: the site is no longer synced, and its already-mirrored files and metadata are left in place.
- **Folders no longer synced** for a retained site — entries dropped from `IncludedFolders`, or newly added to `ExcludedFolders` → **Warning**, listing the folders.
- Site added, folders newly synced, or other field changes (`MirrorRoot`, `SyncInterval`, `MaxConcurrentDownloads`, `Name`) → **Information**.
- First run → an **Information** "baseline established" entry; no diff.

Note that removing a site or folder stops *future* syncing but does not delete content already mirrored to disk — remove that manually if required.

## Symantec DLP Discover

Configure DLP Discover to scan each mirror's `MirrorRoot`, for example:

```text
D:\SharePointMirror\HR
E:\SharePointMirror\Legal
```

Use read-only access for the DLP scanner account. Keep the operational folders out of the scan: the shared `Service.DatabasePath` (metadata) directory and `Service.LogsPath` should be excluded, or placed outside the scanned roots.

## Disaster Recovery

Back up:

- the single SQLite database (`Service.DatabasePath`), **including its `-wal` and `-shm` sidecar files** (the database runs in WAL mode). For a consistent backup, stop the service first, or use a tool that performs an online SQLite backup/checkpoint. Copying `mirror.db` alone while the service is running can capture a torn database.
- every mirror's file repository (`MirrorRoot`).
- production configuration (`appsettings.json`)
- certificate material or certificate-store backup
- logs required for audit retention

Restore the database and all mirror repositories together. The service resumes from stored Graph delta links and does not need a full re-index when the database and mirrors are restored consistently. The database holds every mirror's state keyed by site/drive/item ID, so a single consistent snapshot covers all sites.
