#!/usr/bin/env node
/**
 * Phase 79 Plan 06: DASH-03 Scroll Indicator Test v4
 *
 * Focuses on scrolling the INNER log container (h-full overflow-y-auto p-3)
 * not the outer sidebar panel.
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

  // Step 1: Navigate to task board
  console.log('Step 1: Navigating to task board...');
  await page.goto('http://localhost:6987/occc/tasks', { waitUntil: 'domcontentloaded', timeout: 15000 });
  await sleep(2000);

  // Step 2: Dispatch verbose task
  console.log('Step 2: Dispatching verbose task...');
  const proc = spawn('python3', [DISPATCH_SCRIPT], {
    cwd: '/home/ob/Development/Tools/openrepo',
    detached: false,
    stdio: ['ignore', 'pipe', 'pipe']
  });
  let dispatchOutput = '';
  proc.stdout.on('data', d => { dispatchOutput += d.toString(); });
  proc.stderr.on('data', d => { dispatchOutput += d.toString(); });

  // Step 3: Wait for task to appear via SSE
  console.log('Step 3: Waiting for task in board...');
  let taskAppeared = false;
  for (let i = 0; i < 20; i++) {
    await sleep(500);
    const check = await page.evaluate(() => {
      return document.body.innerText.includes('task-verbose-output-test');
    });
    if (check) {
      console.log(`Task appeared after ${(i + 1) * 500}ms`);
      taskAppeared = true;
      break;
    }
  }

  // Step 4: Click the task card
  console.log('Step 4: Clicking task card...');
  const clickResult = await page.evaluate(() => {
    const cards = document.querySelectorAll('.cursor-pointer');
    for (const card of Array.from(cards)) {
      if (card.textContent && card.textContent.includes('task-verbose-output-test')) {
        card.click();
        return { clicked: true, class: card.className.substring(0, 80) };
      }
    }
    return { clicked: false };
  });
  console.log('Click result:', JSON.stringify(clickResult));
  await sleep(2000);

  // Step 5: Wait for log lines in the inner container
  console.log('Step 5: Waiting for log container to fill...');
  let logContainer_scrollHeight = 0;
  let logContainer_clientHeight = 0;
  let logContainer_found = false;

  for (let attempt = 0; attempt < 12; attempt++) {
    await sleep(1000);
    const state = await page.evaluate(() => {
      // Find the INNER log container: 'h-full overflow-y-auto p-3'
      const allDivs = document.querySelectorAll('div');
      for (const el of Array.from(allDivs)) {
        const cls = el.className || '';
        if (cls.includes('overflow-y-auto') && cls.includes('p-3')) {
          return {
            found: true,
            class: cls.substring(0, 100),
            scrollHeight: el.scrollHeight,
            clientHeight: el.clientHeight,
            childCount: el.children.length,
            overflow: el.scrollHeight > el.clientHeight,
            textSnippet: (el.textContent || '').substring(0, 200)
          };
        }
      }
      return { found: false };
    });

    console.log(`Attempt ${attempt + 1}: log container: scrollHeight=${state.scrollHeight}, clientHeight=${state.clientHeight}, children=${state.childCount}, overflow=${state.overflow}`);

    if (state.found) {
      logContainer_found = true;
      logContainer_scrollHeight = state.scrollHeight;
      logContainer_clientHeight = state.clientHeight;
      if (state.overflow) {
        console.log('Log container overflowing!');
        break;
      }
    }
  }

  await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'dash03-panel-full.png') });

  // Step 6: Scroll the INNER log container to TOP
  console.log('Step 6: Scrolling INNER log container (p-3) to top...');
  const scrollResult = await page.evaluate(() => {
    const allDivs = document.querySelectorAll('div');
    for (const el of Array.from(allDivs)) {
      const cls = el.className || '';
      if (cls.includes('overflow-y-auto') && cls.includes('p-3')) {
        const scrollHeight = el.scrollHeight;
        const clientHeight = el.clientHeight;
        const before = el.scrollTop;

        // Set scrollTop to 0 to trigger autoScrollPaused
        el.scrollTop = 0;

        // Dispatch scroll event — must be on this specific element
        el.dispatchEvent(new Event('scroll', { bubbles: true, cancelable: false }));

        // Also simulate a user scroll using WheelEvent
        el.dispatchEvent(new WheelEvent('wheel', { deltaY: -1000, bubbles: true }));

        return {
          found: true,
          class: cls.substring(0, 100),
          scrollHeight,
          clientHeight,
          overflow: scrollHeight > clientHeight,
          scrollTop_before: before,
          scrollTop_after: el.scrollTop,
          childCount: el.children.length
        };
      }
    }
    return { found: false };
  });
  console.log('Scroll result:', JSON.stringify(scrollResult, null, 2));

  await sleep(800);

  // Step 7: Check for scroll indicator
  console.log('Step 7: Checking for scroll indicator...');
  const indicatorCheck = await page.evaluate(() => {
    const allText = document.body.innerText;
    const buttons = document.querySelectorAll('button');
    let resumeBtn = null;
    for (const btn of Array.from(buttons)) {
      const text = btn.textContent || '';
      if (text.includes('scroll to resume') || (text.includes('↓') && text.includes('resume'))) {
        resumeBtn = btn.outerHTML.substring(0, 300);
        break;
      }
    }

    // Check specifically for the absolute-positioned indicator button
    // It's rendered as: <div class="absolute bottom-3 right-3"><button class="...">↓ scroll to resume</button></div>
    const absoluteDivs = document.querySelectorAll('div[class*="absolute"]');
    let indicatorInAbsolute = null;
    for (const div of Array.from(absoluteDivs)) {
      if (div.textContent && div.textContent.includes('scroll')) {
        indicatorInAbsolute = div.outerHTML.substring(0, 300);
        break;
      }
    }

    // Check for the relative div that would contain the absolute indicator
    const relativeDivs = document.querySelectorAll('div[class*="relative"]');
    let childrenOfRelative = [];
    for (const div of Array.from(relativeDivs)) {
      const children = Array.from(div.children);
      if (children.length > 1) {
        childrenOfRelative.push({
          class: div.className.substring(0, 80),
          childCount: children.length,
          childClasses: children.map(c => c.className.substring(0, 60))
        });
      }
    }

    return {
      has_scroll_to_resume: allText.includes('scroll to resume'),
      has_down_arrow: allText.includes('↓'),
      resume_button_html: resumeBtn,
      indicator_in_absolute: indicatorInAbsolute,
      relative_divs_with_children: childrenOfRelative.slice(0, 3),
      all_buttons: Array.from(buttons).map(b => b.textContent.trim().substring(0, 50)).filter(t => t.length > 0),
      body_snippet: allText.substring(400, 1200)
    };
  });
  console.log('Indicator check:', JSON.stringify(indicatorCheck, null, 2));

  await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'dash03-scroll-indicator.png'), fullPage: false });
  console.log('Screenshot saved: dash03-scroll-indicator.png');

  const indicatorAppeared = indicatorCheck.has_scroll_to_resume || !!indicatorCheck.resume_button_html || !!indicatorCheck.indicator_in_absolute;

  // Step 8: Scroll back to bottom
  console.log('Step 8: Scrolling back to bottom...');
  await page.evaluate(() => {
    const allDivs = document.querySelectorAll('div');
    for (const el of Array.from(allDivs)) {
      const cls = el.className || '';
      if (cls.includes('overflow-y-auto') && cls.includes('p-3')) {
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
  console.log(`Panel overflow: ${panelOverflow} (scrollHeight=${scrollResult.scrollHeight}, clientHeight=${scrollResult.clientHeight}, children=${scrollResult.childCount})`);
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
    logviewer_fix_applied: true,
    note: 'LogViewer.tsx fixed from /api/events to /occc/api/events (same bug as useEvents.ts)',
    indicator_check: indicatorCheck,
    scroll_result: scrollResult
  };

  fs.writeFileSync(
    path.join(SCREENSHOT_DIR, 'dash03-results.json'),
    JSON.stringify(results, null, 2)
  );

  await browser.close();
  return results;
}

main().catch(e => {
  console.error('ERROR:', e.message);
  console.error(e.stack);
  process.exit(1);
});
