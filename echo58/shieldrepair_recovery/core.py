"""Small, stdlib-only preservation and exact decompressed-prefix checks."""
import json
from pathlib import Path
import zlib
from ..shield2.custody import digest,sha


def require(ok,message):
 if not ok:raise ValueError(message)


def extract_prefix(path):
 raw=Path(path).read_bytes();decoder=zlib.decompressobj(16+zlib.MAX_WBITS)
 data=decoder.decompress(raw,32*1024*1024)
 require(not decoder.unconsumed_tail,'oversize trace')
 complete,separator,tail=data.rpartition(b'\n')
 if not separator:complete=b'';tail=data
 rows=[];previous='0'*64
 for line in complete.splitlines():
  row=json.loads(line.decode('utf-8'));payload={k:v for k,v in row.items() if k!='hash'}
  require(row['prev']==previous and digest(payload)==row['hash'],'invalid recorded prefix chain')
  if not rows:require(row['data']['kind']=='episode_header','missing header')
  else:require(row['data']['step']==len(rows)-1,'prefix step order')
  previous=row['hash'];rows.append(row)
 require(bool(rows),'no valid recorded header')
 return {'rows':rows,'gzip_complete':decoder.eof,'valid_records':len(rows),
         'valid_transitions':len(rows)-1,'tail_bytes':len(tail),'tail_sha':__import__('hashlib').sha256(tail).hexdigest()}


def compare_prefix(original,reconstructed):
 require(len(reconstructed)>=len(original),'reconstruction shorter than saved prefix')
 for index,row in enumerate(original):require(row==reconstructed[index],'recorded prefix mismatch at row '+str(index))
 return {'records_equal':len(original),'transitions_equal':max(0,len(original)-1),
         'state_action_reward_evidence':len(original)>1}


def verify_files(root,files):
 for name,expected in files.items():require(sha(Path(root)/name)==expected,'immutable original file '+name)


def resource_caps():
 """Fail closed unless the invoking unit caps this process at one CPU and 2 GiB."""
 import os
 group=next(line.split(':',2)[2] for line in Path('/proc/self/cgroup').read_text().splitlines() if line.startswith('0::'))
 path=Path('/sys/fs/cgroup')/group.lstrip('/')
 cpu=(path/'cpu.max').read_text().split();memory=(path/'memory.max').read_text().strip();swap=(path/'memory.swap.max').read_text().strip()
 require(cpu[0]!='max' and int(cpu[0])<=int(cpu[1]),'one-CPU cgroup required')
 require(memory!='max' and int(memory)<=2*1024**3,'memory cgroup <=2GiB required')
 require(swap=='0','swap disabled for recovery cgroup')
 names=('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')
 require(all(os.environ.get(name)=='1' for name in names),'native thread limits must all be1')
 return {'cgroup':str(path),'cpu_max':cpu,'memory_max':memory,'memory_swap_max':swap,
         'thread_environment':{name:os.environ[name] for name in names},
         'memory_peak_before':(path/'memory.peak').read_text().strip()}
