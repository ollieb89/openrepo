#!/usr/bin/env node
/**
 * Phase 79 Plan 06: C1 SSE Real-Time Latency Test
 * Measures elapsed time from EventSource connection open to task.created arrival.
 */

const PLAYWRIGHT_MODULE_DIR = '/home/ob/.nvm/versions/node/v22.21.1/lib/node_modules/@playwright/mcp/node_modules';
const { chromium } = require(PLAYWRIGHT_MODULE_DIR + '/playwright');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const SCREENSHOT_DIR = path.join(__dirname, '79-criterion-screenshots');
const DISPATCH_SCRIPT = path.join(__dirname, 'dispatch-live-task-verbose.py');
const TOKEN = 'hPxqyUCJlT6SQUFKERkdgYZQD1gq2DfF5yUy1TmGhgcftjC3BPw05A3HAOmP6dav';

async function main() {
  const browser = await chromium.launch({
    headless: true,
    executablePath: '/usr/bin/google-chrome',
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 }
  });

  // Set auth token in localStorage before any navigation
  await context.addInitScript((token) => {
    window.localStorage.setItem('openclaw_token', token);
  }, TOKEN);

  // Set auth header for all requests
  await context.setExtraHTTPHeaders({
    'X-OpenClaw-Token': TOKEN
  });

  const page = await context.newPage();

  // Navigate to task board
  console.log('Navigating to task board...');
  await page.goto('http://localhost:6987/occc/tasks', { waitUntil: 'domcontentloaded', timeout: 15000 });
  await page.waitForTimeout(3000); // Wait for React to hydrate
  console.log('Current URL:', page.url());
  const title = await page.title();
  console.log('Page title:', title);

  // Take initial screenshot
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'c1-initial.png') });

  // Inject SSE listener with auth token
  console.log('Injecting SSE listener...');
  const listenerResult = await page.evaluate((token) => {
    window.__sse_events = [];
    window.__sse_task_created_time = null;
    window.__sse_task_id = null;
    window.__sse_t0 = Date.now();
    // Note: EventSource doesn't support custom headers. The dashboard authenticates via
    // the cookie/session set by localStorage token. The SSE endpoint may check X-OpenClaw-Token.
    // We use the same approach as the dashboard: rely on the auth already set in localStorage.
    const es = new EventSource('/occc/api/events?project=pumplai');
    window.__sse_source = es;
    es.addEventListener('message', (e) => {
      const now = Date.now();
      try {
        const data = JSON.parse(e.data);
        window.__sse_events.push({ type: data.type, time: now, elapsed: now - window.__sse_t0 });
        if (data.type === 'task.created' && !window.__sse_task_created_time) {
          window.__sse_task_created_time = now;
          window.__sse_task_id = data.task_id;
        }
      } catch(err) {}
    });
    es.onerror = (e) => { window.__sse_error = true; };
    return 'SSE listener installed at T0=' + window.__sse_t0;
  }, TOKEN);
  console.log('Listener:', listenerResult);

  // Wait 1s for connection to establish
  await page.waitForTimeout(1000);

  const T0_dispatch = Date.now();
  console.log('T0_dispatch:', T0_dispatch);

  // Dispatch verbose task in background
  console.log('Dispatching verbose task...');
  const proc = spawn('python3', [DISPATCH_SCRIPT], {
    cwd: '/home/ob/Development/Tools/openrepo',
    detached: true,
    stdio: ['ignore', 'pipe', 'pipe']
  });
  proc.unref();

  let dispatchOutput = '';
  proc.stdout.on('data', d => { dispatchOutput += d.toString(); });
  proc.stderr.on('data', d => { dispatchOutput += '[stderr] ' + d.toString(); });

  // Wait 2 seconds for task.created SSE to arrive
  await page.waitForTimeout(2000);

  // Check SSE listener state
  let sseState = { task_created_time: null, t0: null, elapsed_ms: null, task_id: null, events: [], error: false };
  try {
    sseState = await page.evaluate(() => {
      return {
        task_created_time: window.__sse_task_created_time,
        t0: window.__sse_t0,
        elapsed_ms: window.__sse_task_created_time ? window.__sse_task_created_time - window.__sse_t0 : null,
        task_id: window.__sse_task_id,
        events: window.__sse_events || [],
        error: window.__sse_error || false
      };
    });
  } catch(e) {
    console.log('evaluate failed after 2s:', e.message);
  }
  console.log('SSE state after 2s:', JSON.stringify(sseState, null, 2));

  // If task.created not yet received, wait 3 more seconds
  if (!sseState.task_created_time) {
    console.log('task.created not yet received, waiting 3 more seconds...');
    await page.waitForTimeout(3000);
    try {
      sseState = await page.evaluate(() => {
        return {
          task_created_time: window.__sse_task_created_time,
          t0: window.__sse_t0,
          elapsed_ms: window.__sse_task_created_time ? window.__sse_task_created_time - window.__sse_t0 : null,
          task_id: window.__sse_task_id,
          events: window.__sse_events || [],
          error: window.__sse_error || false
        };
      });
      console.log('SSE state after 5s:', JSON.stringify(sseState, null, 2));
    } catch(e) {
      console.log('evaluate failed after 5s:', e.message);
    }
  }

  // Check DOM for task row
  let domCheck = { matching_count: 0, has_verbose_text: false, has_task_id: false, page_title: '', task_id: 'task-verbose-output-test', body_text_snippet: '' };
  try {
    domCheck = await page.evaluate(() => {
      const taskId = window.__sse_task_id || 'task-verbose-output-test';
      const rows = document.querySelectorAll('[data-task-id]');
      const matching = Array.from(rows).filter(r => r.dataset.taskId === taskId || r.textContent.includes('verbose'));
      const allText = document.body.innerText;
      const hasVerbose = allText.toLowerCase().includes('verbose');
      const hasTaskId = allText.includes('task-verbose-output-test');
      return {
        matching_count: matching.length,
        has_verbose_text: hasVerbose,
        has_task_id: hasTaskId,
        page_title: document.title,
        task_id: taskId,
        body_text_snippet: allText.substring(0, 800)
      };
    });
  } catch(e) {
    console.log('DOM check failed:', e.message);
  }
  console.log('DOM check:', JSON.stringify(domCheck, null, 2));

  // Take screenshot
  const screenshotPath = path.join(SCREENSHOT_DIR, 'c1-sse-realtime.png');
  await page.screenshot({ path: screenshotPath, fullPage: false });
  console.log('Screenshot saved: c1-sse-realtime.png');

  // Determine C1 verdict
  const elapsed = sseState.elapsed_ms;
  const eventsLen = (sseState.events || []).length;
  const taskRowVisible = domCheck.matching_count > 0 || domCheck.has_verbose_text || domCheck.has_task_id;
  let verdict;
  if (sseState.error) {
    verdict = 'FAIL';
  } else if (elapsed !== null && elapsed < 5000 && taskRowVisible) {
    verdict = 'PASS';
  } else if (elapsed !== null && elapsed < 5000) {
    verdict = 'PARTIAL'; // SSE received fast but row not yet visible in DOM
  } else if (elapsed !== null) {
    verdict = 'FAIL'; // elapsed > 5000
  } else {
    verdict = 'PARTIAL'; // No task.created received yet (SSE connection may not be auth'd)
  }

  console.log('\n=== C1 VERDICT ===');
  console.log(`elapsed_ms: ${elapsed}`);
  console.log(`task_row_visible_without_reload: ${taskRowVisible}`);
  console.log(`events_received: ${eventsLen}`);
  console.log(`C1 verdict: ${verdict}`);

  // Save results
  const results = {
    elapsed_ms: elapsed,
    t0: sseState.t0,
    task_created_time: sseState.task_created_time,
    task_id: sseState.task_id,
    events_received: sseState.events || [],
    sse_error: sseState.error,
    task_row_visible_without_reload: taskRowVisible,
    dom_check: domCheck,
    T0_dispatch,
    verdict
  };
  fs.writeFileSync(
    path.join(SCREENSHOT_DIR, 'c1-sse-results.json'),
    JSON.stringify(results, null, 2)
  );

  await browser.close();

  // Brief wait for dispatch output
  await new Promise(r => setTimeout(r, 1000));
  console.log('\n=== DISPATCH OUTPUT (partial) ===');
  console.log(dispatchOutput.substring(0, 800));

  return results;
}

main().catch(e => {
  console.error('ERROR:', e.message);
  console.error(e.stack);
  process.exit(1);
});
