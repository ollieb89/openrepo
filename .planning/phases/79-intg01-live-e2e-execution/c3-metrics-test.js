#!/usr/bin/env node
/**
 * Phase 79 Plan 06: C3 Metrics Page DOM Inspection
 * Inspects /occc/metrics page for actual numeric completed count.
 */

const PLAYWRIGHT_MODULE_DIR = '/home/ob/.nvm/versions/node/v22.21.1/lib/node_modules/@playwright/mcp/node_modules';
const { chromium } = require(PLAYWRIGHT_MODULE_DIR + '/playwright');
const path = require('path');
const fs = require('fs');

const SCREENSHOT_DIR = path.join(__dirname, '79-criterion-screenshots');
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

  await context.addInitScript((token) => {
    window.localStorage.setItem('openclaw_token', token);
  }, TOKEN);

  await context.setExtraHTTPHeaders({
    'X-OpenClaw-Token': TOKEN
  });

  const page = await context.newPage();

  // Navigate to metrics page
  console.log('Navigating to metrics page...');
  await page.goto('http://localhost:6987/occc/metrics', { waitUntil: 'domcontentloaded', timeout: 15000 });
  await page.waitForTimeout(3000); // Wait for React to render
  console.log('Current URL:', page.url());
  console.log('Page title:', await page.title());

  // Take initial screenshot
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'c3-metrics-data.png'), fullPage: true });
  console.log('Screenshot saved: c3-metrics-data.png');

  // DOM inspection for numeric data
  const domResult = await page.evaluate(() => {
    const result = {
      page_title: document.title,
      url: window.location.href,
    };

    // Try common patterns for metric value displays
    const selectors = [
      '[data-metric]', '[data-value]', '.metric-value', '.stat-value',
      '.chart-value', '.count-value', 'text[data-testid]',
      '[aria-label*=completed]', '[aria-label*=Completed]',
      'td', 'th', '.recharts-text', '.recharts-label'
    ];

    for (const sel of selectors) {
      try {
        const els = document.querySelectorAll(sel);
        if (els.length > 0) {
          const texts = Array.from(els).slice(0, 10).map(e => e.textContent.trim()).filter(t => t.length > 0 && t.length < 200);
          if (texts.length > 0) {
            result[sel] = texts;
          }
        }
      } catch(e) {}
    }

    // Check page text for numbers near 'completed'
    const allText = document.body.innerText;
    const completedIdx = allText.toLowerCase().indexOf('completed');
    if (completedIdx >= 0) {
      result.completed_context = allText.substring(Math.max(0, completedIdx - 80), completedIdx + 150);
    }

    // Check for any numeric values (1-999) on the page
    const numbers = allText.match(/\b([1-9][0-9]{0,2})\b/g);
    result.numeric_values_found = numbers ? [...new Set(numbers)].slice(0, 15) : [];

    // Full page text snippet
    result.full_text_snippet = allText.substring(0, 2000);

    return result;
  });
  console.log('DOM inspection result:', JSON.stringify(domResult, null, 2));

  // Additional pipeline timeline check
  const pipelineResult = await page.evaluate(() => {
    const timeline = document.querySelector('[data-testid*=timeline], .pipeline-timeline, .timeline');
    const rows = document.querySelectorAll('tr');
    const rowTexts = Array.from(rows).map(r => r.textContent.trim()).filter(t => t.length > 0).slice(0, 10);

    // Look for stat/number display elements
    const statEls = document.querySelectorAll('[class*=stat], [class*=metric], [class*=count], [class*=number]');
    const statTexts = Array.from(statEls).slice(0, 10).map(e => ({
      class: e.className.substring(0, 50),
      text: e.textContent.trim().substring(0, 100)
    }));

    return {
      timeline_found: !!timeline,
      row_count: rows.length,
      row_texts: rowTexts,
      stat_elements: statTexts
    };
  });
  console.log('Pipeline/stats result:', JSON.stringify(pipelineResult, null, 2));

  // Analyze verdict
  const allText = domResult.full_text_snippet || '';
  const numerics = domResult.numeric_values_found || [];

  // Check if any numbers are near completion context
  let numericCompletedCount = null;
  const completedContext = domResult.completed_context || '';
  const numbersInContext = completedContext.match(/\b([1-9][0-9]{0,2})\b/g);
  if (numbersInContext && numbersInContext.length > 0) {
    numericCompletedCount = parseInt(numbersInContext[0]);
  }

  let verdict;
  let reason;

  if (numericCompletedCount !== null && numericCompletedCount > 0) {
    verdict = 'PASS';
    reason = `Found numeric completed count: ${numericCompletedCount} in completed context`;
  } else if (numerics.length > 0 && allText.toLowerCase().includes('completed')) {
    verdict = 'PARTIAL';
    reason = `Page has numbers ${numerics.join(',')} and "completed" text, but numeric value not adjacent to completed label`;
  } else if (allText.toLowerCase().includes('completed')) {
    verdict = 'FAIL';
    reason = '"completed" text found but no numeric count detected in chart/table elements';
  } else {
    verdict = 'FAIL';
    reason = 'Metrics page does not show completed data';
  }

  console.log('\n=== C3 VERDICT ===');
  console.log(`Numeric completed count: ${numericCompletedCount}`);
  console.log(`Numeric values on page: ${numerics.join(', ')}`);
  console.log(`Completed context: "${completedContext.substring(0, 200)}"`);
  console.log(`C3 verdict: ${verdict}`);
  console.log(`Reason: ${reason}`);

  const results = {
    verdict,
    reason,
    numeric_completed_count: numericCompletedCount,
    numeric_values_found: numerics,
    completed_context: completedContext,
    dom_inspection: domResult,
    pipeline: pipelineResult
  };

  fs.writeFileSync(
    path.join(SCREENSHOT_DIR, 'c3-metrics-results.json'),
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
