const { execSync } = require('child_process');

/**
 * Dispatches a directive to a target agent via the OpenClaw CLI.
 * 
 * @param {string} targetId - The ID of the target agent (e.g., 'pumplai_pm').
 * @param {string} directive - The high-level instruction to execute.
 */
function dispatchDirective(targetId, directive) {
  try {
    console.log(`[Router] Dispatching to ${targetId} :: ${directive}`);
    
    // Construct the openclaw command
    // We use --json to get a machine-readable response
    const command = `openclaw agent --agent ${targetId} --message "${directive.replace(/"/g, '\\"')}" --json`;
    
    const output = execSync(command, { encoding: 'utf8' });
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
    process.exit(1);
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
