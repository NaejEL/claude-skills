# hcore - deterministic core of the claude-skills skills.
#
# Python standard library only, 3.9 compatible. This package holds the
# deterministic rules taken out of the SKILL.md files (parsing of JSON blocks,
# counters, registry, cycle journal, relaunch of a dead agent, file merges,
# ship-pr gh/git sequences). The prompts keep only the judgment.
#
# Single entry point: harness.py (CLI), next to this package.

CORE_VERSION = "1.0.0"
