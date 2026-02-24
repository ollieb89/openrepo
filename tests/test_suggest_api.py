"""
test_suggest_api.py — Unit tests for validateDiffText validation logic.

Ports the TypeScript validateDiffText() from
workspace/occc/src/app/api/suggestions/[id]/action/route.ts
to Python for testability without a full Next.js test harness.

The Python implementation lives only here (test-local) — not a separate module.
"""

import re
import unittest


# ---------------------------------------------------------------------------
# Python port of validateDiffText() from action/route.ts
# ---------------------------------------------------------------------------

MAX_DIFF_LINES = 100

FORBIDDEN_PATTERNS = [
    re.compile(r'cap_drop', re.IGNORECASE),
    re.compile(r'no-new-privileges', re.IGNORECASE),
    re.compile(r'LOCK_TIMEOUT', re.IGNORECASE),
    re.compile(r'shell=', re.IGNORECASE),
    re.compile(r'exec\s*\(', re.IGNORECASE),
    re.compile(r'subprocess', re.IGNORECASE),
    re.compile(r'os\.system', re.IGNORECASE),
    re.compile(r'`[^`]+`'),            # backtick shell commands
    re.compile(r'\$\([^)]+\)'),        # shell substitution $(...)
]


def validate_diff_text(diff_text):
    """
    Validates a diff_text value before applying it to soul-override.md.

    Returns:
        dict with keys:
            - 'valid' (bool)
            - 'reason' (str, only present when valid is False)
    """
    if diff_text is None or diff_text == '':
        return {'valid': False, 'reason': 'diff_text is required and must be a non-empty string'}

    if not isinstance(diff_text, str):
        return {'valid': False, 'reason': 'diff_text must be a string'}

    lines = diff_text.split('\n')
    if len(lines) > MAX_DIFF_LINES:
        return {'valid': False, 'reason': f'Diff exceeds {MAX_DIFF_LINES} lines (got {len(lines)})'}

    for pattern in FORBIDDEN_PATTERNS:
        if pattern.search(diff_text):
            return {'valid': False, 'reason': f'Diff contains forbidden pattern: {pattern.pattern}'}

    return {'valid': True}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestValidateDiffText(unittest.TestCase):

    def test_validate_empty_string(self):
        """Empty string should be invalid — bypassing diff_text is not allowed."""
        result = validate_diff_text('')
        self.assertFalse(result['valid'])
        self.assertIn('required', result['reason'])

    def test_validate_none(self):
        """None should be invalid — same as missing diff_text."""
        result = validate_diff_text(None)
        self.assertFalse(result['valid'])
        self.assertIn('required', result['reason'])

    def test_validate_line_limit(self):
        """A string with 101 lines should be rejected; reason must mention line count."""
        # 101 newlines produce 102 parts after split, but we want exactly 101 lines
        text = '\n'.join([f'line {i}' for i in range(101)])
        self.assertEqual(len(text.split('\n')), 101)
        result = validate_diff_text(text)
        self.assertFalse(result['valid'])
        self.assertIn('101', result['reason'])

    def test_validate_forbidden_backtick(self):
        """Backtick shell command should be rejected."""
        result = validate_diff_text('Run this: `ls -la` to see files')
        self.assertFalse(result['valid'])
        self.assertIn('forbidden pattern', result['reason'])

    def test_validate_forbidden_subprocess(self):
        """The word 'subprocess' should be rejected (injection risk)."""
        result = validate_diff_text("subprocess.run(['rm', '-rf', '/'])")
        self.assertFalse(result['valid'])
        self.assertIn('forbidden pattern', result['reason'])

    def test_validate_forbidden_shell_sub(self):
        """Shell substitution $(...) should be rejected."""
        result = validate_diff_text('User is $(whoami) on host $(hostname)')
        self.assertFalse(result['valid'])
        self.assertIn('forbidden pattern', result['reason'])

    def test_validate_valid_behavioral_note(self):
        """A clean behavioral protocol note should be valid."""
        text = '## BEHAVIORAL PROTOCOLS\n- Always verify file paths.\n'
        result = validate_diff_text(text)
        self.assertTrue(result['valid'])
        self.assertNotIn('reason', result)

    def test_validate_cap_drop_forbidden(self):
        """cap_drop (Docker security constraint removal) should be rejected."""
        result = validate_diff_text('cap_drop: ALL')
        self.assertFalse(result['valid'])
        self.assertIn('forbidden pattern', result['reason'])


if __name__ == '__main__':
    unittest.main()
