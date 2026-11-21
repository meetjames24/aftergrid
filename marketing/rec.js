// Aftergrid marketing recorder: drives the real Field Mode and captures frames.
// Usage: node rec.js <phone|desk> <clip> <outdir>
// Writes outdir/NNNN.jpg plus outdir/manifest.json = [{f, d}] (d = seconds on screen).
const p = require('/home/claude/ark/web/node_modules/puppeteer-core');
const fs = require('fs');
const [, , form, clip, out] = process.argv;
const VIEW = form === 'phone' ? {width: 400, height: 556, deviceScaleFactor: 2.7}     // 1080 x 1501
                              : {width: 1280, height: 720, deviceScaleFactor: 1.5};   // 1920 x 1080
const sleep = ms => new Promise(r => setTimeout(r, ms));
const B = 'http://localhost';
let pg, n = 0; const man = [];

async function shot(d) {
  const f = String(n++).padStart(4, '0') + '.jpg';
  await pg.screenshot({path: `${out}/${f}`, type: 'jpeg', quality: 92});
  man.push({f, d});
}
async function hold(d) { await shot(d); }
async function go(url, wait = 900) { await pg.goto(B + url, {waitUntil: 'networkidle0', timeout: 120000}); await sleep(wait); }
// Human-ish typing: one frame per character, uneven rhythm, a pause after spaces.
async function typeIn(sel, text) {
  await pg.click(sel); await sleep(150); await shot(0.35);
  for (const ch of text) {
    await pg.type(sel, ch);
    await shot(ch === ' ' ? 0.16 : 0.055 + Math.random() * 0.06);
  }
  await shot(0.45);
}
async function scrollTo(y, secs) {
  const y0 = await pg.evaluate(() => window.scrollY);
  const steps = Math.round(secs * 30);
  for (let i = 1; i <= steps; i++) {
    const t = i / steps, e = t < .5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
    await pg.evaluate(v => window.scrollTo(0, v), y0 + (y - y0) * e); await shot(1 / 30);
  }
}
// Search from the header box, the way a person would.
async function search(q, holdS = 1.6) {
  await typeIn('header input[name=q]', q);
  await Promise.all([pg.waitForNavigation({waitUntil: 'networkidle0'}), pg.keyboard.press('Enter')]);
  await pg.waitForSelector('#list .item', {timeout: 60000}); await sleep(500);
  await hold(holdS);
}
async function tapFirst(holdS = 0.4) {
  await pg.evaluate(() => { const a = document.querySelector('#list .item'); a.style.borderColor = '#F2A33A'; a.style.boxShadow = '0 0 0 3px rgba(242,163,58,.35)'; });
  await hold(holdS);
}
async function mapTo(z0, z1, lat0, lon0, lat1, lon1, secs) {
  const steps = Math.round(secs * 30);
  for (let i = 0; i <= steps; i++) {
    const t = i / steps, e = t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
    const z = z0 + (z1 - z0) * e, la = lat0 + (lat1 - lat0) * e, lo = lon0 + (lon1 - lon0) * e;
    await pg.evaluate(h => { location.hash = h; }, `#${z.toFixed(3)}/${la.toFixed(5)}/${lo.toFixed(5)}`);
    await sleep(i === 0 ? 4000 : 260); await shot(1 / 30);
  }
}
async function ask(q, every = 1500, speed = 15) {
  await typeIn('#q', q);
  await pg.keyboard.press('Enter');
  const t0 = Date.now();
  while (!(await pg.evaluate(() => window.aftergridAskDone)) && Date.now() - t0 < 900000) {
    // keep the end of the answer in view, like a reader would
    await pg.evaluate(() => { const o = document.getElementById('out'); const r = o.getBoundingClientRect();
      if (r.bottom > innerHeight - 40) window.scrollTo(0, scrollY + r.bottom - innerHeight + 60); });
    await shot(every / 1000 / speed); await sleep(every);
  }
  await pg.evaluate(() => { const o = document.getElementById('out'); window.scrollTo(0, scrollY + o.getBoundingClientRect().bottom - innerHeight + 60); });
  await hold(1.2);
  console.log('ask took', (Date.now() - t0) / 1000, 's');
}

const CLIPS = {
  home: async () => { await go('/'); await hold(1.2); await scrollTo(form === 'phone' ? 900 : 260, 2.2); await hold(0.6); await scrollTo(0, 1.0); await hold(0.4); },
  water: async () => { await go('/'); await hold(0.5); await search('water filter'); },
  food: async () => { await go('/'); await hold(0.4); await search('food storage'); },
  fallout: async () => { await go('/'); await hold(0.4); await search('fallout shelter'); },
  tourniquet: async () => { await go('/'); await hold(0.4); await search('tourniquet'); },
  choking: async () => {
    await go('/'); await hold(0.4); await search('choking', 1.0); await tapFirst();
    const href = await pg.evaluate(() => document.querySelector('#list .item').href);
    await pg.goto(href, {waitUntil: 'networkidle0'}); await sleep(800); await hold(1.2);
    await scrollTo(form === 'phone' ? 520 : 380, 2.4); await hold(1.4);
  },
  anaphylaxis: async () => { await go('/'); await hold(0.4); await search('anaphylaxis'); },
  heatstroke: async () => { await go('/'); await hold(0.4); await search('heat stroke'); },
  snakebite: async () => { await go('/'); await hold(0.4); await search('snakebite'); },
  medtopic: async () => { await go('/topic.html?t=medical'); await hold(1.0); await scrollTo(form === 'phone' ? 900 : 300, 2.5); await hold(0.6); },
  map: async () => { await go('/maps.html#4.5/36.5/-93.5', 3000); await mapTo(4.5, 12.2, 36.5, -93.5, 34.7465, -92.2896, 4.5); await hold(1.2); },
  askwater: async () => { await go('/ask.html', 1500); await hold(0.8); await ask('How do I make water safe to drink with bleach?'); },
  askheat: async () => { await go('/ask.html', 1500); await hold(0.8); await ask('What are the warning signs of heat stroke?'); },
  askbleed: async () => { await go('/ask.html', 1500); await hold(0.8); await ask('How do I stop heavy bleeding from a leg wound?'); },
  langs: async () => {
    for (const l of ['en', 'el', 'fr', 'de', 'pt', 'tr']) {
      await pg.evaluate(v => localStorage.setItem('aftergrid-lang', v), l); await go('/', 600); await hold(0.7);
    }
  },
};

(async () => {
  fs.mkdirSync(out, {recursive: true});
  const b = await p.launch({executablePath: '/usr/bin/google-chrome', protocolTimeout: 1800000,
    args: ['--no-sandbox', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--hide-scrollbars'], headless: 'new'});
  pg = await b.newPage(); await pg.setViewport(VIEW);
  await pg.evaluateOnNewDocument(() => { if (!localStorage.getItem('aftergrid-lang')) localStorage.setItem('aftergrid-lang', 'en'); });
  await go('/'); await pg.evaluate(() => localStorage.setItem('aftergrid-lang', 'en'));
  await CLIPS[clip]();
  fs.writeFileSync(`${out}/manifest.json`, JSON.stringify(man));
  console.log(clip, form, n, 'frames', man.reduce((a, x) => a + x.d, 0).toFixed(1) + 's');
  await b.close();
})();
