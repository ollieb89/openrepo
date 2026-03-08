#!/usr/bin/env node
/**
 * Phase 79 Plan 06: DASH-03 Scroll Indicator Test v5
 *
 * Waits for task to COMPLETE (supplementalLines will be loaded into LogViewer).
 * Then finds the inner log container and scrolls it up.
 */

const PLAYWRIGHT_MODULE_DIR = '/home/ob/.nvm/versions/node/v22.21.1/lib/node_modules/@playwright/mcp/node_modules';
const { chromium } = require(PLAYWRIGHT_MODULE_DIR + '/playwright');
const { spawn, execSync } = require('child_process');
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

  // Step 2: Dispatch verbose task (foreground — wait for completion)
  console.log('Step 2: Dispatching verbose task (will complete in ~12s)...');
  const proc = spawn('python3', [DISPATCH_SCRIPT], {
    cwd: '/home/ob/Development/Tools/openrepo',
    detached: false,
    stdio: ['ignore', 'pipe', 'pipe']
  });
  let dispatchOutput = '';
  proc.stdout.on('data', d => { dispatchOutput += d.toString(); });
  proc.stderr.on('data', d => { dispatchOutput += d.toString(); });

  // Step 3: Wait for task to appear in board via SSE
  console.log('Step 3: Waiting for task in board (SSE push)...');
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
  await sleep(1000);

  // Step 5: Wait for task to complete AND for supplementalLines to populate the log viewer
  // The dispatch script takes ~12s (35 lines x 0.3s)
  // We'll poll until we see 30+ log lines in the inner container
  console.log('Step 5: Waiting for log lines to accumulate (may take up to 20s)...');

  let logContainerInfo = null;
  for (let attempt = 0; attempt < 25; attempt++) {
    await sleep(800);

    const state = await page.evaluate(() => {
      // Use querySelectorAll to find ALL divs with overflow-y-auto
      const candidates = [];
      document.querySelectorAll('div').forEach(el => {
        const cls = el.className || '';
        if (cls.includes('overflow-y-auto')) {
          candidates.push({
            class: cls.substring(0, 100),
            scrollHeight: el.scrollHeight,
            clientHeight: el.clientHeight,
            childCount: el.children.length,
            overflow: el.scrollHeight > el.clientHeight,
            hasP3: cls.includes('p-3')
          });
        }
      });
      return candidates;
    });

    console.log(`Attempt ${attempt + 1}: overflow-y-auto divs:`, state.map(s => `${s.hasP3?'[p-3]':''}children=${s.childCount} scrollH=${s.scrollHeight} clientH=${s.clientHeight}`).join(', '));

    // Find the log container (has p-3 and has many children)
    const logContainer = state.find(s => s.hasP3 && s.childCount > 5);
    if (logContainer) {
      logContainerInfo = logContainer;
      console.log('Found log container with content:', JSON.stringify(logContainer));
      if (logContainer.overflow) {
        console.log('LOG CONTAINER IS OVERFLOWING! Children:', logContainer.childCount);
        break;
      }
    }
  }

  await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'dash03-panel-full.png') });

  if (!logContainerInfo || !logContainerInfo.overflow) {
    console.log('WARNING: Log container not overflowing. Taking final screenshot anyway.');
    console.log('logContainerInfo:', JSON.stringify(logContainerInfo));
  }

  // Step 6: Scroll the log container (p-3) to top using Playwright scroll actions
  console.log('Step 6: Scrolling log container to TOP...');

  // Get the bounding rect of the log container
  const logContainerRect = await page.evaluate(() => {
    let target = null;
    document.querySelectorAll('div').forEach(el => {
      const cls = el.className || '';
      if (cls.includes('overflow-y-auto') && cls.includes('p-3') && el.children.length > 5) {
        target = el;
      }
    });
    if (!target) return null;

    const rect = target.getBoundingClientRect();
    const scrollHeight = target.scrollHeight;
    const clientHeight = target.clientHeight;

    // Scroll to top
    target.scrollTop = 0;
    target.dispatchEvent(new Event('scroll', { bubbles: true }));

    return {
      x: rect.x + rect.width / 2,
      y: rect.y + rect.height / 2,
      scrollHeight,
      clientHeight,
      overflow: scrollHeight > clientHeight,
      childCount: target.children.length,
      class: target.className.substring(0, 100),
      scrollTop_after: target.scrollTop
    };
  });
  console.log('Log container rect + scroll:', JSON.stringify(logContainerRect, null, 2));

  // Also use Playwright mouse wheel at the log container position
  if (logContainerRect) {
    await page.mouse.move(logContainerRect.x, logContainerRect.y);
    await page.mouse.wheel(0, -5000);  // Scroll up
    await sleep(500);
  }

  await sleep(500);

  // Step 7: Check for scroll indicator
  console.log('Step 7: Checking for scroll indicator...');
  const indicatorCheck = await page.evaluate(() => {
    const allText = document.body.innerText;
    const buttons = document.querySelectorAll('button');
    let resumeBtn = null;
    for (const btn of Array.from(buttons)) {
      const text = btn.textContent || '';
      if (text.includes('scroll to resume') || (text.includes('↓') && text.length < 30)) {
        resumeBtn = { html: btn.outerHTML.substring(0, 300), text: text.trim() };
        break;
      }
    }

    // Direct search for the absolute-positioned indicator
    // Note: use getAttribute('class') to handle SVGAnimatedString
    const allEls = document.querySelectorAll('div');
    let indicatorEl = null;
    for (const el of Array.from(allEls)) {
      const cls = el.getAttribute('class') || '';
      if (cls.includes('absolute') && cls.includes('bottom') && el.textContent && el.textContent.includes('scroll')) {
        indicatorEl = el.outerHTML.substring(0, 300);
        break;
      }
    }

    // Check all text for ↓ in leaf elements
    const downArrowMatches = [];
    const textEls = document.querySelectorAll('button, span, p, div');
    for (const el of Array.from(textEls)) {
      const txt = el.textContent || '';
      if (txt.includes('↓') && el.children.length === 0 && txt.length < 50) {
        downArrowMatches.push({ tag: el.tagName, text: txt.trim(), class: (el.getAttribute('class') || '').substring(0, 50) });
      }
    }

    return {
      has_scroll_to_resume: allText.includes('scroll to resume'),
      has_down_arrow: allText.includes('↓'),
      resume_button: resumeBtn,
      indicator_element: indicatorEl,
      down_arrow_elements: downArrowMatches.slice(0, 5),
      all_buttons: Array.from(buttons).map(b => b.textContent.trim().substring(0, 60)).filter(t => t.length > 0),
      body_text_lines: allText.split('\n').filter(l => l.trim().length > 0).slice(-20)
    };
  });
  console.log('Indicator check:', JSON.stringify(indicatorCheck, null, 2));

  await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'dash03-scroll-indicator.png'), fullPage: false });
  console.log('Screenshot saved: dash03-scroll-indicator.png');

  const indicatorAppeared = indicatorCheck.has_scroll_to_resume || !!indicatorCheck.resume_button || !!indicatorCheck.indicator_element;

  // Step 8: Scroll back to bottom
  console.log('Step 8: Scrolling back to bottom...');
  await page.evaluate(() => {
    document.querySelectorAll('div').forEach(el => {
      const cls = el.className || '';
      if (cls.includes('overflow-y-auto') && cls.includes('p-3') && el.children.length > 5) {
        el.scrollTop = el.scrollHeight;
        el.dispatchEvent(new Event('scroll', { bubbles: true }));
      }
    });
  });

  // Also use mouse wheel scroll down
  if (logContainerRect) {
    await page.mouse.move(logContainerRect.x, logContainerRect.y);
    await page.mouse.wheel(0, 10000);
  }

  await sleep(1000);

  const dismissedCheck = await page.evaluate(() => {
    return document.body.innerText.includes('scroll to resume') ? 'INDICATOR STILL VISIBLE' : 'INDICATOR DISMISSED';
  });
  console.log('Indicator dismissed:', dismissedCheck);

  await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'dash03-scroll-resumed.png'), fullPage: false });
  console.log('Screenshot saved: dash03-scroll-resumed.png');

  const indicatorDismissed = dismissedCheck === 'INDICATOR DISMISSED';
  const panelOverflow = logContainerInfo && logContainerInfo.overflow;

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
  console.log(`Panel overflow: ${panelOverflow}`);
  console.log(`  scrollHeight=${logContainerInfo ? logContainerInfo.scrollHeight : 'N/A'}`);
  console.log(`  clientHeight=${logContainerInfo ? logContainerInfo.clientHeight : 'N/A'}`);
  console.log(`  childCount=${logContainerInfo ? logContainerInfo.childCount : 'N/A'}`);
  console.log(`Indicator appeared: ${indicatorAppeared}`);
  console.log(`Indicator dismissed: ${indicatorDismissed}`);
  console.log(`DASH-03 verdict: ${verdict}`);

  const results = {
    verdict,
    panel_overflow: !!panelOverflow,
    scrollHeight: logContainerInfo ? logContainerInfo.scrollHeight : 0,
    clientHeight: logContainerInfo ? logContainerInfo.clientHeight : 0,
    child_count: logContainerInfo ? logContainerInfo.childCount : 0,
    log_container_class: logContainerInfo ? logContainerInfo.class : null,
    indicator_appeared: indicatorAppeared,
    indicator_dismissed: indicatorDismissed,
    task_appeared_via_sse: taskAppeared,
    logviewer_url_fix: 'LogViewer.tsx fixed from /api/events to /occc/api/events',
    indicator_check: indicatorCheck
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
