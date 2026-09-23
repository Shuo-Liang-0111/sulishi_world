"""Record only views actually inspected in the current construction pass."""
from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parents[1];V='G1_012r5';E=R/'evidence'/V
names=['BE_QA_CORNER_FIXTURES','BE_QA_WEST_END_FIXTURES','BE_QA_TRACK_NEAR']
review={'version':V,'images_actually_inspected':[{'file':n+'.png','sha256':hashlib.sha256((E/(n+'.png')).read_bytes()).hexdigest()} for n in names],
 'observed_improvements':['Both endpoint information assemblies have readable front and reverse titles and correctly oriented local maps; the second map has its own source anchor.','Previously observed green pieces beside the near information frame and tall narrow left smear no longer visible at the same camera after bounded1.55m2 replacement.','Four modeled curb strips have finer aggregate scale; the track-angle check retains rail geometry, shelter columns and curb closure.','Two pole shafts retain position/height and now carry portable metre-scale subtle paint microstructure.'],
 'comparisons':['G1_012r4/BE_QA_CORNER_FIXTURES.png','G1_012r4/BE_QA_WEST_END_FIXTURES.png'],
 'limitations':['Large surrounding photo tree masses and unrebuilt street facades remain visibly distorted.','Type codes74/88 and exact anchor convention remain unresolved; tube assembly geometry is inferred from existing VBZ2016 drawings, not exact verified equipment model.','Map graphics are original inferred geographical notices, not actual posted timetables.','Info417, SIPF25 and tactile894 remain unbuilt; platform completeness is not claimed.','Paint and curb materials are inferred proxies; no on-site scan or surveyed weathering is asserted.','No realtime camera, collision, continuous walking or natural facility operation acceptance. MCP viewport screenshot still showed an old solid-view camera and is not counted as review of this camera.'],
 'accepted':False,'full_G1_complete':False}
(E/'native_visual_review.json').write_text(json.dumps(review,indent=2))
print(json.dumps({'version':V,'inspected':len(names),'accepted':False}))
