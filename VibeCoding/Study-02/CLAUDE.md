# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`Study-02` is a Korean-language todo app in plain HTML, CSS and vanilla JavaScript. No build step, package manager, linter or test suite, and no external libraries or network requests. Run it by opening `index.html` in a browser (it also works over `file://`). `Study-01` in the parent repo is an unrelated project. The README is in Korean.

## Architecture

`index.html` loads `style.css` and `app.js` directly; there are no modules. `app.js` is ordered: storage, state, state-changing functions, render, event wiring.

- State lives in `todos` (array of `{id, text, category, done, createdAt}`), `currentFilter` (`all|work|personal|study`, not persisted) and `editingId`.
- Every mutation follows the same order: modify the array, `saveTodos()`, then `render()`. `render()` rebuilds the whole list and also updates filter tab highlighting and the progress bar/text (progress is computed over the *filtered* items).
- `loadTodos()` / `saveTodos()` are the only code that touches `localStorage` (key `todos`). Corrupt JSON or a non-array yields `[]`; an unavailable `localStorage` shows the `#storage-warning` banner instead of breaking the app.
- User text is always inserted with `textContent`, never `innerHTML`.
- Inline editing: `startEdit` sets `editingId`, `render()` swaps in an input and a category select. `commitEdit` guards on `editingId === id` so Enter, blur (`focusout` that leaves the `<li>`) and Esc cannot double-fire during the re-render.

## Categories

Category values are `work`, `personal`, `study`; labels are in `CATEGORY_LABELS` in `app.js`. Adding one means touching `index.html` (`<option>` and filter tab `data-filter`), `CATEGORY_LABELS`, and a `.badge-<value>` rule plus color variable in `style.css`.
