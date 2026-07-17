import { chromium } from 'playwright';

const BASE = 'http://127.0.0.1:8099';
const results = { pass: 0, fail: 0, total: 0 };
function check(name, pass, detail = '') {
  results.total++;
  if (pass) results.pass++; else results.fail++;
  console.log(`${pass ? '  ✅' : '  ❌'} ${name}${detail ? ' — ' + detail : ''}`);
}

async function run() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

  // ── 1. API Tests ──
  console.log('\n=== API ENDPOINTS ===');
  const endpoints = [
    '/api/overview', '/api/projects', '/api/models',
    '/api/sessions?limit=500', '/api/skills', '/api/tools',
    '/api/knowledge', '/api/initiatives',
    '/api/daily-sessions?days=7', '/api/daily-sessions?days=365',
    '/api/skill-detail?days=1', '/api/tool-detail',
    '/api/file-detail?limit=5',
  ];
  for (const ep of endpoints) {
    try {
      const r = await (await fetch(`${BASE}${ep}`)).json();
      const count = Array.isArray(r) ? r.length : 'OK';
      check(`GET ${ep}`, true, `(${count})`);
    } catch(e) { check(`GET ${ep}`, false, e.message); }
  }

  // ── 2. Overview ──
  console.log('\n=== OVERVIEW ===');
  await page.goto(BASE);
  await page.waitForTimeout(3000);
  
  check('Page title', await page.textContent('.page-title') === 'Analytics Overview');
  check('5 stat cards', (await page.$$('.stat-card')).length === 5);
  check('6 range buttons', (await page.$$('.range-btn')).length === 6);
  check('Daily chart bars', (await page.$$('.chart-bar')).length > 0);
  check('Tool dist items', (await page.$$('#toolDistContainer .flex')).length > 0);
  check('Recent sessions', (await page.$$('#recentSessionsContainer .list-item')).length > 0);
  
  // Stat card click -> Sessions
  await page.click('.stat-card:first-child');
  await page.waitForTimeout(1000);
  check('Stat card click -> Sessions', (await page.textContent('.page-title')).includes('Sessions'));
  
  // ── 3. Projects ──
  console.log('\n=== PROJECTS ===');
  await page.evaluate('navigate("projects")');
  await page.waitForTimeout(2000);
  check('Projects loads', (await page.textContent('.page-title')).includes('Projects'));
  check('Project items', (await page.$$('.list-item')).length > 0);
  
  const projItems = await page.$$('.list-item');
  if (projItems.length > 0) {
    await projItems[0].click();
    await page.waitForTimeout(2000);
    check('Project expands', await page.$('.lexpand.open') !== null);
  }

  // ── 4. Sessions ──
  console.log('\n=== SESSIONS ===');
  await page.evaluate('navigate("sessions")');
  await page.waitForTimeout(2000);
  check('Sessions loads', (await page.textContent('.page-title')).includes('Sessions'));
  
  const sessionItems = await page.$$('.list-item');
  check('Session items (494)', sessionItems.length >= 100);
  check('Search box', await page.$('#sessionSearch') !== null);
  
  if (sessionItems.length > 0) {
    await sessionItems[0].click();
    await page.waitForTimeout(2000);
    check('Session expands', await page.$('.lexpand.open') !== null);
  }

  // ── 5. Models ──
  console.log('\n=== MODELS ===');
  await page.evaluate('navigate("monitor")');
  await page.waitForTimeout(2000);
  check('Models loads', (await page.textContent('.page-title')).includes('Model Usage'));
  check('Model stat cards', (await page.$$('.stat-card')).length >= 3);
  check('Model breakdown', (await page.$$('.panel .mb-md')).length > 0);

  // ── 6. Skills ──
  console.log('\n=== SKILLS ===');
  await page.evaluate('navigate("skills")');
  await page.waitForTimeout(2500);
  check('Skills loads', (await page.textContent('.page-title')).includes('Skills'));
  
  const skillItems = await page.$$('.list-item');
  check('Skill items', skillItems.length > 0);
  check('Range buttons', (await page.$$('.range-btn')).length >= 3);
  
  if (skillItems.length > 0) {
    await skillItems[0].click();
    await page.waitForTimeout(2500);
    const expanded = await page.$('.lexpand.open');
    check('Skill expands', expanded !== null);
    if (expanded) {
      check('Has metadata', await expanded.$('.summary-card') !== null);
      check('Has timeline', await expanded.$('.timeline-item') !== null);
      check('Has SKILL.md toggle', await expanded.$('[class*="skill-md"]') !== null);
    }
  }

  // ── 7. Tools ──
  console.log('\n=== TOOLS ===');
  await page.evaluate('navigate("tools")');
  await page.waitForTimeout(2000);
  check('Tools loads', (await page.textContent('.page-title')).includes('Tools'));
  
  const toolItems = await page.$$('.list-item');
  check('Tool items', toolItems.length > 0);
  if (toolItems.length > 0) {
    await toolItems[0].click();
    await page.waitForTimeout(2000);
    check('Tool expands', await page.$('.lexpand.open') !== null);
  }

  // ── 8. Files ──
  console.log('\n=== FILES ===');
  await page.evaluate('navigate("files")');
  await page.waitForTimeout(2000);
  check('Files loads', (await page.textContent('.page-title')).includes('Files'));
  check('Filter inputs', (await page.$$('.search-box input')).length >= 2);
  
  const fileItems = await page.$$('.list-item');
  check('File items', fileItems.length > 0);
  if (fileItems.length > 0) {
    await fileItems[0].click();
    await page.waitForTimeout(2000);
    check('File expands', await page.$('.lexpand.open') !== null);
  }

  // ── 9. Knowledge ──
  console.log('\n=== KNOWLEDGE ===');
  await page.evaluate('navigate("knowledge")');
  await page.waitForTimeout(2000);
  check('Knowledge loads', (await page.textContent('.page-title')).includes('Knowledge'));
  
  const knowItems = await page.$$('.list-item');
  check('Knowledge items', knowItems.length > 0);
  if (knowItems.length > 0) {
    await knowItems[0].click();
    await page.waitForTimeout(1500);
    check('Knowledge expands with sections', await page.$('.lexpand.open') !== null);
  }

  // ── 10. Initiatives ──
  console.log('\n=== INITIATIVES ===');
  await page.evaluate('navigate("initiatives")');
  await page.waitForTimeout(3000);
  check('Initiatives loads', (await page.textContent('.page-title')).includes('Initiatives'));
  
  const initItems = await page.$$('.list-item');
  check('Initiative items', initItems.length > 0);
  if (initItems.length > 0) {
    await initItems[0].click();
    await page.waitForTimeout(2500);
    check('Initiative expands', await page.$('.lexpand.open') !== null);
  }

  // ── Summary ──
  console.log(`\n${'='.repeat(50)}`);
  console.log(`RESULTS: ${results.pass}/${results.total} passed, ${results.fail} failed`);
  console.log(`${'='.repeat(50)}`);

  await browser.close();
  process.exit(results.fail > 0 ? 1 : 0);
}

run().catch(e => { console.error('FATAL:', e); process.exit(1); });
