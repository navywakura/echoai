"""B16: sequential repair using local level gains and faithful counterexamples."""
import fcntl
import json
import subprocess
import sys
from types import FunctionType, SimpleNamespace

from seed import s6b15 as previous, s6b16_prompt as prompts
from echo_arc import repair_outcomes as outcomes

b, model = previous.b, previous.model
REPO, NATIVE, OLD = previous.REPO, previous.NATIVE, previous.OLD
ROOT = REPO / 'lab/seed/s6b16-20261004'
PREVIOUS = previous.ROOT
AUDIT = REPO / 'lab/seed/s6b15-micro-audit-20261004/audit.json'
ORIGINAL_VERIFY, ORIGINAL_PLAY = previous.ORIGINAL_VERIFY, previous.ORIGINAL_PLAY
SOURCES = list(json.loads((PREVIOUS / 'profile.json').read_text())['sources']) + [
    'seed/s6b15_micro_audit.py', 'echo_arc/repair_outcomes.py', 'seed/s6b16_prompt.py',
    'seed/s6b16.py', 'seed/s6b16_micro.py', 'seed/s6b16_qualification.py',
    'tests/test_s6b16_policy.py', 'tests/test_s6b16_runner.py', 'docs/ECHO45-S6-B16-DESIGN.md']


def configuration():
    return dict(previous.ORIGINAL_CONFIG(), condition='S6-B16',
        operator_binding=True, applicability_scope='selected development readings',
        fixed_control='B15 fixed cyclic operators with shared applicability and family pause',
        random_control='18 pilot samples uniform within fixed scheduled operator',
        selector_credit='B15 actual measured operator; incorporated gain excluded by base hash',
        refinement_target='own V3/V4 proposal with any local level gain; bounded three descendants; family pause retained',
        feedback='largest level gain in first two contrasts; losses retained; named paired features',
        micro=dict(arms=['previous', 'updated'], seeds=[740101, 740117, 740129], rounds=4,
            calls=24, max_games=4000, common_first_request=True, baseline_levels=378,
            gate='>=2 aggregate A levels, zero individual regressions, exact replay in updated arm'),
        micro_proposals_in_pilot=False, mandatory_latest_receipt=True,
        previous_campaign_results_in_prompts=False)


def previous_closed():
    if not AUDIT.exists() or not (PREVIOUS / 'closed.json').exists():
        return False
    audit = json.loads(AUDIT.read_text())
    closed = json.loads((PREVIOUS / 'closed.json').read_text())
    profile = json.loads((PREVIOUS / 'profile.json').read_text())
    micro = json.loads((PREVIOUS / 'micro.json').read_text())
    if audit.get('valid') is not True or audit.get('profile_sha256') != b.sha(profile) \
            or audit.get('micro_sha256') != b.sha(micro) or audit.get('calls') != 12 \
            or audit.get('cache_records') != 1280 or micro.get('promote') is not False \
            or closed.get('result') != 'MICRO_NO_PROMOTION' or closed.get('exam_opened') is not False:
        raise RuntimeError('audited negative B15 micro closure required')
    return dict(audit_sha256=b.sha(audit), closure_sha256=b.sha(closed), profile_sha256=b.sha(profile),
                micro_sha256=b.sha(micro), prior_audit_kind=audit['audit_kind'])


def profile():
    old = json.loads((PREVIOUS / 'profile.json').read_text())
    for name, expected in old['sources'].items():
        if model.digest_file(REPO / name) != expected:
            raise RuntimeError('frozen B15 source changed: ' + name)
    for name, expected in old['native_runtime']['artifacts'].items():
        if model.digest_file(REPO / name) != expected:
            raise RuntimeError('native runtime changed')
    identity = model.identity()
    if identity != old['model']:
        raise RuntimeError('model/inference budget changed')
    validation = json.loads((ROOT / 'validation.json').read_text())
    if validation.get('valid') is not True or validation['new_games'] or validation['new_model_calls'] \
            or validation['sources'] != b.hashes() \
            or validation['tests_log_sha256'] != model.digest_file(ROOT / 'qualification/tests.log'):
        raise RuntimeError('current instrument qualification required')
    return dict(sources=b.hashes(), configuration=configuration(), model=identity,
                runtime=b.parent.capacity.previous.runtime(), native_runtime=old['native_runtime'],
                previous_closure=previous_closed(), instrument_validation_sha256=b.sha(validation))


