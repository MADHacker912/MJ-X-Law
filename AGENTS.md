# Instructions & Preferences: Always Use Ponytail

## Core Directive
Whenever the user interacts, asks questions, or requests code to be written, debugged, refactored, or reviewed, **ALWAYS** activate and adhere strictly to the **`ponytail`** skill and methodology (default intensity: **full**).

## The Ponytail Ladder
Before writing any code or architecture, stop at the first rung that holds:
1. **Does this need to exist at all? (YAGNI)**: If it's a speculative need, skip it and say so in one line.
2. **Already in this codebase?**: Reuse existing helpers, utils, types, or patterns already present. Look before writing.
3. **Stdlib does it?**: Use standard library features.
4. **Native platform feature covers it?**: Use native platform capabilities (CSS, HTML inputs, DB constraints, etc.).
5. **Already-installed dependency solves it?**: Reuse existing dependencies; do not add new dependencies if simple code suffices.
6. **Can it be one line?**: Make it one line.
7. **Only then**: Minimum code that works.

## Rules
- **No unrequested abstractions**: No one-off interfaces, no premature wrappers/factories, no unused boilerplate or scaffolding.
- **Deletion over addition**: Boring over clever. Fewest files possible. Shortest working diff wins.
- **Root cause fixes**: Fix bugs at the shared source/root cause, not symptom patching across callers.
- **Output format**: Code first. Then at most three short lines explaining what was skipped and when to add it: `[code] → skipped: [X], add when [Y].` No unrequested essays or lecture text.
- **Turn off condition**: Only disabled if the user explicitly says "stop ponytail" or "normal mode".
