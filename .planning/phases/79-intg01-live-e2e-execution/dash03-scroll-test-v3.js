#!/usr/bin/env node
/**
 * Phase 79 Plan 06: DASH-03 Scroll Indicator Test v3
 *
 * Sequence:
 * 1. Navigate to task board
 * 2. Dispatch verbose task
 * 3. Wait for task to appear in In Progress column (SSE push)
 * 4. Click task card to open terminal panel
 * 5. Wait for log lines to accumulate (30+)
 * 6. Scroll the log container up
 * 7. Check for "↓ scroll to resume" button
 * 8. Scroll back to bottom
 * 9. Check indicator dismissed
 */

const PLAYWRIGHT_MODULE_DIR = '/home/ob/.nvm/versions/node/v22.21.1/lib/node_modules/@playwright/mcp/node_modules';
const { chromium } = require(PLAYWRIGHT_MODULE_DIR + '/playwright');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const SCREENSHOT_DIR = path.join(__dirname, '79-criterion-screenshots');
const DISPATCH_SCRIPT = path.join(__dirname, 'dispatch-live-task-verbose.py');
const TOKEN = 'hPxqyUCJlT6SQUFKERkdgYZQD1gq2DfF5yUy1TmGhgcftjC3BPw05A3HAOmP6dav';

async function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

