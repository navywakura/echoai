import copy
import json
from pathlib import Path
import tempfile
import unittest

from echoai.seed import sandbox
from echoai.seed.refinement import RefinementLibrary, solver_input
from seed.arc_memory import ArcMemory, sha
from seed.integrated_grid_v2 import solve as v2
from seed.echo45_grid import load, predict, ENGINE_SOURCES, REPO
from seed.integration_campaign import file_sha
from tests.test_arc_integration import task


class Deployment(unittest.TestCase):
    def test_v2_deterministic_and_no_private_labels(self):
        a=task();b=copy.deepcopy(a);b['test'][0]['output']=[[9]]
        first=v2(a,max_trials=120)
        self.assertEqual(first,v2(b,max_trials=120))
        self.assertLessEqual(first['metrics']['trials'],120)

    def test_read_limit_rejects_unbounded_values(self):
        memory=ArcMemory()
        for n in (-1,0,257):
            with self.assertRaises(ValueError):memory.candidates(solver_input(task()),n)

    def test_false_receipt_never_becomes_output(self):
        lib=RefinementLibrary();m=ArcMemory();m.remember(task(),[('rot90',)],lib,'source')
        other=task((('flipud',),))
        r=v2(other,lib,memory=m,max_trials=160)
        self.assertEqual(r['metrics']['memory_verified'],0)
        self.assertEqual(r['predictions'],[p['output'] for p in other['test']])

    def test_load_and_predict_rejects_altered_artifact(self):
        sandbox._set_level('S2v')
        lib=RefinementLibrary();m=ArcMemory();m.remember(task(),[('rot90',)],lib,'source')
        payload={'schema':1,'level':'S2v','library':{'concepts':{},'prior':{}},'memory':m.state(),
          'guides':{},'search':{'max_trials':120,'max_depth':4,'beam_width':12,'verification_window':96},
          'sources':{f:file_sha(REPO/f) for f in ENGINE_SOURCES}}
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'model.json';path.write_text(json.dumps({'sha256':sha(payload),'payload':payload}))
            candidate=load(path);result=predict(task(),candidate,guide_units=None)
            self.assertEqual(result['result']['predictions'],[p['output'] for p in task()['test']])
            payload['memory']['diary'][0]['checked']='changed'
            # Even a recomputed outer checksum cannot forge replay consistency.
            path.write_text(json.dumps({'sha256':sha(payload),'payload':payload}))
            with self.assertRaises(ValueError):load(path)


if __name__=='__main__':unittest.main()
