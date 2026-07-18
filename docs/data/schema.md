# データスキーマ（実装者向け要約）

詳細は `design/02-data-schema.md` を参照。ここは編集時のクイックリファレンス。

## tags.json
- `groups[]`: `{ id, label{ja,en}, order, hint? }` — フィルタ UI の見出し。
- `tags[]`: `{ id, group, label{ja,en}, desc?{ja,en}, color? }` — 個々のタグ。
  - `group` は `groups[].id` のいずれか（condition / effect / detail / element）。

## skills.json
- `meta`: `{ gameVersion, generatedAt, totalSkillsInGame, note }`
- `skills[]`:
  - `id` (一意 slug), `skillName{ja,en}`, `pal{ja,en}`, `palDexNo?`
  - `element[]`: 属性 tag id（`elem-*`）
  - `tags[]`: フィルタ対象の tag id（condition/effect/detail/element を混在可）
  - `description{ja,en}`
  - `effects[]`: `{ text{ja,en}, tags?[], targetElement?, scaling? }`
    - `scaling`: `{ kind: "flat"|"range"|"list", unit, perLevel:[5], estimated }`
    - `scaling` 省略時は数値なしのテキスト効果（騎乗・召喚など質的効果）
  - `stackable` (bool), `stackNote?{ja}`
  - `unique` (bool), `sharedWith?[]`
  - `alpha`: `{ hasVariant:bool, note?, description?, effects?[] }`
  - `verified` (bool), `sources[]`

## 追加時のルール
- 使用する tag id / element id / targetElement は必ず `tags.json` に存在させる。
- `scaling.perLevel` は Lv1..Lv5 の長さ 5。固定効果は同値 ×5。
- 端点のみ既知で中間を補間したら `estimated:true`。
- 未確定（パル対応・数値）は `verified:false`。
- 検証は `python3 docs/data/validate.py`（または design 手順）で参照整合性を確認。