async function main() {
  const browser = await chromium.launch({
    headless: true,
    executablePath: '/usr/bin/google-chrome',
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 }
  });

  await context.addInitScript((token) => {
    window.localStorage.setItem('openclaw_token', token);
  }, TOKEN);

  await context.setExtraHTTPHeaders({
    'X-OpenClaw-Token': TOKEN
  });

  const page = await context.newPage();

  // Step 1: Navigate to task board FIRST
  console.log('Step 1: Navigating to task board...');
  await page.goto('http://localhost:6987/occc/tasks', { waitUntil: 'domcontentloaded', timeout: 15000 });
  await sleep(2000);
  console.log('Current URL:', page.url());

  // Step 2: Dispatch verbose task in background
  console.log('Step 2: Dispatching verbose task...');
  const proc = spawn('python3', [DISPATCH_SCRIPT], {
    cwd: '/home/ob/Development/Tools/openrepo',
    detached: false,
    stdio: ['ignore', 'pipe', 'pipe']
  });

  let dispatchOutput = '';
  proc.stdout.on('data', d => { dispatchOutput += d.toString(); });
  proc.stderr.on('data', d => { dispatchOutput += '[stderr] ' + d.toString(); });

  // Step 3: Wait for task to appear in In Progress (SSE push) — max 5s
  console.log('Step 3: Waiting for task to appear in task board via SSE...');
  let taskAppeared = false;
  for (let i = 0; i < 10; i++) {
    await sleep(500);
    const check = await page.evaluate(() => {
      const allText = document.body.innerText;
      return allText.includes('task-verbose-output-test') && allText.includes('In Progress');
    });
    if (check) {
      console.log(`Task appeared after ${(i + 1) * 500}ms`);
      taskAppeared = true;
      break;
    }
  }
  console.log('Task appeared via SSE:', taskAppeared);

  // Take screenshot before click
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'dash03-before-click.png') });

  // Step 4: Click the task card
  console.log('Step 4: Clicking task card...');

  // Use evaluate to find and click the cursor-pointer containing the task
  const clickResult = await page.evaluate(() => {
    // Find the TaskCard div for task-verbose-output-test
    const cards = document.querySelectorAll('.cursor-pointer');
    for (const card of Array.from(cards)) {
      if (card.textContent && card.textContent.includes('task-verbose-output-test')) {
        card.click();
        return { clicked: true, class: card.className.substring(0, 100) };
      }
    }
    return { clicked: false };
  });
  console.log('Click result:', JSON.stringify(clickResult));

  // Wait for panel to open and LogViewer to connect
  await sleep(3000);

  // Check panel state
  const panelState = await page.evaluate(() => {
    const allText = document.body.innerText;
    const logContainers = document.querySelectorAll('div');
    const overflowDivs = Array.from(logContainers)
      .filter(el => {
        const cls = el.className || '';
        return cls.includes('overflow-y-auto');
      })
      .map(el => ({
        class: el.className.substring(0, 80),
        scrollHeight: el.scrollHeight,
        clientHeight: el.clientHeight,
        overflow: el.scrollHeight > el.clientHeight,
        childCount: el.children.length,
        textLen: (el.textContent || '').length
      }));

    return {
      hasConnected: allText.includes('Connected'),
      hasLogOutput: allText.includes('Initializing') || allText.includes('numpy') || allText.includes('pandas'),
      hasWaiting: allText.includes('Waiting for output'),
      hasConnectionLost: allText.includes('Connection lost'),
      overflowDivs,
      textSnippet: allText.substring(400, 1000)
    };
  });
  console.log('Panel state:', JSON.stringify(panelState, null, 2));

  await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'dash03-panel-check.png') });

  // Step 5: Wait for more log lines to accumulate
  console.log('Step 5: Waiting for log lines to accumulate...');
  await sleep(6000); // Wait for more of the 35 output lines to stream in

  // Check log container state
  const logState = await page.evaluate(() => {
    // Find the specific LogViewer log container: "h-full overflow-y-auto p-3"
    const allDivs = document.querySelectorAll('div');
    let logContainer = null;
    for (const el of Array.from(allDivs)) {
      if (el.className && el.className.includes('overflow-y-auto') && el.className.includes('p-3')) {
        logContainer = el;
        break;
      }
    }

    if (!logContainer) {
      // Try any overflow-y-auto div with substantial content
      for (const el of Array.from(allDivs)) {
        if (el.className && el.className.includes('overflow-y-auto') && el.children.length > 5) {
          logContainer = el;
          break;
        }
      }
    }

    return {
      found: !!logContainer,
      class: logContainer ? logContainer.className.substring(0, 100) : null,
      scrollHeight: logContainer ? logContainer.scrollHeight : 0,
      clientHeight: logContainer ? logContainer.clientHeight : 0,
      childCount: logContainer ? logContainer.children.length : 0,
      overflow: logContainer ? logContainer.scrollHeight > logContainer.clientHeight : false,
      textSnippet: logContainer ? logContainer.textContent.substring(0, 300) : null
    };
  });
  console.log('Log container state:', JSON.stringify(logState, null, 2));

  if (!logState.overflow) {
    console.log('Log container not overflowing yet, waiting 5 more seconds...');
    await sleep(5000);

    const logState2 = await page.evaluate(() => {
      const allDivs = document.querySelectorAll('div');
      let logContainer = null;
      for (const el of Array.from(allDivs)) {
        if (el.className && el.className.includes('overflow-y-auto') && el.className.includes('p-3')) {
          logContainer = el;
          break;
        }
      }
      return {
        found: !!logContainer,
        scrollHeight: logContainer ? logContainer.scrollHeight : 0,
        clientHeight: logContainer ? logContainer.clientHeight : 0,
        childCount: logContainer ? logContainer.children.length : 0,
        overflow: logContainer ? logContainer.scrollHeight > logContainer.clientHeight : false
      };
    });
    console.log('Log state after extra wait:', JSON.stringify(logState2, null, 2));
  }

  // Step 6: Scroll the log container to TOP
  console.log('Step 6: Scrolling log container to top...');
  const scrollResult = await page.evaluate(() => {
    const allDivs = document.querySelectorAll('div');

    // Find log container
    let logContainer = null;
    for (const el of Array.from(allDivs)) {
      if (el.className && el.className.includes('overflow-y-auto') && el.className.includes('p-3')) {
        logContainer = el;
        break;
      }
    }

    if (!logContainer) {
      // Fall back to most overflowing div
      let maxOverflow = 0;
      for (const el of Array.from(allDivs)) {
        if (el.className && el.className.includes('overflow-y-auto')) {
          const overflow = el.scrollHeight - el.clientHeight;
          if (overflow > maxOverflow) {
            maxOverflow = overflow;
            logContainer = el;
          }
        }
      }
    }

    if (!logContainer) {
      return { found: false };
    }

    const before = logContainer.scrollTop;
    const scrollHeight = logContainer.scrollHeight;
    const clientHeight = logContainer.clientHeight;

    // Scroll to TOP to trigger autoScrollPaused
    logContainer.scrollTop = 0;

    // Dispatch scroll event to trigger React's onScroll handler
    logContainer.dispatchEvent(new Event('scroll', { bubbles: true, cancelable: false }));

    // Also try a native scroll event
    const scrollEvent = new UIEvent('scroll', { view: window, bubbles: true, cancelable: false });
    logContainer.dispatchEvent(scrollEvent);

    return {
      found: true,
      class: logContainer.className.substring(0, 100),
      scrollHeight,
      clientHeight,
      overflow: scrollHeight > clientHeight,
      scrollTop_before: before,
      scrollTop_after: logContainer.scrollTop,
      childCount: logContainer.children.length
    };
  });
  console.log('Scroll result:', JSON.stringify(scrollResult, null, 2));

  await sleep(500);

  // Step 7: Check for scroll indicator
  console.log('Step 7: Checking for scroll indicator...');
  const indicatorCheck = await page.evaluate(() => {
    const allText = document.body.innerText;
    const buttons = document.querySelectorAll('button');
    let resumeBtn = null;
    let resumeBtnText = null;
    for (const btn of Array.from(buttons)) {
      const text = btn.textContent || '';
      if (text.includes('scroll to resume') || text.includes('↓')) {
        resumeBtn = btn.outerHTML.substring(0, 300);
        resumeBtnText = text.trim();
        break;
      }
    }

    // Check absolute positioned elements (the indicator is position:absolute bottom-3 right-3)
    const absoluteEls = document.querySelectorAll('[class*="absolute"]');
    let absoluteElInfo = null;
    for (const el of Array.from(absoluteEls)) {
      if (el.textContent && el.textContent.includes('scroll')) {
        absoluteElInfo = el.outerHTML.substring(0, 300);
        break;
      }
    }

    return {
      has_scroll_to_resume: allText.includes('scroll to resume'),
      has_down_arrow: allText.includes('↓'),
      resume_button_html: resumeBtn,
      resume_button_text: resumeBtnText,
      absolute_el: absoluteElInfo,
      // Capture all buttons for debugging
      all_buttons: Array.from(buttons).map(b => b.textContent.trim()).filter(t => t.length > 0).slice(0, 10),
      body_snippet: allText.substring(300, 1100)
    };
  });
  console.log('Indicator check:', JSON.stringify(indicatorCheck, null, 2));

  // Take screenshot with indicator
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'dash03-scroll-indicator.png'), fullPage: false });
  console.log('Screenshot saved: dash03-scroll-indicator.png');

  const indicatorAppeared = indicatorCheck.has_scroll_to_resume || !!indicatorCheck.resume_button_html;

  // Step 8: Scroll back to bottom
  console.log('Step 8: Scrolling back to bottom...');
  await page.evaluate(() => {
    const allDivs = document.querySelectorAll('div');
    for (const el of Array.from(allDivs)) {
      if (el.className && el.className.includes('overflow-y-auto') && el.className.includes('p-3')) {
        el.scrollTop = el.scrollHeight;
        el.dispatchEvent(new Event('scroll', { bubbles: true }));
        return;
      }
    }
    // Fallback
    for (const el of Array.from(allDivs)) {
      if (el.className && el.className.includes('overflow-y-auto') && el.scrollHeight > el.clientHeight) {
        el.scrollTop = el.scrollHeight;
        el.dispatchEvent(new Event('scroll', { bubbles: true }));
        return;
      }
    }
  });

  await sleep(1000);

  const dismissedCheck = await page.evaluate(() => {
    return document.body.innerText.includes('scroll to resume') ? 'INDICATOR STILL VISIBLE' : 'INDICATOR DISMISSED';
  });
  console.log('Indicator dismissed:', dismissedCheck);

  await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'dash03-scroll-resumed.png'), fullPage: false });
  console.log('Screenshot saved: dash03-scroll-resumed.png');

  const indicatorDismissed = dismissedCheck === 'INDICATOR DISMISSED';
  const panelOverflow = scrollResult.found && scrollResult.overflow;

  let verdict;
  if (panelOverflow && indicatorAppeared && indicatorDismissed) {
    verdict = 'PASS';
  } else if (panelOverflow && indicatorAppeared) {
    verdict = 'PARTIAL';
  } else if (panelOverflow) {
    verdict = 'FAIL_NO_INDICATOR';
  } else {
    verdict = 'FAIL_NO_OVERFLOW';
  }

  console.log('\n=== DASH-03 VERDICT ===');
  console.log(`Panel overflow: ${panelOverflow} (scrollHeight=${scrollResult.scrollHeight}, clientHeight=${scrollResult.clientHeight})`);
  console.log(`Indicator appeared: ${indicatorAppeared}`);
  console.log(`Indicator dismissed: ${indicatorDismissed}`);
  console.log(`DASH-03 verdict: ${verdict}`);

  const results = {
    verdict,
    panel_overflow: panelOverflow,
    scrollHeight: scrollResult.scrollHeight,
    clientHeight: scrollResult.clientHeight,
    child_count: scrollResult.childCount,
    log_container_class: scrollResult.class,
    indicator_appeared: indicatorAppeared,
    indicator_dismissed: indicatorDismissed,
    task_appeared_via_sse: taskAppeared,
    indicator_check: indicatorCheck,
    scroll_result: scrollResult
  };

  fs.writeFileSync(
    path.join(SCREENSHOT_DIR, 'dash03-results.json'),
    JSON.stringify(results, null, 2)
  );

  await browser.close();

  console.log('\n=== DISPATCH OUTPUT ===');
  console.log(dispatchOutput.substring(0, 500));

  return results;
}

main().catch(e => {
  console.error('ERROR:', e.message);
  console.error(e.stack);
  process.exit(1);
});
