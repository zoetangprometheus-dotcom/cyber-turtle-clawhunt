"""Generate immutable firmware hexagram data from the shared source."""
from pathlib import Path
import json

root = Path(__file__).resolve().parents[1]
data = json.loads((root / 'data/hexagrams.json').read_text())
assert len(data) == 64
assert {h['hexagram_id'] for h in data} == set(range(1, 65))
masks = set()
rows = []
trigrams = {}
for h in sorted(data, key=lambda h: h['hexagram_id']):
    lines = h['lines_bottom_to_top']
    assert len(lines) == 6 and all(v in (0, 1) for v in lines)
    mask = sum(v << i for i, v in enumerate(lines))
    masks.add(mask)
    for name, bits in [(h['upper_trigram'], mask >> 3), (h['lower_trigram'], mask & 7)]:
        assert name not in trigrams or trigrams[name] == bits
        trigrams[name] = bits
    strings = ', '.join(json.dumps(h[key], ensure_ascii=False) for key in ['name_zh', 'upper_trigram', 'lower_trigram'])
    rows.append(f'  {{{h["hexagram_id"]}, {mask}, {strings}}}')
assert masks == set(range(64)) and len(trigrams) == 8
header = ('#pragma once\n#include <stdint.h>\n'
          '// Generated from data/hexagrams.json; lines encoded bottom to top.\n'
          'struct Hexagram { uint8_t id, lines; const char *name, *upper, *lower; };\n'
          'static const Hexagram HEXAGRAMS[64] = {\n' + ',\n'.join(rows) + '\n};\n')
(root / 'firmware/cyber_turtle/Hexagrams.h').write_text(header)
print('Validated and generated all 64 hexagram combinations')
