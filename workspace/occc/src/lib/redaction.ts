/**
 * Sensitive Data Redaction
 *
 * Redacts API keys, tokens, passwords, and other sensitive information from log strings.
 */

// Patterns for sensitive data
const SENSITIVE_PATTERNS = [
  // API keys (common formats)
  /(['"`]?)(api[_-]?key|apikey|token|secret|password|pass)['"`]?\s*[:=]\s*['"`]?([a-zA-Z0-9_-]{20,})['"`]?/gi,
  // Bearer tokens
  /bearer\s+([a-zA-Z0-9._-]+)/gi,
  // JWT tokens
  /eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*/g,
  // Generic key-value pairs with long values
  /(['"`]?)([a-zA-Z_][a-zA-Z0-9_]*['"`]?\s*[:=]\s*['"`]?)([a-zA-Z0-9+/]{40,})['"`]?/gi,
  // Email addresses (optional)
  /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g,
];

/**
 * Redact sensitive data from a log line
 */
export function redactSensitiveData(logLine: string): string {
  let redacted = logLine;

  for (const pattern of SENSITIVE_PATTERNS) {
    redacted = redacted.replace(pattern, (match, ...groups) => {
      // Preserve the structure but replace sensitive values
      if (groups.length >= 3) {
        return `${groups[0]}${groups[1]}[REDACTED]`;
      } else if (groups.length === 1) {
        return '[REDACTED]';
      } else {
        return '[REDACTED]';
      }
    });
  }

  return redacted;
}
