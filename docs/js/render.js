// カード描画・件数表示・選択中フィルタの表示
import { t } from './i18n.js';

const CONDITION_ORDER = ['cond-base', 'cond-party', 'cond-mount', 'cond-active'];

function chip(label, groupId, color) {
  const el = document.createElement('span');
  el.className = 'chip';
  if (groupId) el.dataset.group = groupId;
  if (color) {
    el.style.setProperty('--chip-color', color);
    el.classList.add('chip-colored');
  }
  el.textContent = label;
  return el;
}

function badge(label, kind) {
  const el = document.createElement('span');
  el.className = `badge badge-${kind}`;
  el.textContent = label;
  return el;
}

// star は 0..4（=★0〜★4）
function effectRow(effect, star) {
  const row = document.createElement('div');
  row.className = 'effect-row';
  const per = effect.perStar || [];
  const raw = per[star];
  const v = document.createElement('span');
  v.className = 'effect-value';
  if (raw == null) { v.textContent = '—'; v.classList.add('is-empty'); v.title = 'この★ではソースに値の記載なし'; }
  else v.textContent = raw;
  const label = document.createElement('span');
  label.className = 'effect-text';
  label.textContent = t(effect.label);
  row.append(v, label);
  // 効果単位の重複可否
  const s = document.createElement('span');
  if (effect.noStack) {
    s.className = 'effect-stack no';
    s.textContent = effect.noStackReason === 'ride' ? '重複不可(騎乗)' : '重複不可';
    s.title = effect.noStackReason === 'ride'
      ? '同時に複数のパルにライドできないため重複不可'
      : 'この効果はソースで重複不可と明記';
  } else {
    s.className = 'effect-stack ok';
    s.textContent = '重複可';
  }
  row.append(s);
  return row;
}

function chipsFromTags(ids, tagIndex, group) {
  const frag = document.createDocumentFragment();
  for (const id of ids || []) {
    const tag = tagIndex.get(id);
    if (tag) frag.appendChild(chip(t(tag.label), group || tag.group, tag.color));
  }
  return frag;
}

function renderCard(skill, tagIndex, star) {
  const card = document.createElement('article');
  card.className = 'card';

  // ヘッダー: No. + 亜種 + Pal 名 + 属性
  const head = document.createElement('div');
  head.className = 'card-head';
  const no = document.createElement('span');
  no.className = 'card-no';
  no.textContent = skill.no;
  head.appendChild(no);
  if (skill.variant) head.appendChild(badge(skill.variant === 'B' ? '亜種' : '亜種' + skill.variant, 'variant'));
  const palName = document.createElement('span');
  palName.className = 'card-pal';
  palName.textContent = t(skill.pal);
  head.appendChild(palName);
  head.appendChild(chipsFromTags(skill.element, tagIndex, 'element'));
  card.appendChild(head);

  const name = document.createElement('h2');
  name.className = 'card-name';
  name.textContent = t(skill.skillName);
  card.appendChild(name);

  // チップ: 発動場面 → カテゴリ → 作業 → 状態
  const chips = document.createElement('div');
  chips.className = 'card-chips';
  const conds = [...(skill.conditions || [])].sort(
    (a, b) => CONDITION_ORDER.indexOf(a) - CONDITION_ORDER.indexOf(b)
  );
  chips.appendChild(chipsFromTags(conds, tagIndex));
  chips.appendChild(chipsFromTags(skill.categories, tagIndex));
  chips.appendChild(chipsFromTags(skill.offenseTypes, tagIndex));
  chips.appendChild(chipsFromTags(skill.works, tagIndex));
  chips.appendChild(chipsFromTags(skill.status, tagIndex));
  card.appendChild(chips);

  // バッジ: 重複可否（スキル全体の要約。効果ごとの詳細は各効果行に表示）
  const badges = document.createElement('div');
  badges.className = 'card-badges';
  if (skill.mixedStack) {
    const b = badge('一部重複不可', 'stack-mixed');
    b.title = '効果によって重複可否が異なる（各効果の表示を参照）';
    badges.appendChild(b);
  } else if (skill.noStack) {
    const b = badge(skill.rideExclusive ? '重複不可(騎乗)' : '重複不可', 'stack-no');
    if (skill.rideExclusive) b.title = '同時に複数のパルにライドできないため重複不可扱い';
    badges.appendChild(b);
  } else {
    badges.appendChild(badge('重複可', 'stack-ok'));
  }
  if (badges.children.length) card.appendChild(badges);

  // 効果（★選択で値が変わる）
  if (skill.effects && skill.effects.length) {
    const effs = document.createElement('div');
    effs.className = 'card-effects';
    for (const eff of skill.effects) effs.appendChild(effectRow(eff, star));
    card.appendChild(effs);
  }

  if (skill.description && t(skill.description)) {
    const desc = document.createElement('p');
    desc.className = 'card-desc';
    desc.textContent = t(skill.description);
    card.appendChild(desc);
  }

  if (skill.palGear) {
    const pg = document.createElement('p');
    pg.className = 'card-palgear';
    pg.textContent = '🛠️ ' + t(skill.palGear);
    card.appendChild(pg);
  }

  return card;
}

function noKey(s) {
  const m = /^No\.(\d+)([AB]?)$/.exec(s.no || '');
  const num = m ? parseInt(m[1], 10) : 9999;
  const suf = m ? { '': 0, A: 1, B: 2 }[m[2]] : 9;
  return num * 10 + suf;
}

export function sortSkills(skills, mode, tagIndex) {
  const arr = [...skills];
  const palKey = (s) => t(s.pal);
  const nameKey = (s) => t(s.skillName);
  const condRank = (s) => {
    const i = Math.min(...(s.conditions || []).map((c) => CONDITION_ORDER.indexOf(c)).filter((x) => x >= 0), 99);
    return i;
  };
  const elemKey = (s) => {
    const e = (s.element || [])[0];
    return e ? t(tagIndex.get(e)?.label || e) : 'んzz';
  };
  const cmp = {
    no: (a, b) => noKey(a) - noKey(b),
    pal: (a, b) => palKey(a).localeCompare(palKey(b), 'ja'),
    name: (a, b) => nameKey(a).localeCompare(nameKey(b), 'ja'),
    element: (a, b) => elemKey(a).localeCompare(elemKey(b), 'ja') || noKey(a) - noKey(b),
    condition: (a, b) => condRank(a) - condRank(b) || noKey(a) - noKey(b),
  }[mode] || ((a, b) => noKey(a) - noKey(b));
  return arr.sort(cmp);
}

export function renderCards(container, skills, tagIndex, star) {
  container.innerHTML = '';
  const frag = document.createDocumentFragment();
  for (const s of skills) frag.appendChild(renderCard(s, tagIndex, star));
  container.appendChild(frag);
}

export function renderActiveFilters(container, sel, tagIndex, onRemove) {
  container.innerHTML = '';
  const ids = Object.values(sel).flat();
  if (!ids.length) { container.hidden = true; return; }
  container.hidden = false;
  for (const id of ids) {
    const tag = tagIndex.get(id);
    if (!tag) continue;
    const el = document.createElement('button');
    el.type = 'button';
    el.className = 'active-filter';
    el.textContent = `${t(tag.label)} ✕`;
    el.addEventListener('click', () => onRemove(id));
    container.appendChild(el);
  }
}

export function updateCounts(root, counts) {
  root.querySelectorAll('[data-count-for]').forEach((el) => {
    const c = counts.get(el.dataset.countFor) ?? 0;
    el.textContent = c;
    el.closest('.filter-option')?.classList.toggle('is-zero', c === 0);
  });
}
