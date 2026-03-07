#!/usr/bin/env node
/**
 * Phase 79 Plan 06: DASH-03 Scroll Indicator Test
 * Dispatches verbose task (35 lines), opens task panel, scrolls up to trigger indicator.
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
  // First, update workspace state to change TASK_ID to avoid conflict with completed task
  // We'll dispatch the same task ID — state engine will overwrite with new in_progress state

  const browser = await chromium.launch({
    headless: true,
    executablePath: '/usr/bin/google-chrome',
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 900 }
  });

  await context.addInitScript((token) => {
    window.localStorage.setItem('openclaw_token', token);
  }, TOKEN);

  await context.setExtraHTTPHeaders({
    'X-OpenClaw-Token': TOKEN
  });

  const page = await context.newPage();

  // Dispatch verbose task in background FIRST (so it's in_progress when we navigate)
  console.log('Dispatching verbose task in background...');
  const proc = spawn('python3', [DISPATCH_SCRIPT], {
    cwd: '/home/ob/Development/Tools/openrepo',
    detached: false,
    stdio: ['ignore', 'pipe', 'pipe']
  });

  let dispatchOutput = '';
  proc.stdout.on('data', d => { dispatchOutput += d.toString(); });
  proc.stderr.on('data', d => { dispatchOutput += '[stderr] ' + d.toString(); });

  // Wait 1s for task to be in_progress
  await new Promise(r => setTimeout(r, 1000));

  // Navigate to task board
  console.log('Navigating to task board...');
  await page.goto('http://localhost:6987/occc/tasks', { waitUntil: 'domcontentloaded', timeout: 15000 });
  await page.waitForTimeout(2000);
  console.log('Current URL:', page.url());

  // Check task status
  const taskStatus = await page.evaluate(() => {
    const allText = document.body.innerText;
    const hasVerbose = allText.includes('task-verbose-output-test');
    const hasInProgress = allText.includes('In Progress');
    return { hasVerbose, hasInProgress, snippet: allText.substring(0, 500) };
  });
  console.log('Task status check:', JSON.stringify(taskStatus, null, 2));

  // Try to click on the verbose task row
  console.log('Looking for verbose task row to click...');
  let clickedRow = false;
  try {
    // Try clicking by task ID text
    await page.click('text=task-verbose-output-test', { timeout: 5000 });
    console.log('Clicked on task-verbose-output-test text');
    clickedRow = true;
  } catch(e) {
    console.log('Could not click task text directly, trying row selector...');
    try {
      // Try any row containing the verbose task
      const rows = await page.$$('[class*=task], tr, [role=row]');
      for (const row of rows) {
        const text = await row.textContent();
        if (text && text.includes('verbose')) {
          await row.click();
          console.log('Clicked row containing verbose text');
          clickedRow = true;
          break;
        }
      }
    } catch(e2) {
      console.log('Row click failed:', e2.message);
    }
  }

  await page.waitForTimeout(2000);

  // Check for terminal panel / log viewer
  const panelCheck = await page.evaluate(() => {
    const allText = document.body.innerText;
    const hasConnected = allText.includes('Connected') || allText.includes('connected');
    const hasPanel = !!document.querySelector('[class*=journey], [class*=panel], [class*=terminal], [class*=log]');
    return { hasConnected, hasPanel, snippet: allText.substring(0, 800) };
  });
  console.log('Panel check:', JSON.stringify(panelCheck, null, 2));

  // Wait for log panel to accumulate output (allow overflow)
  console.log('Waiting for log panel to accumulate output...');
  await page.waitForTimeout(5000);

  // Check log lines and overflow
  const overflowCheck = await page.evaluate(() => {
    // Try multiple selector patterns for the log container
    const selectors = [
      '[class*=log-container]',
      '[class*=log-viewer]',
      '[class*=terminal]',
      '[class*=LogViewer]',
      '[class*=output]',
      '[class*=scroll]',
    ];

    let scrollable = null;
    let selectorUsed = null;
    for (const sel of selectors) {
      const el = document.querySelector(sel);
      if (el && el.scrollHeight > 0) {
        scrollable = el;
        selectorUsed = sel;
        break;
      }
    }

    // Also try finding elements with overflow-y: auto or scroll
    if (!scrollable) {
      const allEls = document.querySelectorAll('*');
      for (const el of Array.from(allEls)) {
        const style = window.getComputedStyle(el);
        if ((style.overflowY === 'auto' || style.overflowY === 'scroll') && el.scrollHeight > el.clientHeight) {
          scrollable = el;
          selectorUsed = 'computed-overflow';
          break;
        }
      }
    }

    const logLines = document.querySelectorAll('[class*=log], [class*=output], [class*=line], pre span');

    return {
      log_line_count: logLines.length,
      scrollable_found: !!scrollable,
      scrollable_selector: selectorUsed,
      scrollable_scrollHeight: scrollable ? scrollable.scrollHeight : 0,
      scrollable_clientHeight: scrollable ? scrollable.clientHeight : 0,
      overflow: scrollable ? scrollable.scrollHeight > scrollable.clientHeight : false,
      scrollable_class: scrollable ? scrollable.className.substring(0, 100) : null
    };
  });
  console.log('Overflow check:', JSON.stringify(overflowCheck, null, 2));

  // Wait more if not enough lines
  if (!overflowCheck.overflow || overflowCheck.log_line_count < 20) {
    console.log('Waiting more for streaming output...');
    await page.waitForTimeout(5000);

    // Re-check
    const overflowCheck2 = await page.evaluate(() => {
      const allEls = document.querySelectorAll('*');
      let scrollable = null;
      for (const el of Array.from(allEls)) {
        const style = window.getComputedStyle(el);
        if ((style.overflowY === 'auto' || style.overflowY === 'scroll') && el.scrollHeight > el.clientHeight) {
          scrollable = el;
          break;
        }
      }
      return {
        scrollable_scrollHeight: scrollable ? scrollable.scrollHeight : 0,
        scrollable_clientHeight: scrollable ? scrollable.clientHeight : 0,
        overflow: scrollable ? scrollable.scrollHeight > scrollable.clientHeight : false
      };
    });
    console.log('Overflow check 2:', JSON.stringify(overflowCheck2, null, 2));
  }

  // Scroll UP in log panel
  console.log('Scrolling up in log panel...');
  const scrollResult = await page.evaluate(() => {
    // Find all scrollable elements
    const allEls = document.querySelectorAll('*');
    const scrollables = [];
    for (const el of Array.from(allEls)) {
      const style = window.getComputedStyle(el);
      if ((style.overflowY === 'auto' || style.overflowY === 'scroll')) {
        scrollables.push({
          el,
          scrollHeight: el.scrollHeight,
          clientHeight: el.clientHeight,
          overflow: el.scrollHeight > el.clientHeight
        });
      }
    }

    // Find the most likely log panel (overflowing one or largest)
    const overflowing = scrollables.filter(s => s.overflow);
    const target = overflowing.length > 0 ? overflowing[overflowing.length - 1].el : null;

    if (target) {
      const before = target.scrollTop;
      target.scrollTop = 0;
      // Dispatch scroll event to trigger React handler
      target.dispatchEvent(new Event('scroll', { bubbles: true }));
      return {
        found: true,
        scrollHeight: target.scrollHeight,
        clientHeight: target.clientHeight,
        scrollTop_before: before,
        scrollTop_after: target.scrollTop,
        class: target.className.substring(0, 100)
      };
    }

    return { found: false, scrollables_count: scrollables.length };
  });
  console.log('Scroll result:', JSON.stringify(scrollResult, null, 2));

  // Also try browser scroll
  await page.mouse.wheel(0, -500);
  await page.waitForTimeout(500);

  // Also try keyboard scroll on focused element
  await page.keyboard.press('Home');
  await page.waitForTimeout(1000);

  // Check for scroll indicator
  const indicatorCheck = await page.evaluate(() => {
    const allText = document.body.innerText;
    const hasScrollIndicator = allText.includes('scroll to resume') || allText.includes('scroll to bottom');
    const hasDownArrow = allText.includes('↓');
    const indicator = document.querySelector('[class*=scroll-indicator], [class*=resume], [class*=scroll-resume]');

    // Also check for any elements containing the indicator text
    const allEls = document.querySelectorAll('*');
    let indicatorEl = null;
    for (const el of Array.from(allEls)) {
      if (el.textContent && (el.textContent.includes('scroll to resume') || el.textContent.includes('↓ scroll'))) {
        indicatorEl = el.outerHTML.substring(0, 200);
        break;
      }
    }

    return {
      has_scroll_indicator_text: hasScrollIndicator,
      has_down_arrow: hasDownArrow,
      indicator_by_selector: indicator ? indicator.outerHTML.substring(0, 200) : null,
      indicator_by_text: indicatorEl,
      body_snippet: allText.substring(0, 600)
    };
  });
  console.log('Indicator check:', JSON.stringify(indicatorCheck, null, 2));

  // Take screenshot with indicator (if visible)
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'dash03-scroll-indicator.png'), fullPage: false });
  console.log('Screenshot saved: dash03-scroll-indicator.png');

  // Scroll back to bottom
  console.log('Scrolling back to bottom...');
  await page.evaluate(() => {
    const allEls = document.querySelectorAll('*');
    for (const el of Array.from(allEls)) {
      const style = window.getComputedStyle(el);
      if ((style.overflowY === 'auto' || style.overflowY === 'scroll') && el.scrollHeight > el.clientHeight) {
        el.scrollTop = el.scrollHeight;
        el.dispatchEvent(new Event('scroll', { bubbles: true }));
      }
    }
    return 'scrolled to bottom';
  });

  await page.mouse.wheel(0, 5000);
  await page.keyboard.press('End');
  await page.waitForTimeout(1000);

  // Check indicator dismissed
  const dismissedCheck = await page.evaluate(() => {
    const allText = document.body.innerText;
    return allText.includes('scroll to resume') ? 'INDICATOR STILL VISIBLE' : 'INDICATOR DISMISSED';
  });
  console.log('Indicator dismissed check:', dismissedCheck);

  // Take screenshot after scroll to bottom
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'dash03-scroll-resumed.png'), fullPage: false });
  console.log('Screenshot saved: dash03-scroll-resumed.png');

  // Determine DASH-03 verdict
  const panelOverflow = overflowCheck.overflow || (overflowCheck.scrollable_scrollHeight > overflowCheck.scrollable_clientHeight);
  const indicatorAppeared = indicatorCheck.has_scroll_indicator_text || indicatorCheck.has_down_arrow || !!indicatorCheck.indicator_by_text;
  const indicatorDismissed = dismissedCheck === 'INDICATOR DISMISSED';

  let verdict;
  if (panelOverflow && indicatorAppeared && indicatorDismissed) {
    verdict = 'PASS';
  } else if (panelOverflow && indicatorAppeared) {
    verdict = 'PARTIAL';
  } else {
    verdict = 'FAIL';
  }

  console.log('\n=== DASH-03 VERDICT ===');
  console.log(`Panel overflow: ${panelOverflow} (scrollHeight=${overflowCheck.scrollable_scrollHeight}, clientHeight=${overflowCheck.scrollable_clientHeight})`);
  console.log(`Indicator appeared: ${indicatorAppeared}`);
  console.log(`Indicator dismissed: ${indicatorDismissed}`);
  console.log(`DASH-03 verdict: ${verdict}`);

  const results = {
    verdict,
    panel_overflow: panelOverflow,
    scrollHeight: overflowCheck.scrollable_scrollHeight,
    clientHeight: overflowCheck.scrollable_clientHeight,
    log_line_count: overflowCheck.log_line_count,
    indicator_appeared: indicatorAppeared,
    indicator_dismissed: indicatorDismissed,
    scroll_result: scrollResult,
    indicator_check: indicatorCheck
  };

  fs.writeFileSync(
    path.join(SCREENSHOT_DIR, 'dash03-results.json'),
    JSON.stringify(results, null, 2)
  );

  await browser.close();

  // Wait for dispatch to finish
  await new Promise(r => proc.on('close', r).on('error', r));
  console.log('\n=== DISPATCH OUTPUT (last 500 chars) ===');
  console.log(dispatchOutput.substring(dispatchOutput.length - 500));

  return results;
}

main().catch(e => {
  console.error('ERROR:', e.message);
  console.error(e.stack);
  process.exit(1);
});
