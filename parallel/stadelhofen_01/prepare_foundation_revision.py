"""Unobserved buried foundation is kept below the actual graded ground bed."""
from pathlib import Path
import json
P=Path(__file__).resolve().parent;path=P/'derived/build_input.json';d=json.loads(path.read_text())
assert d['version'] in ['SF1_v04','SF1_v05']
d['version']='SF1_v05';d['plinth_foundation_bottom_z']=min(s['bottom_z'] for s in d['steps'])
d['v05_foundation_revision_basis']='Actual plinth-bottom/ground-bed check after the v04 approach view found the corner-only bottom interpolation bridged above a curved terrain transition. Extend both plinth bodies to the same buried 410.34m LN02 construction bottom as the steps; keep their surveyed footprint and top levels unchanged.'
note='Buried plinth foundation bottom 410.34m LN02 is an inferred construction closure shared with the authored step base, not a surveyed foundation depth.'
if note not in d['evidence_tiers']['inferred']:d['evidence_tiers']['inferred'].append(note)
path.write_text(json.dumps(d,indent=2),encoding='utf-8')
print(d['version'],'plinth foundation bottom',d['plinth_foundation_bottom_z'])
