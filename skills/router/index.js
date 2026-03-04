const fs = require('fs');
const os = require('os');
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

/**
 * Returns true if the directive is administrative (status, monitoring, logs, etc.)
 * and should bypass the topology approval gate.
 *
 * Administrative directives do not spawn L3 containers and must never be blocked
 * by the approval gate — blocking them would prevent operators from diagnosing issues.
 *
 * @param {string} directive
 * @returns {boolean}
 */
function isAdministrative(directive) {
  const adminPrefixes = ['status', 'monitor', 'log', 'list', 'health'];
  const lower = directive.toLowerCase().trim();
  return adminPrefixes.some(prefix => lower.startsWith(prefix));
}

/**
 * Returns true if an approved topology exists for the given project.
 *
 * Checks for `workspace/.openclaw/<projectId>/topology/current.json` under
 * the workspaceRoot. This file is created by approve_topology() (approval.py)
 * after the user accepts a proposal. Its presence is the gate condition.
 *
 * @param {string} projectId - The project identifier.
 * @param {string} workspaceRoot - Root directory containing the workspace folder.
 * @returns {boolean}
 */
function hasApprovedTopology(projectId, workspaceRoot) {
  const topoPath = path.join(
    workspaceRoot, 'workspace', '.openclaw', projectId, 'topology', 'current.json'
  );
  return fs.existsSync(topoPath);
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

  // Approval gate check (CORR-07): block L3 spawning directives when no approved topology exists.
  // Administrative directives (status, monitor, log, list, health) bypass the gate — these must
  // never be blocked since operators need them to diagnose issues even without a topology.
  // Propose directives are handled below and also bypass the gate (they create the topology).
  const autoApproveL1 = config.topology?.auto_approve_l1 ?? false;
  const proposeDirective = directive.match(/\bpropose\b/i) || targetId === '__propose__';

  if (!autoApproveL1 && !proposeDirective && !isAdministrative(directive)) {
    const projectId = config.active_project || process.env.OPENCLAW_PROJECT || '';
    const workspaceRoot = process.env.OPENCLAW_ROOT || path.join(os.homedir(), '.openclaw');
    if (projectId && !hasApprovedTopology(projectId, workspaceRoot)) {
      throw new DispatchError(
        targetId,
        `No approved topology for project '${projectId}'. Run 'openclaw-propose' to generate and approve a topology.`
      );
    }
  }

  // Detect 'propose' directives — route through gateway HTTP API
  // This handles both __propose__ sentinel target and directives containing "propose"
  const proposeMatch = directive.match(/\bpropose\b/i);
  if (proposeMatch || targetId === '__propose__') {
    console.log(`[Router] Routing to openclaw-propose engine via gateway`);
    try {
      // Extract the outcome from the directive (everything after "propose")
      const outcomeMatch = directive.match(/\bpropose\b\s+(.+)/i);
      const outcomeMessage = outcomeMatch ? outcomeMatch[1] : directive;
      const response = await fetch(`${gatewayUrl}/api/agent/__propose__/message`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ message: outcomeMessage }),
        signal: AbortSignal.timeout(300_000), // 5 min
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new DispatchError('__propose__', error.message || response.statusText);
      }
      return await response.json();
    } catch (err) {
      if (err instanceof DispatchError) throw err;
      console.error('[Router] Gateway propose dispatch failed:', err.message);
      if (err.name === 'TypeError' || err.message.includes('fetch failed') || err.message.includes('ECONNREFUSED')) {
        throw new DispatchError('__propose__', `Gateway unreachable at localhost:${gatewayPort}. Start it with: openclaw gateway start`);
      }
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
    console.log(`[Router] Gateway dispatch failed: ${error.message}`);
    if (error instanceof DispatchError) {
      throw error;
    }
    if (error.name === 'TypeError' || error.message.includes('fetch failed') || error.message.includes('ECONNREFUSED')) {
      throw new DispatchError(targetId, `Gateway unreachable at localhost:${gatewayPort}. Start it with: openclaw gateway start`);
    }
    throw error;
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

module.exports = { dispatchDirective, hasApprovedTopology, isAdministrative };
