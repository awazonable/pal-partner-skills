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
            segs=re.split(r'★\s*(\d)\s*[:：]\s*',vl)
            label=segs[0].rstrip('：: ').strip()
            per={}
            for i in range(1,len(segs)-1,2):
                star=int(segs[i]); val=re.sub(r'[、：:\s]+$','',segs[i+1]).strip()
                if star not in per: per[star]=val
            perStar=[per.get(i) for i in range(5)]
            effects.append({'label':{'ja':label},'perStar':perStar})
        full=' '.join(desc_lines)
        # derive conditions
        cond=[]
        if '背中に乗って' in full or '乗って移動' in full or 'ライド' in full: cond.append('cond-mount')
        if '発動する' in full: cond.append('cond-active')
        if '手持ちにいる' in full or '手持ちから出している' in full or 'プレイヤーの近くに出現' in full: cond.append('cond-party')
        if '拠点にいる間' in full or 'アサインすると' in full or '拠点外' in full: cond.append('cond-base')
        cond=list(dict.fromkeys(cond))
        # derive categories
        cat=[]
        if re.search(r'ダメージ|威力|攻撃力|弱点|追撃|爆発|撃ちまく|突っ込む',full): cat.append('cat-offense')
        if re.search(r'防御力|耐性|軽減|無効|盾',full): cat.append('cat-defense')
        if re.search(r'乗って|グライダー|移動速度|ライド|ジャンプ|滑空|グライド|速度',full): cat.append('cat-mobility')
        if re.search(r'掘り出す|ドロップ|落とす|釣り|サルベージ|獲得量|拾っ',full): cat.append('cat-gathering')
        if re.search(r'作業適性|アサイン|効率|作業速度',full) or wks: cat.append('cat-production')
        if re.search(r'回復|HP|重量|サポート',full): cat.append('cat-support')
        cat=list(dict.fromkeys(cat))
        no=self.cur['no']; num=re.sub(r'^No\.','',no)
        variant='B' if num.endswith('B') else ('A' if num.endswith('A') else None)
        tags=els+wks+sts+cond+cat
        rec={'id':'no-'+num.lower(),'no':no,'variant':variant,
             'pal':{'ja':pal},'skillName':{'ja':skill},
             'element':els,'works':wks,'status':sts,'conditions':cond,'categories':cat,
             'tags':list(dict.fromkeys(tags)),
             'description':{'ja':full},'effects':effects,
             'stackable': not ('重複不可' in full),'noStack':'重複不可' in full,
             'palGear':{'ja':palgear} if palgear else None,
             'verified':True,'source':'palworld-lab'}
        self.blocks.append(rec); self.cur=None
    def close(self): self._flush(); super().close()

raw=open(sys.argv[1],encoding='utf-8',errors='replace').read()
m=re.search(r'<body[^>]*>(.*)</body>',raw,re.S); body=m.group(1) if m else raw
p=P(); p.feed(body); p.close()
skills=p.blocks

# ---- tags.json ----
def L(ja,en): return {'ja':ja,'en':en}
groups=[
 {'id':'condition','label':L('発動場面','Condition'),'order':1,'hint':L('いつ・どこで効果が出るか','')},
 {'id':'category','label':L('効果カテゴリ','Effect'),'order':2},
 {'id':'element','label':L('属性','Element'),'order':3,'hint':L('Pal自身/効果対象の属性','')},
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
  'note':'★0〜★4 は濃縮ランク=パートナースキルの5段階レベル。値はソース準拠（一部ソース側の表記ゆれ/★0省略あり→ — 表示）。αパル個体差分は本ソースに明示が無いため未収録。'},
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
