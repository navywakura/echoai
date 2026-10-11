"""Passive evidence collection after the legacy runner cancels its lease.

This stdlib-only module can be copied to /flight/sitl_recovery.py. The launcher
can compile adapt_runner_source(original_source) and execute it in the usual
legacy __main__ globals. Nothing here imports or edits the frozen runner.
Disarm evidence does not turn a failed mission into a successful mission.
"""
import ast
import hashlib
import math
import time


SIM_TIMEOUT_NS = 35_000_000_000
HEARTBEAT_AGE_NS = 2_000_000_000
MAX_WALL_S = 900.0  # ECHO-5's outer episode maximum; caller passes remaining time.
# Frozen nexus0/drone3/assets/runner.py. Unlike ast.dump, bytes are stable
# across host/container Python versions. Deliberately reject even text drift.
LEGACY_SOURCE_SHA256 = 'f10d83d7b750d4c15cef6ea008d688ad8e2c7e15c30af6b16ea3c652725e1c56'


def recover_exception(backend, driver, log, poll, result, *, wall_timeout_s=35.0,
                      monotonic=time.monotonic, sleep=time.sleep):
    """Observe fresh disarm after cancellation; never send or renew anything.

    poll must be the runner's bounded, passive telemetry drain/health check. The
    deadline is checked before and after each poll; callbacks must return (this
    helper cannot preempt arbitrary blocking Python). The runner's existing poll
    and outer process timeout retain their episode limits. Inject clocks for CPU
    tests. Ordinary polling/clock/logging errors cannot replace result['error'].
    """
    result['ok'] = False
    receipt = dict(schema='echo5.sitl.exceptional-recovery.v1',
                   disarmed_observed=False, reason='recovery_error',
                   sim_elapsed_ns=0, wall_s=0.0)
    result['exceptional_recovery'] = receipt
    try:
        if (type(wall_timeout_s) not in (int, float)
                or not math.isfinite(wall_timeout_s)):
            raise ValueError('finite recovery wall timeout required')
        budget = min(MAX_WALL_S, max(0.0, wall_timeout_s))
        wall_start = monotonic()
        sim_start = backend.now_ns()
        if type(sim_start) is not int or sim_start < 0:
            raise ValueError('invalid simulation clock')
        receipt.update(sim_started_ns=sim_start, wall_timeout_s=budget)
        initial_hb = driver.conn.messages.get('HEARTBEAT')
        initial_received = driver.heartbeat_received
        last_sim = sim_start

        def deadline():
            nonlocal last_sim
            now = backend.now_ns()
            wall = monotonic()
            if type(now) is not int or now < last_sim or wall < wall_start:
                return 'clock_regressed'
            last_sim = now
            receipt.update(sim_elapsed_ns=now-sim_start, wall_s=wall-wall_start)
            if wall-wall_start >= budget:
                return 'wall_deadline'
            if now-sim_start >= SIM_TIMEOUT_NS:
                return 'simulation_deadline'
            return None

        while True:
            reason = deadline()
            if reason:
                receipt['reason'] = reason
                break
            poll()
            reason = deadline()
            if reason:
                receipt['reason'] = reason
                break
            hb = driver.conn.messages.get('HEARTBEAT')
            received = driver.heartbeat_received
            fresh = (hb is not None and type(received) is int
                     and received >= sim_start
                     and 0 <= last_sim-received <= HEARTBEAT_AGE_NS
                     and (hb is not initial_hb or received > initial_received))
            if fresh and not hb.base_mode & 128:
                receipt.update(reason='fresh_disarm', disarmed_observed=True,
                               heartbeat_received_ns=received,
                               heartbeat_age_ns=last_sim-received, base_mode=hb.base_mode)
                result['disarmed'] = True
                break
            sleep(min(.02, max(0.0, budget-receipt['wall_s'])))
    except Exception as exc:
        receipt.update(reason='recovery_error', error=repr(exc))
    try:
        log('exceptional_recovery', **receipt)
    except Exception as exc:
        receipt['log_error'] = repr(exc)
    return receipt


def adapt_runner_source(source):
    """Return a guarded in-memory adaptation; reject all unknown code shapes.

    The whole source is pinned, including passive poll, cancellation and final
    teardown. Reapplying the adapter or changing the legacy source requires an
    explicit new review and fingerprint. Copy this module alongside the runner
    before executing the returned source.
    """
    if (type(source) is not str
            or hashlib.sha256(source.encode()).hexdigest() != LEGACY_SOURCE_SHA256):
        raise ValueError('unrecognized legacy runner source; recovery was not injected')
    try:
        tree = ast.parse(source)
    except (SyntaxError, TypeError) as exc:
        raise ValueError('unrecognized legacy runner') from exc
    main = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'main')
    outer = next(node for node in main.body if isinstance(node, ast.Try) and node.finalbody)
    cancellation = outer.handlers[0].body[1]
    cancellation.body.extend(ast.parse('''
from sitl_recovery import recover_exception as _echo5_recover_exception
_echo5_recover_exception(backend, driver, log, poll, result,
    wall_timeout_s=max(0.0, started + cfg['timeouts']['episode_s'] - time.monotonic()))
''').body)
    return ast.unparse(ast.fix_missing_locations(tree)) + '\n'
