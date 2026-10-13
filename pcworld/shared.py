"""One-generation, witnessed candidate recipes shared between development tasks.

This is a supervisor-owned, append-only ReceiptStore, never a rule of universal
correctness. Keep its authority and donor runs outside candidate mounts. Donors
must remain available and audit under the current frozen implementation. No
candidate execution, final-test payload or inferred/generalized prose is copied.

The public API is SharedConceptLibrary(path), publish_from_run(run_dir, task_id,
arm, author_agent_id), lookup(task) and identity(). Both publication and lookup
return JSON cards (lookup: zero or one). The journal retains the full normalized
AST and compatibility contract; cards omit these redundant fields. Integrity or
donor failures raise ValueError/ReceiptError/OSError; incompatibility returns [].
"""
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import stat

from .receipts import ReceiptStore, ReceiptIntegrityError, canonical, digest
from .snapshots import SnapshotStore


SCHEMA = 'pcworld.shared.v1'
MAX_LESSONS = 128
MAX_SOURCE_BYTES = 4096
MAX_AST_BYTES = 65536
MAX_LESSON_BYTES = 98304
MAX_CARD_BYTES = 6000
MAX_DONOR_BYTES = 32 * 1024 * 1024
_HEADER = {'kind': 'shared_library', 'schema': SCHEMA}
_CONTRACT_FIELDS = ('family', 'property', 'checker', 'description', 'input_schema',
                    'input_json_schema', 'preconditions')
_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z')


def _identifier(value):
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise ValueError('invalid bounded task/author identifier')
    return value


def _bounded(value, limit, label):
    if len(canonical(value)) > limit:
        raise ValueError(label + ' exceeds byte limit')
    return value


def _file(path, maximum):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > maximum:
        raise ReceiptIntegrityError('missing, linked or oversized evidence file: ' + path.name)


def _json(path):
    _file(path, MAX_DONOR_BYTES)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        raw = stream.read(MAX_DONOR_BYTES + 1)
    if len(raw) > MAX_DONOR_BYTES:
        raise ValueError('oversized donor JSON')
    return json.loads(raw)


def _custody(path, maximum=MAX_DONOR_BYTES):
    # Check before ReceiptStore's constructor: missing custody must never rekey.
    _file(path / 'receipts/receipts.jsonl', maximum)
    _file(path / 'authority/authority.json', MAX_DONOR_BYTES)
    return ReceiptStore(path / 'receipts', path / 'authority')


def _contract(task):
    if not isinstance(task, dict) or any(k not in task for k in _CONTRACT_FIELDS):
        raise ValueError('complete public repair contract required')
    value = {k: task[k] for k in _CONTRACT_FIELDS}
    if (not isinstance(value['family'], str) or
            value['property'] != 'repair.' + value['family'] or
            any(not isinstance(value[k], str) or not value[k]
                for k in ('checker', 'description', 'input_schema')) or
            not isinstance(value['input_json_schema'], dict) or
            not isinstance(value['preconditions'], list)):
        raise ValueError('invalid public repair contract')
    return json.loads(canonical(_bounded(value, 16384, 'public contract')))


def _source(source):
    if not isinstance(source, str) or not source or len(source.encode()) > MAX_SOURCE_BYTES:
        raise ValueError('source exceeds candidate recipe limit')
    try:
        tree = ast.dump(ast.parse(source), include_attributes=False)
    except (SyntaxError, ValueError, RecursionError) as exc:
        raise ValueError('candidate recipe must have a valid Python AST') from exc
    if len(tree.encode()) > MAX_AST_BYTES:
        raise ValueError('AST exceeds candidate recipe limit')
    return {'source': source, 'source_sha256': hashlib.sha256(source.encode()).hexdigest(),
            'ast': tree, 'ast_sha256': hashlib.sha256(tree.encode()).hexdigest()}


def _card(lesson):
    card = {k: v for k, v in lesson.items() if k not in ('ast', 'contract')}
    return json.loads(canonical(_bounded(card, MAX_CARD_BYTES, 'safe lesson card')))


