const { execFileSync } = require('child_process');
const fs = require('fs');
const path = require('path');

function getConfig() {
  try {
    const configPath = process.env.OPENCLAW_ROOT 
      ? path.join(process.env.OPENCLAW_ROOT, 'openclaw.json')
      : path.join(process.env.HOME || process.env.USERPROFILE, '.openclaw', 'openclaw.json');
    if (fs.existsSync(configPath)) {
      return JSON.parse(fs.readFileSync(configPath, 'utf8'));
    }
  } catch (err) {
    // Ignore error and return empty config
  }
  return {};
}

class DispatchError extends Error {
  constructor(targetId, message) {
    super(`[${targetId}] ${message}`);
    this.name = 'DispatchError';
    this.targetId = targetId;
  }
}

/**
 * Dispatches a directive to a target agent via the OpenClaw CLI or Gateway.
 *
 * @param {string} targetId - The ID of the target agent (e.g., 'pumplai_pm').
 * @param {string} directive - The high-level instruction to execute.
 */
async function dispatchDirective(targetId, directive) {
  const config = getConfig();
  const gatewayPort = config.gateway?.port || 18789;
  const gatewayUrl = `http://localhost:${gatewayPort}`;
  const token = process.env.OPENCLAW_GATEWAY_TOKEN || (config.gateway?.auth?.token || config.gateway?.token || '');

  console.log(`[Router] Dispatching to ${targetId} :: ${directive}`);

  // Detect 'propose' directives — route to openclaw-propose CLI directly
  // This handles both __propose__ sentinel target and directives containing "propose"
  const proposeMatch = directive.match(/\bpropose\b/i);
  if (proposeMatch || targetId === '__propose__') {
    console.log(`[Router] Routing to openclaw-propose engine`);
    try {
      const args = ['--json'];
      // Extract the outcome from the directive (everything after "propose")
      const outcomeMatch = directive.match(/\bpropose\b\s+(.+)/i);
      if (outcomeMatch) {
        args.unshift(outcomeMatch[1]);
      } else if (targetId !== '__propose__') {
        // directive is the outcome itself (no "propose" keyword in outcome position)
        args.unshift(directive);
      }
      const output = execFileSync('openclaw-propose', args, {
        encoding: 'utf8',
        timeout: 300000,
      });
      return JSON.parse(output);
    } catch (err) {
      console.error('[Router] openclaw-propose failed:', err.message);
      throw new DispatchError('__propose__', err.message);
    }
  }

  try {
    const response = await fetch(`${gatewayUrl}/api/agent/${targetId}/message`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({ message: directive }),
      signal: AbortSignal.timeout(300_000), // 5 min
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new DispatchError(targetId, error.message || response.statusText);
    }

    const result = await response.json();
    console.log(`Directive successfully routed to ${targetId} via Gateway. Run ID: ${result.runId || result.run_id}`);
    return result;
  } catch (error) {
    console.log(`[Router] Gateway dispatch failed (${error.message}), falling back to execFileSync...`);
    
    // Fallback path
    try {
      const output = execFileSync('openclaw', [
        'agent', '--agent', targetId, '--message', directive, '--json'
      ], { encoding: 'utf8', timeout: 300000 });
      const result = JSON.parse(output);
      
      if (result.status === 'ok') {
        console.log(`Directive successfully routed to ${targetId} via CLI. Run ID: ${result.runId || result.run_id}`);
        return result;
      } else {
        throw new Error(`Agent returned status: ${result.status}`);
      }
    } catch (fallbackError) {
      console.error('Failed to dispatch directive via fallback:', fallbackError.message);
      if (fallbackError.stdout) console.error('STDOUT:', fallbackError.stdout);
      if (fallbackError.stderr) console.error('STDERR:', fallbackError.stderr);
      throw fallbackError;
    }
  }
}

// CLI execution handling
if (require.main === module) {
  const [,, targetId, directive] = process.argv;
  if (!targetId || !directive) {
    console.error('Usage: node index.js <targetId> <directive>');
    process.exit(1);
  }
  dispatchDirective(targetId, directive).catch(() => process.exit(1));
}

module.exports = { dispatchDirective };
