import bpy,json
from pathlib import Path
ROOT=Path('F:/MyWorld/ZurichWorld')
issues=[]
for obj in bpy.data.collections['02_SURVEY_LOD2_REFERENCE'].objects:
    test=obj.data.copy()
    before={'vertices':len(test.vertices),'edges':len(test.edges),'polygons':len(test.polygons),'loops':len(test.loops)}
    changed=test.validate(verbose=False,clean_customdata=False)
    if changed:
        after={'vertices':len(test.vertices),'edges':len(test.edges),'polygons':len(test.polygons),'loops':len(test.loops)}
        issues.append({'id':obj.name,'before':before,'after':after})
    bpy.data.meshes.remove(test)
report={'issues':issues,'count':len(issues),'source_unchanged':True}
(ROOT/'evidence/G1_003/mesh_audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
