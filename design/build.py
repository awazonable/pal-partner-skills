#!/usr/bin/env python3
"""パートナースキル一覧HTML → docs/data/{tags,skills}.json 生成スクリプト。

使い方:
    python3 design/build.py <source.html> docs/data/tags.json docs/data/skills.json

- <source.html> は「パルワールド配合・攻略ラボ」のパートナースキル一覧を保存したもの
  （出典サイトのデータのためリポジトリには同梱しない）。
- 属性/作業/状態は本文中のリンク要素(theory-*-link)から抽出。
- 発動場面(conditions)/効果カテゴリ(categories)は説明文からキーワード導出。
- ★0〜★4 の値はソース準拠の文字列で保持（★省略箇所は null）。
"""
import sys,re,json
from html.parser import HTMLParser

ELEM={'無属性':'elem-neutral','闇属性':'elem-dark','雷属性':'elem-electric','炎属性':'elem-fire',
      '水属性':'elem-water','地属性':'elem-ground','氷属性':'elem-ice','草属性':'elem-grass','竜属性':'elem-dragon'}
WORK={'伐採':'work-logging','採集':'work-gathering','採掘':'work-mining','発電':'work-electricity',
      '手作業':'work-handiwork','水やり':'work-watering','牧場':'work-ranch','火おこし':'work-kindling',
      '種まき':'work-planting','運搬':'work-transport','冷却':'work-cooling','製薬':'work-medicine'}
STAT={'氷まみれ':'st-frozen','炎上':'st-burning','泥まみれ':'st-muddy','ずぶ濡れ':'st-wet',
      'ツタまみれ':'st-vined','暗闇':'st-darkness','毒':'st-poison','帯電':'st-electrified'}

# ---- 攻撃カテゴリの補正・細分 ----
def _terrain_only(d):
    # 岩/木/鉱石/建築 を壊す(採掘・移動)だけで戦闘要素が無い＝攻撃ではない
    return bool((re.search(r'(岩|木|鉱石|金属鉱石|建築物?|石建築)',d) and re.search(r'(壊す|破壊|効率|に(対して)?与えるダメージ)',d))
                and not re.search(r'敵|エネミー|プレイヤーの攻撃力|武器の?ダメージ|弱点|状態異常|追撃|属性に変化|付与',d))
def _expl_def(d):  # 爆発する攻撃を受けた際の軽減＝防御
    return bool(re.search(r'爆発する攻撃を受けた',d))
def _enemy_debuff(d):  # 敵の攻撃力を低下＝防御寄りのデバフ
    return bool(re.search(r'敵の攻撃力を(低下|下げ)',d))

def offense_subtypes(d, cond):
    """攻撃スキルを内訳サブカテゴリに分類（複数可）。
    能動/受動はここでは分けない（発動場面 cond-active/party で表現できて冗長なため）。
    パルが直接ダメージを与える系は off-attack に統合。"""
    r=set()
    if re.search(r'攻撃(に|が).{0,10}(付与|状態異常|状態値)',d) or re.search(r'一発で.{0,6}(まみれ|状態)になる',d) \
       or re.search(r'攻撃が.{0,4}(炎上|帯電|氷まみれ|ずぶ濡れ|泥まみれ|ツタまみれ|暗闇|毒)',d):
        r.add('off-status')
    pal_atk = re.search(r'(このパル|戦っているパル|のパル|』[^。]{0,4})の(防御力[とや]?)?攻撃力',d) \
              or ('パルの攻撃力' in d) or re.search(r'』の.{0,4}攻撃力',d)
    if (pal_atk and re.search(r'(増加|上がる|上昇|アップ|多いほど|数だけ|数ほど|スタック|補正)',d)) \
       or re.search(r'パートナースキルのダメージ.{0,6}(上昇|増加)',d):
        r.add('off-pal')
    if re.search(r'(近接武器|遠距離武器|武器|プレイヤー).{0,15}(ダメージ|攻撃力).{0,6}(増加|上がる|上昇|アップ)',d) \
       or re.search(r'弱点',d) or re.search(r'プレイヤーの攻撃が.{0,4}属性に変化',d) or re.search(r'銃弾のダメージ',d) \
       or re.search(r'(状態の敵|非戦闘.{0,4}(敵|エネミー)).{0,14}与えるダメージ.{0,6}(増加|アップ)',d):
        r.add('off-player')
    # パルが直接攻撃（旧 off-active + off-passive を統合）
    if ('cond-active' in cond) \
       or re.search(r'ライド中.{0,30}(連射|発射|照射|砲撃|レーザー|ハンマー|ミサイル|ミニガン|グレネード|振り下ろして攻撃|攻撃できる)',d) \
       or re.search(r'上空から砲撃',d) \
       or re.search(r'追撃',d) or re.search(r'あわせて',d) \
       or (re.search(r'状態の敵に',d) and re.search(r'(ダメージを与える|敵が爆発|敵の周囲に炎|周囲の敵)',d)) \
       or re.search(r'(ローリングやステップ|ローリング).{0,20}(旋風|ダメージ)',d) or re.search(r'矢が着弾.{0,10}爆発',d):
        r.add('off-attack')
    return r

