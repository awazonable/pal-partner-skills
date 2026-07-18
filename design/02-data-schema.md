# データスキーマ設計

> **更新（実データ採用後）**：実データ（ユーザー提供HTML→`design/build.py`で生成）採用に伴い、
> 確定スキーマは **`docs/data/schema.md`** を正とする。主な差分：
> - 効果値は `scaling.perLevel`(数値) → **`effects[].perStar`(★0〜★4 の文字列 5 値)**。
> - タグのグループを `condition / category / element / **work** / **status**` に拡張
>   （作業適性・状態異常のファセットを追加）。
> - スキルに `no`(図鑑番号)・`variant`(B亜種)・`palGear` を追加。`alpha`/`verified(false)` は現状未使用
>   （αパル差分は未収録・拡張ポイントとして残置）。
>
> 以下は初版（タグ駆動・レベル配列）の設計思想。基本方針は現行と共通。

データは 2 ファイル構成。**タグ定義（`tags.json`）とスキル本体（`skills.json`）を分離**し、
タグを増減しても UI コードを変えずに済む「データ駆動」にする。

```
docs/data/
├─ tags.json     # タグ（特徴）マスタ：グループ + 個々のタグ
├─ skills.json   # パートナースキル本体
└─ schema.md     # このファイルの要約（実装者向け）
```

## 設計原則

1. **多言語**：表示テキストは `{ "ja": "...", "en": "..." }`。ja を主とし en は任意。
2. **タグ駆動フィルタ**：スキルは `tags: [tagId,...]` を持つだけ。フィルタ UI は
   `tags.json` のグループ定義から自動生成する。
3. **レベル 5 段階**：数値効果は必ず `perLevel`（長さ 5、Lv1〜Lv5）で保持。固定効果は
   同値を 5 個並べる。端点のみ既知なら線形補間し `estimated:true`。
4. **重複可否**：`stackable`(bool) + `stackNote`。
5. **αパル差分**：`alpha` オブジェクトで通常値と別に併記。
6. **データ信頼度**：`verified`(bool) と `sources`。未検証は UI で控えめに表示。

---

## tags.json

```jsonc
{
  "groups": [
    // フィルタ UI の見出し。order 昇順で表示。
    { "id": "condition", "label": { "ja": "発動場面", "en": "Condition" }, "order": 1,
      "hint": { "ja": "いつ・どこで効果が出るか" } },
    { "id": "effect",    "label": { "ja": "効果カテゴリ", "en": "Effect" }, "order": 2 },
    { "id": "detail",    "label": { "ja": "詳細タグ", "en": "Detail" }, "order": 3 },
    { "id": "element",   "label": { "ja": "属性", "en": "Element" }, "order": 4,
      "hint": { "ja": "Pal 自身の属性、または効果対象の属性" } }
  ],
  "tags": [
    { "id": "cond-base",   "group": "condition", "label": { "ja": "拠点配置", "en": "Base" },
      "desc": { "ja": "拠点に配置しているときに効果" }, "color": "#3b7" },
    { "id": "cond-party",  "group": "condition", "label": { "ja": "手持ち(パッシブ)", "en": "Party" },
      "desc": { "ja": "手持ち(パーティ)にいるだけで常時効果" } },
    { "id": "cond-mount",  "group": "condition", "label": { "ja": "騎乗", "en": "Mount" } },
    { "id": "cond-active", "group": "condition", "label": { "ja": "アクティブ発動", "en": "Active" },
      "desc": { "ja": "プレイヤー操作で発動する攻撃・投擲・召喚" } },

    { "id": "eff-offense",    "group": "effect", "label": { "ja": "攻撃", "en": "Offense" } },
    { "id": "eff-defense",    "group": "effect", "label": { "ja": "防御・耐性", "en": "Defense" } },
    { "id": "eff-mobility",   "group": "effect", "label": { "ja": "移動", "en": "Mobility" } },
    { "id": "eff-gathering",  "group": "effect", "label": { "ja": "収集", "en": "Gathering" } },
    { "id": "eff-production", "group": "effect", "label": { "ja": "生産・拠点", "en": "Production" } },
    { "id": "eff-support",    "group": "effect", "label": { "ja": "支援", "en": "Support" } },

    // detail（複数付与前提の細目。UI では「詳細タグ」に一覧）
    { "id": "detail-melee",           "group": "detail", "label": { "ja": "近接", "en": "Melee" } },
    { "id": "detail-ranged",          "group": "detail", "label": { "ja": "遠距離", "en": "Ranged" } },
    { "id": "detail-attack-speed",    "group": "detail", "label": { "ja": "攻撃速度", "en": "Atk Speed" } },
    { "id": "detail-element-attack",  "group": "detail", "label": { "ja": "属性攻撃強化", "en": "Elem Atk" } },
    { "id": "detail-status",          "group": "detail", "label": { "ja": "状態異常付与", "en": "Status" } },
    { "id": "detail-resistance",      "group": "detail", "label": { "ja": "属性耐性", "en": "Resist" } },
    { "id": "detail-fishing",         "group": "detail", "label": { "ja": "釣り", "en": "Fishing" } },
    { "id": "detail-salvage",         "group": "detail", "label": { "ja": "サルベージ", "en": "Salvage" } },
    { "id": "detail-gathering-drop",  "group": "detail", "label": { "ja": "採取ドロップ増", "en": "Loot" } },
    { "id": "detail-capture",         "group": "detail", "label": { "ja": "捕獲補助", "en": "Capture" } },
    { "id": "detail-work-suitability","group": "detail", "label": { "ja": "作業適性", "en": "Work Suit." } },
    { "id": "detail-ranch",           "group": "detail", "label": { "ja": "牧場", "en": "Ranch" } },
    { "id": "detail-carry",           "group": "detail", "label": { "ja": "携行重量", "en": "Carry" } },
    { "id": "detail-mount-ground",    "group": "detail", "label": { "ja": "地上騎乗", "en": "Ground" } },
    { "id": "detail-mount-flying",    "group": "detail", "label": { "ja": "飛行騎乗", "en": "Flying" } },
    { "id": "detail-mount-swim",      "group": "detail", "label": { "ja": "水上騎乗", "en": "Swim" } },
    { "id": "detail-element-synergy", "group": "detail", "label": { "ja": "特定属性パル強化", "en": "Elem Synergy" } },

    // element（Pal 自身 or 効果対象の属性）
    { "id": "elem-fire",     "group": "element", "label": { "ja": "火", "en": "Fire" } },
    { "id": "elem-water",    "group": "element", "label": { "ja": "水", "en": "Water" } },
    { "id": "elem-grass",    "group": "element", "label": { "ja": "草", "en": "Grass" } },
    { "id": "elem-electric", "group": "element", "label": { "ja": "電気", "en": "Electric" } },
    { "id": "elem-ice",      "group": "element", "label": { "ja": "氷", "en": "Ice" } },
    { "id": "elem-ground",   "group": "element", "label": { "ja": "地面", "en": "Ground" } },
    { "id": "elem-dark",     "group": "element", "label": { "ja": "闇", "en": "Dark" } },
    { "id": "elem-dragon",   "group": "element", "label": { "ja": "龍", "en": "Dragon" } },
    { "id": "elem-neutral",  "group": "element", "label": { "ja": "無", "en": "Neutral" } }
  ]
}
```

