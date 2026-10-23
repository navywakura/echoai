"""Explicit public interface to the local ECHO-5 engine; no engine copies."""
from pathlib import Path
import sys

BASE=Path(__file__).resolve().parents[2]
SRC=BASE/'simulation/src'
if str(SRC) not in sys.path:sys.path.insert(0,str(SRC))
import echo5
if Path(echo5.__file__).resolve().parent!=SRC/'echo5':raise RuntimeError('wrong echo5 source')
from echo5 import transfer_independent as data
from echo5.budget import Budget
from echo5.solver import solve
from echo5.programs import execute
from echo5.trace import Recorder,verify_journal

BEAMS=(24,8,4,48)
LIMIT=2_000_000


def config(beam):
 if type(beam) is not int or beam not in BEAMS:raise ValueError('unregistered beam')
 return {'max_depth':4,'beam_width':beam,'max_candidates':12000,'grammar':None,
         'strategy':'certified','ranking_bound':True}


def actor(task,beam,journal=None):
 if type(task) is not dict or set(task)!={'train','test'}:raise ValueError('public task only')
 if any(type(q) is not dict or set(q)!={'input'} for q in task['test']):raise ValueError('query labels forbidden')
 if any(type(d) is not dict or set(d)!={'input','output'} for d in task['train']):raise ValueError('demonstrations only')
 return solve(task,budget=LIMIT,library=None,learn=False,cache_policy='interned',
              synthesis=config(beam),journal=journal)
