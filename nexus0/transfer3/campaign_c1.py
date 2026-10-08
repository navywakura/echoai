"""Plan C1 sealed campaign A -> B -> C. The examiner side. Holds no secret.

Order is the mechanism and every step checks the one before it:

    protocol  frozen here; its hash is what the custodian commits to
    freeze    needs the PUBLISHED notice; trains A and binds payloads to it
    exam B    verifies the reveal against the published commitment before
              touching a room, regenerates every room from its seed, examines
              once under a latch that a crash consumes
    exam C    only with a passing B exam from the same freeze
    certify   needs the secret, revealed by the custodian after C: checks the
              protocol was committed first and that the rooms are exactly what
              that secret produces, so nobody chose them after the fact

`kind == 'rehearsal'` runs the whole chain with a published secret and can
never certify green. Only a `campaign` notice from an external custodian can.
"""
import argparse
import json
from pathlib import Path

from echoai.nexus0.sim3.canon import canonical_bytes, loads_strict, sha256_bytes
from echoai.nexus0.sim3.seal import open_once, seal
from . import bench_c1, calib_c1, custodian_c1, school_c1
from .camera_c1 import OFFSETS, OffsetRoom, declared_body
from .custody import validate_notice, verify_protocol, verify_reveal
from .rehearsal_v2 import shape
from .space_a2 import feasible

ROOT = bench_c1.ROOT
# Rehearsal needs enough rooms for the sign test to be able to pass at 1/240,
# otherwise it could never exercise the opening of C.
COUNTS = dict(campaign={'B': 64, 'C': 64}, rehearsal={'B': 16, 'C': 16})

# Amendment decided by Roger on 2026-09-19, before any real protocol existed,
# after the first rehearsal. The strict rule "the learned arm never loses a
# mission the uncalibrated nominal completes" failed once in 1 080 C1 missions,
# and that loss was NOT caused by calibration: in that room the agent with
# PERFECT calibration also fails; the uncalibrated one arrived by luck. Losses
# attributable to calibration across all C1 data: 0 of 1 080. Extrapolated, the
# strict rule would fail a real campaign ~66% of the time on the control's luck.
# The blocking rule therefore compares against the oracle-calibrated agent; the
# strict count is still computed and published, never hidden.
BLOCKING = ('hard_constraints', 'no_attributable_failures', 'more_missions', 'amortised',
            'beyond_fixed_priors', 'significant')
REPORTED = ('no_new_failures',)
REGRESSION_RULE = ('the learned arm may not lose any mission that an agent with the TRUE '
                   'mount offset completes; losses to the uncalibrated nominal are reported')


def manifest():
    here = Path(__file__)
    entries = [here, here.with_name('consumer_c1.py'), ROOT/'tests/test_transfer3_campaign_c1.py',
               ROOT/'docs/TRANSFER3-PLAN-C1-DESIGN.md']
    entries += [ROOT/'nexus0'/p for p in bench_c1.MODULES]+[ROOT.parent/p for p in bench_c1.PARENT_MODULES]
    return {str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else '../'+str(p.relative_to(ROOT.parent)):
            sha256_bytes(p.read_bytes()) for p in bench_c1.dependency_paths(entries)}


def public_shapes():
    """Every geometry already public anywhere under lab/transfer3, plus probes and gyms."""
    shapes = set()

    def walk(value):
        if isinstance(value, dict):
            if isinstance(value.get('shape'), str):
                shapes.add(value['shape'])
            for v in value.values():
                walk(v)
        elif isinstance(value, list):
            for v in value:
                walk(v)
    for p in sorted((ROOT/'lab/transfer3').rglob('*.json')):
        walk(loads_strict(p.read_bytes()))
    shapes |= bench_c1.probe_shapes()
    shapes |= {r['shape'] for r in school_c1.gym_rooms()}
    return sorted(shapes)


def protocol(kind):
    if kind not in COUNTS:
        raise ValueError('kind')
    return dict(version='c1-campaign', kind=kind, candidate='Plan C1 camera extrinsic calibration',
                confirmed_by='plan-c1-confirmation.json', conditions=[list(o) for o in OFFSETS],
                arms=bench_c1.PROTOCOL['arms'], priors=bench_c1.PROTOCOL['priors'],
                reserve=bench_c1.RESERVE, margin=bench_c1.MARGIN,
                school=bench_c1.PROTOCOL['school'], counts=COUNTS[kind],
                criteria=list(BLOCKING), reported_not_blocking=list(REPORTED),
                regression_rule=REGRESSION_RULE, ceiling_arm='oracle',
                alpha_denominator=bench_c1.PROTOCOL['alpha_denominator'],
                c_requires_passing_b=True,
                generator='space_a2 two-wall rooms; seed = HMAC(secret, split, attempt)',
                excluded_shapes=public_shapes(), examiner_manifest=manifest(),
                learning_in_exam=False)


def check_protocol(notice, protocol_bytes):
    validate_notice(notice)
    if notice['protocol_sha256'] != sha256_bytes(protocol_bytes):
        raise ValueError('notice does not commit to this protocol')
    protocol_value = loads_strict(protocol_bytes)
    if protocol_value['kind'] != notice['kind']:
        raise ValueError('protocol/notice kind mismatch')
    bench_c1.verify_manifest(protocol_value['examiner_manifest'])
    return protocol_value