class P(HTMLParser):
    def __init__(self):
        super().__init__(); self.blocks=[]; self.cur=None; self.aclass=None; self.toks=[]
    def handle_starttag(self,tag,attrs):
        if tag=='a':
            cl=dict(attrs).get('class','')
            self.aclass=('el' if 'theory-element-link' in cl else 'wk' if 'theory-work-link' in cl
                         else 'st' if 'theory-status-link' in cl else None)
    def handle_endtag(self,tag):
        if tag=='a': self.aclass=None
    def handle_data(self,d):
        t=d.strip()
        if not t: return
        if re.match(r'^No\.\d+[AB]?$',t):
            self._flush(); self.cur={'no':t}; self.toks=[]; return
        if self.cur is None: return
        if self.aclass=='el' and t in ELEM: self.toks+=[('el',ELEM[t]),('t',t)]
        elif self.aclass=='wk' and t in WORK: self.toks+=[('wk',WORK[t]),('t',t)]
        elif self.aclass=='st' and t in STAT: self.toks+=[('st',STAT[t]),('t',t)]
        else: self.toks.append(('t',t))
    def _flush(self):
        if self.cur is None: return
        toks=self.toks
        texts=[x for k,x in toks if k=='t']
        els=list(dict.fromkeys(x for k,x in toks if k=='el'))
        wks=list(dict.fromkeys(x for k,x in toks if k=='wk'))
        sts=list(dict.fromkeys(x for k,x in toks if k=='st'))
        name_parts=[]; body_start=0
        for i,tx in enumerate(texts):
            if '個別ページへ' in tx: body_start=i+1; break
            name_parts.append(tx)
        pal=name_parts[0] if name_parts else ''
        skill=' '.join(name_parts[1:]) if len(name_parts)>1 else ''
        body=texts[body_start:]
        # 本文と★値行を順序どおりに走査。各★効果へ直前のサブ効果テキスト(ctx)を紐づけ、
        # 効果ごとに重複可否（源の「重複不可」／騎乗）を判定する。
        # ctx はサブ効果境界（①②③…の丸数字）でリセットし、別サブ効果の語が混ざらないようにする。
        effects=[]; desc_lines=[]; palgear=None; ctx=[]
        for b in body:
            if b.startswith('(') and ('解放' in b or 'テクノロジー' in b):
                palgear=b.strip('()'); continue
            if '★' not in b:
                if re.match(r'^[①-⑳]', b): ctx=[b]      # 新しいサブ効果の開始
                else: ctx.append(b)
                desc_lines.append(b); continue
            # ★を含む値行
            vl=re.sub(r'([：:])★\s*(\d[\d.]*\s*%)', r'\1★0：\2', b)  # 「：★30%」(★0：欠落)修復
            segs=re.split(r'★\s*(\d)\s*[:：]\s*',vl)
            label=segs[0].rstrip('：: 、').strip()
            per={}
            for i in range(1,len(segs)-1,2):
                star=int(segs[i]); val=segs[i+1]
                val=re.sub(r'、★.*$','',val)                       # 「、★0.4%」等の末尾ゴミ除去
                val=re.sub(r'[、：:\s]+$','',val).strip()
                if star not in per: per[star]=val
            if not label and effects:
                # ★4 が次行に分割 → 直前の効果へマージ（ctx は据え置き）
                prev=effects[-1]['perStar']
                for k,v in per.items():
                    if prev[k] is None: prev[k]=v
                continue
            perStar=[per.get(i) for i in range(5)]
            context=' '.join(ctx)
            src_ns='重複不可' in context
            ride_ns=bool(re.search(r'乗って|ライド',context))
            effects.append({'label':{'ja':label},'perStar':perStar,
                            'noStack':bool(src_ns or ride_ns),
                            'noStackReason':('source' if src_ns else ('ride' if ride_ns else None))})
            ctx=[]
        # ★0 のみ未記載（上昇量/増加量/軽減量/拡大 系）は「なし」に正規化
        for e in effects:
            p=e['perStar']; lb=e['label']['ja']
            if p[0] is None and all(p[i] is not None for i in range(1,5)) \
               and re.search(r'上昇|増加|軽減|拡大|強化',lb):
                p[0]='なし'
        full=' '.join(desc_lines)
        # derive conditions
        cond=[]
        if '背中に乗って' in full or '乗って移動' in full or 'ライド' in full: cond.append('cond-mount')
        if '発動する' in full: cond.append('cond-active')
        if '手持ちにいる' in full or '手持ちから出している' in full or 'プレイヤーの近くに出現' in full: cond.append('cond-party')
        if '拠点にいる間' in full or 'アサインすると' in full or '拠点外' in full: cond.append('cond-base')
        cond=list(dict.fromkeys(cond))
        # derive categories（説明文＋効果ラベルから）
        efflabels=' '.join(e['label']['ja'] for e in effects)
        cat=[]
        if re.search(r'ダメージが増加|ダメージ増加|与えるダメージ|ダメージを与える|与ダメ|威力|攻撃力|弱点|追撃|爆発|撃ちまく|突っ込む|状態異常|まみれ.*付与|状態値|付与される|状態になる|状態にする|刀となる|居合',full) \
           or re.search(r'威力|ダメージ増加',efflabels): cat.append('cat-offense')
        if re.search(r'防御力|耐性|軽減|無効|盾|バリア|無敵時間',full): cat.append('cat-defense')
        if re.search(r'乗って|グライダー|移動速度|ライド|ジャンプ|滑空|グライド|速度',full): cat.append('cat-mobility')
        if re.search(r'掘り出す|ドロップ|落とす|釣り|サルベージ|獲得量|拾っ|捕獲|収穫|作物',full): cat.append('cat-gathering')
        if re.search(r'作業適性|アサイン|効率|作業速度|収穫|作物',full) or wks: cat.append('cat-production')
        if re.search(r'回復|HP|重量|サポート|スタミナ|満腹|クールタイムが減少',full): cat.append('cat-support')
        if re.search(r'探知|透明|鍵|自動で近くにあるアイテム|位置を|センス|嗅覚|気づかれにくく|拠点へ移動|帰還',full): cat.append('cat-utility')
        cat=list(dict.fromkeys(cat))
        # 攻撃カテゴリの誤検出補正（本来は攻撃でないもの）＋内訳サブカテゴリ
        offtypes=[]
        if 'cat-offense' in cat:
            if _terrain_only(full):
                cat.remove('cat-offense')                       # 破壊効率＝採掘/移動
            elif _expl_def(full) or _enemy_debuff(full):
                cat.remove('cat-offense')                       # 爆発耐性/敵デバフ＝防御寄り
                if 'cat-defense' not in cat: cat.append('cat-defense')
            else:
                offtypes=sorted(offense_subtypes(full, cond))   # 真の攻撃 → 内訳を付与
        if not cat: cat.append('cat-mobility') if 'cond-mount' in cond else None
        no=self.cur['no']; num=re.sub(r'^No\.','',no)
        variant='B' if num.endswith('B') else ('A' if num.endswith('A') else None)
        # 重複可否は効果単位で判定済み。スキル単位は要約（フィルタ/バッジ用）。
        # 騎乗効果に数値行が無い（"乗って移動できる"のみ）場合も騎乗＝重複不可を反映。
        ride_present='cond-mount' in cond
        # 同名パルが多いほど強化＝手持ち効果が本当にスタックする（例：メルパカ）。数値行を持たない場合の補正。
        same_pal_stack=bool(re.search(re.escape(pal)+r'の数(が多いほど|だけ)', full))
        eff_ns=[e['noStack'] for e in effects]
        has_nostack=any(eff_ns) or ride_present or ('重複不可' in full)
        has_stack=any(not x for x in eff_ns) or same_pal_stack
        mixed=has_nostack and has_stack
        # 全効果が「重複不可」で、その理由がすべて騎乗のみ（源に「重複不可」表記なし）か
        ride_only = (not mixed) and has_nostack and ('重複不可' not in full) \
                    and all(e['noStackReason']=='ride' for e in effects if e['noStack'])
        tags=els+wks+sts+cond+cat+offtypes
        rec={'id':'no-'+num.lower(),'no':no,'variant':variant,
             'pal':{'ja':pal},'skillName':{'ja':skill},
             'element':els,'works':wks,'status':sts,'conditions':cond,'categories':cat,
             'offenseTypes':offtypes,
             'tags':list(dict.fromkeys(tags)),
             'description':{'ja':full},'effects':effects,
             'stackable': not has_nostack,'noStack':has_nostack,
             'mixedStack':mixed,'rideExclusive':ride_only,
             'palGear':{'ja':palgear} if palgear else None,
             'verified':True,'source':'palworld-lab'}
        self.blocks.append(rec); self.cur=None
    def close(self): self._flush(); super().close()

