from pathlib import Path
import json
root=Path(__file__).resolve().parents[1]
samples=json.loads((root/'data/content-examples.json').read_text())
hexagrams=json.loads((root/'data/hexagrams.json').read_text())
(root/'h5/data.js').write_text('window.TURTLE_DATA='+json.dumps({'examples':samples,'hexagrams':hexagrams},ensure_ascii=False)+';\n')
print('Updated demo data from data/content-examples.json and data/hexagrams.json')
