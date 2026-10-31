from pathlib import Path
import json
root=Path(__file__).resolve().parents[1]
a=json.loads((root/'data/hexagrams.json').read_text())
assert sorted(x['hexagram_id'] for x in a)==list(range(1,65))
assert len({tuple(x['lines_bottom_to_top']) for x in a})==64
assert len({(x['upper_trigram'],x['lower_trigram']) for x in a})==64
codes={'乾':[1,1,1],'坤':[0,0,0],'震':[1,0,0],'巽':[0,1,1],'坎':[0,1,0],'離':[1,0,1],'艮':[0,0,1],'兌':[1,1,0]}
for x in a:
 assert x['lines_bottom_to_top']==codes[x['lower_trigram']]+codes[x['upper_trigram']],x
assert a[10]['lines_bottom_to_top']==[1,1,1,0,0,0] # 泰：下乾上坤
assert a[11]['lines_bottom_to_top']==[0,0,0,1,1,1] # 否：下坤上乾
print('PASS: 64 unique IDs, 64 unique pairs, 64 unique patterns, all trigram concatenations and asymmetric direction anchors. Culture review NOT validated.')
