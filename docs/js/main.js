// 起動・状態管理・イベント配線
import {
  buildTagIndex, renderFilterGroups, collectSelected, skillMatches,
  computeCounts, buildLeavesByGroup, syncParents, NONE_PREFIX,
} from './filters.js';
import { renderCards, renderActiveFilters, updateCounts, sortSkills } from './render.js';
import { t } from './i18n.js';

const els = {
  filterGroups: document.getElementById('filterGroups'),
  sidebar: document.getElementById('sidebar'),
  search: document.getElementById('searchInput'),
  cards: document.getElementById('cards'),
  emptyState: document.getElementById('emptyState'),
  resultCount: document.getElementById('resultCount'),
  totalCount: document.getElementById('totalCount'),
  totalInGame: document.getElementById('totalInGame'),
  activeFilters: document.getElementById('activeFilters'),
  levelButtons: document.getElementById('levelButtons'),
  sortSelect: document.getElementById('sortSelect'),
  clearFilters: document.getElementById('clearFilters'),
  filterToggle: document.getElementById('filterToggle'),
  themeToggle: document.getElementById('themeToggle'),
  flagNoStack: document.getElementById('flagNoStack'),
  flagVariant: document.getElementById('flagVariant'),
  flagPalGear: document.getElementById('flagPalGear'),
};

const state = { tags: null, skills: [], tagIndex: null, leaves: null, star: 0 };

function readFlags() {
  return {
    noStack: els.flagNoStack.checked,
    variant: els.flagVariant.checked,
    palGear: els.flagPalGear.checked,
  };
}

// 「(なし)」等も含めたタグ表示名
function tagLabel(id) {
  if (id.startsWith(NONE_PREFIX)) {
    const g = state.tags.groups.find((x) => x.id === id.slice(NONE_PREFIX.length));
    return `${g ? t(g.label) : ''}（なし）`;
  }
  const tag = state.tagIndex.get(id);
  return tag ? t(tag.label) : id;
}

// ---- URL hash 同期 ----
function optionRows() { return els.filterGroups.querySelectorAll('.filter-option'); }

function writeHash() {
  const inc = [], exc = [];
  optionRows().forEach((r) => {
    if (r.dataset.state === 'inc') inc.push(r.dataset.tagId);
    else if (r.dataset.state === 'exc') exc.push(r.dataset.tagId);
  });
  const p = new URLSearchParams();
  if (inc.length) p.set('t', inc.join(','));
  if (exc.length) p.set('x', exc.join(','));
  if (els.search.value.trim()) p.set('q', els.search.value.trim());
  if (state.star !== 0) p.set('star', state.star);
  if (els.sortSelect.value !== 'no') p.set('sort', els.sortSelect.value);
  const fl = Object.entries(readFlags()).filter(([, v]) => v).map(([k]) => k);
  if (fl.length) p.set('f', fl.join(','));
  const h = p.toString();
  history.replaceState(null, '', h ? `#${h}` : location.pathname + location.search);
}

function restoreFromHash() {
  const p = new URLSearchParams(location.hash.slice(1));
  const inc = new Set((p.get('t') || '').split(',').filter(Boolean));
  const exc = new Set((p.get('x') || '').split(',').filter(Boolean));
  optionRows().forEach((r) => {
    r.dataset.state = inc.has(r.dataset.tagId) ? 'inc' : exc.has(r.dataset.tagId) ? 'exc' : '';
  });
  els.search.value = p.get('q') || '';
  const st = parseInt(p.get('star'), 10);
  state.star = st >= 0 && st <= 4 ? st : 0;
  els.sortSelect.value = p.get('sort') || 'no';
  const fl = new Set((p.get('f') || '').split(',').filter(Boolean));
  els.flagNoStack.checked = fl.has('noStack');
  els.flagVariant.checked = fl.has('variant');
  els.flagPalGear.checked = fl.has('palGear');
}

