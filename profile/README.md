# Profile

`profile.example.yml` is the schema. `PROFILE.template.md` is the shape of the human-readable fit model. `profile.yml` may use nested maps, inline lists, and block lists. `tools/check_setup.py` parses that subset and reports empty gates.

Setup copies the example to `profile.yml` and writes `PROFILE.md`. Both real files are gitignored. Until `status` is `ready`, the agent follows `SETUP.md` and does not search.
