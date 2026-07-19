// フィルタ UI の生成と絞り込みロジック（データ駆動・3状態・階層・「(なし)」対応）
import { t } from './i18n.js';

// 「(なし)」オプションを出すグループ（任意ファセット）
const NONE_GROUPS = ['element', 'work', 'status'];
export const NONE_PREFIX = 'none:';

export function buildTagIndex(tagsData) {
  const idx = new Map();
  for (const tag of tagsData.tags) idx.set(tag.id, tag);
  return idx;
}

// グループ内の「葉」タグ id（ヘッダ＝children を持つタグは除外）
function leafIds(tagsData, groupId) {
  return tagsData.tags.filter((x) => x.group === groupId && !x.children).map((x) => x.id);
}

// skill がそのグループで持つ葉タグ集合
function skillGroupTags(skill, leaves) {
  const set = new Set();
  for (const id of skill.tags || []) if (leaves.has(id)) set.add(id);
  return set;
}

// ---- UI 生成 ----
export function renderFilterGroups(tagsData, container, onChange) {
  container.innerHTML = '';
  const groups = [...tagsData.groups].sort((a, b) => a.order - b.order);

  // 3状態オプション行を作る
  function makeOption(tag, isChild) {
    const row = document.createElement('div');
    row.className = 'filter-option' + (isChild ? ' is-child' : '');
    row.dataset.tagId = tag.id;
    row.dataset.group = tag.group;
    row.dataset.state = '';
    row.tabIndex = 0;
    row.setAttribute('role', 'button');

    const box = document.createElement('span');
    box.className = 'tri-box';
    const label = document.createElement('span');
    label.className = 'filter-option-label';
    if (tag.color) {
      const dot = document.createElement('span');
      dot.className = 'tag-dot';
      dot.style.background = tag.color;
      label.appendChild(dot);
    }
    label.appendChild(document.createTextNode(t(tag.label)));
    const count = document.createElement('span');
    count.className = 'filter-count';
    count.dataset.countFor = tag.id;

    row.append(box, label, count);
    const cycle = () => {
      row.dataset.state = { '': 'inc', inc: 'exc', exc: '' }[row.dataset.state];
      onChange();
    };
    row.addEventListener('click', cycle);
    row.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); cycle(); }
    });
    return row;
  }

  for (const group of groups) {
    const section = document.createElement('section');
    section.className = 'filter-group';
    section.dataset.group = group.id;

    const title = document.createElement('h3');
    title.className = 'filter-group-title';
    title.textContent = t(group.label);
    if (group.hint) {
      const hint = document.createElement('span');
      hint.className = 'filter-group-hint';
      hint.textContent = t(group.hint);
      title.appendChild(hint);
    }
    section.appendChild(title);

    const opts = document.createElement('div');
    opts.className = 'filter-options';

    for (const tag of tagsData.tags.filter((x) => x.group === group.id)) {
      if (tag.parent) continue; // 子は親の下で描画
      if (tag.children) {
        // 親ヘッダ（全選択/全解除）＋子
        const header = document.createElement('div');
        header.className = 'filter-parent';
        const box = document.createElement('span');
        box.className = 'tri-box parent-box';
        const lab = document.createElement('span');
        lab.className = 'filter-option-label parent-label';
        lab.textContent = t(tag.label);
        const count = document.createElement('span');
        count.className = 'filter-count';
        count.dataset.countFor = tag.id;
        header.append(box, lab, count);
        header.tabIndex = 0;
        header.setAttribute('role', 'button');
        header.title = '子カテゴリを全選択 / 全解除';
        opts.appendChild(header);

        const kids = document.createElement('div');
        kids.className = 'filter-children';
        const childRows = [];
        for (const cid of tag.children) {
          const ctag = tagsData.tags.find((x) => x.id === cid);
          if (ctag) { const r = makeOption(ctag, true); kids.appendChild(r); childRows.push(r); }
        }
        opts.appendChild(kids);

        const toggleAll = () => {
          const allInc = childRows.every((r) => r.dataset.state === 'inc');
          childRows.forEach((r) => (r.dataset.state = allInc ? '' : 'inc'));
          onChange();
        };
        header.addEventListener('click', toggleAll);
        header.addEventListener('keydown', (e) => {
          if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleAll(); }
        });
        header._childRows = childRows;
        header._box = box;
      } else {
        opts.appendChild(makeOption(tag, false));
      }
    }

    // 「(なし)」オプション
    if (NONE_GROUPS.includes(group.id)) {
      const noneTag = { id: NONE_PREFIX + group.id, group: group.id, label: { ja: '（なし）' } };
      const r = makeOption(noneTag, false);
      r.classList.add('is-none');
      opts.appendChild(r);
    }

    section.appendChild(opts);
    container.appendChild(section);
  }
}

