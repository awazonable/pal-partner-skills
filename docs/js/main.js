// 起動・状態管理・イベント配線
import {
  buildTagIndex, renderFilterGroups, collectSelectedTags,
  skillMatches, computeCounts,
} from './filters.js';
import {
  renderCards, renderActiveFilters, updateCounts, sortSkills,
} from './render.js';

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

// star: 0..4（=★0〜★4 濃縮ランク）
const state = { tags: null, skills: [], tagIndex: null, star: 0 };

function readFlags() {
  return {
    noStack: els.flagNoStack.checked,
    variant: els.flagVariant.checked,
    palGear: els.flagPalGear.checked,
  };
}

// ---- URL hash 同期（共有可能な絞り込み）----
function writeHash() {
  const sel = collectSelectedTags(els.filterGroups);
  const tagIds = Object.values(sel).flat();
  const params = new URLSearchParams();
  if (tagIds.length) params.set('t', tagIds.join(','));
  if (els.search.value.trim()) params.set('q', els.search.value.trim());
  if (state.star !== 0) params.set('star', state.star);
  if (els.sortSelect.value !== 'no') params.set('sort', els.sortSelect.value);
  const active = Object.entries(readFlags()).filter(([, v]) => v).map(([k]) => k);
  if (active.length) params.set('f', active.join(','));
  const hash = params.toString();
  history.replaceState(null, '', hash ? `#${hash}` : location.pathname + location.search);
}

function restoreFromHash() {
  const params = new URLSearchParams(location.hash.slice(1));
  const tagIds = new Set((params.get('t') || '').split(',').filter(Boolean));
  els.filterGroups.querySelectorAll('input[type=checkbox]').forEach((cb) => {
    cb.checked = tagIds.has(cb.value);
  });
  els.search.value = params.get('q') || '';
  const st = parseInt(params.get('star'), 10);
  state.star = st >= 0 && st <= 4 ? st : 0;
  els.sortSelect.value = params.get('sort') || 'no';
  const flags = new Set((params.get('f') || '').split(',').filter(Boolean));
  els.flagNoStack.checked = flags.has('noStack');
  els.flagVariant.checked = flags.has('variant');
  els.flagPalGear.checked = flags.has('palGear');
}

// ---- 強化ランク（★0〜★4）セレクタ ----
function buildLevelButtons() {
  els.levelButtons.innerHTML = '';
  for (let s = 0; s <= 4; s++) {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'level-btn';
    b.textContent = '★' + s;
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
  const sel = collectSelectedTags(els.filterGroups);
  const text = els.search.value.trim();
  const flags = readFlags();

  const filtered = state.skills.filter((s) => skillMatches(s, sel, text, flags));
  const sorted = sortSkills(filtered, els.sortSelect.value, state.tagIndex);

  renderCards(els.cards, sorted, state.tagIndex, state.star);
  els.resultCount.textContent = sorted.length;
  els.totalCount.textContent = state.skills.length;
  els.emptyState.hidden = sorted.length !== 0;

  updateCounts(els.filterGroups, computeCounts(state.skills, state.tags, sel, text, flags));
  renderActiveFilters(els.activeFilters, sel, state.tagIndex, (id) => {
    const cb = els.filterGroups.querySelector(`input[value="${CSS.escape(id)}"]`);
    if (cb) { cb.checked = false; apply(); }
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
      loadJSON('./data/tags.json'),
      loadJSON('./data/skills.json'),
    ]);
    state.tags = tags;
    state.skills = skillsDoc.skills || [];
    state.tagIndex = buildTagIndex(tags);
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
  [els.flagNoStack, els.flagVariant, els.flagPalGear]
    .forEach((cb) => cb.addEventListener('change', apply));
  els.clearFilters.addEventListener('click', () => {
    els.filterGroups.querySelectorAll('input[type=checkbox]').forEach((cb) => (cb.checked = false));
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
