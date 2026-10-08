from setuptools import setup,find_packages
from pathlib import Path
import json
root=Path(__file__).parent
files=list(json.loads((root/'SOURCE-MANIFEST.json').read_text())['files'])+['SOURCE-MANIFEST.json']
packages=['echoai']+['echoai.'+p for p in find_packages('.') if all(x.isidentifier() for x in p.split('.'))]
setup(packages=packages,package_dir={'echoai':'.'},package_data={'echoai':files},include_package_data=False)