def _derive(run_dir, task_id, arm, author_agent_id):
    """Rebuild only whitelisted, nonfinal evidence from a freshly audited donor."""
    _identifier(task_id)
    _identifier(author_agent_id)
    if arm not in ('S', 'I2', 'F', 'E'):
        raise ValueError('unknown donor arm')
    run = Path(run_dir).resolve(strict=True)
    if len(str(run).encode()) > 1024:
        raise ValueError('donor path exceeds provenance bound')
    root = _custody(run)
    roots = root.records
    if len(roots) != 2 or roots[0]['body'].get('kind') != 'run_contract':
        raise ValueError('completed donor run contract required')
    run_contract = roots[0]['body']
    # One-generation acquisition only; check BEFORE lazy audit, which itself
    # may inspect shared libraries. This also prevents cyclic donor recursion.
    if 'shared_library' in run_contract:
        raise ValueError('shared-library donors cannot publish another generation')
    tasks = _json(run / 'tasks.json')
    report = _json(run / 'result.json')
    if (digest(tasks) != run_contract.get('tasks_sha256') or
            roots[1]['body'].get('kind') != 'run_result' or
            digest(report) != roots[1]['body'].get('result_sha256')):
        raise ValueError('donor task/result custody mismatch')
    matches = [t for t in tasks if t.get('id') == task_id]
    episodes = [e for e in report['episodes'] if e.get('task') == task_id and e.get('arm') == arm]
    if len(matches) != 1 or len(episodes) != 1:
        raise ValueError('unique donor task and episode required')
    task, result = matches[0], episodes[0]
    contract = _contract(task)
    episode = run / (task_id + '-' + arm)
    receipts = _custody(episode).records
    if (not receipts or receipts[0]['body'].get('task_sha256') != digest(task) or
            receipts[0]['body'].get('task') != task_id or receipts[0]['body'].get('arm') != arm or
            _json(episode / 'result.json') != result):
        raise ValueError('donor episode identity mismatch')
    anchored = [r for r in receipts if 'task_result' in r['body']]
    if len(anchored) != 1 or anchored[0]['body']['task_result'] != result:
        raise ValueError('donor result is not anchored in episode custody')
    if (result.get('development_accepted') is not True or result.get('error') is not None or
            result.get('final_cases_passed') is not True or
            result.get('counterexamples_repaired') is not True):
        raise ValueError('accepted repaired donor required')
    from .pilot import audit_run
    audit = audit_run(run)
    if audit.get('valid') is not True:
        raise ValueError('donor audit failed')
    # Audit/recovery must not silently substitute a different donor version.
    if root.records != roots or _custody(episode).records != receipts:
        raise ValueError('donor changed during audit')
    candidate = result.get('candidate')
    commits = [r for r in receipts if r['body'].get('operation') == 'repair_committed'
               and r['body'].get('snapshot') == candidate]
    freezes = [r for r in receipts if r['body'].get('operation') == 'candidate_frozen'
               and r['body'].get('snapshot') == candidate]
    if not commits or len(freezes) != 1 or commits[-1]['n'] >= freezes[0]['n']:
        raise ValueError('actual final snapshot must have a committed repair before freeze')
    commit = commits[-1]
    bysha = {r['sha256']: r for r in receipts}
    properties = []
    for receipt in receipts:
        body = receipt['body']
        if (body.get('kind') != 'property' or 'property' not in body or
                body.get('final_evaluation') is not False or receipt['n'] >= commit['n']):
            continue
        prop = body['property']
        execution = bysha.get(body.get('execution_receipt'), {})
        observed = execution.get('body', {})
        if (prop.get('scope') != task['property'] or prop.get('checker') != task['checker'] or
                execution.get('n', receipt['n']) >= receipt['n'] or
                observed.get('candidate_snapshot') != prop.get('snapshot') or
                observed.get('execution', {}).get('snapshot') != prop.get('snapshot') or
                canonical(observed.get('input')) != canonical(prop.get('input'))):
            raise ValueError('nonfinal property lacks matching prior execution')
        properties.append(receipt)
    retained = result.get('counterexamples', [])
    public = task.get('public_inputs', [])
    if not isinstance(retained, list) or not retained or not isinstance(public, list) or not public:
        raise ValueError('public checks and retained counterexamples required')
    supports = {}
    for value in public + retained:
        match = next((p for p in properties if p['body']['property'].get('snapshot') == candidate
                      and p['body']['property'].get('status') == 'supported'
                      and canonical(p['body']['property'].get('input')) == canonical(value)), None)
        if match is None or not any(canonical(v) == canonical(value)
                                    for v in commit['body'].get('verified_inputs', [])):
            raise ValueError('final repair lacks nonfinal support for every public/retained case')
        supports[digest(value)] = match
    refutation = next((r for r in properties
                       if r['body']['property'].get('status') == 'contradicted'
                       and r['body']['property'].get('snapshot') != candidate
                       and any(canonical(r['body']['property'].get('input')) == canonical(v)
                               for v in retained)), None)
    if refutation is None:
        raise ValueError('nonfinal confirmed source counterexample required')
    refuted = refutation['body']['property']
    support = supports[digest(refuted['input'])]
    if (support['n'] <= refutation['n'] or
            canonical(refuted.get('expected')) != canonical(support['body']['property'].get('expected'))):
        raise ValueError('counterexample support must follow and agree with refutation')
    snapshots_path = episode / 'snapshots'
    if not snapshots_path.is_dir() or snapshots_path.is_symlink():
        raise ValueError('donor snapshot custody missing')
    snapshots = SnapshotStore(snapshots_path)
    snapshots.get(refuted['snapshot'])
    snapshots.get(commit['body']['base_snapshot'])
    snapshot = snapshots.get(candidate)
    source = snapshots.read(snapshot, 'solution.py').decode('utf-8')
    witness = {k: refuted[k] for k in ('input', 'observed', 'expected')}
    _bounded(witness, 1536, 'counterexample')
    lesson = {'schema': SCHEMA, 'status': 'candidate', 'requires_verification': True,
              'scope': 'Observed repair recipe; verify against the current task before use.',
              'contract': contract, 'compatibility_sha256': digest(contract),
              **_source(source), 'counterexample': witness,
              'provenance': {'run_dir': str(run), 'task_id': task_id, 'arm': arm,
                             'author_agent_id': author_agent_id, 'family': task['family'],
                             'checker': task['checker'], 'snapshot': candidate,
                             'refuted_snapshot': refuted['snapshot'],
                             'run_receipt': roots[-1]['sha256'],
                             'result_receipt': anchored[0]['sha256'],
                             'repair_receipt': commit['sha256'],
                             'refutation_receipt': refutation['sha256'],
                             'support_receipt': support['sha256'],
                             'public_receipts': list(dict.fromkeys(
                                 supports[digest(v)]['sha256'] for v in public))}}
    lesson['lesson_id'] = digest(lesson)
    _bounded(lesson, MAX_LESSON_BYTES, 'stored lesson')
    _card(lesson)
    return lesson


