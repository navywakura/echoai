"""Incident preservation and exact prefix checks; no physical simulator."""
import gzip
import json
from pathlib import Path
import tempfile
import unittest
from echoai.echo58.shield2.custody import canonical,digest,sha
from echoai.echo58.shieldrepair_recovery.core import extract_prefix,compare_prefix,verify_files


def records(n=2):
 prev='0'*64;out=[]
 for i in range(n):
  row={'prev':prev,'data':{'kind':'episode_header','identity':{'seed':1}} if i==0 else {'step':i-1,'action':[0.,0.],'cost':0}}
  row['hash']=digest(row);prev=row['hash'];out.append(row)
 return out


class RecoveryTests(unittest.TestCase):
 def test_truncated_gzip_recovers_complete_valid_lines(self):
  rows=records(3);blob=gzip.compress(''.join(canonical(r)+'\n' for r in rows).encode())
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'trace.gz';p.write_bytes(blob[:-8]);result=extract_prefix(p)
   self.assertEqual(result['rows'],rows);self.assertFalse(result['gzip_complete'])
   self.assertEqual(result['valid_transitions'],2)

 def test_header_only_is_not_transition_evidence(self):
  row=records(1)[0]
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'trace.gz';p.write_bytes(gzip.compress((canonical(row)+'\n').encode())[:-8])
   self.assertEqual(extract_prefix(p)['valid_transitions'],0)

 def test_incomplete_last_line_is_preserved_as_tail_metadata(self):
  first=records(1)[0];raw=(canonical(first)+'\n{"prev":').encode()
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'trace.gz';p.write_bytes(gzip.compress(raw)[:-8]);out=extract_prefix(p)
   self.assertEqual(out['rows'],[first]);self.assertGreater(out['tail_bytes'],0)

 def test_corrupted_hash_is_rejected_not_ignored(self):
  rows=records();rows[1]['data']['cost']=1
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'trace.gz';p.write_bytes(gzip.compress(''.join(canonical(r)+'\n' for r in rows).encode()))
   with self.assertRaises(ValueError):extract_prefix(p)

 def test_exact_prefix_required_including_data_and_chain(self):
  old=records(2);compare_prefix(old,records(3))
  changed=records(3);changed[1]['data']['action']=[.1,0.]
  with self.assertRaises(ValueError):compare_prefix(old,changed)
  with self.assertRaises(ValueError):compare_prefix(old,records(1))

 def test_completed_file_snapshot_detects_mutation(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);p=root/'receipt.json';p.write_text('original');files={'receipt.json':sha(p)}
   verify_files(root,files);p.write_text('changed')
   with self.assertRaises(ValueError):verify_files(root,files)

if __name__=='__main__':unittest.main()
