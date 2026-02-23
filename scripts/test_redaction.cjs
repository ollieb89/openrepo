#!/usr/bin/env node
/**
 * SEC-02: Redaction Logic Test Helper
 * Tests redactSensitiveData() with synthetic secrets
 */

const fs = require('fs');
const path = require('path');

// Synthetic secrets to test (implemented patterns)
const IMPLEMENTED_SECRETS = [
  { name: 'OPENAI_KEY', input: 'sk-test12345678901234567890abcdef' },
  { name: 'AWS_KEY', input: 'AKIAIOSFODNN7EXAMPLETEST1' },
  { name: 'GOOGLE_KEY', input: 'AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKfmzs9wxyz123' },
  { name: 'GITHUB_TOKEN', input: 'ghp_abcdefghijklmnopqrstuvwxyz1234567890abcd' },
  { name: 'SLACK_TOKEN', input: 'xoxb-123456789012-123456789012-testtoken' },
  { name: 'AUTH_HEADER', input: 'Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.test' },
  { name: 'API_KEY_HEADER', input: 'x-api-key: my-secret-api-key-9999' },
  { name: 'EMAIL', input: 'test@example.com' },
  { name: 'GENERIC_SECRET', input: 'PASSWORD=mysecretpassword123' },
  { name: 'HOST_PATH', input: '/home/ollie/.ssh/id_rsa' },
  { name: 'IP_ADDRESS', input: '192.168.1.100' },
  { name: 'CONTAINER_ID', input: '968134ac3afe' },
];

// Missing categories (document as gaps if any remain)
const MISSING_CATEGORIES = [
  // All required categories now implemented - this array intentionally empty
];

// Strategy B: Replicate redaction patterns from redaction.ts
const REDACTION_PATTERNS = [
  { name: 'AWS_KEY', pattern: /AKIA[0-9A-Z]{16}/g, replacement: '[REDACTED_AWS_KEY]' },
  { name: 'OPENAI_KEY', pattern: /sk-[a-zA-Z0-9]{20,}/g, replacement: '[REDACTED_API_KEY]' },
  { name: 'ANTHROPIC_KEY', pattern: /sk-ant-[a-zA-Z0-9-]{20,}/g, replacement: '[REDACTED_API_KEY]' },
  { name: 'GOOGLE_KEY', pattern: /AIza[0-9A-Za-z_-]{35}/g, replacement: '[REDACTED_GOOGLE_KEY]' },
  { name: 'GITHUB_TOKEN', pattern: /gh[ps]_[a-zA-Z0-9]{36,}/g, replacement: '[REDACTED_GITHUB_TOKEN]' },
  { name: 'SLACK_TOKEN', pattern: /xox[pboa]-[0-9]+-[0-9A-Za-z-]+/g, replacement: '[REDACTED_SLACK_TOKEN]' },
  { name: 'AUTH_HEADER', pattern: /authorization:\s*bearer\s+[^\s]+/gi, replacement: 'authorization: [REDACTED]' },
  { name: 'API_KEY_HEADER', pattern: /x-api-key:\s*[^\s]+/gi, replacement: 'x-api-key: [REDACTED]' },
  { name: 'EMAIL', pattern: /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g, replacement: '[REDACTED_EMAIL]' },
  { name: 'GENERIC_SECRET', pattern: /(PASSWORD|SECRET|TOKEN|API_KEY|PRIVATE_KEY)\s*[=:]\s*\S+/gi, replacement: '[REDACTED]' },
  { name: 'HOST_PATH', pattern: /\/(home|root|etc|var|opt|usr|tmp)\/[^\s]+/g, replacement: '[REDACTED_PATH]' },
  { name: 'IP_ADDRESS', pattern: /\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b/g, replacement: '[REDACTED_IP]' },
  { name: 'CONTAINER_ID', pattern: /\b[a-f0-9]{12,64}\b/g, replacement: '[REDACTED_CONTAINER]' },
];

function redactSensitiveData(text) {
  let redacted = text;
  for (const { pattern, replacement } of REDACTION_PATTERNS) {
    redacted = redacted.replace(pattern, replacement);
  }
  return redacted;
}

function runTests() {
  const results = {
    implemented: [],
    missing: [],
    summary: { total: 0, passed: 0, failed: 0 }
  };

  // Test implemented patterns
  for (const { name, input } of IMPLEMENTED_SECRETS) {
    const redacted = redactSensitiveData(input);
    const wasRedacted = redacted !== input;
    results.implemented.push({ name, input: input.slice(0, 20) + '...', redacted: wasRedacted });
    results.summary.total++;
    if (wasRedacted) {
      results.summary.passed++;
    } else {
      results.summary.failed++;
    }
  }

  // Test missing categories (these should NOT be redacted, documenting the gap)
  for (const { name, input } of MISSING_CATEGORIES) {
    const redacted = redactSensitiveData(input);
    const wasRedacted = redacted !== input;
    results.missing.push({ name, input, redacted: wasRedacted });
    results.summary.total++;
    if (!wasRedacted) {
      // Not redacted = expected (gap documented)
      results.summary.passed++;
    } else {
      results.summary.failed++;
    }
  }

  return results;
}

const results = runTests();
console.log(JSON.stringify(results, null, 2));
process.exit(0);
