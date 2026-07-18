# データスキーマ（実装者向け要約）

`tags.json` と `skills.json` は **`design/build.py`（ソースHTML→構造化）で生成**する。
手修正する場合は下記の形を守り、`python3 docs/data/validate.py` で参照整合性を確認する。

## tags.json
- `groups[]`: `{ id, label{ja,en}, order, hint? }` — フィルタ UI の見出し。
- `tags[]`: `{ id, group, label{ja,en}, color? }`
  - `group` は groups の id：`condition` / `category` / `element` / `work` / `status`。

## skills.json
- `meta`: `{ gameVersion:"1.0", generatedAt, totalSkills, source, note }`
- `skills[]`（1件＝1パルのパートナースキル。亜種も別エントリ）:
  - `id`（例 `no-005b`）, `no`（例 `No.005B`）, `variant`（`null`|`"A"`|`"B"` 亜種）
  - `pal{ja}`, `skillName{ja}`
  - ファセット（すべて tag id）:
    - `element[]` … `elem-*`（無/闇/雷/炎/水/地/氷/草/竜）
    - `works[]` … `work-*`（伐採/採集/採掘/…）
    - `status[]` … `st-*`（炎上/帯電/…）
    - `conditions[]` … `cond-base|party|mount|active`（説明文から導出）
    - `categories[]` … `cat-offense|defense|mobility|gathering|production|support`（導出）
    - `tags[]` … 上記の統合（フィルタ用。冗長だが検索を単純化）
  - `description{ja}`
  - `effects[]`: `{ label{ja}, perStar:[5] }`
    - **`perStar` は ★0〜★4 の 5 値**。値は**ソース準拠の文字列**（`"+15%"`, `"250"`, `"特大"`, `"11分40秒"` 等）。
    - ソース側で ★0 が省略/欠落している箇所は `null`（UI では `—` 表示）。
  - `stackable`（bool＝`!noStack`）, `noStack`（bool）, `rideExclusive`（bool）
    - `noStack` = 説明文に「重複不可」 **または** 騎乗(`cond-mount`)スキル
      （同時に複数ライドできないため）。ただし**同名パルの数でスタックする**効果
      （例：メルパカ）は除外し `stackable` のまま。
    - `rideExclusive` = 騎乗由来で重複不可になった（ソースには「重複不可」表記が無い）場合 true。
      UI ではバッジを「重複不可(騎乗)」と表示。
  - `palGear{ja}`|null（パルギア解放条件のメモ）
  - `verified`（bool）, `source`（string）

## 追加・修正時のルール
- 使う tag id はすべて `tags.json` に存在させる。
- `effects[].perStar` は必ず長さ 5（★0〜★4）。不明な★は `null`。
- タグ体系（属性9・作業12・状態8）は `design/build.py` の辞書と一致させる。
- 変更後は `python3 docs/data/validate.py`（errors=0 を確認。warnings は★欠落や条件未導出で非致命）。

## 注意
- **αパル個体差分**（同一パルをα個体で捕獲すると効果が変わるバグ）は現ソースに明示が無く未収録。
  必要になったら `alpha{ hasVariant, note, effects[] }` を各スキルに追加し、UI 側で併記表示を足す
  （旧 PoC スキーマに実装例あり／`design/` 参照）。
