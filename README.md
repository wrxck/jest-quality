# jest-quality

Enforce Jest testing best practices in Claude Code sessions.

## What it checks

- No casting to `jest.Mock` or `any` in tests -- use `jest.mocked()` instead
- No `jest.fn() as` casts -- use `jest.fn<ReturnType, Args>()` for typing
- Proper `jest.mock()` with `jest.mocked()` pattern instead of manual type casts
- Test structure: prefer specific matchers, async/await over done callbacks

## Installation

```
claude plugin marketplace add wrxck/claude-plugins
claude plugin install jest-quality@wrxck-claude-plugins
```
