from pathlib import Path
import runpy
R=Path(__file__).resolve().parents[1]
runpy.run_path(str(R/'tools/prepare_bellevue_corner_fixtures.py'),init_globals={'FIXTURE_CONFIG':{'out_dir':'derived/bellevue/west_end_fixtures','mast_id':1793,'info_ids':[2120,2585],'mast_ground_local':8.295417785644531,'info_ground_local':8.338964462280273,'cut_lower':408.05,'cut_base':'corner_fixture_photo_cut.json','cut_output':'west_end_fixture_photo_cut.json'}})
