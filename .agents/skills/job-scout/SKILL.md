---
name: job-scout
description: Discover, verify and record new roles that pass the person's gates, including wide searches beyond the existing employer catalogue.
---

# job-scout

Use this workspace's maintained job-search workflow. The person's identity, accounts, tracker and paths are in `workspace.json`; their positioning, preferences and sources are in `profile/`.

The workspace root is three directories above this skill directory. Resolve the links below from this file, not from the caller's working directory.

1. Read [AGENTS.md](../../../AGENTS.md), then [playbooks/README.md](../../../playbooks/README.md) and the `profile/` files the playbook names.
2. Follow [playbooks/job-scout.md](../../../playbooks/job-scout.md). This is the canonical workflow; do not copy its instructions into this skill or an agent-specific command.
3. Use the user's accompanying request as arguments: `[N picks | focus]`. If omitted, use the playbook's defaults. Literal template text such as `$ARGUMENTS` or the argument hint is not a supplied argument.
   Requests to expand the lookup, find unturned stones or improve thin discovery use the playbook's wide discovery mode. Broaden sources and search vocabulary while preserving the person's current role and contract scope.
4. Use the tools available to the current agent. Preserve the playbook's evidence, personal-account and authorization boundaries. If a required source is inaccessible, record that gap; do not infer a successful check.

Routine tracker upkeep follows the standing authority recorded in AGENTS.md and `profile/PREFERENCES.md`, if any. This does not authorize sending messages, submitting applications, scheduling calls, uploading a CV or changing consents.
