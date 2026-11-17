---
name: job-setup
description: Interview a new person and generate their private job-search workspace configuration (workspace.json, profile files, AGENTS.md, tracker tabs) from this kit.
---

# job-setup

The workspace root is three directories above this skill directory. Resolve the links below from this file, not from the caller's working directory.

1. Follow [SETUP.md](../../../SETUP.md). It is the canonical onboarding interview; do not copy its steps here.
2. Use the user's accompanying request as arguments (for example a pasted CV or `resume` to continue an unfinished setup). Literal template text such as `$ARGUMENTS` is not an argument.
3. Create no files until the person confirms the summary. Do not create the tracker spreadsheet, read their accounts, or run a live status or scout pass without their explicit instruction.
