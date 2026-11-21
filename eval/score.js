// Aftergrid retrieval test: does Ask put a relevant source in front of the AI?
// Usage: node score.js <label> [k=3]   -> writes results-<label>.json and prints hit@k by category.
const p = require('/home/claude/ark/web/node_modules/puppeteer-core');
const fs = require('fs');
const [, , label = 'run', kArg] = process.argv;
const Q = JSON.parse(fs.readFileSync(__dirname + '/questions.json', 'utf8'));
(async () => {
  const b = await p.launch({executablePath: '/usr/bin/google-chrome', protocolTimeout: 3600000, args: ['--no-sandbox'], headless: 'new'});
  const pg = await b.newPage();
  await pg.evaluateOnNewDocument(() => localStorage.setItem('aftergrid-lang', 'en'));
  await pg.goto('http://localhost/ask.html', {waitUntil: 'networkidle0'});
  await pg.waitForFunction(() => window.agRetrieve);
  const res = [];
  for (const x of Q) {
    const t0 = Date.now();
    const r = await pg.evaluate(async q => { const o = await window.agRetrieve(q, true); return {sq: o.sq, hits: o.hits.map(h => ({title: h.title, book: h.book, href: h.href}))}; }, x.q);
    const re = new RegExp(x.expect, 'i');
    const pos = r.hits.findIndex(h => re.test(h.title));
    res.push({...x, sq: r.sq, hits: r.hits, pos, ms: Date.now() - t0});
    console.log(`${pos >= 0 ? 'HIT ' + (pos + 1) : 'MISS  '} ${String(x.id).padStart(2)} ${x.q}  ->  ${r.hits.map(h => h.title).join(' | ')}`);
  }
  fs.writeFileSync(`${__dirname}/results-${label}.json`, JSON.stringify(res, null, 1));
  const k = Number(kArg || 3);
  for (const cat of ['medical', 'griddown', 'all']) {
    const s = res.filter(r => cat === 'all' || r.cat === cat);
    const top1 = s.filter(r => r.pos === 0).length, topk = s.filter(r => r.pos >= 0 && r.pos < k).length;
    console.log(`${label} ${cat.padEnd(8)} top-1 ${top1}/${s.length} (${Math.round(100 * top1 / s.length)}%)   in sources ${topk}/${s.length} (${Math.round(100 * topk / s.length)}%)`);
  }
  await b.close();
})();
