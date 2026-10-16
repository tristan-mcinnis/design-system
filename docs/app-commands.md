# House app commands

One rule for how the house apps command each other. `DESIGN.md` is the look,
`SWIFT.md` is the code, this is the wiring.

The goal: Quick Launch is the front door. From its launcher you start an RTI
recording, toggle dictation, warm or unload a model, capture a thought to
memory. It lists what every app can do without knowing any of them by name.

## The shape

Three transports, because three already exist and work. An app publishes a
**manifest** saying which one it speaks. Nothing else is invented.

| transport | who speaks it today | use when |
|---|---|---|
| `socket` | local-dictation (`src/ipc.rs`) | a running app owns live state |
| `http`   | local-models daemon on 8078 | a daemon already serves HTTP |
| `exec`   | memory, via the `recall` CLI | a CLI already does the job |

**Sockets, not URL schemes.** A URL scheme is callable by any web page that can
open a link. A Unix socket at mode 0600 in the user's own config directory is
callable only by them. Starting a recording or a microphone must not be one
stray click away.

## The manifest

Each app writes one file at:

    ~/Library/Application Support/House/commands/<app-id>.json

Written at launch and rewritten whenever the command set changes. Readers must
tolerate a missing, stale or malformed file: a bad manifest means that app
offers nothing, never a crash.

    {
      "schema": 1,
      "app": "rti",
      "name": "RTI",
      "transport": "socket",
      "endpoint": "~/.config/rti/control.sock",
      "status": "status",
      "commands": [
        {"id": "record.start", "title": "Start Recording", "verb": "start",
         "needs": null, "unavailableWhen": "recording"},
        {"id": "record.stop",  "title": "Stop Recording",  "verb": "stop",
         "needs": null, "unavailableWhen": "!recording"}
      ]
    }

- `endpoint` is a socket path, a base URL, or an executable path by transport.
  Always written **resolved and absolute**, never with a `~`. The example above
  shows a tilde for readability only.
- `needs` is `null`, `"text"`, or `"choice"` when the command takes one argument.
- `unavailableWhen` names a boolean field of the status document, optionally
  negated with `!`. Quick Launch hides or dims the row; it never guesses. It is a
  **display hint only**: the app still accepts the command at any time and answers
  idempotently, per the rules below. A row being dimmed and a command being
  refused are different things, and only the first is this field's business.

## Choices, and the `http` transport

A command whose `needs` is `"choice"` must say where the choices come from. A
list frozen into a manifest at launch is stale by lunchtime (a registry gains
models while the daemon runs), so the manifest names a route instead:

    {"id": "models.warm", "title": "Warm Model", "needs": "choice",
     "choicesFrom": "/v1/choices/model"}

`choicesFrom` answers `{"choices": [{"id", "title", "detail"}]}`. It is
transport-agnostic: a socket app answers it as a verb, an `exec` app as a
subcommand, an `http` app as a `GET`. The caller fetches it when the user opens
the command, never at launch.

For the `http` transport specifically:

- A command is `POST {endpoint}{verb}`. `status` and `choicesFrom` are `GET`.
  No existing route is bent to fit.
- The argument is posted as `{"argument": "<value>"}`, mirroring the socket
  protocol's single argument, so a caller needs no knowledge of any app's own
  field names. An app may accept it as a synonym for whatever it already calls
  that field.
- The caller **always** posts `{"argument": "<value>", "wait": false}`. Nothing
  in a manifest says which commands are slow, and rather than add a field for
  it, the caller simply never asks to wait: an app with nothing slow to do
  ignores an unknown key, and one with slow work starts it and replies
  `{"started": true}`. The caller then polls `status` until `busy` clears.

## The socket protocol

Deliberately small, copied from local-dictation, which is the reference:

- One request per line, one reply line. UTF-8. A word, then optional argument
  text after a single space.
- An unknown verb replies one line starting `err `, naming the offending word,
  as local-dictation already does (`err unknown command "foo"`). Never a crash,
  never a hang. The shipped wording is the rule; the contract moved to it.
- `status` replies with one line of JSON, the status document below.
- The listener must be off the app's critical path, and **if the socket cannot
  be bound the app logs and carries on**. Losing remote control must never cost
  the primary function. This is the existing rule in `ipc.rs` and it holds.

**Line framing, as both sides implement it.** The reference server is
`local-dictation/src/ipc.rs`; the reference client is Quick Launch's
`UnixSocketLineClient`. They agree on this and nothing else is assumed:

- The transport is a `SOCK_STREAM` Unix domain socket. Each exchange is one
  connection: connect, send one request line, read one reply line, close.
- The request is the UTF-8 verb, then optionally one space and the argument
  text, then `\n`. The client replaces newlines and carriage returns inside the
  argument with spaces, so one request is always one line.
- The server reads at most 256 bytes of request and drops a client that sends
  no newline within 500 ms. It serves one connection at a time, so a client
  must close promptly.
