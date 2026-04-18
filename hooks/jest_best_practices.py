#!/usr/bin/env python3
"""
Claude Code hook to enforce Jest testing best practices:
- don't cast as any or jest.Mock, use proper types
- use jest.mock() with jest.mocked() pattern
- avoid common anti-patterns
"""

import json
import re
import sys
from pathlib import Path


def strip_strings_and_comments(code: str) -> str:
    out = list(code)
    i = 0
    n = len(code)
    state = None
    while i < n:
        ch = code[i]
        if state is None:
            if ch == '/' and i + 1 < n and code[i + 1] == '/':
                while i < n and code[i] != '\n':
                    out[i] = ' '
                    i += 1
                continue
            if ch == '/' and i + 1 < n and code[i + 1] == '*':
                out[i] = ' '
                out[i + 1] = ' '
                i += 2
                while i < n:
                    if code[i] == '*' and i + 1 < n and code[i + 1] == '/':
                        out[i] = ' '
                        out[i + 1] = ' '
                        i += 2
                        break
                    if code[i] != '\n':
                        out[i] = ' '
                    i += 1
                continue
            if ch == "'" or ch == '"':
                state = ch
                i += 1
                continue
            if ch == '`':
                state = '`'
                i += 1
                continue
            i += 1
            continue
        if state == "'" or state == '"':
            if ch == '\\' and i + 1 < n:
                if code[i] != '\n':
                    out[i] = ' '
                if code[i + 1] != '\n':
                    out[i + 1] = ' '
                i += 2
                continue
            if ch == state:
                state = None
                i += 1
                continue
            if ch != '\n':
                out[i] = ' '
            i += 1
            continue
        if state == '`':
            if ch == '\\' and i + 1 < n:
                if code[i] != '\n':
                    out[i] = ' '
                if code[i + 1] != '\n':
                    out[i + 1] = ' '
                i += 2
                continue
            if ch == '$' and i + 1 < n and code[i + 1] == '{':
                i += 2
                depth = 1
                while i < n and depth > 0:
                    c2 = code[i]
                    if c2 == '{':
                        depth += 1
                    elif c2 == '}':
                        depth -= 1
                        if depth == 0:
                            i += 1
                            break
                    i += 1
                continue
            if ch == '`':
                state = None
                i += 1
                continue
            if ch != '\n':
                out[i] = ' '
            i += 1
            continue
    return ''.join(out)


def is_test_file(file_path: str) -> bool:
    """check if file is a jest test file"""
    name = Path(file_path).name.lower()
    return (
        '.test.' in name or
        '.spec.' in name or
        '__tests__' in file_path
    )


def check_mock_casting(scrubbed: str) -> list[str]:
    """check for bad mock type casting patterns"""
    issues = []
    lines = scrubbed.split('\n')

    for line_num, line in enumerate(lines, 1):
        if re.search(r'as\s+jest\.Mock\b', line):
            issues.append(
                f"line {line_num}: don't cast as jest.Mock - use jest.mocked() instead"
            )

        if re.search(r'as\s+any\b', line):
            issues.append(
                f"line {line_num}: don't cast as any - find the correct type or use jest.mocked()"
            )

        if re.search(r'as\s+jest\.MockedFunction', line):
            issues.append(
                f"line {line_num}: use jest.mocked(fn) instead of casting to jest.MockedFunction"
            )

        if re.search(r'as\s+jest\.SpyInstance', line):
            issues.append(
                f"line {line_num}: use jest.spyOn() return type directly, avoid casting"
            )

    return issues


