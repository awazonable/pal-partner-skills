// フィルタ UI の生成と絞り込みロジック（データ駆動）
import { t } from './i18n.js';

// id -> tag の索引
export function buildTagIndex(tagsData) {
  const idx = new Map();
  for (const tag of tagsData.tags) idx.set(tag.id, tag);
  return idx;
}

// グループ順に並べた [group, tags[]] のリスト
export function tagsByGroup(tagsData) {
  const groups = [...tagsData.groups].sort((a, b) => a.order - b.order);
  return groups.map((g) => [g, tagsData.tags.filter((tag) => tag.group === g.id)]);
}

// skill が持つ全タグ（tags + element を統合）
function skillTagSet(skill) {
  return new Set([...(skill.tags || []), ...(skill.element || [])]);
}

// #filterGroups にグループごとのチェックボックス群を描画
export function renderFilterGroups(tagsData, container, onChange) {
  container.innerHTML = '';
  for (const [group, tags] of tagsByGroup(tagsData)) {
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
    for (const tag of tags) {
      const label = document.createElement('label');
      label.className = 'filter-option';
      label.dataset.tagId = tag.id;

      const input = document.createElement('input');
      input.type = 'checkbox';
      input.value = tag.id;
      input.dataset.group = group.id;
      input.addEventListener('change', onChange);

      const text = document.createElement('span');
      text.className = 'filter-option-label';
      if (tag.color) {
        const dot = document.createElement('span');
        dot.className = 'tag-dot';
        dot.style.background = tag.color;
        text.appendChild(dot);
      }
      text.appendChild(document.createTextNode(t(tag.label)));

      const count = document.createElement('span');
      count.className = 'filter-count';
      count.dataset.countFor = tag.id;

      label.append(input, text, count);
      opts.appendChild(label);
    }
    section.appendChild(opts);
    container.appendChild(section);
  }
}

// 選択中タグを { groupId: [tagId,...] } で取得
export function collectSelectedTags(container) {
  const sel = {};
  container.querySelectorAll('input[type=checkbox]:checked').forEach((cb) => {
    (sel[cb.dataset.group] ||= []).push(cb.value);
  });
  return sel;
}

// 1 スキルが条件に一致するか。excludeGroup 指定時はそのグループ条件を無視（件数計算用）
export function skillMatches(skill, sel, text, flags, excludeGroup = null) {
  if (text) {
    const hay = [
      t(skill.skillName), skill.skillName?.en,
      t(skill.pal), skill.pal?.en,
      t(skill.description), skill.description?.en,
    ].join(' ').toLowerCase();
    if (!hay.includes(text.toLowerCase())) return false;
  }
  if (flags.stackable && skill.stackable !== true) return false;
  if (flags.unique && skill.unique !== true) return false;
  if (flags.alpha && !(skill.alpha && skill.alpha.hasVariant)) return false;
  if (flags.verified && skill.verified !== true) return false;

  const st = skillTagSet(skill);
  for (const [groupId, ids] of Object.entries(sel)) {
    if (groupId === excludeGroup || ids.length === 0) continue;
    // グループ内は OR、グループ間は AND
    if (!ids.some((id) => st.has(id))) return false;
  }
  return true;
}

// 各タグの該当件数（同一グループの選択は無視して「追加したら何件か」を出す）
export function computeCounts(skills, tagsData, sel, text, flags) {
  const counts = new Map();
  for (const tag of tagsData.tags) {
    let c = 0;
    for (const s of skills) {
      if (skillMatches(s, sel, text, flags, tag.group) && skillTagSet(s).has(tag.id)) c++;
    }
    counts.set(tag.id, c);
  }
  return counts;
}
