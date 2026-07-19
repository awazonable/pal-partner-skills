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
    - `categories[]` … `cat-offense|defense|mobility|gathering|production|support|utility`（導出）
    - `offenseTypes[]` … 攻撃(`cat-offense`)の内訳サブカテゴリ（導出）：
      `off-player`(プレイヤー攻撃強化) / `off-pal`(パル攻撃強化) / `off-attack`(パルが直接攻撃) /
      `off-status`(状態異常付与)。攻撃以外は空。
      能動/受動は分けない（発動場面 `cond-active`/`cond-party` で表現でき冗長なため統合）。
      tags.json 上では `cat-offense` が親（`children`）、`off-*` が子（`parent:"cat-offense"`）で
      いずれも `group:"category"`。UI は攻撃を親、子を階層チェックボックスで表示する。
    - `tags[]` … 上記の統合（フィルタ用。冗長だが検索を単純化）
  - `description{ja}`
  - `effects[]`: `{ label{ja}, perStar:[5], noStack, noStackReason }`
    - **`perStar` は ★0〜★4 の 5 値**。値は**ソース準拠の文字列**（`"+15%"`, `"250"`, `"特大"`, `"11分40秒"` 等）。
    - ソース側で ★0 が省略/欠落している箇所は `null`（UI では `—` 表示）。
    - **`noStack`（bool）／`noStackReason`（`"source"|"ride"|null`）＝効果ごとの重複可否**。
      判定は「直前のサブ効果テキストに『重複不可』があるか（source）」「騎乗/ライド効果か（ride）」。
      サブ効果境界（①②③…）で文脈をリセットして混線を防ぐ。
  - `stackable`, `noStack`, `mixedStack`, `rideExclusive`（すべて bool。効果単位の要約）
    - `noStack` = いずれかの効果が重複不可、または騎乗スキル、または本文に「重複不可」。
    - `mixedStack` = 重複可の効果と重複不可の効果が混在（例：メルパカ＝騎乗不可＋同名スタックのバフ）。
      UI ではバッジ「一部重複不可」。効果ごとの可否は各効果行に表示する。
    - `rideExclusive` = 重複不可の理由がすべて騎乗のみ（源に「重複不可」表記なし）。バッジ「重複不可(騎乗)」。
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
