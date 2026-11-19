# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Current state

`Study-04` is an empty directory: no source files, no build/lint/test tooling, no README. There is no architecture to document yet, so update this file once code exists (commands, entry points, how the pieces fit together).

## Repository context

`Study-04` sits in a git repo whose root is `C:\Users\User\Desktop\VibeCoding` (a `.gitignore` is at the root). Sibling directories `Study-01` to `Study-03` are independent study projects, each with its own `CLAUDE.md` and Korean `README.md`:

- `Study-01`: PyTorch MNIST handwriting digit recognition (`train.py`, `model.py`, `draw_and_predict.py`).
- `Study-02`: vanilla HTML/CSS/JS todo app, no build step.
- `Study-03`: vanilla JS quiz app with project slash commands in `.claude/commands/` (`quiz-add`, `quiz-range`, `quiz-validate`).

If Study-04 follows the same pattern, expect a self-contained project in this folder with a Korean README and a project-local `CLAUDE.md`, and commit it as its own `Add Study-04` style commit.
