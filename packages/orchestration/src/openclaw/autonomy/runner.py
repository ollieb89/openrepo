import os
import sys
import json
import time
import asyncio
import subprocess
import logging
import re
from typing import Dict, Any, List, Optional

# Ensure openclaw package is in path (since this runs inside the L3 container mounted at /openclaw_src)
sys.path.insert(0, '/openclaw_src')

from openclaw.state_engine import JarvisState
from openclaw.autonomy.events import (
    AutonomyEventBus,
    AutonomyPlanGenerated,
    AutonomyProgressUpdated,
    AutonomyConfidenceUpdated,
    AutonomyEscalationTriggered,
    AutonomyToolsSelected,
    AutonomyCourseCorrection,
)

logger = logging.getLogger("autonomy.runner")

class AutonomyRunner:
    """
    Executes the self-directed task breakdown, validation, and inline sequential
    execution loop for an L3 agent.
    """
    def __init__(self):
        self.task_id = os.environ.get("TASK_ID", "unknown")
        self.task_description = os.environ.get("TASK_DESCRIPTION", "")
        self.cli_runtime = os.environ.get("CLI_RUNTIME", "claude-code")
        self.state_file = os.environ.get("OPENCLAW_STATE_FILE")
        self.soul_file = os.environ.get("SOUL_FILE")
        self.max_retries = int(os.environ.get("AUTONOMY_MAX_RETRIES", "1"))
        self.confidence_threshold = float(os.environ.get("AUTONOMY_CONFIDENCE_THRESHOLD", "0.4"))
        self.confidence_score = 1.0
        self.active_tools = []

    def _detect_deviation(self, success: bool, output: str, duration: float) -> bool:
        """Detect if a step has deviated from expected progress using heuristics."""
        # Explicit failure
        if not success:
            logger.info(f"Deviation detected: Step failed (success={success})")
            return True

        # Time-based threshold (180 seconds = 3 minutes)
        if duration > 180:
            logger.info(f"Deviation detected: Step took {duration:.1f}s (threshold: 180s)")
            return True

        # Error keyword density
        lower_output = output.lower()
        error_count = (
            lower_output.count("error") +
            lower_output.count("exception") +
            lower_output.count("traceback")
        )
        if error_count > 3:
            logger.info(f"Deviation detected: High error density ({error_count} error keywords)")
            return True

        return False

    def _reflect_and_correct(self, failed_step: Dict[str, Any], output: str) -> List[Dict[str, Any]]:
        """Use LLM reflection to generate recovery steps for a deviation."""
        logger.info(f"Initiating course correction for step: {failed_step.get('action', 'unknown')}")

        prompt = f"""
The following step has deviated from expected progress:

Action: {failed_step.get('action', 'No action specified')}
Expected Outcome: {failed_step.get('expected_outcome', 'No expected outcome specified')}
Output/Error (truncated): {output[-1500:] if len(output) > 1500 else output}

Analyze why this step failed and provide a recovery plan. Output your response as a JSON object containing a "steps" array with 1-2 recovery steps.

Each step should have:
- "id": A unique identifier string
- "action": A clear description of what to do
- "expected_outcome": What completing this step should achieve

Return ONLY the JSON block, no other text.
"""

        response = self._invoke_cli(prompt)
        plan = self._extract_json(response)

        if plan and "steps" in plan and isinstance(plan["steps"], list):
            recovery_steps = plan["steps"]
            logger.info(f"Course correction generated {len(recovery_steps)} recovery steps")
            return recovery_steps

        logger.warning("Course correction: Failed to generate recovery steps from LLM reflection")
        return []

    def _analyze_tool_requirements(self) -> List[str]:
        """Analyze the task description to determine necessary tool categories."""
        logger.info("Analyzing task intent to determine tool constraints")
        prompt = f"""
Analyze the following task and determine which tool categories are strictly necessary to complete it.
Available categories: ["file_read", "file_write", "shell_execution", "web_search", "git_operations"]
Reply ONLY with a JSON array of the required categories as strings. If you are unsure, reply with ["all"].

TASK:
{self.task_description}
"""
        output = self._invoke_cli(prompt)
        tools = self._extract_json(output)
        
        if not tools or not isinstance(tools, list):
            logger.warning("Tool analysis failed or returned invalid format. Defaulting to ['all']")
            tools = ["all"]
            
        logger.info(f"Tool analysis selected: {tools}")
        
        # Emit event
        AutonomyEventBus.emit(AutonomyToolsSelected(
            task_id=self.task_id,
            selected_tools=tools
        ))
        
        return tools

    def _build_tool_constraint_prompt(self, tools: List[str]) -> str:
        """Build the constraint string based on selected tools."""
        if not tools or "all" in tools:
            return ""
        return f"\n\nCRITICAL INSTRUCTION: For this task, you are STRICTLY LIMITED to the following tool categories: {', '.join(tools)}. Do not use any other tools."

    def _invoke_cli(self, prompt: str, timeout: int = 600) -> str:
        """Invoke the CLI runtime non-interactively."""
        cmd = [self.cli_runtime]
        if self.soul_file and os.path.exists(self.soul_file):
            if self.cli_runtime in ["claude-code", "codex"]:
                with open(self.soul_file, 'r') as f:
                    soul_content = f.read()
                cmd.extend(["--system-prompt", soul_content])
                
        # Use print to get a one-off response
        cmd.extend(["--print", prompt])
        
        logger.info(f"Invoking CLI for prompt (length: {len(prompt)})")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            if result.returncode != 0:
                logger.error(f"CLI failed (exit code {result.returncode}): {result.stderr}")
                return ""
            return result.stdout
        except subprocess.TimeoutExpired:
            logger.error("CLI invocation timed out")
            return ""
        except Exception as e:
            logger.error(f"Failed to invoke CLI: {e}")
            return ""

    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON block from text."""
        # Try to find ```json block
        match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if match:
            json_str = match.group(1)
        else:
            # Fallback: try to parse the whole string
            json_str = text
            
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}\nContent: {text[:200]}...")
            return None

    def planning_phase(self) -> List[Dict[str, Any]]:
        """
        Generate execution plan using LLM, validate it, and emit event.
        """
        prompt = f"""