// 親ヘッダの表示状態（全選択/一部/なし）を同期
export function syncParents(container) {
  container.querySelectorAll('.filter-parent').forEach((h) => {
    const rows = h._childRows || [];
    const inc = rows.filter((r) => r.dataset.state === 'inc').length;
    const any = rows.filter((r) => r.dataset.state !== '').length;
    h.dataset.state = inc === rows.length && rows.length ? 'all' : (any ? 'some' : 'none');
  });
}

// 選択状態を { group: { inc:Set, exc:Set } } で取得
export function collectSelected(container) {
  const sel = {};
  container.querySelectorAll('.filter-option').forEach((row) => {
    const st = row.dataset.state;
    if (!st) return;
    const g = row.dataset.group;
    (sel[g] ||= { inc: new Set(), exc: new Set() });
    (st === 'inc' ? sel[g].inc : sel[g].exc).add(row.dataset.tagId);
  });
  return sel;
}

// 1グループ分の合否（include=OR / exclude=NOT / 「(なし)」対応）
function groupPass(groupTags, crit, groupId) {
  const noneId = NONE_PREFIX + groupId;
  const hasNone = groupTags.size === 0;
  const test = (id) => (id === noneId ? hasNone : groupTags.has(id));
  if (crit.inc.size) {
    let ok = false;
    for (const id of crit.inc) if (test(id)) { ok = true; break; }
    if (!ok) return false;
  }
  for (const id of crit.exc) if (test(id)) return false;
  return true;
}

// スキルが条件に一致するか。excludeGroup 指定でそのグループを無視（件数計算用）
export function skillMatches(skill, sel, text, flags, tagsData, leavesByGroup, excludeGroup = null) {
  if (text) {
    const hay = [
      t(skill.skillName), skill.skillName?.en, t(skill.pal), skill.pal?.en,
      t(skill.description), skill.description?.en, skill.no,
    ].join(' ').toLowerCase();
    if (!hay.includes(text.toLowerCase())) return false;
  }
  if (flags.noStack && skill.noStack !== true) return false;
  if (flags.variant && !skill.variant) return false;
  if (flags.palGear && !skill.palGear) return false;

  for (const [groupId, crit] of Object.entries(sel)) {
    if (groupId === excludeGroup) continue;
    const leaves = leavesByGroup.get(groupId);
    if (!leaves) continue;
    if (!groupPass(skillGroupTags(skill, leaves), crit, groupId)) return false;
  }
  return true;
}

export function buildLeavesByGroup(tagsData) {
  const m = new Map();
  for (const g of tagsData.groups) m.set(g.id, new Set(leafIds(tagsData, g.id)));
  return m;
}

// 各オプションの件数（同一グループの選択は無視して「その条件を足したら何件か」）
export function computeCounts(skills, tagsData, sel, text, flags, leavesByGroup) {
  const counts = new Map();
  const perGroupBase = new Map(); // group -> [skills passing other groups]
  for (const g of tagsData.groups) {
    perGroupBase.set(g.id, skills.filter((s) => skillMatches(s, sel, text, flags, tagsData, leavesByGroup, g.id)));
  }
  for (const tag of tagsData.tags) {
    const base = perGroupBase.get(tag.group) || [];
    if (tag.children) {
      // 親：子のいずれかを持つ数（＝そのカテゴリ全体）
      const kids = new Set(tag.children);
      counts.set(tag.id, base.filter((s) => (s.tags || []).some((x) => kids.has(x))).length);
    } else {
      counts.set(tag.id, base.filter((s) => (s.tags || []).includes(tag.id)).length);
    }
  }
  // 「(なし)」件数
  for (const gid of NONE_GROUPS) {
    const leaves = leavesByGroup.get(gid);
    const base = perGroupBase.get(gid) || [];
    counts.set(NONE_PREFIX + gid, base.filter((s) => skillGroupTags(s, leaves).size === 0).length);
  }
  return counts;
}