def worker_init():
    OLD.worker_init()
    configure()


def play_one(item):
    row = ORIGINAL_PLAY(item)
    if item[1][1] in b.EXAM_SEEDS:
        row['origin'] = 'RESERVED_EXAM_S6B16'
    return row


def measurement(namespace='primary'):
    function = FunctionType(previous.measurement.__code__, dict(previous.measurement.__globals__,
                ROOT=ROOT, b=b, status=status), 'measurement', previous.measurement.__defaults__)
    return function(namespace)


def verify(measure, label, request, answer, current, before_a, before_b):
    # Reuse B15's actual-operator receipt and conservative V3 certificate.
    return previous.verify(measure, label, request, answer, current, before_a, before_b)


def audit_dispatch(command, *args, **kwargs):
    command = list(command)
    if '-m' not in command or command[command.index('-m') + 1] != 'seed.s6b13':
        raise RuntimeError('unexpected audit entry point')
    command[command.index('-m') + 1] = 'seed.s6b16'
    return subprocess.run(command, *args, **kwargs)


def status(stage, **fields):
    value = dict(at=b.now(), condition='S6-B16', stage=stage, **fields)
    b.atomic(ROOT / 'status.json', value)
    print(b.canonical(value), flush=True)


def publish(stage):
    green = False
    lines = ['# S6-B16 — refinamiento con ganancias locales de niveles', '', 'Estado: **'+stage+'**.', '',
        'B15 terminó válido y negativo: 12 propuestas, ninguna sin regresiones. B16 compara',
        'el controlador previo y el corregido en cuatro intentos secuenciales por semilla.', '']
    if (ROOT / 'micro.json').exists():
        m = json.loads((ROOT / 'micro.json').read_text())
        lines += ['Micro: ' + b.canonical({k:m[k] for k in ('valid','promote','summary')}), '']
    for phase in ('pilot','campaign'):
        if (ROOT / (phase+'.json')).exists():
            result = json.loads((ROOT / (phase+'.json')).read_text())
            lines += [phase + ': ' + b.canonical({k:result[k] for k in ('paired_A','accepted_echo','promote')}), '']
    if (ROOT / 'exam/audit.json').exists():
        exam = json.loads((ROOT / 'exam/audit.json').read_text())
        green = exam['green'] and set(exam['checks']) == {'B1','B2','B3','B4','B5'} and all(exam['checks'].values())
        lines += ['Examen: ' + b.canonical(exam['checks']), '']
    lines += ['S6 verde: **'+('sí' if green else 'no')+'**. Las mejoras locales no sustituyen V3 ni V4.', '',
        '[Contrato](ECHO45-S6-B16-DESIGN.md) · [Estado](../lab/seed/s6b16-20261004/status.json).', '']
    (REPO / 'docs/ECHO45-S6-B16-RESULTS.md').write_text('\n'.join(lines))
    begin,end = '<!-- S6B16-BEGIN -->','<!-- S6B16-END -->'
    block = begin+'\n**S6-B16: '+stage+'; S6 '+('verde' if green else 'abierto')+'.** '
    block += ('Micro secuencial → piloto → auditoría → campaña → auditoría → examen. '
              'B15 cerrado negativo y reconstruido. [Contrato](ECHO45-S6-B16-DESIGN.md) · '
              '[Resultado](ECHO45-S6-B16-RESULTS.md).\n'+end)
    for name in ('NOW.md','ECHO45-ECHO5-ROADMAP.md','RXLABS_STATUS.md'):
        path=REPO/'docs'/name
        text=path.read_text()
        if begin in text:
            first,rest=text.split(begin,1)
            text=first+block+rest.split(end,1)[1]
        else:
            first,rest=text.split('\n',1)
            text=first+'\n\n'+block+'\n'+rest
        row=next((line for line in text.splitlines() if '| S6 B1–B5 |' in line),None)
        if row:
            text=text.replace(row,'| '+('✅' if green else '❌')+' | S6 B1–B5 | B16: '+stage+' |',1)
        path.write_text(text)


