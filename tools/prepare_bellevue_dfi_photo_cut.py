"""Replace the distorted low photo mass around the source-located DFI only."""
from pathlib import Path
import runpy
from shapely.geometry import Point

ROOT=Path(__file__).resolve().parents[1]
runpy.run_path(str(ROOT/'tools/prepare_bellevue_west_shelter_cut.py'),init_globals={
 'CUT_MASK':Point(2683562.571,1246862.671).buffer(1.85),
 'CUT_UPPER':412.10,'CUT_BASE':'shelter_photo_cut.json',
 'CUT_OUTPUT':'fixtures_photo_cut.json','CUT_STATS_KEY':'dfi_stats',
 'CUT_DESCRIPTION':'Replace distorted low photo geometry within 1.85m of official DFI64 point, bounded above at LN02 412.10m. Actual reverse-camera rays hit nodes33591/33595 at LN02~409.5-409.8 where source orthophoto shows platform/DFI context; exact artifact origin remains uncertain. DFI physical replacement is present, original photo collection retained. No nearby surveyed tree/other VBZ point lies inside this volume.',
})
