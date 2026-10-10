"""Offline, resumable V3 batch evaluation. No LLM, learning or automatic submission.

prepare separates public inputs from labels; workers receive only public inputs;
grading happens in the parent after each fresh solver process has exited.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed, CancelledError
import ctypes
import csv
from datetime import datetime, timezone
import fcntl
import hashlib
import io
import json
import math
import os
from pathlib import Path
import platform
import re
import resource
import signal
import statistics
import subprocess
import sys
import threading
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))
sys.path.insert(0, str(ROOT))
SCHEMA = 'echo45-arc-v3-batch-1'
DEFAULT_CANDIDATE = ROOT / 'lab/seed/relational-v3-20261003/primary/candidate.json'
BAD_RUN = {'ERROR', 'TIMEOUT', 'INTERRUPTED'}


def sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key: ' + key)
        result[key] = value
    return result


def read(path):
    return json.loads(Path(path).read_text(), object_pairs_hook=_unique,
                      parse_constant=lambda s: (_ for _ in ()).throw(ValueError('nonfinite JSON')))


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp-' + str(os.getpid()))
    tmp.write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n')
    tmp.replace(path)


def now():
    return datetime.now(timezone.utc).isoformat()


def arc_grid(value):
    if type(value) not in (list, tuple) or not 1 <= len(value) <= 30:
        raise ValueError('ARC grid must have 1..30 rows')
    if type(value[0]) not in (list, tuple) or not 1 <= len(value[0]) <= 30:
        raise ValueError('ARC grid must have 1..30 columns')
    width = len(value[0])
    if any(type(row) not in (list, tuple) or len(row) != width or
           any(type(cell) is not int or not 0 <= cell <= 9 for cell in row) for row in value):
        raise ValueError('rectangular integer-colour ARC grid required')
    return [list(row) for row in value]


def public_input(task):
    from echoai.seed.refinement import solver_input
    public = solver_input(task)
    return {'train': [{'input': arc_grid(p['input']), 'output': arc_grid(p['output'])}
                      for p in public['train']],
            'test': [{'input': arc_grid(p['input'])} for p in public['test']]}


def grade(predictions, expected, *, test_outputs=None):
    n = len(expected) if expected is not None else test_outputs
    if type(n) is not int or n < 1:
        raise ValueError('positive test output count required')
    predictions = [None] * n if predictions is None else predictions
    if len(predictions) != n:
        raise ValueError('prediction count differs from test inputs')
    values = [None if p is None else arc_grid(p) for p in predictions]
    abstained = sum(p is None for p in values)
    if expected is None:
        return dict(scored=False, exact_task=None, exact_outputs=None,
                    test_outputs=n, abstained_outputs=abstained)
    exact = sum(p is not None and p == arc_grid(e) for p, e in zip(values, expected))
    return dict(scored=True, exact_task=exact == n, exact_outputs=exact,
                test_outputs=n, abstained_outputs=abstained)


def submission(rows):
    """A single V3 prediction duplicated into two slots; placeholders stay labelled."""
    out = {}
    fallbacks = 0
    for tid, row in sorted(rows.items()):
        preds = row['predictions']
        preds = [None] * row['test_outputs'] if preds is None else preds
        if len(preds) != row['test_outputs']:
            raise ValueError('prediction count differs from test inputs')
        out[tid] = []
        for pred in preds:
            fallbacks += pred is None
            value = [[0]] if pred is None else arc_grid(pred)
            out[tid].append({'attempt_1': value, 'attempt_2': value})
    return out, dict(fallback_outputs=fallbacks, fallback_grid=[[0]],
                     distinct_attempts_per_output=1, attempt_2='duplicate of attempt_1',
                     placeholders_scored_in_strict_report=False, submitted=False)


def _closure(scope, path):
    if scope not in ('development', 'public-evaluation'):
        raise ValueError('unknown evaluation scope')
    if scope == 'development':
        return None
    if path is None:
        raise PermissionError('B24 closure required before opening public evaluation')
    from seed.arc_b24_closure import validate
    return validate(Path(path))


def prepare(tasks, candidate, root, *, label, scope='development', ids=None,
            solutions=None, workers=4, budget=500000, timeout=120, b24_closure=None):
    closure = _closure(scope, b24_closure)  # Before any task directory/file is read.
    tasks, candidate, root = Path(tasks).resolve(), Path(candidate).resolve(), Path(root).resolve()
    if root.exists():
        raise ValueError('new batch directory required')
    if type(workers) is not int or not 1 <= workers <= 4:
        raise ValueError('one to four workers required')
    if type(budget) is not int or not 100 <= budget <= 20_000_000:
        raise ValueError('bounded integer work budget required')
    if isinstance(timeout, bool) or not math.isfinite(timeout) or not 0 < timeout <= 3600:
        raise ValueError('bounded per-task timeout required')
    from echoai.seed import gym
    if scope == 'development':
        gym._guard(tasks)
        if solutions is not None:
            gym._guard(solutions)
    from seed.echo45_v3 import load
    payload, _, _ = load(candidate)
    candidates = {p.stem: p for p in sorted(tasks.glob('*.json'))} if tasks.is_dir() else read(tasks)
    if not tasks.is_dir() and 'train' in candidates and 'test' in candidates:
        candidates = {tasks.stem: candidates}
    if type(candidates) is not dict or not candidates:
        raise ValueError('task directory, single task or challenge mapping required')
    selection = sorted(candidates) if ids is None else sorted(ids)
    if not selection or len(set(selection)) != len(selection) or not set(selection) <= set(candidates):
        raise ValueError('nonempty unique task id selection required')
    if any(not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', tid) for tid in selection):
        raise ValueError('invalid task id')
    if scope == 'development' and set(selection) & set(gym.split()['holdout']):
        raise PermissionError('reserved training holdout is not development')
    external = read(solutions) if solutions is not None else None
    prepared = {}
    for tid in selection:
        source = candidates[tid]
        if isinstance(source, Path):
            if scope == 'development':
                gym._guard(source)
            task = read(source)
        else:
            task = source
        public = public_input(task)
        if external is not None:
            if tid not in external:
                raise ValueError('missing external solution: ' + tid)
            expected = external[tid]
            if not isinstance(expected, list) or len(expected) != len(public['test']):
                raise ValueError('solution count differs from test inputs')
            if all('output' in p for p in task['test']) and expected != [p['output'] for p in task['test']]:
                raise ValueError('conflicting embedded and external solutions')
        elif all('output' in p for p in task['test']):
            expected = [p['output'] for p in task['test']]
        elif any('output' in p for p in task['test']):
            raise ValueError('partial solutions are not supported')
        else:
            expected = None
        expected = None if expected is None else [arc_grid(g) for g in expected]
        prepared[tid] = (public, expected, file_sha(source) if isinstance(source, Path) else sha(task))
    profile = dict(schema=SCHEMA, label=label, scope=scope, python=sys.version,
                   platform=platform.platform(), prepared_at=now(),
                   options=dict(workers=workers, budget=budget, timeout=timeout,
                                views=True, consistency=True, verification_window=32,
                                beam_width=12, learn=False, guide=False),
                   sources={**payload['sources'], 'seed/arc_v3_batch.py': file_sha(__file__),
                            'echo_arc/observe.py': file_sha(ROOT/'echo_arc/observe.py'),
                            'seed/arc_b24_closure.py': file_sha(ROOT/'seed/arc_b24_closure.py')},
                   candidate_sha256=file_sha(candidate), candidate_payload_sha256=sha(payload),
                   b24_closure=closure, tasks={})
    root.mkdir(parents=True)
    (root / 'artifacts').mkdir()
    (root / 'artifacts/candidate.json').write_bytes(candidate.read_bytes())
    for tid, (public, expected, source_sha) in prepared.items():
        save(root / f'inputs/{tid}.json', public)
        save(root / f'labels/{tid}.json', expected)
        profile['tasks'][tid] = dict(public_sha256=file_sha(root/f'inputs/{tid}.json'),
                                    labels_sha256=file_sha(root/f'labels/{tid}.json'),
                                    source_sha256=source_sha, test_outputs=len(public['test']),
                                    labelled=expected is not None)
    save(root / 'manifest.json', {'payload': profile, 'sha256': sha(profile)})
    save(root / 'status.json', dict(stage='PREPARED', tasks=len(prepared), completed=0, model_calls=0))
    return profile


def integrity(root):
    document = read(root/'manifest.json')
    p = document['payload']
    if sha(p) != document['sha256'] or p['schema'] != SCHEMA or p['python'] != sys.version:
        raise ValueError('batch manifest or interpreter changed')
    for name, digest in p['sources'].items():
        if file_sha(ROOT/name) != digest:
            raise ValueError('source changed: ' + name)
    if file_sha(root/'artifacts/candidate.json') != p['candidate_sha256']:
        raise ValueError('candidate changed')
    for tid, spec in p['tasks'].items():
        for folder, key in (('inputs', 'public_sha256'), ('labels', 'labels_sha256')):
            if file_sha(root/f'{folder}/{tid}.json') != spec[key]:
                raise ValueError(folder + ' changed: ' + tid)
    return p, document['sha256']


def solve_one(public, candidate, *, budget, journal=None):
    if any('output' in item for item in public.get('test', [])):
        raise ValueError('test label supplied to worker')
    public = public_input(public)
    from seed.echo45_v3 import load
    from seed.relational_solver import solve
    from echo_arc.observe import Journal
    t = time.perf_counter()
    p, memory, policy = load(Path(candidate))
    before = sha([memory.state(), policy.state()])
    log = Journal(journal) if journal else None
    try:
        result = solve(public, memory=memory, policy=policy, learn=False,
                       episode=p.get('next_episode', 256), session='arc-v3-batch',
                       views=True, consistency=True, verification_window=32,
                       beam_width=12, budget=budget, journal=log)
    finally:
        if log:
            log.close()
    if sha([memory.state(), policy.state()]) != before:
        raise ValueError('evaluation changed frozen memory/policy')
    status = result['status']
    try:
        predictions = None if result['predictions'] is None else [arc_grid(g) for g in result['predictions']]
    except ValueError:
        predictions = None
        status = 'INVALID_PREDICTION'
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return dict(status=status, predictions=predictions, result=result, work=result['metrics']['work'],
                solve_wall_seconds=time.perf_counter()-t, cpu_seconds=usage.ru_utime+usage.ru_stime,
                peak_rss_bytes=usage.ru_maxrss*(1 if sys.platform == 'darwin' else 1024),
                state_unchanged=True, model_calls=0)


def _worker_guard():
    """Linux child-owned deadline and parent-death signal, including parent SIGKILL."""
    if sys.platform != 'linux':
        raise RuntimeError('batch worker lifecycle requires Linux')
    parent = int(os.environ['ECHO_ARC_BATCH_PARENT_PID'])
    deadline = float(os.environ['ECHO_ARC_BATCH_DEADLINE'])
    # Called in the fresh child, never via preexec_fn in a multithreaded parent.
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(1, int(signal.SIGTERM), 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), 'PR_SET_PDEATHSIG failed')
    if os.getppid() != parent:
        os.kill(os.getpid(), signal.SIGTERM)
    signal.signal(signal.SIGALRM, signal.SIG_DFL)
    signal.setitimer(signal.ITIMER_REAL, max(.001, deadline-time.monotonic()))


def _process_identity(pid):
    try:
        fields = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
        return None if fields[0] == 'Z' else fields[19]  # Linux starttime, PID reuse guard.
    except FileNotFoundError:
        return None


class WorkerGroup:
    def __init__(self):
        self.stopping = threading.Event()
        self.lock = threading.Lock()
        self.children = set()

    @staticmethod
    def terminate(proc):
        if proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
                proc.wait(timeout=.2)
            except subprocess.TimeoutExpired:
                try: os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError: pass
                proc.wait()
            except ProcessLookupError:
                proc.wait()

    def stop(self):
        self.stopping.set()
        with self.lock:
            for proc in tuple(self.children):
                self.terminate(proc)


def _worker():
    _worker_guard()
    request = json.load(sys.stdin, object_pairs_hook=_unique)
    if set(request) != {'public', 'candidate', 'budget', 'journal', 'sources_sha256'}:
        raise ValueError('unexpected worker request fields')
    for name, digest in request['sources_sha256'].items():
        if file_sha(ROOT/name) != digest:
            raise ValueError('worker source changed: ' + name)
    response = solve_one(request['public'], request['candidate'], budget=request['budget'], journal=request['journal'])
    response['request_sha256'] = sha(request)
    print(json.dumps(response, allow_nan=False))


def _execute(root, p, profile_sha, tid, group):
    if group.stopping.is_set():
        raise CancelledError()
    spec = p['tasks'][tid]
    reservation = root/f'started/{tid}.json'
    base = dict(task_id=tid, profile_sha256=profile_sha, test_outputs=spec['test_outputs'],
                predictions=None, work=None, cpu_seconds=None, peak_rss_bytes=None, model_calls=0)
    if reservation.exists():
        previous = read(reservation)
        pid = previous.get('child_pid')
        active = _process_identity(pid) if pid else None
        if active is not None and previous.get('child_starttime') == active:
            raise RuntimeError('prior worker still active; wait for its recorded deadline')
        # Preserve unaccounted interrupted work. Never silently buy another attempt.
        base.update(status='INTERRUPTED', worker_wall_seconds=None,
                    diagnostic='prior task started without a complete receipt; not replayed')
    else:
        public = read(root/f'inputs/{tid}.json')
        if file_sha(root/f'inputs/{tid}.json') != spec['public_sha256']:
            raise ValueError('input changed before worker')
        request = dict(public=public, candidate=str(root/'artifacts/candidate.json'),
                       budget=p['options']['budget'],
                       journal=str(root/f'journals/{tid}/journal.jsonl') if p['scope']=='development' else None,
                       sources_sha256=p['sources'])
        started = time.perf_counter()
        proc = None
        try:
            with group.lock:
                if group.stopping.is_set():
                    raise CancelledError()
                save(root/f'requests/{tid}.json', request)
                record = dict(at=now(), request_sha256=sha(request), profile_sha256=profile_sha,
                              parent_pid=os.getpid(), timeout_seconds=p['options']['timeout'])
                save(reservation, record)
                proc = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '_worker'],
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                        text=True, cwd=ROOT, start_new_session=True,
                                        env={**os.environ, 'PYTHONHASHSEED':'0', 'OMP_NUM_THREADS':'1',
                                             'OPENBLAS_NUM_THREADS':'1',
                                             'ECHO_ARC_BATCH_PARENT_PID':str(os.getpid()),
                                             'ECHO_ARC_BATCH_DEADLINE':str(time.monotonic()+p['options']['timeout'])})
                group.children.add(proc)
                record.update(child_pid=proc.pid, child_starttime=_process_identity(proc.pid))
                save(reservation, record)
            stdout, stderr = proc.communicate(json.dumps(request), timeout=p['options']['timeout'])
            (root/'logs').mkdir(exist_ok=True)
            (root/f'logs/{tid}.stderr').write_text(stderr)
            if group.stopping.is_set():
                base.update(status='INTERRUPTED', diagnostic='batch cancelled; owned worker terminated')
            elif proc.returncode == -signal.SIGALRM:
                base.update(status='TIMEOUT', diagnostic='child wall limit reached; work unknown')
            else:
                if proc.returncode:
                    raise RuntimeError('worker exit ' + str(proc.returncode))
                response = json.loads(stdout, object_pairs_hook=_unique)
                if response.pop('request_sha256') != sha(request):
                    raise ValueError('worker response belongs to another request')
                if response['work'] > p['options']['budget'] or response['state_unchanged'] is not True:
                    raise ValueError('worker exceeded work limit or changed state')
                grade(response['predictions'], None, test_outputs=spec['test_outputs'])
                base.update(response)
        except CancelledError:
            raise
        except subprocess.TimeoutExpired:
            base.update(status='TIMEOUT', diagnostic='per-task wall limit reached; work unknown')
        except Exception as exc:
            base.update(status='ERROR', diagnostic=type(exc).__name__+': '+str(exc))
            (root/'logs').mkdir(exist_ok=True)
            (root/f'logs/{tid}.exception').write_text(traceback.format_exc())
        finally:
            if proc is not None:
                WorkerGroup.terminate(proc)
                for stream in (proc.stdin, proc.stdout, proc.stderr):
                    if stream: stream.close()
                with group.lock:
                    group.children.discard(proc)
        base['worker_wall_seconds'] = time.perf_counter()-started
    base['grading'] = grade(base['predictions'], read(root/f'labels/{tid}.json'),
                            test_outputs=spec['test_outputs'])
    save(root/f'results/{tid}.json', {'payload':base, 'sha256':sha(base)})
    return base


def _receipt(root, tid, profile_sha):
    doc = read(root/f'results/{tid}.json')
    row = doc['payload']
    if sha(row) != doc['sha256'] or row['profile_sha256'] != profile_sha or row['task_id'] != tid:
        raise ValueError('invalid result receipt: ' + tid)
    expected = grade(row['predictions'], read(root/f'labels/{tid}.json'), test_outputs=row['test_outputs'])
    if row['grading'] != expected:
        raise ValueError('grading receipt differs from predictions')
    return row


def _report(root, p, profile_sha, rows, *, final=False, failure=None):
    scored = [r for r in rows.values() if r['grading']['scored']]
    times = [r['worker_wall_seconds'] for r in rows.values() if r['worker_wall_seconds'] is not None]
    exact = sum(r['grading']['exact_task'] for r in scored)
    outputs = sum(r['test_outputs'] for r in scored)
    report = dict(schema=SCHEMA, profile_sha256=profile_sha, label=p['label'], scope=p['scope'],
                  tasks_total=len(p['tasks']), tasks_completed=len(rows), scored_tasks=len(scored),
                  exact_tasks=exact, exact_task_rate=exact/len(scored) if scored else None,
                  scored_test_outputs=outputs, exact_test_outputs=sum(r['grading']['exact_outputs'] for r in scored),
                  test_outputs_total=sum(s['test_outputs'] for s in p['tasks'].values()),
                  abstained_test_outputs=sum(r['grading']['abstained_outputs'] for r in rows.values()),
                  timeouts=sum(r['status']=='TIMEOUT' for r in rows.values()),
                  errors=sum(r['status']=='ERROR' for r in rows.values()),
                  interrupted=sum(r['status']=='INTERRUPTED' for r in rows.values()),
                  invalid_predictions=sum(r['status']=='INVALID_PREDICTION' for r in rows.values()),
                  instrument_clean=failure is None and not any(r['status'] in BAD_RUN for r in rows.values()),
                  complete=final and len(rows)==len(p['tasks']),
                  final_integrity_checked=final, failure=failure,
                  known_work=sum(r['work'] for r in rows.values() if r['work'] is not None),
                  tasks_with_unknown_work=sum(r['work'] is None for r in rows.values()),
                  model_calls=0, official_score=False, S6_green=False,
                  peak_worker_rss_bytes=max((r['peak_rss_bytes'] or 0 for r in rows.values()),default=0),
                  cpu_seconds=sum(r['cpu_seconds'] or 0 for r in rows.values()),
                  timing=dict(worker_seconds_total=sum(times), samples=len(times),
                              mean_seconds=statistics.mean(times) if times else None,
                              median_seconds=statistics.median(times) if times else None,
                              p90_seconds=sorted(times)[math.ceil(.9*len(times))-1] if times else None,
                              maximum_seconds=max(times) if times else None))
    save(root/'report.json', report)
    fields=('task_id','status','exact_task','exact_outputs','test_outputs','abstained_outputs',
            'work','worker_wall_seconds','cpu_seconds','peak_rss_bytes')
    output=io.StringIO();writer=csv.DictWriter(output,fieldnames=fields);writer.writeheader()
    for tid,row in sorted(rows.items()):
        flat={**row,**row['grading']};writer.writerow({f:flat.get(f) for f in fields})
    (root/'results.csv').write_text(output.getvalue())
    if report['complete'] and report['instrument_clean']:
        values,meta=submission(rows)
        save(root/'submission.json',values);save(root/'submission-metadata.json',meta)
    else:
        for name in ('submission.json', 'submission-metadata.json'):
            (root/name).unlink(missing_ok=True)
    stage = failure or ('COMPLETE' if report['complete'] and report['instrument_clean'] else
                        'COMPLETE_WITH_ERRORS' if report['complete'] else 'RUNNING')
    status=dict(stage=stage, at=now(),
                completed=len(rows),total=len(p['tasks']),exact_tasks=exact,
                timeouts=report['timeouts'],errors=report['errors'],model_calls=0)
    save(root/'status.json',status);print(json.dumps(status),flush=True)
    return report


def run(root):
    root=Path(root).resolve()
    with (root/'run.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        p = None
        rows = {}
        group = WorkerGroup()
        pool = None
        futures = {}
        handlers = {}
        def cancel(signum, frame):
            group.stopping.set()
            raise KeyboardInterrupt('batch cancellation signal ' + str(signum))
        try:
            p,profile_sha=integrity(root)
            if threading.current_thread() is threading.main_thread():
                for sig in (signal.SIGINT,signal.SIGTERM):
                    handlers[sig]=signal.signal(sig,cancel)
            rows={tid:_receipt(root,tid,profile_sha) for tid in p['tasks'] if (root/f'results/{tid}.json').exists()}
            pending=[tid for tid in p['tasks'] if tid not in rows]
            _report(root,p,profile_sha,rows)
            pool=ThreadPoolExecutor(max_workers=p['options']['workers'])
            futures={pool.submit(_execute,root,p,profile_sha,tid,group):tid for tid in pending}
            for future in as_completed(futures):
                tid=futures[future];rows[tid]=future.result()
                _report(root,p,profile_sha,rows)
            pool.shutdown(wait=True);pool=None
            integrity(root)  # No COMPLETE or usable submission before this succeeds.
            return _report(root,p,profile_sha,rows,final=True)
        except BaseException as exc:
            group.stopping.set()
            for future in futures: future.cancel()
            group.stop()
            if pool is not None:
                pool.shutdown(wait=True,cancel_futures=True);pool=None
            failure='INTERRUPTED' if isinstance(exc,(KeyboardInterrupt,CancelledError)) else 'INSTRUMENT_BLOCKED'
            if p is not None:
                for tid in p['tasks']:
                    if tid not in rows and (root/f'results/{tid}.json').exists():
                        try: rows[tid]=_receipt(root,tid,profile_sha)
                        except (ValueError,KeyError,OSError): pass  # Preserve invalid bytes; no clean report.
                _report(root,p,profile_sha,rows,failure=failure)
            else:
                for name in ('submission.json','submission-metadata.json'):
                    (root/name).unlink(missing_ok=True)
                if (root/'report.json').exists():
                    report=read(root/'report.json')
                    report.update(complete=False,instrument_clean=False,final_integrity_checked=False,failure=failure)
                    save(root/'report.json',report)
                save(root/'status.json',dict(stage=failure,at=now(),error_type=type(exc).__name__))
            raise
        finally:
            for sig,handler in handlers.items(): signal.signal(sig,handler)


def estimate(root, target_tasks):
    root=Path(root).resolve();p,profile_sha=integrity(root);r=read(root/'report.json')
    if r['profile_sha256']!=profile_sha or not r['complete'] or not r['instrument_clean']:
        raise ValueError('complete clean calibration required')
    if type(target_tasks)is not int or target_tasks<1:
        raise ValueError('positive target task count required')
    t=r['timing'];workers=p['options']['workers']
    value=dict(calibration_tasks=t['samples'],target_tasks=target_tasks,workers=workers,
               mean_projection_seconds=target_tasks*t['mean_seconds']/workers,
               p90_scenario_seconds=target_tasks*t['p90_seconds']/workers,
               per_task_limit_seconds=p['options']['timeout'],
               timeout_budget_seconds=math.ceil(target_tasks/workers)*p['options']['timeout'],
               confidence_interval=False, note='Empirical scenarios, not bounds; task mix, CPU contention and batch overhead may differ.')
    save(root/f'estimate-{target_tasks}.json',value)
    return value


def main():
    if sys.argv[1:]==['_worker']:
        _worker();return
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    prep=sub.add_parser('prepare');prep.add_argument('--tasks',type=Path,required=True)
    prep.add_argument('--candidate',type=Path,default=DEFAULT_CANDIDATE)
    prep.add_argument('--root',type=Path,required=True);prep.add_argument('--label',required=True)
    prep.add_argument('--scope',choices=('development','public-evaluation'),default='development')
    prep.add_argument('--ids',type=Path);prep.add_argument('--solutions',type=Path)
    prep.add_argument('--workers',type=int,default=4);prep.add_argument('--budget',type=int,default=500000)
    prep.add_argument('--timeout',type=float,default=120);prep.add_argument('--b24-closure',type=Path)
    running=sub.add_parser('run');running.add_argument('--root',type=Path,required=True)
    estimating=sub.add_parser('estimate');estimating.add_argument('--root',type=Path,required=True)
    estimating.add_argument('--target-tasks',type=int,required=True)
    args=vars(parser.parse_args());command=args.pop('command')
    if command=='prepare':
        args['ids']=read(args['ids']) if args['ids'] else None
        p=prepare(**args);print(json.dumps({'prepared':len(p['tasks']),'root':str(args['root'])}))
    elif command=='run':
        report=run(**args)
        if not report['instrument_clean']:sys.exit(2)
    else:
        print(json.dumps(estimate(**args),indent=2))


if __name__=='__main__':
    main()
