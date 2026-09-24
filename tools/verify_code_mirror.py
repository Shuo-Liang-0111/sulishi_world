"""Verify a clean, same-commit code-only mirror; never copy or delete assets."""
from pathlib import Path
import argparse,datetime,hashlib,json,os,subprocess

parser=argparse.ArgumentParser()
parser.add_argument('--mirror',type=Path,required=True)
parser.add_argument('--receipt',type=Path,required=True)
args=parser.parse_args()
source=Path(__file__).resolve().parents[1];mirror=args.mirror.resolve()
assert source!=mirror and not source.is_relative_to(mirror) and not mirror.is_relative_to(source)
expected='https://github.com/Shuo-Liang-0111/sulishi_world'

def git(root,*args):
    return subprocess.check_output(['git',*args],cwd=root).decode('utf-8').strip()

heads=[]
for root in [source,mirror]:
    assert git(root,'remote','get-url','origin').removesuffix('.git')==expected
    assert git(root,'branch','--show-current')=='main'
    assert not git(root,'status','--porcelain'),'Worktree is not clean: '+str(root)
    heads.append(git(root,'rev-parse','HEAD'))
assert heads[0]==heads[1],'Mirror has a different commit'
files=subprocess.check_output(['git','ls-files','-z'],cwd=source).decode('utf-8').rstrip('\0').split('\0')
mirror_files=subprocess.check_output(['git','ls-files','-z'],cwd=mirror).decode('utf-8').rstrip('\0').split('\0')
assert files==mirror_files
forbidden={'.blend','.blend1','.glb','.gltf','.bin','.png','.jpg','.jpeg','.exr','.hdr','.zip','.7z','.mp4','.fbx'}
entries=[];crlf_only=[];totals=[0,0]
for name in files:
    assert Path(name).suffix.lower() not in forbidden,name
    blobs=[]
    for i,root in enumerate([source,mirror]):
        path=(root/name).resolve()
        assert path.is_relative_to(root) and path.is_file(),name
        blob=path.read_bytes();assert len(blob)<1_000_000 and b'\0' not in blob,name
        blob.decode('utf-8');blobs.append(blob);totals[i]+=len(blob)
    assert blobs[0].replace(b'\r\n',b'\n')==blobs[1].replace(b'\r\n',b'\n'),name
    if blobs[0]!=blobs[1]:crlf_only.append(name)
    entries.append(dict(file=name,source_sha256=hashlib.sha256(blobs[0]).hexdigest(),
                        mirror_sha256=hashlib.sha256(blobs[1]).hexdigest()))
actual=set()
for directory,dirs,names in os.walk(mirror):
    if Path(directory)==mirror:dirs[:]=[d for d in dirs if d!='.git']
    actual.update((Path(directory)/name).relative_to(mirror).as_posix() for name in names)
assert actual==set(files),'Unexpected mirror files: '+str(sorted(actual-set(files)))
subprocess.run(['git','fsck','--full','--no-reflogs'],cwd=mirror,check=True,capture_output=True)
receipt=args.receipt.resolve()
assert receipt.is_relative_to(source/'evidence')
record=dict(verified_at=datetime.datetime.now().astimezone().isoformat(),commit=heads[0],
    source=str(source),mirror=str(mirror),remote=expected,tracked_files=len(files),
    source_bytes=totals[0],mirror_bytes=totals[1],crlf_only=crlf_only,
    other_content_differences=[],extra_files=[],git_fsck_exit_code=0,
    scene_assets_copied=False,complete_scene_backup=False,files=entries)
receipt.parent.mkdir(parents=True,exist_ok=True)
receipt.write_text(json.dumps(record,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in record.items() if k not in ['files','crlf_only']},indent=2))
