# Security

utask keeps your tasks in a local SQLite database and talks to Apple Reminders (EventKit), Google Tasks and Microsoft To Do with **your own** credentials. Tokens live in the macOS Keychain, not in files. There is no server of ours in between and no analytics.

Report a problem privately: open a GitHub security advisory on this repository or write to the address in the profile of the maintainer. Please do not post exploit details in public issues.

## Audit 2026-10-27

Scope: the Python package, the scripts, the release workflow, the standalone binary, the website. Method: reading all of `task_sync/`, running proof-of-concept inputs, `pip-audit` on the installed dependencies (no known vulnerabilities), a scan of all 78 commits for tokens, keys and credential files (none found).

### Fixed in this audit

| # | Finding | Severity | Fix |
|---|---|---|---|
| 1 | **Command execution through a task title.** The Pomodoro notification built an AppleScript string from the task title (`display notification "…{title}…"`). A title such as `x" & (do shell script "…") & "` ran a shell command when the timer finished. Titles come from your lists, including shared ones. `utask-wrapper.sh` had the same pattern with its argument. | high | The text is now passed as an `osascript` argument, never as part of the script (`task_sync/notify.py`, wrapper). Test: `tests/test_security.py` runs the injection and checks that nothing happens. |
| 2 | **A task title could crash the interface.** Titles were shown as Textual markup: `Buy [/oops] milk` raised `MarkupError` and closed the app; `[WIP] fix the build` lost its `[WIP]`. A shared task is enough to make the app unusable. | medium | All remote text is escaped before display (list, focus screen, search). |
| 3 | **`daemon-start` was broken in the standalone binary.** The launchd entry passed the binary path twice. | medium (function) | The entry now matches how the program is started; paths are XML-escaped. |
| 4 | **`setup.sh` deleted relative to the current folder.** `rm -rf build dist env …` ran wherever you called the script from. | medium | The script changes into the repository folder first and refuses to run elsewhere. |
| 5 | **Config folder permissions depended on import order.** The folder was created with the default umask (world-readable) when the database module loaded first; the database and the log were readable (`0644`). | low | The folder is created `0700`, database and log are set to `0600`. |
| 6 | **`utask doctor` gave false assurance.** It reported "✅ Google" because a token existed, and always ended with "System Integrity Confirmed", while the Google refresh token had been revoked (`invalid_grant`) since June. | medium (trust) | Doctor now tries the token (refresh) and says what to do; it only reports success when nothing failed. |
| 8 | **The website made requests to Google.** The page head contained `preconnect` hints to `fonts.googleapis.com` and `fonts.gstatic.com`, so a visitor's browser contacted Google although no font was loaded. | low (privacy) | Removed; the site now makes no third-party requests (no web fonts, no analytics). |
| 7 | **Release workflow** had default token permissions and outdated action versions. | low | `permissions: contents: write` only, newer action versions. |

### Open, and what to do about it

| # | Finding | Severity | Recommendation |
|---|---|---|---|
| A | **Several accounts of one provider share one Keychain entry.** Tokens are stored as `google_token` / `microsoft_client_id`; the account label is only a display name. A second Google account overwrites the first, and both labels then sync with one token. | medium | Key the secrets by label (`google_<label>_token`) with a one-time migration. Not changed here because it touches stored data. |
| B | **Microsoft sign-in is not persisted.** The MSAL token cache lives in memory only, so `acquire_token_silent` finds no account in a new process and the Microsoft sync returns nothing. | medium (function) | Persist an MSAL `SerializableTokenCache` in the Keychain. Doctor now says so instead of reporting a green tick. |
| C | **The standalone binary is not signed or notarized.** Users must remove the quarantine flag by hand (`xattr -d com.apple.quarantine`), which teaches them to bypass Gatekeeper. | medium (supply chain trust) | Sign with a Developer ID and notarize; publish SHA-256 checksums next to the download. |
| D | **Release actions are pinned by version tag, not commit SHA.** | low | Pin `actions/*` and `softprops/action-gh-release` to full commit SHAs. |
| E | **Legacy plaintext token file code** (`config.py`, `api_google.py`, `api_ms.py`): not used by the current commands, but it writes `tokens.json` (`0600`) if called. | low | Delete the legacy modules. |
| F | **Website sends no security headers** (HSTS, CSP, `X-Content-Type-Options`, `Referrer-Policy`, `X-Frame-Options`). It is a static site without forms. | low | Add them in the nginx server block. A starting point is in `docs/nginx-headers.conf` (the CSP works because the site loads nothing from other hosts). |
| G | Remote task descriptions are rendered as Markdown, so links in a shared task can be followed from the details panel. | low | Treat links in shared lists like links in email. |

### What was checked and found fine

SQL is built with SQLModel/SQLAlchemy (parameterized), no `shell=True`, no `eval`/`exec`/`pickle`, OAuth uses the installed-app loopback flow, tokens are not written to the log, the dependency set has no known vulnerabilities (`pip-audit`), the repository history contains no secrets.
