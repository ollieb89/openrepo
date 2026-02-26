const { execFileSync } = require('child_process');

/**
 * Dispatches a directive to a target agent via the OpenClaw CLI.
 *
 * @param {string} targetId - The ID of the target agent (e.g., 'pumplai_pm').
 * @param {string} directive - The high-level instruction to execute.
 */
function dispatchDirective(targetId, directive) {
  try {
    console.log(`[Router] Dispatching to ${targetId} :: ${directive}`);

    // Use execFileSync to avoid shell interpretation entirely.
    // Arguments are passed as an array — no shell metacharacter injection possible.
    const output = execFileSync('openclaw', [
      'agent', '--agent', targetId, '--message', directive, '--json'
    ], { encoding: 'utf8', timeout: 300000 });
    const result = JSON.parse(output);
    
    if (result.status === 'ok') {
      console.log(`Directive successfully routed to ${targetId}. Run ID: ${result.runId}`);
      return result;
    } else {
      throw new Error(`Agent returned status: ${result.status}`);
    }
  } catch (error) {
    console.error('Failed to dispatch directive:', error.message);
    // Log the actual error output if available
    if (error.stdout) console.error('STDOUT:', error.stdout);
    if (error.stderr) console.error('STDERR:', error.stderr);
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
  dispatchDirective(targetId, directive);
}

module.exports = { dispatchDirective };