- The reply is one line ending in `\n`. The client stops reading at the first
  newline; if the server closes without one, whatever arrived is the reply, and
  an empty close is a failure. Replies are `ok <verb>`, `err <message>`, or for
  `status` one line of JSON.
- The client sets a path-length limit of 103 bytes (`sockaddr_un.sun_path` on
  Darwin is 104 with the terminator) and refuses a longer endpoint before
  opening a descriptor. The descriptor is close-on-exec. Connect, send and
  receive each carry a timeout; a refused or missing socket fails at once.

**Liveness.** A manifest outlives its app: a crash leaves the file, and an app
may not remove it on a clean quit either. So a reader never treats a manifest
as proof the app runs. For a `socket` app that declares a `status` verb, the
reader asks `status` on each refresh (a read younger than 2 seconds is reused,
so opening the launcher twice in a row costs one read). Before that, the
reader checks whether a `socket` manifest's `endpoint` path exists, with or
without a `status` verb (one file check, no connection). A manifest whose socket
file is missing is not listed: none of its rows are drawn and no `status` is
asked. The
dispatcher then sorts each socket failure into one of two kinds. A **timeout**
is a send that stalls (EAGAIN or EWOULDBLOCK) or a reply that does not arrive
in time after the connection was made (the reader waits 1 second for `status`).
**Unreachable** is everything else: the path is missing, the connection is
refused, the connect itself times out, the path is over 103 bytes, the send
fails for any other reason (EPIPE, ECONNRESET), or the peer closes without
sending a line. An unreachable `status` hides **all** of that app's rows,
including commands with no `unavailableWhen`, and they return as soon as
`status` answers again. A timeout, or a reply that is not a status document,
hides nothing: a busy app is alive, and `unavailableWhen` alone decides its
rows. An `err` reply is a refusal and also hides nothing. The contract
carries no pid, so liveness is the socket's answer, never a process check.
Hidden rows, including those of an app whose socket file is missing, stay
reachable by id, so an alias or hotkey bound to a dead app's command still
dispatches and fails with an unreachable error, not silently.
`exec` and `http` apps are not checked this way: an `exec` app has no process
to ask, and an `http` daemon is judged by its own `status` route as before.

An app should delete its own manifest on a clean stop, which keeps the folder
honest; rti does. local-dictation does not yet, and relies on the reader rule.

**Socket path**: `~/.config/<app>/control.sock`, overridable by an environment
variable. `<app>` is the app's own existing config directory, which need not
equal its app id (local-dictation's id is `dictation` but its directory is
`local-dictation`). Readers never guess: the manifest's `endpoint` carries the
resolved **absolute** path, and that is authoritative. Never `temp_dir()`: a GUI-launched app and a CLI client resolve
different `$TMPDIR` values and would never meet at the same path. That lesson is
already paid for; do not re-learn it.

## The status document

Every app answers `status` with at least:

    {"app": "rti", "ok": true, "busy": false, "detail": "Idle"}

plus whatever booleans its `unavailableWhen` clauses name (`recording`,
`paused`, `warm`). `detail` is one short human phrase, shown verbatim.

## Status for the `exec` transport

A CLI is stateless: it cannot answer for the app, and shelling out on every
status read would be both slow and a second source of truth. So for `exec`,
`status` is **an absolute path to a JSON file**, not a verb:

    "transport": "exec",
    "endpoint": "/Users/you/.local/bin/recall",
    "status": "~/Library/Application Support/House/commands/memory.status.json"

The owning app writes that file **atomically**, from state it already holds, and
rewrites it only when the state changes. It holds the same status document as
every other transport.

Reading it: missing or malformed means unavailable, exactly like a dead socket.
**Do not expire it by age.** An app whose state rarely changes has an old file
and is perfectly healthy; treating that as stale would hide a working app. The
file is current until the app says otherwise.

## Rules

- A command is **idempotent where it can be**: `stop` on a stopped app is a
  no-op that replies success, not an error.
- A command **never blocks the caller** longer than a second. Work that cannot
  finish in that time must offer a non-blocking form (a `wait: false` flag, or
  an equivalent) that starts the work and returns at once; the caller then
  polls `status`. Warming a cold model is the worked example: it takes tens of
  seconds, so it must be startable without waiting.
- The caller dispatches **every** command off its main thread with a timeout
  regardless, and says "started" rather than freezing. An app being slow must
  never be able to wedge the launcher.
- No command may **destroy data** without the owning app confirming in its own
  UI. Deleting, overwriting and clearing stay in the app that owns them.
- Commands are **user-visible strings**, sentence case, naming the effect:
  "Start Recording", not "toggle_session".
- An app that gains a command adds it to its manifest in the same commit.

## Quick Launch's side

Reads every manifest, shows the commands in its launcher catalog, dispatches by
transport, and reads `status` to keep a row honest. A missing app or a dead
socket hides its rows, a timeout leaves them as `unavailableWhen` decides, and
neither blocks the launcher (see **Liveness**).
