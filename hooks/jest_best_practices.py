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


def is_test_file(file_path: str) -> bool:
    """check if file is a jest test file"""
    name = Path(file_path).name.lower()
    return (
        '.test.' in name or
        '.spec.' in name or
        '__tests__' in file_path
    )


def check_mock_casting(content: str) -> list[str]:
    """check for bad mock type casting patterns"""
    issues = []
    lines = content.split('\n')

    for line_num, line in enumerate(lines, 1):
        # check for casting to jest.Mock
        if re.search(r'as\s+jest\.Mock\b', line):
            issues.append(
                f"line {line_num}: don't cast as jest.Mock - use jest.mocked() instead"
            )

        # check for casting to any in test context
        if re.search(r'as\s+any\b', line):
            # skip if it's in a comment
            if not line.strip().startswith('//'):
                issues.append(
                    f"line {line_num}: don't cast as any - find the correct type or use jest.mocked()"
                )

        # check for (fn as jest.MockedFunction<...>)
        if re.search(r'as\s+jest\.MockedFunction', line):
            issues.append(
                f"line {line_num}: use jest.mocked(fn) instead of casting to jest.MockedFunction"
            )

        # check for (fn as jest.SpyInstance)
        if re.search(r'as\s+jest\.SpyInstance', line):
            issues.append(
                f"line {line_num}: use jest.spyOn() return type directly, avoid casting"
            )

    return issues


def check_mock_patterns(content: str) -> list[str]:
    """check for correct mock patterns"""
    issues = []
    lines = content.split('\n')

    for line_num, line in enumerate(lines, 1):
        # check for jest.fn() with manual type casting
        if re.search(r'jest\.fn\(\)\s+as\b', line):
            issues.append(
                f"line {line_num}: don't cast jest.fn() - use jest.fn<ReturnType, Args>() for typing"
            )

        # check for .mockImplementation with casting
        if re.search(r'\.mockImplementation\([^)]*\)\s+as\b', line):
            issues.append(
                f"line {line_num}: avoid casting after mockImplementation - type the mock properly"
            )

        # check for manual Mock type annotations that should use jest.mocked
        if re.search(r':\s*jest\.Mock[<\s]', line) and 'jest.mocked' not in line:
            issues.append(
                f"line {line_num}: prefer jest.mocked(fn) over manual jest.Mock type annotation"
            )

        # check for mockReturnValue on non-mocked function (common mistake)
        if re.search(r'\w+\.mockReturnValue\(', line):
            # this is fine if using jest.mocked, flag if casting
            context_start = max(0, line_num - 5)
            context = '\n'.join(lines[context_start:line_num])
            if 'as jest.Mock' in context or 'as any' in context:
                issues.append(
                    f"line {line_num}: ensure mock is typed with jest.mocked() not casting"
                )

    return issues


def check_mock_setup(content: str) -> list[str]:
    """check for proper mock setup patterns"""
    issues = []
    lines = content.split('\n')

    # look for jest.mock calls and verify jest.mocked usage
    has_jest_mock = any(re.search(r'jest\.mock\([\'"]', line) for line in lines)

    if has_jest_mock:
        has_jest_mocked = any(re.search(r'jest\.mocked\(', line) for line in lines)

        if not has_jest_mocked:
            # check if they're using the old pattern
            for line_num, line in enumerate(lines, 1):
                if re.search(r'require\([\'"][^\'"]+[\'"]\)\s+as\s+jest\.Mock', line):
                    issues.append(
                        f"line {line_num}: use jest.mocked(import) instead of require with cast"
                    )

    # check for manual mock implementations that could use jest.mocked
    for line_num, line in enumerate(lines, 1):
        # pattern: const mockedX = someImport as jest.Mock
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
        # check for expect().toBe(true/false) anti-pattern
        if re.search(r'expect\([^)]+\)\.toBe\((true|false)\)', line):
            issues.append(
                f"line {line_num}: prefer .toBeTruthy()/.toBeFalsy() or more specific matchers"
            )

        # check for expect(x === y).toBe(true)
        if re.search(r'expect\([^)]+===?[^)]+\)\.toBe\(true\)', line):
            issues.append(
                f"line {line_num}: use expect(x).toBe(y) or .toEqual(y) instead"
            )

        # check for done callback (prefer async/await)
        if re.search(r'it\([^,]+,\s*\([^)]*done[^)]*\)\s*=>', line):
            issues.append(
                f"line {line_num}: prefer async/await over done callback"
            )

    return issues


def validate(file_path: str, content: str) -> list[str]:
    """run all jest best practice checks"""
    if not is_test_file(file_path):
        return []

    all_issues = []
    all_issues.extend(check_mock_casting(content))
    all_issues.extend(check_mock_patterns(content))
    all_issues.extend(check_mock_setup(content))
    all_issues.extend(check_test_structure(content))
    return all_issues


def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    tool_input = input_data.get('tool_input', {})
    file_path = tool_input.get('file_path', '')

    if not file_path:
        sys.exit(0)

    content = tool_input.get('new_string', '') or tool_input.get('content', '')
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