You are an autonomous L3 specialist. Before executing the following task, you must break it down into a sequence of executable steps.
Output your plan strictly as a JSON object containing a "steps" array.
Each step should have an "id" (string), "action" (string description of what to do), and "expected_outcome" (string).

TASK:
{self.task_description}

Return ONLY the JSON block.{self._build_tool_constraint_prompt(self.active_tools)}
"""
        
        for attempt in range(self.max_retries + 1):
            logger.info(f"Planning pass (attempt {attempt + 1})")
            output = self._invoke_cli(prompt)
            plan = self._extract_json(output)
            
            if plan and "steps" in plan:
                # Validation pass (LLM self-reflection)
                logger.info("Executing self-reflection validation pass")
                val_prompt = f"Review the following execution plan for logical flaws. If it is sound, reply exactly with 'VALID'. If it has flaws, reply with a revised JSON plan.\nPlan:\n{json.dumps(plan)}"
                val_output = self._invoke_cli(val_prompt)
                
                if val_output.strip().upper().startswith("VALID"):
                    logger.info("Plan validated successfully")
                    # Emit event
                    AutonomyEventBus.emit(AutonomyPlanGenerated(
                        task_id=self.task_id,
                        plan=plan
                    ))
                    return plan["steps"]
                else:
                    revised_plan = self._extract_json(val_output)
                    if revised_plan and "steps" in revised_plan:
                        logger.info("Plan revised during validation")
                        AutonomyEventBus.emit(AutonomyPlanGenerated(
                            task_id=self.task_id,
                            plan=revised_plan
                        ))
                        return revised_plan["steps"]
            
            logger.warning("Invalid plan generated, retrying...")
            
        logger.error("Failed to generate a valid plan after max retries")
        return []

    async def _heartbeat(self, step_number: int, total_steps: int):
        """Emit heartbeat events for long-running steps."""
        start_time = time.time()
        while True:
            await asyncio.sleep(30)
            elapsed = time.time() - start_time
            AutonomyEventBus.emit(AutonomyProgressUpdated(
                task_id=self.task_id,
                step_number=step_number,
                total_steps=total_steps,
                status="running",
                duration_seconds=elapsed,
                output_snippet="Heartbeat: Step is still executing..."
            ))

    async def execute_step(self, step: Dict[str, Any], step_num: int, total_steps: int) -> tuple[bool, str]:
        """Execute a single plan step."""
        logger.info(f"Executing step {step_num}/{total_steps}: {step.get('action')}")
        
        prompt = f"""
