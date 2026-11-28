// Render the desktop icons (aftergrid-*.svg) to the PNG sizes KDE looks for. Run after make_art.py:
//   node content/tools/render_icons.js
const {chromium} = require('playwright'); const fs = require('fs'), path = require('path');
const R = path.join(__dirname, '../../build/config/includes.chroot/usr/share/icons/hicolor');
(async () => {
  const b = await chromium.launch(); const p = await b.newPage();
  for (const f of fs.readdirSync(R + '/scalable/apps').filter(f => /^aftergrid-(?!os).*\.svg$/.test(f))) {
    const svg = fs.readFileSync(R + '/scalable/apps/' + f, 'utf8');
    for (const s of [48, 64, 128, 256]) {
      await p.setViewportSize({width: s, height: s});
      await p.setContent(`<style>html,body{margin:0;background:transparent}</style><img src="data:image/svg+xml;base64,${Buffer.from(svg).toString('base64')}" width=${s} height=${s}>`);
      await p.waitForTimeout(50); fs.mkdirSync(`${R}/${s}x${s}/apps`, {recursive: true});
      await p.screenshot({path: `${R}/${s}x${s}/apps/${f.replace('.svg', '.png')}`, omitBackground: true});
    }
  }
  await b.close();
})();
