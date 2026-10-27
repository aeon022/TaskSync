# utask: the first 10 minutes

utask shows Apple Reminders, Google Tasks and Microsoft To Do in one terminal app and keeps them in sync. Your tasks live in a local database; the providers are synced to and from it.

## 1. Check the install

```sh
utask doctor
```

It checks the config folder, the shared folder, the background service and each connected provider. Apple Reminders asks for permission the first time; allow it. A line that says `NOT INSTALLED` for the daemon is fine, it is optional.

## 2. Connect accounts

```sh
utask auth-google --label "Private"
utask auth-microsoft --client-id "YOUR_ID" --label "Work"
```

Apple Reminders needs no setup. Tokens are stored in the macOS Keychain, not in files. To re-authorize, run the same command with the same label again. Google needs a `client_secret.json` from your own Google Cloud project in `~/.config/tasksync/`; Microsoft needs the client ID of an app you registered. These are your own credentials, so utask never sees anyone else's tasks.

## 3. Sync and open the interface

```sh
utask sync        # pull everything once
utask ui          # the terminal interface
```

## 4. Keys you need on day one

| Key | What |
|---|---|
| `j` / `k` or arrows | move |
| `tab` | switch between lists, tasks, details |
| `space` | mark done / reopen |
| `a` | add a task to the current list |
| `/` | search across all lists and accounts |
| `:` | command bar |
| `s` | sync now |
| `?` | the manual |
| `q` | quit |

**Add with a due date:** press `a`, type `Call the plumber @tomorrow` and Enter. After `@` anything dateparser understands works: `@friday`, `@24.12.`, `@in 2 days`, `@übermorgen`. Set or clear it later with `:due friday` / `:due none` on the highlighted task.

**Pick a look:** `:theme terminal` uses your terminal's own colors; `:theme mocha`, `latte`, `nord`, `dracula`, `gruvbox` and more are there too. `^p` opens a picker.

**Many at once:** `v` marks tasks (visual mode), then `space` completes them, `d` deletes them, `S` moves them to tomorrow, `:move "Work"` sends them to another account.

## 5. Keep it syncing in the background (optional)

```sh
utask daemon-start     # installs a macOS LaunchAgent
utask logs             # what the daemon did
utask daemon-stop
```

## 6. Several Macs

```sh
utask config set-shared "~/Library/Mobile Documents/com~apple~CloudDocs/utask"
```

The list of accounts then lives in iCloud Drive and every Mac sees the same ones; tokens stay in each Mac's Keychain (iCloud Keychain syncs them if you have it on).

## What utask does not do (yet)

Priority is only the `!` or `!!` in a title. Due dates are date-only (the time of day of an Apple reminder is kept but not shown). If something looks wrong after a sync, `utask doctor` first, then `:log` inside the interface.