class SharedConceptLibrary:
    """Persistent bounded recipes. First compatible publication wins lookup.

    A new library requires a new path. Existing partial/deleted custody is an
    error, not an empty library. identity() hashes authenticated public records,
    including the creation receipt, and does not read or disclose authority keys.
    """

    def __init__(self, path):
        path = Path(path)
        if path.is_symlink():
            raise ValueError('library path must not be a symlink')
        if path.exists():
            self.path = path.resolve()
            self.store = _custody(self.path)
        else:
            path.mkdir(mode=0o700, parents=True, exist_ok=False)
            self.path = path.resolve()
            self.store = ReceiptStore(self.path / 'receipts', self.path / 'authority')
            self.store.append(_HEADER)
        self._records()

    def _records(self):
        _file(self.path / 'receipts/receipts.jsonl', (MAX_LESSONS + 1) * (MAX_LESSON_BYTES + 1024))
        _file(self.path / 'authority/authority.json', MAX_LESSON_BYTES + 4096)
        records = self.store.records
        if not records or records[0]['body'] != _HEADER or len(records) > MAX_LESSONS + 1:
            raise ReceiptIntegrityError('invalid shared library header or capacity')
        for record in records[1:]:
            body = record['body']
            if set(body) != {'kind', 'lesson'} or body['kind'] != 'shared_lesson':
                raise ReceiptIntegrityError('unknown shared journal record')
            lesson = _bounded(body['lesson'], MAX_LESSON_BYTES, 'stored lesson')
            if (lesson.get('schema') != SCHEMA or lesson.get('status') != 'candidate' or
                    lesson.get('requires_verification') is not True or
                    lesson.get('lesson_id') != digest({k: v for k, v in lesson.items() if k != 'lesson_id'}) or
                    lesson.get('compatibility_sha256') != digest(lesson.get('contract')) or
                    any(lesson.get(k) != v for k, v in _source(lesson.get('source')).items())):
                raise ReceiptIntegrityError('shared source/AST or lesson identity mismatch')
            _card(lesson)
        return records

    def identity(self):
        return digest(self._records())

    def publish_from_run(self, run_dir, task_id, arm, author_agent_id):
        records = self._records()
        lesson = _derive(run_dir, task_id, arm, author_agent_id)
        # Recheck after donor audit; another supervisor must not silently change
        # the library between validation and publication. ReceiptStore serializes
        # individual appends; acquisition is otherwise a single-supervisor API.
        if self._records() != records:
            raise ValueError('library changed during publication')
        for record in records[1:]:
            if record['body']['lesson']['lesson_id'] == lesson['lesson_id']:
                return _card(lesson)
        if len(records) - 1 >= MAX_LESSONS:
            raise ValueError('shared lesson capacity exhausted')
        self.store.append({'kind': 'shared_lesson', 'lesson': lesson})
        return _card(lesson)

    def lookup(self, task):
        records = self._records()
        if len(records) == 1:
            return []
        # A fixture or incompatible task simply cannot consume repair recipes.
        try:
            contract = _contract(task)
            task_id = _identifier(task.get('id'))
        except ValueError:
            return []
        for record in records[1:]:
            lesson = record['body']['lesson']
            p = lesson['provenance']
            if p['task_id'] == task_id or lesson['contract'] != contract:
                continue
            verified = _derive(p['run_dir'], p['task_id'], p['arm'], p['author_agent_id'])
            if verified != lesson:
                raise ReceiptIntegrityError('shared lesson differs from audited donor evidence')
            if self._records() != records:
                raise ReceiptIntegrityError('library changed during lookup')
            return [_card(lesson)]
        return []