You are executing step {step_num} of {total_steps} for task {self.task_id}.
Action: {step.get('action')}
Expected Outcome: {step.get('expected_outcome')}

Please execute this step now using your available tools. Reply with a summary of the outcome.{self._build_tool_constraint_prompt(self.active_tools)}
"""
        start_time = time.time()
        heartbeat_task = asyncio.create_task(self._heartbeat(step_num, total_steps))
        
        # Execute in executor to not block asyncio loop (since _invoke_cli is sync)
        loop = asyncio.get_event_loop()
        output = await loop.run_in_executor(None, self._invoke_cli, prompt)
        
        heartbeat_task.cancel()
        duration = time.time() - start_time
        
        if not output:
            # Failure
            AutonomyEventBus.emit(AutonomyProgressUpdated(
                task_id=self.task_id,
                step_number=step_num,
                total_steps=total_steps,
                status="failed",
                duration_seconds=duration,
                output_snippet="Step execution failed or timed out."
            ))
            return False, ""
            
        # Success
        AutonomyEventBus.emit(AutonomyProgressUpdated(
            task_id=self.task_id,
            step_number=step_num,
            total_steps=total_steps,
            status="completed",
            duration_seconds=duration,
            output_snippet=output[:500]  # snippet
        ))
        return True, output

    def _update_state(self, status: str, message: str):
        """Update jarvis state directly."""
        if not self.state_file:
            return
        try:
            js = JarvisState(self.state_file)
            js.update_task(self.task_id, status, message)
        except Exception as e:
            logger.error(f"Failed to update state: {e}")

    def _evaluate_confidence(self, success: bool, output: str) -> None:
        """Evaluate and update confidence score based on step outcome."""
        old_score = self.confidence_score
        factors = {}
        
        if not success:
            self.confidence_score -= 0.3
            factors["step_failure"] = -0.3
            
        if output:
            lower_output = output.lower()
            # Check for tool errors
            if "command not found" in lower_output or "syntaxerror" in lower_output or "error:" in lower_output:
                self.confidence_score -= 0.15
                factors["tool_error"] = -0.15
                
            # Check for unclear requirements
            if "i need more context" in lower_output or "unclear" in lower_output or "i cannot proceed" in lower_output:
                self.confidence_score -= 0.5
                factors["unclear_requirements"] = -0.5
                
        # Ensure score stays between 0 and 1
        self.confidence_score = max(0.0, min(1.0, self.confidence_score))
        
        if self.confidence_score != old_score:
            logger.info(f"Confidence score updated: {old_score:.2f} -> {self.confidence_score:.2f} | Factors: {factors}")
            AutonomyEventBus.emit(AutonomyConfidenceUpdated(
                task_id=self.task_id,
                score=self.confidence_score,
                factors=factors
            ))

    async def _escalation_pause_loop(self):
        """Poll the state file indefinitely waiting for an unpause signal."""
        logger.info("Entering escalation pause loop. Waiting for L2/Human intervention...")
        while True:
            await asyncio.sleep(10)
            if not self.state_file:
                continue
            try:
                js = JarvisState(self.state_file)
                status = js.get_task(self.task_id).get("status", "")
                if status in ["executing", "resumed"]:
                    logger.info("Unpause signal received. Exiting pause loop.")
                    break
                elif status in ["failed", "completed"]:
                    logger.info(f"Task externally marked as {status}. Terminating.")
                    sys.exit(0 if status == "completed" else 1)
            except Exception as e:
                logger.error(f"Error checking state during pause loop: {e}")

    async def _trigger_escalation(self, reason: str):
        """Trigger escalation process and pause."""
        logger.error(f"ESCALATING: {reason} (Score: {self.confidence_score:.2f})")
        AutonomyEventBus.emit(AutonomyEscalationTriggered(
            task_id=self.task_id,
            reason=reason,
            confidence=self.confidence_score
        ))
        self._update_state("escalating", f"Task escalated: {reason}")
        await self._escalation_pause_loop()

    async def execution_phase(self, steps: List[Dict[str, Any]]):
        """Execute the planned steps sequentially with dynamic course correction."""
        if not steps:
            self._update_state("failed", "Autonomy runner failed to generate a valid plan.")
            return

        total_steps = len(steps)
        current_step_idx = 0

        while current_step_idx < total_steps:
            step = steps[current_step_idx]
            step_num = current_step_idx + 1

            start_time = time.time()
            success, output = await self.execute_step(step, step_num, total_steps)
            duration = time.time() - start_time

            self._evaluate_confidence(success, output)

            if self.confidence_score < self.confidence_threshold:
                await self._trigger_escalation("Confidence dropped below threshold during step execution")
                # After pausing and resuming, we reset confidence and retry the current step
                self.confidence_score = 1.0
                continue

            # Check for deviation using heuristics
            if self._detect_deviation(success, output, duration):
                logger.warning(f"Step {step_num} deviation detected. Initiating course correction...")

                # Generate recovery steps via LLM reflection
                recovery_steps = self._reflect_and_correct(step, output)

                if recovery_steps:
                    # Emit course correction event
                    AutonomyEventBus.emit(AutonomyCourseCorrection(
                        task_id=self.task_id,
                        failed_step=step,
                        recovery_steps=recovery_steps
                    ))

                    # Splice recovery steps into the plan after current step
                    # The failed step remains in the list (marked by us proceeding past it)
                    steps = steps[:current_step_idx + 1] + recovery_steps + steps[current_step_idx + 1:]
                    total_steps = len(steps)

                    logger.info(f"Inserted {len(recovery_steps)} recovery steps. New total: {total_steps} steps")

                    # Log the failed step as completed (with failure status)
                    AutonomyEventBus.emit(AutonomyProgressUpdated(
                        task_id=self.task_id,
                        step_number=step_num,
                        total_steps=total_steps,
                        status="failed",
                        duration_seconds=duration,
                        output_snippet=output[:500] if output else "Deviation detected - recovery initiated"
                    ))
                else:
                    # Reflection failed to generate steps - let confidence handling take over
                    logger.warning(f"Course correction failed to generate recovery steps for step {step_num}")
                    # Mark as failed to ensure confidence drops
                    success = False

            # Only advance if no deviation was detected OR if deviation was handled
            # If deviation occurred and recovery steps were inserted, the loop continues
            # and the next iteration will execute the first recovery step
            current_step_idx += 1

        logger.info("All steps completed successfully.")
        # Let the standard entrypoint.sh or container lifecycle know it finished successfully
        sys.exit(0)

    def run(self):
        """Main entrypoint."""
        self.active_tools = self._analyze_tool_requirements()
        steps = self.planning_phase()
        asyncio.run(self.execution_phase(steps))

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    runner = AutonomyRunner()
    runner.run()