def check_mock_patterns(scrubbed: str) -> list[str]:
    """check for correct mock patterns"""
    issues = []
    lines = scrubbed.split('\n')

    for line_num, line in enumerate(lines, 1):
        if re.search(r'jest\.fn\(\)\s+as\b', line):
            issues.append(
                f"line {line_num}: don't cast jest.fn() - use jest.fn<ReturnType, Args>() for typing"
            )

        if re.search(r'\.mockImplementation\([^)]*\)\s+as\b', line):
            issues.append(
                f"line {line_num}: avoid casting after mockImplementation - type the mock properly"
            )

        if re.search(r':\s*jest\.Mock[<\s]', line) and 'jest.mocked' not in line:
            issues.append(
                f"line {line_num}: prefer jest.mocked(fn) over manual jest.Mock type annotation"
            )

        if re.search(r'\w+\.mockReturnValue\(', line):
            context_start = max(0, line_num - 5)
            context = '\n'.join(lines[context_start:line_num])
            if 'as jest.Mock' in context or 'as any' in context:
                issues.append(
                    f"line {line_num}: ensure mock is typed with jest.mocked() not casting"
                )

    return issues


def check_mock_setup(scrubbed: str) -> list[str]:
    """check for proper mock setup patterns"""
    issues = []
    lines = scrubbed.split('\n')

    has_jest_mock = any(re.search(r'jest\.mock\(', line) for line in lines)

    if has_jest_mock:
        has_jest_mocked = any(re.search(r'jest\.mocked\(', line) for line in lines)

        if not has_jest_mocked:
            for line_num, line in enumerate(lines, 1):
                if re.search(r'require\([^)]*\)\s+as\s+jest\.Mock', line):
                    issues.append(
                        f"line {line_num}: use jest.mocked(import) instead of require with cast"
                    )

    for line_num, line in enumerate(lines, 1):
        if re.search(r'const\s+\w+\s*=\s*\w+\s+as\s+jest\.Mock', line):
            issues.append(
                f"line {line_num}: use 'const mockedFn = jest.mocked(fn)' instead of casting"
            )

    return issues


def check_test_structure(content: str) -> list[str]:
    """check for test structure best practices"""
    issues = []
    lines = content.split('\n')

    for line_num, line in enumerate(lines, 1):
        if re.search(r'expect\([^)]+===?[^)]+\)\.toBe\(true\)', line):
            issues.append(
                f"line {line_num}: use expect(x).toBe(y) or .toEqual(y) instead"
            )

        if re.search(r'it\([^,]+,\s*\([^)]*done[^)]*\)\s*=>', line):
            issues.append(
                f"line {line_num}: prefer async/await over done callback"
            )

    return issues


def validate(file_path: str, content: str) -> list[str]:
    """run all jest best practice checks"""
    if not is_test_file(file_path):
        return []

    scrubbed = strip_strings_and_comments(content)
    all_issues = []
    all_issues.extend(check_mock_casting(scrubbed))
    all_issues.extend(check_mock_patterns(scrubbed))
    all_issues.extend(check_mock_setup(scrubbed))
    all_issues.extend(check_test_structure(content))
    return all_issues


def extract_content(tool_input: dict) -> str:
    edits = tool_input.get('edits')
    if isinstance(edits, list) and edits:
        return '\n'.join(e.get('new_string', '') for e in edits)
    return tool_input.get('new_string', '') or tool_input.get('content', '')


def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    tool_input = input_data.get('tool_input', {})
    file_path = tool_input.get('file_path', '')

    if not file_path:
        sys.exit(0)

    content = extract_content(tool_input)
    if not content:
        sys.exit(0)

    issues = validate(file_path, content)

    if issues:
        print("jest best practices issues:", file=sys.stderr)
        for issue in issues[:8]:
            print(f"  • {issue}", file=sys.stderr)
        if len(issues) > 8:
            print(f"  ... and {len(issues) - 8} more", file=sys.stderr)
        print("", file=sys.stderr)
        print("correct pattern:", file=sys.stderr)
        print("  jest.mock('./module')", file=sys.stderr)
        print("  const mockedFn = jest.mocked(realFn)", file=sys.stderr)
        sys.exit(2)

    sys.exit(0)


if __name__ == '__main__':
    main()