def freeze(notice, protocol_bytes, latch_dir):
    protocol_value = check_protocol(notice, protocol_bytes)
    schools = {f'{o[0]},{o[1]}': school_c1.train(o) for o in OFFSETS}
    for school in schools.values():
        school_c1.replay(school)
    payloads = {k: s['payload'] for k, s in schools.items()}
    latch_dir = Path(latch_dir)
    latch_dir.mkdir(parents=True, exist_ok=True)
    binding = 'public-notice-sha256:'+sha256_bytes(canonical_bytes(notice))
    for split in custodian_c1.SPLITS:
        row = notice['splits'][split]
        seal(latch_dir/f'{split}.json', split=split, commitment=row['inventory_commitment'],
             inventory_sha256='pending-reveal', custodian=binding, n_packages=row['count'])
    return dict(stage='freeze', kind=notice['kind'], notice_sha256=sha256_bytes(canonical_bytes(notice)),
                protocol_sha256=sha256_bytes(protocol_bytes), counts=protocol_value['counts'],
                schools=schools, payloads=payloads,
                payloads_sha256=sha256_bytes(canonical_bytes(payloads)))


def bind_rooms(reveal, split, count, excluded):
    """Every revealed room must match its committed package and be fresh."""
    rooms, entries = reveal['rooms'], reveal['entries']
    if reveal['split'] != split or len(rooms) != count or len(entries) != count:
        raise ValueError('reveal size/split')
    seen = set(excluded)
    for entry, room in zip(entries, rooms):
        if entry['package_sha256'] != custodian_c1.package_sha(room):
            raise ValueError('room does not match its committed package')
        world = OffsetRoom(room['seed'], declared_body(), (0, 0))
        if shape(world) != room['shape'] or feasible(world) is not None:
            raise ValueError('revealed seed does not produce the committed room')
        if room['shape'] in seen:
            raise ValueError('revealed room is not fresh')
        seen.add(room['shape'])
    return rooms


def examine(rooms, frozen, *, isolated=True, progress=False):
    """Pure core, shared by the latched exam and by the audit.

    The `oracle` arm carries the TRUE mount offset of each condition. It is an
    external ceiling used only to attribute losses, never a competitor, and it is
    held to the same hard constraints as every other arm.
    """
    conditions = {}
    for o in OFFSETS:
        key = f'{o[0]},{o[1]}'
        payloads = dict(nominal=calib_c1.nominal(), learned=frozen['payloads'][key],
                        oracle=calib_c1.prior(o),
                        **{name: calib_c1.prior(v) for name, v in bench_c1.PRIORS.items()})
        cache, arms = {}, {}
        for name, payload in payloads.items():
            signature = tuple(payload['offset'])
            if signature not in cache:
                cache[signature] = [bench_c1.episode(r['seed'], o, payload, isolated=isolated) for r in rooms]
            arms[name] = cache[signature]
            if progress:
                print('offset', o, name, 'reached', sum(r['reached'] for r in arms[name]), flush=True)
        conditions[key] = arms
    return conditions, verdict_for(conditions, frozen['schools'])


def verdict_for(conditions, schools):
    evaluation = bench_c1.evaluate(conditions, schools, confirm=True)
    checks = dict(evaluation['checks'])
    attributable = sum(1 for arms in conditions.values()
                       for learned, oracle in zip(arms['learned'], arms['oracle'])
                       if oracle['reached'] and not learned['reached'])
    checks['no_attributable_failures'] = attributable == 0
    return dict(evaluation, checks=checks, attributable_losses=attributable,
                strict_losses=evaluation['comparisons']['nominal']['lost'],
                passes_including_strict=evaluation['passes'],
                blocking=list(BLOCKING), reported_not_blocking=list(REPORTED),
                passes=all(checks[c] for c in BLOCKING))


def exam(split, notice, protocol_bytes, frozen, reveal, latch_dir, *, prior=None,
         isolated=True, progress=False):
    protocol_value = check_protocol(notice, protocol_bytes)
    if frozen['notice_sha256'] != sha256_bytes(canonical_bytes(notice)) \
            or frozen['protocol_sha256'] != sha256_bytes(protocol_bytes):
        raise ValueError('freeze is not bound to this notice and protocol')
    excluded = list(protocol_value['excluded_shapes'])
    if split == 'C':
        if prior is None or prior['split'] != 'B' or not prior['verdict']['passes'] \
                or prior['freeze_sha256'] != sha256_bytes(canonical_bytes(frozen)):
            raise ValueError('C requires a passing B exam from the same freeze')
        excluded += [r['shape'] for r in prior['rooms']]
    with open_once(Path(latch_dir)/f'{split}.json'):
        verify_reveal(notice, split, reveal['entries'], bytes.fromhex(reveal['salt']))
        rooms = bind_rooms(reveal, split, protocol_value['counts'][split], excluded)
        conditions, verdict = examine(rooms, frozen, isolated=isolated, progress=progress)
    return dict(stage='exam', split=split, kind=notice['kind'], isolated=isolated,
                notice_sha256=frozen['notice_sha256'], freeze_sha256=sha256_bytes(canonical_bytes(frozen)),
                reveal_sha256=sha256_bytes(canonical_bytes(reveal)), rooms=rooms,
                conditions=conditions, verdict=verdict,
                transfer3_green=False, campaign_C_opened=split == 'C')