def configure():
    b.ROOT,b.SOURCES=ROOT,list(dict.fromkeys(SOURCES))
    b.B=[(v,seed,0,2000) for v in (2,3) for seed in range(29620,29640)]
    b.EXAM_SEEDS=tuple(range(29700,29760))
    b.SEEDS,b.CAMPAIGN_SEEDS=(750101,750117,750129),(760101,)
    b.MAX_CALLS=120  # 24 calibration + 36 pilot + 60 campaign.
    model.CLI,model.TOKENIZER=NATIVE/'build/bin/llama-cli',NATIVE/'build/bin/llama-tokenize'
    model.TIMEOUT=1800
    b.prompts,b.verify,b.play_one=prompts,verify,play_one
    b.evidence=SimpleNamespace(comparison=outcomes.comparison)
    b.profile,b.config,b.status,b.publish=profile,configuration,status,publish
    b.old=SimpleNamespace(worker_init=worker_init,accounting=OLD.accounting)
    b.reserve_games=FunctionType(b.parent.reserve_games.__code__,dict(b.parent.reserve_games.__globals__,ROOT=ROOT,MAX_GAMES=b.MAX_GAMES))
    b._play=FunctionType(b.parent.play_one.__code__,dict(b.parent.play_one.__globals__,ROOT=ROOT,A=b.A,B=b.B,EXAM_SEEDS=b.EXAM_SEEDS))
    b.measurement=measurement
    b.subprocess=SimpleNamespace(run=audit_dispatch,STDOUT=subprocess.STDOUT)


def micro_gate():
    from seed import s6b16_micro
    m=json.loads((ROOT/'micro.json').read_text())
    if m.get('valid') is not True or m['profile_sha256']!=b.sha(b.integrity()) \
            or m['promote']!=s6b16_micro.gate(m['cells']):
        raise RuntimeError('micro result/gate custody mismatch')
    expected={f'micro/{arm}-{seed}/{i:03d}' for arm in s6b16_micro.ARMS for seed in s6b16_micro.SEEDS
              for i in range(s6b16_micro.ROUNDS)}
    if len(m['cells'])!=24 or {c['cell'] for c in m['cells']}!=expected:
        raise RuntimeError('missing or repeated micro calls')
    for name,digest in m['artifacts'].items():
        if model.digest_file(ROOT/name)!=digest:
            raise RuntimeError('micro artifact changed: '+name)
    for cell in m['cells']:
        if json.loads((ROOT/'micro-records'/(cell['cell']+'.json')).read_text())['summary']!=cell:
            raise RuntimeError('micro summary differs from its recorded step')
    return m['promote']


def dispatch(args):
    if args==['prepare']:
        b.prepare()
    elif args==['follow']:
        if not previous_closed():
            raise RuntimeError('B15 reconstruction and negative closure required')
        b.prepare()
        with (ROOT/'pipeline.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            if (ROOT/'closed.json').exists():
                return
            b.atomic(ROOT/'previous-audit-gate.json',previous_closed())
            b._journal=ROOT/'live/journal.jsonl'
            b._journal.parent.mkdir(exist_ok=True)
            b._journal.touch(exist_ok=True)  # The viewer stats its explicit path at startup.
            with (ROOT/'observer-process.log').open('a') as log:
                subprocess.Popen([sys.executable,str(REPO/'observe.py'),'--launch',str(b._journal)],
                                 stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            from seed import s6b16_micro
            s6b16_micro.run()
            if not micro_gate():
                b.atomic(ROOT/'closed.json',dict(at=b.now(),result='MICRO_NO_PROMOTION',s6_green=False,exam_opened=False))
                status('CLOSED',result='MICRO_NO_PROMOTION',s6_green=False)
                publish('MICRO_NO_PROMOTION')
                return
            b.follow()
    elif len(args)==2 and args[0]=='audit' and args[1] in ('pilot','campaign'):
        if not previous_closed() or not micro_gate():
            raise RuntimeError('previous closure and valid micro gate required')
        b.main(args)
    else:
        raise SystemExit('use prepare, follow, audit pilot/campaign')


def main(args):
    try:
        dispatch(args)
    except Exception as exc:
        status('BLOCKED_INSTRUMENT',reason=type(exc).__name__+': '+str(exc))
        publish('BLOCKED_INSTRUMENT')
        raise


if __name__=='__main__':
    from seed import s6b16
    s6b16.main(sys.argv[1:])
else:
    configure()
