"""Replayable SF1 central entrance construction; all local outputs are bounded."""
import sys,os,math,json,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent));sys.path.insert(0,'H:/MyWorld/ZurichWorld/tools')
from sf1_common import *
from mathutils.geometry import tessellate_polygon
from blender_photo_clip import cut_object
from blender_geometry_fingerprint import mesh_digest

def build():
    assert not bpy.data.collections.get(D['import_collection'])
    C=collection(D['import_collection']);C['source_identity']='Stadelhoferstrasse8 / EGID2372568 / AV38215'
    C['sf1_version']=D['version'];C['build_spec_sha256']=sha(OUT/'derived/build_input.json')
    C['origin_lv95_ln02']=D['origin'];C['public_runtime_enabled']=False
    C['inference_boundary']=json.dumps(D['evidence_tiers'],ensure_ascii=False)
    C['scope']='Only central ground-floor entrance, canopy, surveyed stair, plinths, and contiguous apron.'
    groups={};parts=json.loads((OUT/'derived/part_outlines.json').read_text())
    def add(name,verts,faces,mat,bevel=0,smooth=False,role='construction'):
        key=(name,mat.name);g=groups.setdefault(key,dict(v=[],f=[],mat=mat,bevel=bevel,smooth=smooth,role=role))
        n=len(g['v']);g['v'].extend([list(p) for p in verts]);g['f'].extend([[n+i for i in f] for f in faces])
    def box3(name,c,sz,mat,bevel=.0015,role='construction'):
        vv=[P(c[0]+i*sz[0]/2,c[1]+j*sz[1]/2,c[2]+k*sz[2]/2) for i,j,k in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
        # (U, outward N, up) is a left-handed facade frame.
        add(name,vv,[(1,2,3,0),(7,6,5,4),(4,5,1,0),(5,6,2,1),(6,7,3,2),(7,4,0,3)],mat,bevel,role=role)
    def prism(name,poly,low,high,mat,bevel=.0015,vertical=False,role='construction'):
        # polygon coordinates (u,z) on facade or (u,v) on floor; both ends closed.
        clean=[]
        for p in poly:
            if not clean or np.linalg.norm(np.array(p)-clean[-1])>1e-9:clean.append(np.array(p))
        if len(clean)>2 and np.linalg.norm(clean[0]-clean[-1])<1e-9:clean.pop()
        poly=np.array(clean);n=len(poly)
        def at(p,k):
            h=k(*p) if callable(k) else k
            return P(p[0],h,p[1]) if vertical else P(p[0],p[1],h)
        vv=[at(p,low) for p in poly]+[at(p,high) for p in poly]
        p2=[Vector((p[0],p[1],0)) for p in poly];index={tuple(p):i for i,p in enumerate(p2)}
        tris=[[p if isinstance(p,int) else index[tuple(p)] for p in t] for t in tessellate_polygon([p2])]
        faces=[list(reversed(t)) for t in tris]+[[i+n for i in t] for t in tris]+[(j,(j+1)%n,(j+1)%n+n,j+n) for j in range(n)]
        # Establish consistent outward normals regardless of input winding.
        area=sum(poly[i,0]*poly[(i+1)%n,1]-poly[(i+1)%n,0]*poly[i,1] for i in range(n))
        if (area<0)^(not vertical):faces=[list(reversed(f)) for f in faces]
        add(name,vv,faces,mat,bevel,role=role)
    def tube(name,pts,r,mat,sides=12,role='construction'):
        pts=np.array([P(*p) for p in pts]);vv=[];ff=[]
        for i,p in enumerate(pts):
            axis=pts[min(i+1,len(pts)-1)]-pts[max(0,i-1)];axis/=np.linalg.norm(axis)
            seed=np.array([0,0,1]) if abs(axis[2])<.95 else np.array([1,0,0]);xx=np.cross(axis,seed);xx/=np.linalg.norm(xx);yy=np.cross(axis,xx)
            vv.extend([p+r*(xx*np.cos(a)+yy*np.sin(a)) for a in np.arange(sides)*math.tau/sides])
        for i in range(len(pts)-1):
            for j in range(sides):a=i*sides+j;b=i*sides+(j+1)%sides;ff.append((a,b,b+sides,a+sides))
        ff.extend([list(range(sides-1,-1,-1)),[(len(pts)-1)*sides+i for i in range(sides)]])
        add(name,vv,ff,mat,0,True,role)
    def graded_solid(name,bed,low_offset,high_offset,mat,bevel=0,role='walk_surface'):
        uv=bed['vertices'];nn=len(uv)
        vv=[P(u,v,grade(u,v)+low_offset) for u,v in uv]+[P(u,v,grade(u,v)+high_offset) for u,v in uv]
        ff=[list(reversed(t)) for t in bed['triangles']]+[[i+nn for i in t] for t in bed['triangles']]
        ff.extend([[a,b,b+nn,a+nn] for a,b in bed['boundary_edges']])
        add(name,vv,ff,mat,bevel,role=role)
    def finish(name,color,rough=.7,metal=0,micro=.0002,variation=.04,scale=3):
        m=bpy.data.materials.new('SF1_MAT_'+name);m.use_nodes=True;nt=m.node_tree;ns=nt.nodes;ln=nt.links;bs=ns.get('Principled BSDF')
        bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Roughness'].default_value=rough;bs.inputs['Metallic'].default_value=metal
        tx=ns.new('ShaderNodeTexCoord');noise=ns.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=scale;noise.inputs['Detail'].default_value=4
        ln.new(tx.outputs['Object'],noise.inputs['Vector']);ramp=ns.new('ShaderNodeValToRGB')
        ramp.color_ramp.elements[0].position=.18;ramp.color_ramp.elements[0].color=(*[c*(1-variation) for c in color],1)
        ramp.color_ramp.elements[1].position=.82;ramp.color_ramp.elements[1].color=(*[c*(1+variation) for c in color],1)
        ln.new(noise.outputs['Fac'],ramp.inputs[0]);ln.new(ramp.outputs['Color'],bs.inputs['Base Color'])
        if micro:
            fine=ns.new('ShaderNodeTexNoise');fine.inputs['Scale'].default_value=650;fine.inputs['Detail'].default_value=2.3;fine.inputs['Roughness'].default_value=.72
            ln.new(tx.outputs['Object'],fine.inputs['Vector']);b=ns.new('ShaderNodeBump');b.inputs['Distance'].default_value=micro;b.inputs['Strength'].default_value=.40
            ln.new(fine.outputs['Fac'],b.inputs['Height']);ln.new(b.outputs['Normal'],bs.inputs['Normal'])
        m['basis']='Material family observed in dated reference; exact optical finish/aging inferred.'
        return m
    stones=[finish('pale_limestone_%02d'%i,tuple(np.array([.53,.545,.525])*(.956+i*.011)),.78,variation=.045,micro=.00032) for i in range(8)]
    granite=[finish('grey_granite_%02d'%i,tuple(np.array([.31,.317,.298])*(.96+i*.008)),.78,variation=.13,micro=.00055,scale=48) for i in range(11)]
    mortar=finish('recessed_mineral_joints',(.17,.177,.161),.96,micro=.0005,variation=.1,scale=140)
    iron=finish('dark_aged_iron',(.056,.065,.057),.42,.68,.00009,.13,5)
    frame=finish('grey_painted_door_joinery',(.25,.288,.263),.45,.03,.00007,.055,3)
    frameedge=finish('painted_joinery_recess',(.22,.247,.228),.56,.02,.00010,.05,5)
    gasket=finish('black_glazing_seal',(.012,.016,.014),.8,0,0,.05)
    stainless=finish('satin_stainless',(.48,.50,.49),.39,.92,.000018,.03,30)
    interior=finish('inferred_recess_plaster',(.30,.29,.25),.89,0,.00016,.08)
    white=finish('sign_white',(.78,.80,.78),.44,0,0,0)
    blue=finish('station_enamel_blue',(.008,.025,.13),.4,.12,0,.02)
    red=finish('station_enamel_red',(.46,.012,.019),.39,.12,0,.02)
    glass=finish('clear_glazing',(.92,.97,.95),.105,0,0,.012)
    bs=glass.node_tree.nodes.get('Principled BSDF');bs.inputs['Transmission Weight'].default_value=1;bs.inputs['IOR'].default_value=1.46
    roofglass=glass.copy();roofglass.name='SF1_MAT_weathered_canopy_glass';rbs=roofglass.node_tree.nodes.get('Principled BSDF');rbs.inputs['Roughness'].default_value=.19
    nt=roofglass.node_tree;noise=nt.nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=19;noise.inputs['Detail'].default_value=5
    rough=nt.nodes.new('ShaderNodeMapRange');rough.inputs['From Min'].default_value=.15;rough.inputs['From Max'].default_value=.85;rough.inputs['To Min'].default_value=.09;rough.inputs['To Max'].default_value=.26
    nt.links.new(noise.outputs['Fac'],rough.inputs['Value']);nt.links.new(rough.outputs['Result'],rbs.inputs['Roughness'])
    # Closed, supported graded subbase; every surface above is a real stone solid.
    scope=D['scope_local'];u0,u1=scope['u'];v0,v1=scope['v'];rect=D.get('apron_outline',[(u0,v0),(u1,v0),(u1,v1),(u0,v1)])
    # A connected triangulated bed follows the same shaped edge transition as
    # the stone. A single large n-gon would interpolate across the entire site.
    graded_solid('SF1_APRON_CONTINUOUS_SUBBASE',parts['apron_subbase'],-.18,-.004,mortar,0,'walk_support')
    for i,step in enumerate(D['steps']):
        prism('SF1_STAIR_%d_BODY'%i,step['outline'],step['bottom_z'],step['top_z']-.045,granite[4],.003,role='step_support')
        if i==3:prism('SF1_LANDING_BEDDING',step['outline'],step['top_z']-.045,step['top_z']-.006,mortar,0,role='walk_support')
    for i,poly in enumerate(D['wall_outlines']):
        prism('SF1_CHEEK_%d_MASONRY'%i,poly,D.get('plinth_foundation_bottom_z',lambda u,v:grade(u,v)-.09),D['landing_z']-.075,stones[3],.004,role='plinth')
        prism('SF1_CHEEK_%d_COPING'%i,poly,D['landing_z']-.075,D['landing_z'],granite[7],.0035,role='walk_support')
    if D.get('left_wall_foot'):
        wf=D['left_wall_foot'];rows=wf['samples'];vv=[];ff=[]
        for r in rows:
            u=r['u'];front=r['top_front_v'];bottom=wf['bottom_front_v'];th=wf['thickness_m']
            vv.extend([P(u,bottom,wf['bottom_z']),P(u,bottom-th,wf['bottom_z']),
                       P(u,front-th,wf['top_z']),P(u,front,wf['top_z'])])
        for i in range(len(rows)-1):
            for j in range(4):
                ff.append([4*i+j,4*i+(j+1)%4,4*(i+1)+(j+1)%4,4*(i+1)+j])
        ff.extend([[3,2,1,0],[4*(len(rows)-1)+j for j in range(4)]])
        add('SF1_LEFT_WALL_FOOT_CONNECTION',vv,ff,stones[3],0,False,'facade')
    for p in parts['parts']:
        role=p['role'];poly=p['outline'];i=p['index']
        if role=='facade_ashlar':prism('SF1_FACADE_ASHLAR',poly,-.52,.017,stones[p['tone']],.0015,True,'facade')
        elif role=='forecourt_slab':graded_solid('SF1_APRON_GRANITE',p['surface_mesh'],-.043,0,granite[p['tone']],.0012,'walk_surface')
        elif role=='landing_slab':prism('SF1_LANDING_GRANITE',poly,D['landing_z']-.045,D['landing_z'],granite[p['tone']],.0012,role='walk_surface')
        else:
            step=D['steps'][p['step_index']];prism('SF1_TREAD_%d_STONES'%p['step_index'],poly,step['top_z']-.055,step['top_z'],granite[p['tone']],.003,role='step_surface')
    # Recessed mortar backing follows each pier/spandrel, not a plane across doors.
    for x0,x1 in [(0,1.095),(3.105,5.00865),(7.01865,W-3.105),(W-1.095,W)]:
        box3('SF1_WALL_PIER_BACKING',((x0+x1)/2,-.29,13.24),(x1-x0,.45,4.25),mortar,0,'facade')
    # Central cornice and side returns meet retained upper survey photography.
    for z,depth,height,proj in [(15.43,.62,.09,.06),(15.52,.75,.08,.12),(15.64,.83,.16,.17),(15.77,.67,.08,.07)]:
        box3('SF1_FIRST_STOREY_CORNICE',(W/2,-.20+proj,z),(W+.54,depth,height),stones[5],.003,'facade')
    for x in [-.18,W+.18]:
        box3('SF1_OUTER_PILASTER_BACKING',(x,-.135,13.34),(.56,.75,4.20),mortar,0,'facade')
        for j in range(10):
            bot=D['landing_z']+.005+j*(15.385-(D['landing_z']+.005))/10
            top=D['landing_z']+.005+(j+1)*(15.385-(D['landing_z']+.005))/10
            box3('SF1_OUTER_PILASTER',(x,-.125,(bot+top)/2),(.59,.78,top-bot-.003),stones[j%8],.0015,'facade')
        box3('SF1_PILASTER_PLINTH',(x,-.09,11.43),(.70,.91,.30),stones[4],.003,'facade')
        for z,depth,height,proj,width in [(15.43,.62,.09,.06,.70),(15.52,.75,.08,.12,.83),(15.64,.83,.16,.17,.91),(15.77,.67,.08,.07,.76)]:
            box3('SF1_PILASTER_CORNICE_RETURN',(x,-.20+proj,z),(width,depth,height),stones[5],.003,'facade')
    # Source-survey wing setback is approximately v=-0.75m. Close the narrow
    # cropped return strips so a cut mesh edge cannot leave a hollow open flank.
    for xa,xb in [(-1.32,-.47),(W+.47,13.27)]:
        box3('SF1_WING_RETURN_BACKING',((xa+xb)/2,-.84,(D['landing_z']-.03+15.80)/2),(xb-xa,.29,15.80-D['landing_z']+.03),mortar,0,'facade')
        for j in range(11):
            bottom=D['landing_z']-.015+j*(15.69-(D['landing_z']-.015))/11
            top=D['landing_z']-.015+(j+1)*(15.69-(D['landing_z']-.015))/11
            box3('SF1_WING_RETURN_MASONRY',((xa+xb)/2,-.825,(bottom+top)/2),(xb-xa,.33,top-bottom-.003),stones[j%8],.0015,'facade')
        box3('SF1_WING_RETURN_CAP',((xa+xb)/2,-.80,15.75),(xb-xa+.015,.39,.12),stones[5],.002,'facade')
    # Connect the recessed wing face to the back of the projecting pilaster.
    # Their u extents met in v03, but a 145mm gap remained in the depth direction.
    for x in [-.471,W+.471]:
        box3('SF1_WING_CORNER_RETURN_BACKING',(x,-.60,13.525),(.13,.61,4.55),mortar,0,'facade')
        for j in range(11):
            bot=D['landing_z']-.015+j*(15.69-(D['landing_z']-.015))/11
            top=D['landing_z']-.015+(j+1)*(15.69-(D['landing_z']-.015))/11
            box3('SF1_WING_CORNER_RETURN_STONES',(x,-.60,(bot+top)/2),(.16,.63,top-bot-.003),stones[j%8],.0015,'facade')
        box3('SF1_WING_CORNER_RETURN_CAP',(x,-.60,15.75),(.18,.67,.12),stones[5],.002,'facade')
    # Three arch openings with actual reveal, profiled stone rings and grey paired doors.
    land=D['landing_z'];spring=parts['spring_z'];r=parts['opening_radius']
    for bay,u in enumerate(parts['centers']):
        label='SF1_BAY%d_'%(bay+1)
        for side in [-1,1]:
            x=u+side*(r+.065)
            box3(label+'REVEAL_JAMB',(x,-.205,(land+spring)/2),(.13,.45,spring-land),stones[2],.002,'facade')
            for rr,pr,ww in [(r+.115,.080,.048),(r+.19,.045,.045)]:
                box3(label+'STONE_VERTICAL_MOULDING',(u+side*rr,pr,(land+spring)/2),(ww,.09,spring-land),stones[4],.002,'facade')
            box3(label+'IMPOST',(u+side*(r+.14),.078,spring+.035),(.46,.33,.11),stones[5],.0025,'facade')
        for j in range(17):
            a=j*math.pi/17+.001;b=(j+1)*math.pi/17-.001
            poly=[(u+(r+.17)*math.cos(t),spring+(r+.17)*math.sin(t)) for t in np.linspace(a,b,6)]+[(u+r*math.cos(t),spring+r*math.sin(t)) for t in np.linspace(b,a,6)]
            prism(label+'ARCH_VOUSSOIRS',poly,-.45,.025,stones[(j+bay)%8],.0013,True,'facade')
        for rr,rad,dep in [(r+.052,.029,.075),(r+.165,.024,.076),(r+.235,.027,.037)]:
            tube(label+'ARCH_MOULDING',[(u+rr*math.cos(t),dep,spring+rr*math.sin(t)) for t in np.linspace(0,math.pi,97)],rad,stones[4],12,'facade')
        prism(label+'KEYSTONE',[(u-.12,spring+r-.017),(u+.12,spring+r-.017),(u+.16,spring+r+.29),(u-.16,spring+r+.29)],.07,.17,stones[5],.002,True,'facade')
        # Real arched glass infill; seam at the centre is occupied by the mullion.
        gr=r-.095;gz=spring+.012
        arc=[(u+gr*math.cos(t),gz+gr*math.sin(t)) for t in np.linspace(0,math.pi,65)]+[(u+gr,gz)]
        prism(label+'FANLIGHT_GLASS',arc,-.116,-.102,glass,0,True,'glazing')
        tube(label+'FANLIGHT_FRAME',[(u+(r-.045)*math.cos(t),-.074,spring+(r-.045)*math.sin(t)) for t in np.linspace(0,math.pi,97)],.039,frame,16,'joinery')
        tube(label+'FANLIGHT_GASKET',[(u+(r-.086)*math.cos(t),-.068,spring+(r-.086)*math.sin(t)) for t in np.linspace(0,math.pi,97)],.008,gasket,8,'joinery')
        box3(label+'FANLIGHT_MULLION',(u,-.074,spring+(r-.054)/2),(.059,.086,r-.054),frame,.002,'joinery')
        doorhead=spring-.044;bottom=land+.018
        for x in [u-r+.025,u+r-.025]:box3(label+'FIXED_OUTER_FRAME',(x,-.086,(bottom+doorhead)/2),(.074,.16,doorhead-bottom+.11),frame,.0025,'joinery')
        box3(label+'FRAME_HEADER',(u,-.075,doorhead),(2*r,.15,.115),frame,.0025,'joinery')
        box3(label+'STONE_THRESHOLD',(u,-.06,land-.014),(2*r,.68,.048),granite[7],.002,'walk_surface')
        for side in [-1,1]:
            leaflabel=label+('LEFT_' if side<0 else 'RIGHT_')
            a=u-r+.070 if side<0 else u+.005;b=u-.005 if side<0 else u+r-.070
            mid=(a+b)/2;lw=b-a;low=bottom;hi=doorhead-.060
            for x in [a+.037,b-.037]:box3(leaflabel+'LEAF_STILES',(x,-.079,(low+hi)/2),(.074,.088,hi-low),frame,.0018,'door')
            for z,h in [(low+.06,.12),(land+1.075,.095),(land+1.775,.065),(hi-.045,.09)]:
                box3(leaflabel+'LEAF_RAILS',(mid,-.079,z),(lw,.088,h),frame,.0018,'door')
            # Two narrow recessed opaque panels per leaf.
            for half in [-1,1]:
                cx=mid+half*lw*.235;pw=lw*.40
                box3(leaflabel+'LOWER_PANEL',(cx,-.097,land+.568),(pw,.045,.785),frameedge,.002,'door')
                box3(leaflabel+'RAISED_PANEL_FACE',(cx,-.066,land+.567),(pw-.033,.020,.738),frame,.0035,'door')
                for x in [cx-pw/2-.010,cx+pw/2+.010]:box3(leaflabel+'PANEL_MOULDING',(x,-.039,land+.568),(.023,.020,.820),frame,.004,'door')
                for z in [land+.158,land+.978]:box3(leaflabel+'PANEL_MOULDING',(cx,-.039,z),(pw+.042,.020,.023),frame,.004,'door')
            for z0,z1 in [(land+1.135,land+1.735),(land+1.812,hi-.095)]:
                box3(leaflabel+'LEAF_GLASS',(mid,-.080,(z0+z1)/2),(lw-.158,.012,z1-z0),glass,0,'glazing')
                for x in [a+.086,b-.086]:box3(leaflabel+'LEAF_GLAZING_BEAD',(x,-.032,(z0+z1)/2),(.025,.025,z1-z0+.04),frame,.001,'door')
                for z in [z0-.009,z1+.009]:box3(leaflabel+'LEAF_GLAZING_BEAD',(mid,-.032,z),(lw-.14,.025,.024),frame,.001,'door')
            # Lock plate, return lever and hinge barrels remain editable true solids.
            hx=u+side*.088
            box3(leaflabel+'LOCK_PLATE',(hx,-.019,land+1.07),(.045,.015,.19),iron,.005,'hardware')
            tube(leaflabel+'HANDLE',[(hx,.010,land+1.12),(hx,.080,land+1.12),(hx+side*.105,.080,land+1.12)],.011,stainless,12,'hardware')
            for zz in [land+.30,land+1.40,land+2.30]:tube(leaflabel+'HINGES',[(a if side<0 else b,-.031,zz-.055),(a if side<0 else b,-.031,zz+.055)],.012,iron,12,'hardware')
        # Recess depth and opaque background; no invented publicly usable interior.
        box3(label+'RECESS_FLOOR',(u,-1.05,land-.048),(2.15,1.7,.10),granite[2],.001,'closed_interior')
        box3(label+'RECESS_BACK',(u,-1.87,13.15),(2.34,.18,3.9),interior,.001,'closed_interior')
        for x in [u-1.1,u+1.1]:box3(label+'RECESS_SIDE',(x,-1.0,13.15),(.16,1.7,3.9),interior,.001,'closed_interior')
        box3(label+'RECESS_CEILING',(u,-1.02,15.04),(2.32,1.78,.12),interior,.001,'closed_interior')
    # Iron/glass canopy: wall anchors, curved brackets, open T bars and thin panes.
    zroof=15.307
    for u in [.16,4.06,7.97,W-.16]:
        box3('SF1_CANOPY_WALL_ANCHORS',(u,-.035,14.45),(.15,.20,1.46),iron,.003,'canopy_support')
        # A bowed knee reaches the cantilever tip, with progressively shorter webs.
        vs=np.linspace(.10,4.03,49);zz=13.86+1.26*np.sqrt(np.clip(vs/4.03,0,1))
        tube('SF1_CANOPY_CURVED_BRACKETS',[(u,float(v),float(z)) for v,z in zip(vs,zz)],.036,iron,12,'canopy_support')
        for v in np.linspace(.20,3.84,15):
            low=13.86+1.26*math.sqrt(v/4.03)
            box3('SF1_CANOPY_BRACKET_WEBS',(u,float(v),(low+15.19)/2),(.026,.023,15.19-low),iron,.001,'canopy_support')
        box3('SF1_CANOPY_PRIMARY_WEB',(u,2.055,15.192),(.018,4.15,.16),iron,.0015,'canopy_support')
        box3('SF1_CANOPY_PRIMARY_FLANGE',(u,2.055,15.266),(.095,4.15,.018),iron,.001,'canopy_support')
        for z in [13.92,14.40,14.95]:
            tube('SF1_CANOPY_ANCHOR_BOLTS',[(u,.050,z),(u,.093,z)],.013,iron,6,'hardware')
        tube('SF1_CANOPY_ANCHOR_FINIAL',[(u,.08,13.80),(u,.08,13.90)],.045,iron,16,'canopy_support')
    # Glazed roof subdivisions: 16 across by 4 along the measured projection.
    for i in range(17):
        u=W*i/16
        box3('SF1_CANOPY_GLAZING_T_WEB',(u,2.04,zroof-.035),(.012,4.082,.070),iron,.0008,'canopy_frame')
        box3('SF1_CANOPY_GLAZING_T_CAP',(u,2.04,zroof+.005),(.036,4.082,.016),iron,.0008,'canopy_frame')
    for j in range(5):
        v=4.07*j/4
        box3('SF1_CANOPY_TRANSVERSE_BARS',(W/2,v,zroof-.028),(W,.025,.067),iron,.001,'canopy_frame')
    for i in range(16):
        for j in range(4):
            box3('SF1_CANOPY_GLASS_PANES',((i+.5)*W/16,(j+.5)*4.07/4,zroof+.001),(W/16-.040,4.07/4-.032,.010),roofglass,.0008,'glazing')
    for v in [.02,4.075]:
        box3('SF1_CANOPY_PERIMETER_FASCIA',(W/2,v,15.206),(W+.105,.075,.185),iron,.003,'canopy_frame')
        tube('SF1_CANOPY_EDGE_BEAD',[(0,v+.041,15.12),(W,v+.041,15.12)],.012,iron,12,'canopy_frame')
    for u in [-.020,W+.020]:box3('SF1_CANOPY_SIDE_FASCIA',(u,2.04,15.206),(.075,4.09,.185),iron,.003,'canopy_frame')
    # Small scalloped fascia, built with rounded iron lobes.
    for i in range(132):
        u=(i+.5)*W/132
        poly=[(u-.034,15.142),(u+.034,15.142)]+[(u+.034*math.cos(t),15.110+.034*math.sin(t)) for t in np.linspace(0,-math.pi,13)]
        prism('SF1_CANOPY_SCALLOPED_EDGE',poly,4.08,4.098,iron,.0008,True,'canopy_frame')
    # Drain pipes are coupled to the eave and reach the ground/plinth.
    for u in [-.34,W+.34]:
        tube('SF1_CANOPY_DOWNPIPES',[(u,.17,land-.004),(u,.17,14.92),(u,.17,15.23),(u+.20 if u<0 else u-.20,.05,15.23)],.037,iron,20,'canopy_drain')
        for z in [11.62,13.2,14.7]:box3('SF1_DOWNPIPE_CLIPS',(u,.12,z),(.11,.18,.042),iron,.002,'hardware')
    # Handrails: grounded at the actual adjacent tread and apron levels.
    for u in [4.24,8.20]:
        pts=[(u,.61,land+.78),(u,.61,land+.91),(u,.75,land+.95),(u,2.02,land+.95),(u,3.43,grade(u,3.42)+.95),(u,3.61,grade(u,3.42)+.95),(u,3.66,grade(u,3.42)+.90),(u,3.66,grade(u,3.42)+.76)]
        # Fillet each bend with a short quadratic curve, retaining the straight
        # hand-contact runs and all support heights at their actual locations.
        rounded=[np.array(pts[0])]
        for j in range(1,len(pts)-1):
            aa=np.array(pts[j-1]);bb=np.array(pts[j]);cc=np.array(pts[j+1]);la=np.linalg.norm(aa-bb);lc=np.linalg.norm(cc-bb)
            dist=min(.045,la*.30,lc*.30);q0=bb+(aa-bb)*dist/la;q1=bb+(cc-bb)*dist/lc
            rounded.append(q0)
            rounded.extend([(1-t)**2*q0+2*(1-t)*t*bb+t*t*q1 for t in np.linspace(0,1,9)[1:]])
        rounded.append(np.array(pts[-1]))
        tube('SF1_STAIR_CONTINUOUS_HANDRAILS',rounded,.022,stainless,20,'handrail')
        post_v=D.get('handrail_post_v',[.80,2.04,2.96,3.42])
        positions=[(post_v[0],land),(post_v[1],land),(post_v[2],D['steps'][0]['top_z']),(post_v[3],grade(u,post_v[3]))]
        for v,z in positions:
            # Intersect each vertical post with the final rounded centreline,
            # not a second, independently approximated rail-height formula.
            cross=[]
            for a,b in zip(rounded[:-1],rounded[1:]):
                if min(a[1],b[1])-1e-9<=v<=max(a[1],b[1])+1e-9 and abs(a[1]-b[1])>1e-9:
                    cross.append(float(a[2]+(b[2]-a[2])*(v-a[1])/(b[1]-a[1])))
            assert cross,(u,v)
            rail_z=max(cross)
            tube('SF1_STAIR_HANDRAIL_POSTS',[(u,v,z+.006),(u,v,rail_z+.001)],.022,stainless,16,'handrail')
            footprint=[(u-.055,v-.05),(u+.055,v-.05),(u+.055,v+.05),(u-.055,v+.05)]
            floor=grade if v>3.4 else (lambda x,y,z=z:z)
            prism('SF1_HANDRAIL_BASEPLATES',footprint,lambda x,y:floor(x,y)-.001,lambda x,y:floor(x,y)+.019,stainless,.003,role='hardware')
            bed=[(u-.052,v-.047),(u+.052,v-.047),(u+.052,v+.047),(u-.052,v+.047)]
            prism('SF1_HANDRAIL_ANCHOR_BEDDING',bed,lambda x,y:floor(x,y)-.012,lambda x,y:floor(x,y),mortar,0,role='anchor_bedding')
    # Source-observed sign with stable station identity, not invented live content.
    sign_u=W/2;sign_w=4.22;sign_z=14.72;sign_v=4.12
    box3('SF1_STATION_SIGN_CASE',(sign_u,sign_v,sign_z),(sign_w,.115,.63),iron,.012,'signage')
    box3('SF1_STATION_SIGN_BLUE',(sign_u+.51,sign_v+.061,sign_z),(sign_w-1.03,.012,.577),blue,.003,'signage')
    box3('SF1_STATION_SIGN_RED',(sign_u-sign_w/2+.518,sign_v+.061,sign_z),(1.008,.012,.577),red,.003,'signage')
    for u in [sign_u-1.7,sign_u+1.7]:tube('SF1_SIGN_HANGERS',[(u,sign_v,15.2),(u,sign_v,sign_z+.31)],.013,iron,12,'signage')
    def text_obj(name,body,u,v,z,size,mat):
        data=bpy.data.curves.new(name,'FONT');data.body=body;data.size=size;data.extrude=.0007;data.bevel_depth=.0003
        data.align_y='CENTER';ob=bpy.data.objects.new(name,data);C.objects.link(ob);ob.location=P(u,v,z)
        from mathutils import Matrix
        # text local XY = facade U / vertical, with its face towards forecourt.
        matx=Matrix(((U[0],0,N[0]),(U[1],0,N[1]),(0,1,0)))
        ob.rotation_euler=matx.to_euler();data.materials.append(mat);ob['sf1_role']='signage'
        return ob
    text_obj('SF1_SIGN_STATION_NAME','Stadelhofen',sign_u-.16,sign_v+.074,sign_z+.013,.36,white)
    text_obj('SF1_SIGN_CITY_NAME','Zürich',sign_u-sign_w/2+1.10,sign_v+.074,sign_z-.084,.11,white)
    # SBB double arrows; real shallow extruded profile rather than pasted artwork.
    logo_u=sign_u-sign_w/2+.52
    for sign in [-1,1]:
        x=logo_u+sign*.06
        tube('SF1_SIGN_SBB_ARROW',[(x+sign*.03,sign_v+.078,sign_z+.163),(x+sign*.20,sign_v+.078,sign_z),(x+sign*.03,sign_v+.078,sign_z-.163)],.025,white,10,'signage')
    box3('SF1_SIGN_SBB_CROSSBAR',(logo_u,sign_v+.081,sign_z),(.59,.018,.043),white,.001,'signage')
    box3('SF1_SIGN_SBB_CENTER',(logo_u,sign_v+.081,sign_z),(.045,.018,.335),white,.001,'signage')
    # Slim notice frames occupy evidenced positions. Text is intentionally limited
    # to stable public identity; changing commercial listings are not fabricated.
    for k,u in enumerate([4.08,7.99]):
        box3('SF1_DIRECTORY_CASE',(u,.130,land+1.47),(.64,.065,1.82),iron,.008,'signage')
        box3('SF1_DIRECTORY_FACE',(u,.167,land+1.47),(.595,.009,1.77),white,.002,'signage')
        box3('SF1_DIRECTORY_HEADER',(u,.173,land+2.07),(.574,.006,.44),blue,.001,'signage')
        text_obj('SF1_DIRECTORY_STATION_'+str(k),'Zürich\nStadelhofen',u-.248,.182,land+2.12,.081,white)
        # Subtle typographic rules, no fictitious destinations or operating times.
        for j in range(7):box3('SF1_DIRECTORY_RULES',(u,.179,land+1.66-j*.17),(.44,.003,.006),frame,.0001,'signage')
        text_obj('SF1_DIRECTORY_INFO_'+str(k),'Information',u-.239,.182,land+1.78,.066,blue)
    # Assemble watertight solids by semantic part and material, not one fused mesh.
    created=[]
    for (name,matname),g in groups.items():
        me=bpy.data.meshes.new(name+'_MESH');me.from_pydata(g['v'],[],g['f']);me.update()
        import bmesh
        bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
        ob=bpy.data.objects.new(name,me);C.objects.link(ob);me.materials.append(g['mat']);ob['sf1_role']=g['role']
        ob['source_spec']='parallel/stadelhofen_01/derived/build_input.json';ob['public_runtime_enabled']=False
        if g['smooth']:
            for p in me.polygons:p.use_smooth=True
        if g['bevel']:
            mod=ob.modifiers.new('manufactured_edge_radius','BEVEL');mod.width=g['bevel'];mod.segments=2
            mod.affect='EDGES';mod.limit_method='ANGLE'
            normal=ob.modifiers.new('area_weighted_normals','WEIGHTED_NORMAL');normal.keep_sharp=True;normal.weight=30
        created.append(ob.name)
    # A reviewable local mechanism; saved closed, not exposed to public runtime.
    control=bpy.data.objects.new('SF1_DOOR_CENTRE_CONTROL',None);C.objects.link(control)
    control['open_fraction']=0.;control.id_properties_ui('open_fraction').update(min=0,max=1)
    control['mechanism_basis']='Hinged paired leaves and 95 degree outward test motion inferred from dated photograph; no current hardware survey.'
    control['public_runtime_enabled']=False
    from mathutils import Matrix
    for side in [-1,1]:
        prefix='SF1_BAY2_'+('LEFT_' if side<0 else 'RIGHT_')
        pivot=bpy.data.objects.new(prefix+'PIVOT',None);C.objects.link(pivot);pivot.location=P(W/2+side*(r-.070),-.079,land)
        bpy.context.view_layer.update()
        for ob in list(C.objects):
            if ob.name.startswith(prefix) and ob!=pivot:
                matrix=ob.matrix_world.copy();ob.parent=pivot;ob.matrix_world=matrix
        driver=pivot.driver_add('rotation_euler',2).driver;driver.type='SCRIPTED'
        var=driver.variables.new();var.name='f';var.type='SINGLE_PROP';var.targets[0].id=control;var.targets[0].data_path='["open_fraction"]'
        driver.expression=str(side*math.radians(95))+'*f'
    for ob in C.objects:ob['sf1_package']='stadelhofen_01';ob['base_sha256']=D['base_sha256']
    return C,created

def apply_local_crop():
    inventory=json.loads((OUT/'derived/native_context_inventory.json').read_text())
    byname={r['original_name']:r for r in inventory['objects']};reports=[]
    b=D['scope_local'];boxes=D.get('crop_boxes',[[*b['u'],*b['v'],*b['z']]])
    for name in D['candidate_old_objects']:
        row=byname[name];ob=bpy.data.objects[row['local_name']]
        assert json.loads(json.dumps(mesh_digest(ob.data)))==row['mesh_digest'],name
        before=mesh_digest(ob.data)
        result=cut_object(ob,Q,boxes);assert result,name
        result['base_object']=name;result['before_digest']=before;result['after_digest']=mesh_digest(ob.data);result['crop_boxes_uvz']=boxes
        reports.append(result)
    return reports

if __name__=='__main__':
    assert bpy.context.scene.get('sf1_version')=='SF1_baseline'
    assert sha(D['base_native'])==D['base_sha256']
    collection_authored,names=build();crops=apply_local_crop()
    version=D.get('version','SF1_v01');tag=version.split('_')[-1]
    s=bpy.context.scene;s['sf1_version']=version;s['sf1_quality']='working local batch; visual acceptance and main integration pending'
    for name in ['SF1_QA_APPROACH','SF1_QA_CONTEXT']:
        if name in D.get('camera_ground_z',{}):
            ob=bpy.data.objects[name];target=P(6,0,13.1 if name=='SF1_QA_APPROACH' else 16.35)
            if name in D.get('camera_uv',{}):ob.location=P(*D['camera_uv'][name],ob.location.z)
            ob.location.z=D['camera_ground_z'][name]+1.65;ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler()
            ob['eye_height_basis']='1.65m above original visible near-horizontal source triangle; corrected from over-extrapolated apron plane'
    if not bpy.data.objects.get('SF1_QA_DOOR_OPEN'):camera('SF1_QA_DOOR_OPEN',6.04,2.07,D['landing_z']+1.65,(6.01,-.7,12.6),24)
    s.camera=bpy.data.objects['SF1_QA_ENTRY'];configure_render();bpy.context.view_layer.update()
    native=OUT/f'native/{version}_stadelhofen_entry.blend';assert not native.exists()
    bpy.ops.wm.save_as_mainfile(filepath=str(native),compress=True)
    bpy.data.libraries.write(str(OUT/f'native/{version}_author_increment.blend'),{collection_authored},fake_user=True,compress=True)
    write('derived/crop_manifest.json',dict(base_native=D['base_native'],base_sha256=D['base_sha256'],cuts=crops,unmodified_source_collection=True,bounds_frame=dict(A=D['A'],U=D['U'],N=D['N'])))
    write(f'evidence/{tag}/construction.json',dict(version=version,native=str(native),sha256=sha(native),increment=f'native/{version}_author_increment.blend',increment_sha256=sha(OUT/f'native/{version}_author_increment.blend'),authored_objects=[dict(name=o.name,role=o.get('sf1_role'),type=o.type,vertices=len(o.data.vertices) if o.type=='MESH' else None,faces=len(o.data.polygons) if o.type=='MESH' else None,mesh_digest=mesh_digest(o.data) if o.type=='MESH' else None) for o in collection_authored.objects],photo_changes=[r['base_object'] for r in crops],source_code_sha256=sha(__file__),build_input_sha256=sha(OUT/'derived/build_input.json'),process_id=os.getpid(),visually_accepted=False))
    print('SF1_CONSTRUCTION_SAVED',str(native),flush=True)