raw=open(sys.argv[1],encoding='utf-8',errors='replace').read()
m=re.search(r'<body[^>]*>(.*)</body>',raw,re.S); body=m.group(1) if m else raw
p=P(); p.feed(body); p.close()
skills=p.blocks

# ---- 手動オーバーライド（ソース側で説明文が空/誤記の箇所を補完）----
# 出典検証は design/01-research.md 参照。
OVERRIDES={
  # ミミドッグ「鍵開け」：ソースは説明文が空。palworld-lab/検索で効果を補完。
  'no-144':{'description':{'ja':'手持ちから出している間、ミミドッグの力で鍵を使わずに宝箱を開けられる。開けられる宝箱の種類は濃縮ランク（スキルレベル）で変化する。（クールタイム80秒）'},
            'conditions':['cond-party'],'categories':['cat-utility']},
  # ユキツネ「だっこフロスト」：ソースは説明文が空。基種キツネビ「だっこファイヤー」の氷版として補完。
  'no-029b':{'description':{'ja':'発動すると、プレイヤーに装備され、冷気（氷）放射器と化す。（キツネビ「だっこファイヤー」の氷属性版）'},
             'conditions':['cond-active'],'categories':['cat-offense'],'offenseTypes':['off-attack'],'element':['elem-ice']},
}
# No.025 ラヴィ：ソース誤記「★0.4%」= ★4：0.4%
VALUE_FIX={'no-025':{'回復量':{4:'0.4%'}}}