---

## skills.json

```jsonc
{
  "meta": {
    "gameVersion": "1.0",
    "generatedAt": "2026-07-18",
    "note": "PoC 代表サンプル。全 82 種の網羅・数値確定は要拡充。",
    "totalSkillsInGame": 82
  },
  "skills": [
    {
      "id": "best-boy",                        // 一意 slug
      "skillName": { "ja": "ベストボーイ", "en": "Best Boy" },
      "pal":       { "ja": "パピライ", "en": "Pupperai" },
      "palDexNo": null,                        // 図鑑番号（任意）
      "element":   ["elem-neutral"],           // Pal 自身の属性（tag id で参照）
      "tags": [                                // フィルタ対象。condition/effect/detail/element を混在
        "cond-party", "eff-offense", "detail-melee"
      ],
      "description": {                         // 概要（現行 Lv の値は effects 側で表示）
        "ja": "手持ちにいる間、プレイヤーの近接武器ダメージを増加させる。",
        "en": "While in party, increases the player's melee weapon damage."
      },
      "effects": [                             // 表示用の効果。Lv スライダーで値が変わる
        {
          "text": { "ja": "近接武器ダメージ", "en": "Melee weapon damage" },
          "tags": ["detail-melee"],           // 効果単位のタグ（任意、skill.tags を補足）
          "targetElement": null,              // 属性シナジー時に対象属性 tag id
          "scaling": {
            "kind": "range",                   // "flat" | "range" | "list"
            "unit": "%",                       // 表示単位（"%","+","x","" など）
            "perLevel": [10, 16, 22, 28, 35],  // 長さ 5（Lv1..Lv5）
            "estimated": true                  // 端点以外を補間した場合 true
          }
        }
      ],
      "stackable": false,
      "stackNote": { "ja": "同一スキルは重複しない" },
      "unique": false,                          // その Pal 固有か（複数 Pal が持つスキルは false）
      "sharedWith": [],                         // 同名スキルを持つ他 Pal（任意）
      "alpha": {                                // αパル差分（無ければ hasVariant:false）
        "hasVariant": false
      },
      "verified": true,
      "sources": ["game8:610065"]
    },

    // αパル差分の例（構造のみ。数値は要検証）
    {
      "id": "example-alpha",
      "skillName": { "ja": "（例）", "en": "(example)" },
      "pal": { "ja": "（例）", "en": "(example)" },
      "element": ["elem-dark"],
      "tags": ["cond-active", "eff-offense", "detail-status"],
      "description": { "ja": "攻撃に状態異常を付与する。" },
      "effects": [ /* 通常個体の効果 */ ],
      "stackable": false,
      "unique": true,
      "alpha": {
        "hasVariant": true,
        "note": { "ja": "α個体では効果が変化（バグの可能性）。要検証。" },
        "description": { "ja": "α個体での効果説明" },
        "effects": [ /* α個体の効果（perLevel など通常と同形式） */ ]
      },
      "verified": false,
      "sources": []
    }
  ]
}
```

### `scaling.kind` の使い分け
- `flat`：レベルで変化しない固定効果。`perLevel` は同値 ×5（例：`[1,1,1,1,1]`）。
- `range`：Lv1〜Lv5 が既知レンジ。中間が不明なら線形補間し `estimated:true`。
- `list`：5 段階すべての実測値が判明している場合。`estimated:false`。

### バリデーション観点（実装時）
- `tags` / `element` / `effects[].tags` の各 id は `tags.json` に存在すること。
- `effects[].scaling.perLevel` は長さ 5。
- `alpha.hasVariant:true` なら `alpha.effects` か `alpha.description` を持つこと。
