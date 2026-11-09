"""Explicit N4 build binding. Reading a binding never builds or launches it."""
import argparse
import json
from pathlib import Path
from m3_source_preflight import ROOT,sha,write
from m3_runtime_layout import matched

SOURCES=('tools/m3_n4_peer/main.cpp','tools/m3_n4_peer/CMakeLists.txt','tools/m3_n4_fixture.py')


def peer_path(name):
    return 'build/m3-n4-peer/m3_n4_peer' if name=='baseline' else 'build/m3-n4-'+name+'-peer/m3_n4_peer'


def sdk_files(root,sdk):
    root=Path(root);base=root/sdk
    files=[base/'bin/robotweax-journal-worker',*sorted((base/'lib').glob('lib*.a')),*sorted((base/'include').rglob('*.hpp'))]
    if len(files)<3 or not list((base/'lib').glob('lib*.a')) or not list((base/'include').rglob('*.hpp')):raise ValueError('incomplete installed SDK binding')
    return {str(p.relative_to(root)):sha(p) for p in files}


def create_binding(root,sdk,peer,worker,provider):
    root=Path(root).resolve();sdk=Path(sdk).resolve();peer=Path(peer).resolve();worker=Path(worker).resolve();provider=Path(provider).resolve()
    if worker!=sdk/'bin/robotweax-journal-worker':raise ValueError('worker is outside selected SDK')
    if provider!=root/'install/srt-m0/lib/librobotweax-srt.a':raise ValueError('provider is not the pinned installed archive')
    relative=str(sdk.relative_to(root));files=sdk_files(root,relative)
    for p in [peer,provider,*[root/s for s in SOURCES]]:files[str(p.relative_to(root))]=sha(p)
    return dict(schema_version=1,sdk=relative,peer=str(peer.relative_to(root)),worker=str(worker.relative_to(root)),provider=str(provider.relative_to(root)),files=files,
        scope='post-build fixture bytes and selected SDK headers/archives/worker/provider/source; not runtime qualification')


def native_layout(root,name):
    root=Path(root);layout=matched(root,name);peer=peer_path(name)
    binding=None
    if name!='baseline':
        path=root/Path(peer).parent/'fixture-binding.json'
        if not path.is_file():raise ValueError('matched N4 peer binding missing; isolated fixture build required')
    inventory={p:sha(root/p) for p in (peer,layout['sdk']+'/bin/robotweax-journal-worker',layout['sdk']+'/lib/librobotweax_srt_bridge_endpoint.a',layout['sdk']+'/lib/librobotweax_srt_bridge_transport.a','install/srt-m0/lib/librobotweax-srt.a')}
    if name!='baseline':
        binding=json.loads(path.read_text())
        expected=create_binding(root,root/layout['sdk'],root/peer,root/layout['sdk']/'bin/robotweax-journal-worker',root/'install/srt-m0/lib/librobotweax-srt.a')
        if binding!=expected:raise ValueError('stale or mismatched N4 fixture binding')
        inventory.update(binding['files'])
    return dict(layout=layout,peer=peer,worker=layout['sdk']+'/bin/robotweax-journal-worker',runtime_sha256=inventory,binding=binding)


def main():
    p=argparse.ArgumentParser(description='Post-build metadata only; never launches the fixture')
    for key in ('sdk','peer','worker','provider','out'):p.add_argument('--'+key,required=True,type=Path)
    a=p.parse_args();write(a.out,create_binding(ROOT,a.sdk,a.peer,a.worker,a.provider))


if __name__=='__main__':main()
