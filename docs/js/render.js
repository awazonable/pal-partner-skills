// カード描画・件数表示・選択中フィルタの表示
import { t } from './i18n.js';

const CONDITION_ORDER = ['cond-base', 'cond-party', 'cond-mount', 'cond-active'];

// scaling を現在レベルの表示文字列にする
function formatValue(scaling, level) {
  if (!scaling || !Array.isArray(scaling.perLevel)) return null;
  const v = scaling.perLevel[level - 1];
  if (v == null) return null;
  const unit = scaling.unit || '';
  let s;
  if (unit === '%') s = `${v}%`;
  else if (unit === '+') s = `+${v}`;
  else if (unit === 'Lv+') s = `Lv +${v}`;
  else if (unit === 'x') s = `×${v}`;
  else s = `${v}${unit}`;
  return { text: s, estimated: !!scaling.estimated, flat: scaling.kind === 'flat' };
}

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

function effectRow(effect, level, tagIndex) {
  const row = document.createElement('div');
  row.className = 'effect-row';

  const val = formatValue(effect.scaling, level);
  if (val) {
    const v = document.createElement('span');
    v.className = 'effect-value';
    v.textContent = val.text;
    if (val.estimated) v.title = '中間レベルを補間した推定値';
    row.appendChild(v);
  }

  const label = document.createElement('span');
  label.className = 'effect-text';
  label.textContent = t(effect.text);
  row.appendChild(label);

  if (effect.targetElement && tagIndex.has(effect.targetElement)) {
    const et = tagIndex.get(effect.targetElement);
    row.appendChild(chip(t(et.label), et.group, et.color));
  }
  if (val && val.estimated) {
    const note = document.createElement('span');
    note.className = 'effect-note';
    note.textContent = '※推定';
    row.appendChild(note);
  }
  if (val && val.flat) {
    const note = document.createElement('span');
    note.className = 'effect-note flat';
    note.textContent = 'Lv非依存';
    row.appendChild(note);
  }
  return row;
}

function renderCard(skill, tagIndex, level) {
  const card = document.createElement('article');
  card.className = 'card';
  if (skill.verified === false) card.classList.add('is-unverified');

  // ヘッダー: Pal 名 + 属性チップ
  const head = document.createElement('div');
  head.className = 'card-head';
  const palName = document.createElement('span');
  palName.className = 'card-pal';
  palName.textContent = t(skill.pal);
  head.appendChild(palName);
  for (const eid of skill.element || []) {
    const et = tagIndex.get(eid);
    if (et) head.appendChild(chip(t(et.label), 'element', et.color));
  }
  card.appendChild(head);

  const name = document.createElement('h2');
  name.className = 'card-name';
  name.textContent = t(skill.skillName);
  card.appendChild(name);

  // チップ行: condition/effect/detail タグ（属性は上で表示済み）+ バッジ
  const chips = document.createElement('div');
  chips.className = 'card-chips';
  const nonElementTags = (skill.tags || []).filter((id) => {
    const tag = tagIndex.get(id);
    return tag && tag.group !== 'element';
  });
  // condition を先頭に、続けて effect/detail
  nonElementTags.sort((a, b) => {
    const ga = tagIndex.get(a).group, gb = tagIndex.get(b).group;
    const rank = (g) => (g === 'condition' ? 0 : g === 'effect' ? 1 : 2);
    return rank(ga) - rank(gb);
  });
  for (const id of nonElementTags) {
    const tag = tagIndex.get(id);
    chips.appendChild(chip(t(tag.label), tag.group));
  }
  card.appendChild(chips);

  const badges = document.createElement('div');
  badges.className = 'card-badges';
  badges.appendChild(
    skill.stackable
      ? badge('重複可', 'stack-ok')
      : badge('重複不可', 'stack-no')
  );
  if (skill.unique) badges.appendChild(badge('ユニーク', 'unique'));
  if (skill.alpha && skill.alpha.hasVariant) badges.appendChild(badge('α差分あり', 'alpha'));
  if (skill.verified === false) badges.appendChild(badge('要検証', 'unverified'));
  card.appendChild(badges);

  // 効果
  if (skill.effects && skill.effects.length) {
    const effs = document.createElement('div');
    effs.className = 'card-effects';
    for (const eff of skill.effects) effs.appendChild(effectRow(eff, level, tagIndex));
    card.appendChild(effs);
  }

  const desc = document.createElement('p');
  desc.className = 'card-desc';
  desc.textContent = t(skill.description);
  card.appendChild(desc);

  if (skill.stackNote) {
    const sn = document.createElement('p');
    sn.className = 'card-stacknote';
    sn.textContent = '重複: ' + t(skill.stackNote);
    card.appendChild(sn);
  }

  // αパル差分（併記）
  if (skill.alpha && skill.alpha.hasVariant) {
    const details = document.createElement('details');
    details.className = 'alpha-block';
    const summary = document.createElement('summary');
    summary.textContent = 'α個体での効果を表示';
    details.appendChild(summary);
    if (skill.alpha.note) {
      const n = document.createElement('p');
      n.className = 'alpha-note';
      n.textContent = t(skill.alpha.note);
      details.appendChild(n);
    }
    if (skill.alpha.description) {
      const d = document.createElement('p');
      d.className = 'alpha-desc';
      d.textContent = t(skill.alpha.description);
      details.appendChild(d);
    }
    for (const eff of skill.alpha.effects || []) {
      details.appendChild(effectRow(eff, level, tagIndex));
    }
    card.appendChild(details);
  }

  return card;
}

export function sortSkills(skills, mode, tagIndex) {
  const arr = [...skills];
  const palKey = (s) => t(s.pal);
  const nameKey = (s) => t(s.skillName);
  const condRank = (s) => {
    const c = (s.tags || []).find((id) => CONDITION_ORDER.includes(id));
    const i = CONDITION_ORDER.indexOf(c);
    return i < 0 ? 99 : i;
  };
  const elemKey = (s) => {
    const e = (s.element || [])[0];
    return e ? t(tagIndex.get(e)?.label || e) : 'zzz';
  };
  const cmp = {
    pal: (a, b) => palKey(a).localeCompare(palKey(b), 'ja'),
    name: (a, b) => nameKey(a).localeCompare(nameKey(b), 'ja'),
    element: (a, b) => elemKey(a).localeCompare(elemKey(b), 'ja') || palKey(a).localeCompare(palKey(b), 'ja'),
    condition: (a, b) => condRank(a) - condRank(b) || palKey(a).localeCompare(palKey(b), 'ja'),
  }[mode] || (() => 0);
  return arr.sort(cmp);
}

export function renderCards(container, skills, tagIndex, level) {
  container.innerHTML = '';
  const frag = document.createDocumentFragment();
  for (const s of skills) frag.appendChild(renderCard(s, tagIndex, level));
  container.appendChild(frag);
}

// 選択中フィルタをチップで表示（クリックで解除）
export function renderActiveFilters(container, sel, tagIndex, onRemove) {
  container.innerHTML = '';
  const ids = Object.values(sel).flat();
  if (!ids.length) {
    container.hidden = true;
    return;
  }
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
