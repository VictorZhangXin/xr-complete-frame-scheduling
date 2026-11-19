import sys,subprocess,json,platform
from pathlib import Path
ROOT=Path(__file__).resolve().parent
if sys.version_info[:2]!=(3,12):raise RuntimeError('Expected Python 3.12')
import numpy,scipy,matplotlib
packages=(numpy,scipy,matplotlib)
for module in packages:
    if not Path(module.__file__).resolve().is_relative_to(Path(sys.prefix).resolve()):raise RuntimeError('Dependency escaped fresh environment')
record={'python':sys.version,'prefix':sys.prefix,'platform':platform.platform(),'packages':{m.__name__:{'version':m.__version__,'path':m.__file__} for m in packages},'commands':[]}
freeze=subprocess.run([sys.executable,'-m','pip','freeze'],check=True,text=True,capture_output=True)
(ROOT/'requirements-lock.txt').write_text(freeze.stdout,encoding='utf-8')
for args in (['tests.py'],['-O','tests.py'],['test_loop.py'],['-O','test_loop.py'],['test_revision.py'],['-O','test_revision.py']):
    proc=subprocess.run([sys.executable,*args],cwd=ROOT,capture_output=True,text=True)
    filename='fresh_'+('_'.join(args).replace('.py','').replace('-',''))+'.log'
    (ROOT/'review'/filename).write_text(proc.stdout+proc.stderr,encoding='utf-8')
    record['commands'].append({'args':args,'exit_code':proc.returncode,'log':filename})
    if proc.returncode:raise RuntimeError(filename)
(ROOT/'review/fresh_environment.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print('Fresh environment and six test commands passed',flush=True)
