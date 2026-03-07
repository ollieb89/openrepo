#!/usr/bin/env node
/**
 * Phase 79 Plan 06: DASH-03 Scroll Indicator Test v2
 * More targeted: finds TaskCard by cursor-pointer, clicks it, waits for LogViewer.
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
  console.log('Navigating to task board...');
  await page.goto('http://localhost:6987/occc/tasks', { waitUntil: 'domcontentloaded', timeout: 15000 });
  await sleep(2000);
  console.log('Current URL:', page.url());

  // Step 2: Dispatch verbose task in background
  console.log('Dispatching verbose task in background...');
  const proc = spawn('python3', [DISPATCH_SCRIPT], {
    cwd: '/home/ob/Development/Tools/openrepo',
    detached: false,
    stdio: ['ignore', 'pipe', 'pipe']
  });

  let dispatchOutput = '';
  proc.stdout.on('data', d => { dispatchOutput += d.toString(); });
  proc.stderr.on('data', d => { dispatchOutput += '[stderr] ' + d.toString(); });

  // Wait 1.5s for task to be created and in_progress
  await sleep(1500);

  // Step 3: Find and click the in-progress verbose task card
  console.log('Looking for in-progress task card...');

  // First take a screenshot to see what's on the page
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'dash03-before-click.png') });

  // Find all cursor-pointer elements that contain 'verbose' text
  const cardInfo = await page.evaluate(() => {
    const cards = document.querySelectorAll('.cursor-pointer');
    const results = [];
    for (const card of Array.from(cards)) {
      const text = card.textContent || '';
      if (text.includes('verbose') || text.includes('task-verbose')) {
        results.push({
          tagName: card.tagName,
          className: card.className.substring(0, 100),
          text: text.substring(0, 200),
          rect: card.getBoundingClientRect()
        });
      }
    }
    return results;
  });
  console.log('Task cards found:', JSON.stringify(cardInfo, null, 2));

  // Click the first matching card
  let clicked = false;
  try {
    // Try clicking the cursor-pointer element containing verbose text
    const verboseCard = await page.$('.cursor-pointer:has-text("verbose")');
    if (verboseCard) {
      await verboseCard.click();
      console.log('Clicked verbose task card');
      clicked = true;
    } else {
      console.log('No .cursor-pointer:has-text("verbose") found, trying text match...');
      // Try clicking a div that contains the task text
      await page.click('text=Build a verbose output test project', { timeout: 3000 });
      clicked = true;
      console.log('Clicked by text match');
    }
  } catch(e) {
    console.log('Click attempt failed:', e.message);
    // Try a more aggressive approach: find by text content and click parent
    try {
      const clicked2 = await page.evaluate(() => {
        const allEls = document.querySelectorAll('*');
        for (const el of Array.from(allEls)) {
          if (el.className && el.className.includes && el.className.includes('cursor-pointer') &&
              el.textContent && el.textContent.includes('verbose')) {
            el.click();
            return { success: true, class: el.className.substring(0, 100) };
          }
        }
        return { success: false };
      });
      console.log('JS click result:', JSON.stringify(clicked2));
      clicked = true;
    } catch(e2) {
      console.log('JS click failed:', e2.message);
    }
  }

  await sleep(2000);

  // Check if panel opened
  const panelState = await page.evaluate(() => {
    const allText = document.body.innerText;
    const hasConnected = allText.includes('Connected');
    const hasOutputLine = allText.includes('Initializing') || allText.includes('Checking Python') || allText.includes('numpy');
    const hasClearBtn = !!document.querySelector('button');

    // Find the log container specifically (h-full overflow-y-auto p-3)
    const logContainers = document.querySelectorAll('div[class*="overflow-y-auto"]');
    const logContainerInfo = Array.from(logContainers).map(el => ({
      class: el.className.substring(0, 80),
      scrollHeight: el.scrollHeight,
      clientHeight: el.clientHeight,
      scrollTop: el.scrollTop,
      overflow: el.scrollHeight > el.clientHeight,
      childCount: el.children.length,
      textSnippet: el.textContent ? el.textContent.substring(0, 100) : ''
    }));

    return {
      hasConnected,
      hasOutputLine,
      logContainerInfo,
      url: window.location.href,
      textSnippet: allText.substring(300, 900)
    };
  });
  console.log('Panel state:', JSON.stringify(panelState, null, 2));

  await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'dash03-panel-open.png') });

  // Wait more for lines to accumulate (10+ lines)
  console.log('Waiting for more output lines...');
  await sleep(5000);

  // Check panel state again
  const panelState2 = await page.evaluate(() => {
    const logContainers = document.querySelectorAll('div[class*="overflow-y-auto"]');
    return Array.from(logContainers).map(el => ({
      class: el.className.substring(0, 80),
      scrollHeight: el.scrollHeight,
      clientHeight: el.clientHeight,
      overflow: el.scrollHeight > el.clientHeight,
      childCount: el.children.length,
      textSnippet: el.textContent ? el.textContent.substring(0, 200) : ''
    }));
  });
  console.log('Panel state 2 (after 5s more):', JSON.stringify(panelState2, null, 2));

  // Find and scroll the log container
  const scrollResult = await page.evaluate(() => {
    // Find the div with class containing "overflow-y-auto" and "p-3" (the log container)
    const containers = document.querySelectorAll('div[class*="overflow-y-auto"]');
    let logContainer = null;

    // The log container from LogViewer.tsx has class "h-full overflow-y-auto p-3"
    for (const el of Array.from(containers)) {
      if (el.className.includes('p-3') && el.scrollHeight > 100) {
        logContainer = el;
        break;
      }
    }

    // If not found, try the most overflowing one
    if (!logContainer) {
      let maxOverflow = 0;
      for (const el of Array.from(containers)) {
        const overflow = el.scrollHeight - el.clientHeight;
        if (overflow > maxOverflow) {
          maxOverflow = overflow;
          logContainer = el;
        }
      }
    }

    if (!logContainer) {
      return { found: false, containers_found: containers.length };
    }

    const before = logContainer.scrollTop;
    const scrollHeight = logContainer.scrollHeight;
    const clientHeight = logContainer.clientHeight;

    // Scroll to top to trigger autoScrollPaused
    logContainer.scrollTop = 0;
    logContainer.dispatchEvent(new Event('scroll', { bubbles: true }));

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

  // Check for scroll indicator
  const indicatorCheck = await page.evaluate(() => {
    const allText = document.body.innerText;
    const hasScrollToResume = allText.includes('scroll to resume');
    const hasDownArrow = allText.includes('↓');

    // Look specifically for the button with text "↓ scroll to resume"
    const buttons = document.querySelectorAll('button');
    let resumeBtn = null;
    for (const btn of Array.from(buttons)) {
      if (btn.textContent && btn.textContent.includes('scroll to resume')) {
        resumeBtn = btn.outerHTML.substring(0, 200);
        break;
      }
    }

    // Also check the relative div that contains the log viewer
    const relativeDivs = document.querySelectorAll('div[class*="relative"]');
    let absoluteBottom = null;
    for (const div of Array.from(relativeDivs)) {
      const abs = div.querySelector('[class*="absolute"]');
      if (abs) {
        absoluteBottom = abs.outerHTML.substring(0, 200);
        break;
      }
    }

    return {
      has_scroll_to_resume: hasScrollToResume,
      has_down_arrow: hasDownArrow,
      resume_button_html: resumeBtn,
      absolute_element: absoluteBottom,
      body_snippet_from_300: allText.substring(300, 900)
    };
  });
  console.log('Indicator check:', JSON.stringify(indicatorCheck, null, 2));

  // Take screenshot with indicator (if visible)
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'dash03-scroll-indicator.png'), fullPage: false });
  console.log('Screenshot saved: dash03-scroll-indicator.png');

  const indicatorAppeared = indicatorCheck.has_scroll_to_resume || !!indicatorCheck.resume_button_html;

  // Scroll back to bottom
  console.log('Scrolling back to bottom...');
  await page.evaluate(() => {
    const containers = document.querySelectorAll('div[class*="overflow-y-auto"]');
    for (const el of Array.from(containers)) {
      if (el.className.includes('p-3') || (el.scrollHeight > el.clientHeight)) {
        el.scrollTop = el.scrollHeight;
        el.dispatchEvent(new Event('scroll', { bubbles: true }));
      }
    }
  });

  await sleep(1000);

  const dismissedCheck = await page.evaluate(() => {
    const allText = document.body.innerText;
    return allText.includes('scroll to resume') ? 'INDICATOR STILL VISIBLE' : 'INDICATOR DISMISSED';
  });
  console.log('Indicator dismissed:', dismissedCheck);

  await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'dash03-scroll-resumed.png'), fullPage: false });
  console.log('Screenshot saved: dash03-scroll-resumed.png');

  const indicatorDismissed = dismissedCheck === 'INDICATOR DISMISSED';
  const panelOverflow = scrollResult.overflow || (scrollResult.scrollHeight > scrollResult.clientHeight);

  let verdict;
  if (panelOverflow && indicatorAppeared && indicatorDismissed) {
    verdict = 'PASS';
  } else if (panelOverflow && indicatorAppeared) {
    verdict = 'PARTIAL';
  } else if (panelOverflow) {
    verdict = 'FAIL'; // overflow but indicator didn't appear
  } else {
    verdict = 'FAIL'; // no overflow even with 35 lines
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
    log_container_class: scrollResult.class,
    child_count: scrollResult.childCount,
    indicator_appeared: indicatorAppeared,
    indicator_dismissed: indicatorDismissed,
    indicator_check: indicatorCheck,
    scroll_result: scrollResult
  };

  fs.writeFileSync(
    path.join(SCREENSHOT_DIR, 'dash03-results.json'),
    JSON.stringify(results, null, 2)
  );

  await browser.close();

  console.log('\n=== DISPATCH OUTPUT (last 600) ===');
  console.log(dispatchOutput.substring(Math.max(0, dispatchOutput.length - 600)));

  return results;
}

main().catch(e => {
  console.error('ERROR:', e.message);
  console.error(e.stack);
  process.exit(1);
});
