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
        desc_lines=[]; val_lines=[]; palgear=None
        for b in body:
            if '★' in b: val_lines.append(b)
            elif b.startswith('(') and ('解放' in b or 'テクノロジー' in b): palgear=b.strip('()')
            else: desc_lines.append(b)
        effects=[]
        for vl in val_lines:
            # ソース誤記の修復：「ラベル：★30%」(★0：欠落) → 「ラベル：★0：30%」
            vl=re.sub(r'([：:])★\s*(\d[\d.]*\s*%)', r'\1★0：\2', vl)
            segs=re.split(r'★\s*(\d)\s*[:：]\s*',vl)
            label=segs[0].rstrip('：: 、').strip()
            per={}
            for i in range(1,len(segs)-1,2):
                star=int(segs[i]); val=segs[i+1]
                val=re.sub(r'、★.*$','',val)          # 誤記「、★0.4%」等の末尾ゴミ除去
                val=re.sub(r'[、：:\s]+$','',val).strip()
                if star not in per: per[star]=val
            if not label and effects:
                # ★4 が次行に分割されているケース → 直前の効果へマージ
                prev=effects[-1]['perStar']
                for k,v in per.items():
                    if prev[k] is None: prev[k]=v
                continue
            perStar=[per.get(i) for i in range(5)]
            effects.append({'label':{'ja':label},'perStar':perStar})
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
        no=self.cur['no']; num=re.sub(r'^No\.','',no)
        variant='B' if num.endswith('B') else ('A' if num.endswith('A') else None)
        # 重複可否の判定
        source_nostack = '重複不可' in full
        # 同名パルが多いほど強化される＝手持ち効果が本当にスタックする（例：メルパカ）
        same_pal_stack = bool(re.search(re.escape(pal)+r'の数(が多いほど|だけ)', full))
        # 騎乗効果は同時に複数ライドできないため本質的に重複不可（同名スタック型は除く）
        ride_nostack = ('cond-mount' in cond) and not same_pal_stack
        noStack = source_nostack or ride_nostack
        ride_exclusive = ride_nostack and not source_nostack
        tags=els+wks+sts+cond+cat
        rec={'id':'no-'+num.lower(),'no':no,'variant':variant,
             'pal':{'ja':pal},'skillName':{'ja':skill},
             'element':els,'works':wks,'status':sts,'conditions':cond,'categories':cat,
             'tags':list(dict.fromkeys(tags)),
             'description':{'ja':full},'effects':effects,
             'stackable': not noStack,'noStack':noStack,'rideExclusive':ride_exclusive,
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
             'conditions':['cond-active'],'categories':['cat-offense'],'element':['elem-ice']},
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
    s['tags']=list(dict.fromkeys(s['element']+s['works']+s['status']+s['conditions']+s['categories']))

# ---- tags.json ----
def L(ja,en): return {'ja':ja,'en':en}
groups=[
 {'id':'condition','label':L('発動場面','Condition'),'order':1,'hint':L('いつ・どこで効果が出るか','')},
 {'id':'category','label':L('効果カテゴリ','Effect'),'order':2},
 {'id':'element','label':L('関連属性','Element'),'order':3,'hint':L('効果に関わる属性（対象属性など）。パル自身の属性ではない','')},
 {'id':'work','label':L('作業適性','Work'),'order':4},
 {'id':'status','label':L('状態異常','Status'),'order':5},
]
tags=[
 {'id':'cond-base','group':'condition','label':L('拠点配置','Base')},
 {'id':'cond-party','group':'condition','label':L('手持ち(パッシブ)','Party')},
 {'id':'cond-mount','group':'condition','label':L('騎乗/ライド','Mount')},
 {'id':'cond-active','group':'condition','label':L('アクティブ発動','Active')},
 {'id':'cat-offense','group':'category','label':L('攻撃','Offense')},
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
