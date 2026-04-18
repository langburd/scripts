# AGENTS.md

This file provides guidance to AI coding assistants when working with code in this repository.

## What this repo is

A collection of standalone DevOps utility scripts — mostly Bash (~70%), some Python 3.12 (~30%) — organized by domain (`git/`, `aws_config/`, `kubeconfig/`, `mac/`). Each script is independent. This is not a library; there are no shared modules or entry points.

## Verifying changes

Run `pre-commit run --all-files` before considering a change done. Pre-commit is the single source of truth for lint/format; it runs:

- Bash: `shellcheck`, `shfmt` (indent 4)
- Python: `black` (line-length 100), `flake8`, `isort` (black profile), `pylint` (fail-under 9.8), `pyright`
- Markdown: `markdownlint` (MD013 disabled)
- Misc: large-file / merge-conflict / YAML / trailing-whitespace / line-ending checks

Match these settings when writing new code — don't introduce a different formatter or line length.

## Runtime caveat

Many scripts call live AWS, GitHub, Azure, or Kubernetes APIs with the user's real credentials. Do not execute them to "test" a change — read the code and rely on pre-commit for verification. Only run a script when the user explicitly asks.

## Script inputs

Scripts take inputs from environment variables (e.g., `GITHUB_TOKEN`, `ORGANIZATION`, `TARGET_DIRECTORY`), not config files or flags. When adding a new script, follow the same pattern rather than introducing argparse or a config file.