def audit_exam(report, frozen):
    if report['freeze_sha256'] != sha256_bytes(canonical_bytes(frozen)):
        raise ValueError('audit needs the exam freeze')
    conditions, verdict = examine(report['rooms'], frozen, isolated=report['isolated'])
    if canonical_bytes(conditions) != canonical_bytes(report['conditions']) \
            or canonical_bytes(verdict) != canonical_bytes(report['verdict']):
        raise ValueError('exam does not reconstruct')
    return dict(replay_valid=True, sha256=sha256_bytes(canonical_bytes(report)))


def certify(notice, protocol_bytes, frozen, exam_b, exam_c, secret):
    protocol_value = check_protocol(notice, protocol_bytes)
    freeze_sha = sha256_bytes(canonical_bytes(frozen))
    for name, report in (('B', exam_b), ('C', exam_c)):
        if report['split'] != name or report['freeze_sha256'] != freeze_sha or not report['verdict']['passes']:
            raise ValueError(f'{name} exam missing, failing or from another freeze')
    verify_protocol(notice, protocol_bytes, secret)
    taken = list(protocol_value['excluded_shapes'])
    for name, report in (('B', exam_b), ('C', exam_c)):
        expected = custodian_c1.generate_split(secret, name, protocol_value['counts'][name], taken)
        if expected != report['rooms']:
            raise ValueError(f'{name} rooms are not the ones the committed secret produces')
        taken += [r['shape'] for r in expected]
    green = notice['kind'] == 'campaign'
    return dict(stage='certificate', kind=notice['kind'], transfer3_green=green,
                notice_sha256=frozen['notice_sha256'], protocol_sha256=frozen['protocol_sha256'],
                freeze_sha256=freeze_sha, exam_b_sha256=sha256_bytes(canonical_bytes(exam_b)),
                exam_c_sha256=sha256_bytes(canonical_bytes(exam_c)),
                custodian=notice['custodian'], publication_reference=notice['publication_reference'],
                scope='software simulation; camera extrinsic calibration in static two-wall rooms; '
                      'no hardware, HIL, flight or DRONE-3',
                validity='depends on the custodian having generated and held the secret where '
                         'neither agent could read it, and published the notice before the freeze')


def _write(path, value):
    with Path(path).open('xb') as stream:
        stream.write(canonical_bytes(value))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='command', required=True)
    a = sub.add_parser('protocol')
    a.add_argument('out', type=Path)
    a.add_argument('--rehearsal', action='store_true')
    f = sub.add_parser('freeze')
    for name in ('notice', 'protocol', 'latches', 'out'):
        f.add_argument(name, type=Path)
    e = sub.add_parser('exam')
    e.add_argument('split', choices=custodian_c1.SPLITS)
    for name in ('notice', 'protocol', 'freeze', 'reveal', 'latches', 'out'):
        e.add_argument(name, type=Path)
    e.add_argument('--prior', type=Path)
    e.add_argument('--local', action='store_true')
    u = sub.add_parser('audit')
    u.add_argument('report', type=Path)
    u.add_argument('freeze', type=Path)
    c = sub.add_parser('certify')
    for name in ('notice', 'protocol', 'freeze', 'exam_b', 'exam_c', 'secret', 'out'):
        c.add_argument(name, type=Path)
    args = p.parse_args()
    read = lambda path: loads_strict(Path(path).read_bytes())
    if args.command == 'protocol':
        _write(args.out, protocol('rehearsal' if args.rehearsal else 'campaign'))
        print('protocol written, sha256', sha256_bytes(Path(args.out).read_bytes()))
    elif args.command == 'freeze':
        result = freeze(read(args.notice), args.protocol.read_bytes(), args.latches)
        _write(args.out, result)
        print('frozen; payloads', result['payloads_sha256'])
    elif args.command == 'exam':
        result = exam(args.split, read(args.notice), args.protocol.read_bytes(), read(args.freeze),
                      read(args.reveal), args.latches, prior=read(args.prior) if args.prior else None,
                      isolated=not args.local, progress=True)
        _write(args.out, result)
        print(args.split, result['verdict']['checks'], 'passes', result['verdict']['passes'])
    elif args.command == 'audit':
        print(audit_exam(read(args.report), read(args.freeze)))
    else:
        result = certify(read(args.notice), args.protocol.read_bytes(), read(args.freeze),
                         read(args.exam_b), read(args.exam_c), bytes.fromhex(read(args.secret)['secret']))
        _write(args.out, result)
        print(json.dumps({k: result[k] for k in ('kind', 'transfer3_green', 'scope', 'validity')}, indent=2))


if __name__ == '__main__':
    main()