// ---- 強化ランク（★0〜★4） ----
function buildLevelButtons() {
  els.levelButtons.innerHTML = '';
  for (let s = 0; s <= 4; s++) {
    const b = document.createElement('button');
    b.type = 'button'; b.className = 'level-btn'; b.textContent = '★' + s;
    b.setAttribute('role', 'radio');
    b.addEventListener('click', () => { state.star = s; syncLevelButtons(); apply(); });
    els.levelButtons.appendChild(b);
  }
}
function syncLevelButtons() {
  [...els.levelButtons.children].forEach((b, i) => {
    const on = i === state.star;
    b.classList.toggle('is-active', on);
    b.setAttribute('aria-checked', on ? 'true' : 'false');
  });
}

// ---- 描画 ----
function apply() {
  const sel = collectSelected(els.filterGroups);
  const text = els.search.value.trim();
  const flags = readFlags();

  const filtered = state.skills.filter((s) => skillMatches(s, sel, text, flags, state.tags, state.leaves));
  const sorted = sortSkills(filtered, els.sortSelect.value, state.tagIndex);

  renderCards(els.cards, sorted, state.tagIndex, state.star);
  els.resultCount.textContent = sorted.length;
  els.totalCount.textContent = state.skills.length;
  els.emptyState.hidden = sorted.length !== 0;

  updateCounts(els.filterGroups, computeCounts(state.skills, state.tags, sel, text, flags, state.leaves));
  syncParents(els.filterGroups);

  const entries = [];
  for (const [, crit] of Object.entries(sel)) {
    crit.inc.forEach((id) => entries.push({ id, mode: 'inc', label: tagLabel(id) }));
    crit.exc.forEach((id) => entries.push({ id, mode: 'exc', label: tagLabel(id) }));
  }
  renderActiveFilters(els.activeFilters, entries, (id) => {
    const r = els.filterGroups.querySelector(`.filter-option[data-tag-id="${CSS.escape(id)}"]`);
    if (r) { r.dataset.state = ''; apply(); }
  });
  syncLevelButtons();
  writeHash();
}

// ---- テーマ ----
function initTheme() {
  const saved = localStorage.getItem('pal-theme');
  if (saved) document.documentElement.dataset.theme = saved;
  els.themeToggle.addEventListener('click', () => {
    const cur = document.documentElement.dataset.theme;
    const isDark = cur ? cur === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches;
    const next = isDark ? 'light' : 'dark';
    document.documentElement.dataset.theme = next;
    localStorage.setItem('pal-theme', next);
  });
}

async function loadJSON(path) {
  const res = await fetch(path, { cache: 'no-cache' });
  if (!res.ok) throw new Error(`${path}: ${res.status}`);
  return res.json();
}

async function init() {
  initTheme();
  buildLevelButtons();
  try {
    const [tags, skillsDoc] = await Promise.all([
      loadJSON('./data/tags.json'), loadJSON('./data/skills.json'),
    ]);
    state.tags = tags;
    state.skills = skillsDoc.skills || [];
    state.tagIndex = buildTagIndex(tags);
    state.leaves = buildLeavesByGroup(tags);
    const total = skillsDoc.meta?.totalSkills ?? state.skills.length;
    if (els.totalInGame) els.totalInGame.textContent = total;
  } catch (err) {
    els.cards.innerHTML = `<p class="load-error">データの読み込みに失敗しました：${err.message}<br>HTTP サーバ経由で開いているか確認してください（file:// 直開きは不可）。</p>`;
    return;
  }

  renderFilterGroups(state.tags, els.filterGroups, apply);
  restoreFromHash();
  syncLevelButtons();

  els.search.addEventListener('input', apply);
  els.sortSelect.addEventListener('change', apply);
  [els.flagNoStack, els.flagVariant, els.flagPalGear].forEach((cb) => cb.addEventListener('change', apply));
  els.clearFilters.addEventListener('click', () => {
    optionRows().forEach((r) => (r.dataset.state = ''));
    els.search.value = '';
    [els.flagNoStack, els.flagVariant, els.flagPalGear].forEach((cb) => (cb.checked = false));
    apply();
  });
  els.filterToggle.addEventListener('click', () => {
    const open = els.sidebar.classList.toggle('is-open');
    els.filterToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
  });

  apply();
}

init();
