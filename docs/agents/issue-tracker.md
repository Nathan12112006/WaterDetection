# Issue tracker: Local Markdown

Issues and specs (also known as PRDs) for this repository live as Markdown files in `.scratch/`.

## Conventions

- Use one directory per feature: `.scratch/<feature-slug>/`.
- Store the specification at `.scratch/<feature-slug>/spec.md`.
- Store each implementation issue in its own file at `.scratch/<feature-slug>/issues/<NN>-<slug>.md`, numbered from `01`. Do not create one combined ticket file.
- Record triage state in a `Status:` line near the top of each issue file. See `triage-labels.md` for the allowed role strings.
- Append comments and conversation history under a `## Comments` heading at the bottom of the file.

## Publishing to the issue tracker

When a skill says to publish to the issue tracker, create a file under `.scratch/<feature-slug>/`, creating the directory when needed.

## Fetching a ticket

When a skill says to fetch the relevant ticket, read the file at the referenced path. The user will normally provide the path or issue number.

## Wayfinding operations

The `/wayfinder` skill uses one map file and one child file per ticket.

- **Map:** `.scratch/<effort>/map.md`, containing Notes, Decisions-so-far, and Fog.
- **Child ticket:** `.scratch/<effort>/issues/<NN>-<slug>.md`, numbered from `01`, with the question in the body. A `Type:` line records `research`, `prototype`, `grilling`, or `task`. A `Status:` line records `claimed` or `resolved`.
- **Blocking:** Record dependencies in a `Blocked by: NN, NN` line near the top. A ticket becomes unblocked when every listed ticket is `resolved`.
- **Frontier:** Scan `.scratch/<effort>/issues/` for tickets that are open, unblocked, and unclaimed. The lowest ticket number wins.
- **Claim:** Set `Status: claimed` and save the file before starting work.
- **Resolve:** Append the answer under an `## Answer` heading, set `Status: resolved`, and append a short context pointer and link to Decisions-so-far in `map.md`.
