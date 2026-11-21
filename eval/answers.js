// Aftergrid answer test: full offline-AI answers to key questions, checked for facts that must be present.
// Usage: node answers.js <label>
const p = require('/home/claude/ark/web/node_modules/puppeteer-core');
const fs = require('fs');
const label = process.argv[2] || 'run';
const ONLY = process.env.ONLY ? process.env.ONLY.split(',').map(Number) : null;
const T0 = [
  {q: 'How do I stop heavy bleeding from a leg wound?', must: [/pressure/i, /tourniquet/i], mustNot: [/elastic (bandage|band)[^.]*tourniquet|tourniquet[^.]*elastic(?! )/i]},
  {q: "my kid swallowed something and can't breathe", must: [/back blow|abdominal thrust|chest thrust|heimlich/i]},
  {q: "someone collapsed and isn't breathing", must: [/compression|cpr/i, /100|120|5 cm|2 inch/i]},
  {q: "bee sting, face swelling up, can't breathe", must: [/epinephrine|adrenaline|epipen|auto-?injector/i]},
  {q: 'how to treat a burn from boiling water', must: [/cool/i, /20 minutes|running water/i]},
  {q: 'what are the warning signs of heat stroke', must: [/confus/i, /cool/i]},
  {q: 'how do I make oral rehydration solution', must: [/6 (level )?teaspoons|six (level )?teaspoons/i, /half|1\/2|½/i]},
  {q: 'running a generator indoors and everyone has a headache', must: [/carbon monoxide/i, /fresh air|outside|outdoors/i]},
  {q: 'how much bleach to purify drinking water', must: [/(2|two) drops/i, /30 minutes/i]},
  {q: "nosebleed that won't stop", must: [/lean(ing)? forward/i, /pinch/i]},
];
const T = ONLY ? T0.filter((t, i) => ONLY.includes(i + 1)) : T0;
(async () => {
  const b = await p.launch({executablePath: '/usr/bin/google-chrome', protocolTimeout: 3600000, args: ['--no-sandbox'], headless: 'new'});
  const pg = await b.newPage();
  await pg.evaluateOnNewDocument(() => localStorage.setItem('aftergrid-lang', 'en'));
  const res = [];
  for (const t of T) {
    await pg.goto('http://localhost/ask.html', {waitUntil: 'networkidle0'});
    await pg.waitForFunction(() => document.getElementById('state').textContent.includes('running'), {timeout: 60000});
    const t0 = Date.now();
    await pg.type('#q', t.q); await pg.keyboard.press('Enter');
    await pg.waitForFunction(() => window.aftergridAskDone, {timeout: 900000});
    const r = await pg.evaluate(() => ({answer: document.getElementById('out').innerText,
      sources: [...document.querySelectorAll('#src a')].map(a => a.innerText),
      cites: document.querySelectorAll('#out a.cite').length,
      warn: (document.querySelector('#out .note') || {}).innerText || ''}));
    const missing = t.must.filter(re => !re.test(r.answer)).map(String), bad = (t.mustNot || []).filter(re => re.test(r.answer)).map(String);
    const pass = !missing.length && !bad.length;
    res.push({...t, must: t.must.map(String), mustNot: (t.mustNot || []).map(String), ...r, missing, bad, pass, secs: Math.round((Date.now() - t0) / 1000)});
    console.log(`${pass ? 'PASS' : 'FAIL'} ${Math.round((Date.now() - t0) / 1000)}s ${t.q}\n   sources: ${r.sources.join(' | ')}\n   cites: ${r.cites}  warn: ${r.warn}${missing.length ? '\n   missing: ' + missing.join(', ') : ''}${bad.length ? '\n   BAD: ' + bad.join(', ') : ''}`);
  }
  fs.writeFileSync(`${__dirname}/answers-${label}.json`, JSON.stringify(res, null, 1));
  console.log(`${label}: ${res.filter(r => r.pass).length}/${res.length} answers pass`);
  await b.close();
})();
