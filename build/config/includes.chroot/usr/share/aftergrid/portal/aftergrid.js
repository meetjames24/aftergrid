// Aftergrid portal helpers: shared by every page. Works on the desktop (localhost)
// and on phones connected to the Aftergrid hotspot (same origin, relative URLs).
// Theme: light by default; Night mode when chosen, or automatically in low-power mode. Applied before anything draws.
(() => { try { const t = localStorage.getItem('aftergrid-theme'); if (t === 'night') document.documentElement.dataset.theme = 'night'; } catch (e) {} })();

const Aftergrid = {
  index: null, books: [],
  lang: (() => { try { return localStorage.getItem('aftergrid-lang') || (navigator.language || 'en').slice(0, 2); } catch (e) { return 'en'; } })(),
  T(s) { const d = (typeof AFTERGRID_I18N !== 'undefined' && AFTERGRID_I18N[this.lang]) || {}; return d[s] || s; },
  theme() { return document.documentElement.dataset.theme === 'night' ? 'night' : 'light'; },
  setTheme(t, save = true) {
    if (t === 'night') document.documentElement.dataset.theme = 'night'; else delete document.documentElement.dataset.theme;
    if (save) try { localStorage.setItem('aftergrid-theme', t); } catch (e) {}
    window.dispatchEvent(new Event('aftergrid-theme'));
    const moon = '<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z"/></svg>';
    const sun = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="12" cy="12" r="4.5"/><path d="M12 2v2.5M12 19.5V22M2 12h2.5M19.5 12H22M4.9 4.9l1.8 1.8M17.3 17.3l1.8 1.8M4.9 19.1l1.8-1.8M17.3 6.7l1.8-1.8"/></svg>';
    const b = document.getElementById('theme'); if (b) b.innerHTML = t === 'night' ? sun + this.T('Day') : moon + this.T('Night');
  },
  setLang(l) { try { localStorage.setItem('aftergrid-lang', l); } catch (e) {} location.reload(); },
  translatePage() {
    document.documentElement.lang = this.lang;
    document.querySelectorAll('[data-t]').forEach(el => { el.textContent = this.T(el.textContent.trim()); });
    document.querySelectorAll('[data-tp]').forEach(el => { el.placeholder = this.T(el.placeholder); });
  },

  async load() {
    try { this.index = await (await fetch('/index.json', {cache: 'no-store'})).json(); }
    catch (e) { this.index = {zims: [], maps: [], pdfs: [], ai: false}; }
    try {
      const xml = await (await fetch('/kiwix/catalog/v2/entries?count=-1')).text();
      const doc = new DOMParser().parseFromString(xml, 'application/xml');
      this.books = [...doc.getElementsByTagName('entry')].map(e => {
        const t = n => (e.getElementsByTagName(n)[0] || {}).textContent || '';
        const html = [...e.getElementsByTagName('link')].find(l => l.getAttribute('type') === 'text/html');
        return {name: t('name'), title: t('title'), id: t('id').replace('urn:uuid:', ''),
                href: html ? html.getAttribute('href') : null};
      });
    } catch (e) { this.books = []; }
    return this;
  },

  // Find a library book by the start of its file name, e.g. "mdwiki_en_all".
  book(prefix) {
    return this.books.find(b => b.href && (b.name.startsWith(prefix) || decodeURIComponent(b.href).includes('/content/' + prefix)));
  },

  // Full-text search. Kiwix refuses to search books in different languages at once,
  // so search the English library and the UI-language library separately, then merge.
  async searchAll(q, n) {
    const ISO3 = {en: 'eng', el: 'ell', fr: 'fra', de: 'deu', pt: 'por', tr: 'tur'};
    const langs = [...new Set([ISO3[this.lang], 'eng'].filter(Boolean))];
    const one = async lang => {
      const url = `/kiwix/search?pattern=${encodeURIComponent(q)}&format=xml&pageLength=${n || 25}&books.filter.lang=${lang}`;
      try {
        const doc = new DOMParser().parseFromString(await (await fetch(url)).text(), 'application/xml');
        return [...doc.getElementsByTagName('item')].map(it => {
          const t = k => (it.getElementsByTagName(k)[0] || {}).textContent || '';
          const href = t('link'); const stem = decodeURIComponent(href.split('/content/')[1] || '').split('/')[0];
          const b = this.books.find(x => x.href && decodeURIComponent(x.href).replace(/\/$/, '').endsWith('/content/' + stem));
          return {title: t('title'), href, snippet: t('description').slice(0, 260), book: b ? b.title.slice(0, 28) : stem};
        });
      } catch (e) { return []; }
    };
    const lists = await Promise.all(langs.map(one));
    const out = [];   // interleave so neither language buries the other
    for (let i = 0; out.length < (n || 25) && lists.some(l => i < l.length); i++) lists.forEach(l => l[i] && out.push(l[i]));
    return out.slice(0, n || 25);
  },
  pdf(name) { return (this.index.pdfs || []).find(p => p.file === name); },

  header(title) {
    const h = document.createElement('header');
    h.innerHTML = `<h1><a href="/"><img src="/aftergrid-mark.svg" alt="" width="34" height="34" style="vertical-align:-7px;margin-right:10px">AFTERGRID</a></h1>
      <form class="search" action="/search.html"><input name="q" placeholder="${this.T('Search the whole library…')}" aria-label="Search"><button class="primary">${this.T('Search')}</button></form>
      <div class="status"><span>${this.T(title || '')}</span><button id="theme" class="themebtn" type="button"></button><select id="lang" aria-label="Language">${Object.entries(typeof AFTERGRID_LANGS !== 'undefined' ? AFTERGRID_LANGS : {en:'English'}).map(([c,n]) => `<option value="${c}"${c === this.lang ? ' selected' : ''}>${n}</option>`).join('')}</select></div>`;
    document.body.prepend(h);
    h.querySelector('#lang').onchange = (e) => this.setLang(e.target.value);
    let chosen = null; try { chosen = localStorage.getItem('aftergrid-theme'); } catch (e) {}
    if (!chosen && this.index && this.index.lowpower) this.setTheme('night', false);   // low-power mode: dark unless the user chose
    else this.setTheme(this.theme(), false);
    h.querySelector('#theme').onclick = () => this.setTheme(this.theme() === 'night' ? 'light' : 'night');
    this.translatePage();
    const ic = document.createElement('link'); ic.rel = 'icon'; ic.href = '/aftergrid-mark.svg'; document.head.append(ic);
    const f = document.createElement('footer');
    f.textContent = this.T('Aftergrid works without internet. Information here is reference material, not a substitute for trained help when it is available.');
    document.body.append(f);
  },

  // Render a list of resources: {k:'kind', label, zim:'prefix'} | {pdf:'file.pdf'} | {search:'terms', zim:'prefix'} | {href}
  render(el, items) {
    el.innerHTML = '';
    for (const it of items) {
      let href = it.href || null, ok = true;
      if (it.zim) {
        const b = this.book(it.zim);
        if (!b) ok = false;
        else if (it.search) href = `/kiwix/search?books.name=${encodeURIComponent(b.name)}&pattern=${encodeURIComponent(it.search)}`;
        else href = b.href;
      } else if (it.pdf) {
        const p = this.pdf(it.pdf); ok = !!p; href = p ? p.url : null;
      }
      const a = document.createElement(ok ? 'a' : 'div');
      a.className = 'item' + (ok ? '' : ' missing');
      if (ok) a.href = href;
      a.innerHTML = `<span class="k">${this.T(it.k || '')}</span><span>${this.T(it.label)}${ok ? '' : ' <small>' + this.T('(not on this Aftergrid yet: Aftergrid Control → Download)') + '</small>'}</span>`;
      el.append(a);
    }
  }
};
