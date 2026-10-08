"""Read-only diagnosis of the frozen V2 guide, receipts and existing results."""
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
import json
import statistics
import sys

REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO.parent))
from seed.echo45_grid_v2 import load
from seed.integration_campaign import read,save,file_sha
from seed.arc_memory import sha
from echoai.seed import gym,dsl
from echoai.seed.refinement import solver_input

ROOT=REPO/'lab/seed/capacity-forensics-20261002'


def describe(numbers):
    return {'min':min(numbers),'median':statistics.median(numbers),'max':max(numbers),'mean':statistics.mean(numbers)}


def main():
    if ROOT.exists():raise ValueError('new forensic output required')
    model=REPO/'lab/seed/integration-v2-20261002/candidate.json'
    p,lib,memory,guides=load(model)
    exact=Counter();feature_counts=[];signature_labels=defaultdict(set)
    features=set();programs=set()
    for payload in memory.payloads.values():
        task={'train':payload['demonstrations']}
        f=guides[65536].features(task);feature_counts.append(len(f));features.update(f)
        labels={step[0] for step in payload['program']} & set(guides[65536].names)
        signature_labels[f].add(tuple(sorted(labels)))
        for feature in f:
            for label in labels:exact[feature,label]+=1
        programs.add(sha(payload['program']))
    bank={}
    for units,g in guides.items():
        owners=defaultdict(set)
        for pair in exact:
            for i in g._indices(*pair):owners[i].add(pair)
        bank[str(units)]={'slots':units,'nonzero':sum(v>0 for v in g.weights),
           'occupancy':sum(v>0 for v in g.weights)/units,'max_weight':max(g.weights),
           'saturated_255':sum(v==255 for v in g.weights),'counter_mass':sum(g.weights),
           'cross_key_shared_slots':sum(len(keys)>1 for keys in owners.values()),
           'distinct_key_excess_placements':sum(len(keys)-1 for keys in owners.values()),
           'units_bytes':len(g.weights)}
    result={'candidate_sha256':sha(p),'training_receipts':len(memory.actor.diary),
      'unique_programs':len(programs),'guide_names':len(guides[65536].names),
      'distinct_features':len(features),'distinct_feature_label_keys':len(exact),
      'weighted_key_updates':sum(exact.values()),'hashes_per_key':8,
      'features_per_training_task':describe(feature_counts),
      'signature_collisions_before_hash':sum(len(v)>1 for v in signature_labels.values()),
      'banks':bank,'cohorts':{},'new_runs':0,'sources':{f:file_sha(REPO/f) for f in
      ('seed/capacity_forensics.py','seed/kenyon_capacity.py','seed/integrated_grid_v2.py','seed/arc_memory.py')}}
    for name,folder in (('development','integration-v2-20261002'),('followup','integration-followup-20261002/run')):
        profile=read(REPO/'lab/seed'/folder/'profile.json');rows=[]
        for key,record in profile['tasks'].items():
            task=solver_input(read(gym.POOLS[record['pool']]/(record['id']+'.json')))
            f=guides[65536].features(task)
            exact_scores={name:8*sum(exact[feature,name] for feature in f) for name in guides[65536].names}
            ideal=sorted(exact_scores,key=lambda n:(-exact_scores[n],n))
            ranks={n:sorted(g.names,key=lambda name:(-sum(g.weights[i] for feature in f for i in g._indices(feature,name)),name)) for n,g in guides.items()}
            out={a:read(REPO/'lab/seed'/folder/'primary'/a/(key.replace('/','-')+'.json')) for a in
                 ('v2','v2_640','v2_65536','v2_no_guide','v2_no_memory')}
            truth=out['v2']['result']
            rows.append({'task':key,'feature_count':len(f),'known_features':sum(x in features for x in f),
              'top1_65k_eq_500k':ranks[65536][0]==ranks[500000][0],
              'top10_65k_eq_500k':ranks[65536][:10]==ranks[500000][:10],
              'top1_ideal':{str(n):ranks[n][0]==ideal[0] for n in ranks},
              'predictions_65k_eq_500k':out['v2_65536']['result']['predictions']==truth['predictions'],
              'correct':out['v2']['correct'],'verified_programs':truth['verified_programs'],
              'memory_reads':truth['metrics']['memory_reads'],'memory_verified':truth['metrics']['memory_verified'],
              'different_work_65k_500k':out['v2_65536']['result']['metrics']['primitive_calls']!=truth['metrics']['primitive_calls'],
              'winning_program':truth['program'],
              'unsupported_winning_steps':[s[0] for s in truth['program'] or () if s[0] not in guides[65536].names]})
        result['cohorts'][name]={'tasks':len(rows),'feature_counts':describe([r['feature_count'] for r in rows]),
          'empty_features':sum(r['feature_count']==0 for r in rows),
          'verified_any':sum(r['verified_programs']>0 for r in rows),'correct':sum(r['correct'] for r in rows),
          'memory_reads':sum(r['memory_reads'] for r in rows),'memory_verified':sum(r['memory_verified'] for r in rows),
          'same_top1_65k_500k':sum(r['top1_65k_eq_500k'] for r in rows),
          'same_top10_65k_500k':sum(r['top10_65k_eq_500k'] for r in rows),
          'same_predictions_65k_500k':sum(r['predictions_65k_eq_500k'] for r in rows),
          'different_work_65k_500k':sum(r['different_work_65k_500k'] for r in rows),
          'rows':rows}
    ROOT.mkdir(parents=True)
    save(ROOT/'result.json',result)
    save(ROOT/'protected-before.json',{f:file_sha(REPO/f) for f in read(REPO/'lab/seed/integration-closure-20261002/protected-before.json')})
    print(json.dumps({**{k:v for k,v in result.items() if k not in ('sources','cohorts')},
         'cohorts':{k:{a:b for a,b in v.items() if a!='rows'} for k,v in result['cohorts'].items()}},indent=2))


if __name__=='__main__':main()