for s in skills:
    ov=OVERRIDES.get(s['id'])
    if ov:
        for k,v in ov.items(): s[k]=v
    vf=VALUE_FIX.get(s['id'])
    if vf:
        for e in s['effects']:
            fix=vf.get(e['label']['ja'])
            if fix:
                for idx,val in fix.items(): e['perStar'][idx]=val
    # tags 統合を再計算（オーバーライド反映）
    s['tags']=list(dict.fromkeys(s['element']+s['works']+s['status']+s['conditions']+s['categories']+s.get('offenseTypes',[])))

# ---- tags.json ----
def L(ja,en): return {'ja':ja,'en':en}
groups=[
 {'id':'condition','label':L('発動場面','Condition'),'order':1,'hint':L('いつ・どこで効果が出るか','')},
 {'id':'category','label':L('効果カテゴリ','Effect'),'order':2},
 {'id':'element','label':L('関連属性','Element'),'order':3,'hint':L('効果に関わる属性（対象属性など）。パル自身の属性ではない','')},
 {'id':'work','label':L('作業適性','Work'),'order':4},
 {'id':'status','label':L('状態異常','Status'),'order':5},
]
# cat-offense は「攻撃」の親ヘッダ。子(off-*)を持ち、フィルタ上は子の集合として扱う。
tags=[
 {'id':'cond-base','group':'condition','label':L('拠点配置','Base')},
 {'id':'cond-party','group':'condition','label':L('手持ち(パッシブ)','Party')},
 {'id':'cond-mount','group':'condition','label':L('騎乗/ライド','Mount')},
 {'id':'cond-active','group':'condition','label':L('アクティブ発動','Active')},
 {'id':'cat-offense','group':'category','label':L('攻撃','Offense'),
  'children':['off-player','off-pal','off-attack','off-status']},
 {'id':'off-player','group':'category','parent':'cat-offense','label':L('プレイヤー攻撃強化','Player buff')},
 {'id':'off-pal','group':'category','parent':'cat-offense','label':L('パル攻撃強化','Pal buff')},
 {'id':'off-attack','group':'category','parent':'cat-offense','label':L('パルが直接攻撃','Pal attack')},
 {'id':'off-status','group':'category','parent':'cat-offense','label':L('状態異常付与','Status infliction')},
 {'id':'cat-defense','group':'category','label':L('防御・耐性','Defense')},
 {'id':'cat-mobility','group':'category','label':L('移動','Mobility')},
 {'id':'cat-gathering','group':'category','label':L('収集','Gathering')},
 {'id':'cat-production','group':'category','label':L('生産・拠点','Production')},
 {'id':'cat-support','group':'category','label':L('支援・回復','Support')},
 {'id':'cat-utility','group':'category','label':L('探索・便利','Utility')},
]
ELEMLABEL={'elem-neutral':('無','#9aa0a6'),'elem-dark':('闇','#8659c4'),'elem-electric':('雷','#e8c53a'),
 'elem-fire':('炎','#e8613c'),'elem-water':('水','#3aa6e8'),'elem-ground':('地','#b08050'),
 'elem-ice':('氷','#6fd6d6'),'elem-grass':('草','#4caf50'),'elem-dragon':('竜','#7a63d6')}
for eid,(lab,col) in ELEMLABEL.items():
    tags.append({'id':eid,'group':'element','label':{'ja':lab+'属性','en':eid.split('-')[1]},'color':col})
for ja,wid in WORK.items():
    tags.append({'id':wid,'group':'work','label':{'ja':ja,'en':wid.split('-')[1]}})
for ja,sid in STAT.items():
    tags.append({'id':sid,'group':'status','label':{'ja':ja,'en':sid.split('-')[1]}})

tagsdoc={'groups':groups,'tags':tags}
skillsdoc={'meta':{'gameVersion':'1.0','generatedAt':'2026-07-18','totalSkills':len(skills),
  'source':'パルワールド配合・攻略ラボ（ユーザー提供のHTMLを構造化）',
  'note':'★0〜★4 は濃縮ランク=パートナースキルの5段階レベル。値はソース準拠（一部ソース側の表記ゆれ/★0省略あり→ — 表示）。騎乗(cond-mount)は同時に複数ライドできないため重複不可扱い（rideExclusive）。ただし同名パルの数でスタックする効果（例:メルパカ）は重複可のまま。αパル個体差分は本ソースに明示が無いため未収録。'},
  'skills':skills}
json.dump(tagsdoc,open(sys.argv[2],'w',encoding='utf-8'),ensure_ascii=False,indent=2)
json.dump(skillsdoc,open(sys.argv[3],'w',encoding='utf-8'),ensure_ascii=False,indent=1)
# stats
print("skills",len(skills),"tags",len(tags))
from collections import Counter
cc=Counter(); 
for s in skills:
    for c in s['conditions']: cc[c]+=1
print("conditions:",dict(cc))
noneval=sum(1 for s in skills for e in s['effects'] if any(v is None for v in e['perStar']))
print("effects with a None star:",noneval)
print("no-condition skills:",sum(1 for s in skills if not s['conditions']))
