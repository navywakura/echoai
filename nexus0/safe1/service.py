"""Bounded operator setup/landing calls; never renew a mission's health permit here."""
import threading
import time


def serviced_call(operation, service, timeout):
    """Keep the main loop responsive while an operator command awaits its ACK.

    Only the main thread services the lease. A hung main thread still expires
    after 500 ms. The operation itself remains bounded; timeout tears down SITL,
    never reports a successful landing or starts another mission.
    """
    done = threading.Event()
    values, errors = [], []

    def execute():
        try:
            values.append(operation())
        except Exception as exc:
            errors.append(exc)
        finally:
            done.set()

    deadline = time.monotonic()+timeout
    service()
    threading.Thread(target=execute, daemon=True).start()
    while not done.is_set():
        remaining = deadline-time.monotonic()
        if remaining <= 0:
            raise TimeoutError('operator operation')
        service()
        done.wait(min(.02, remaining))
    if time.monotonic() >= deadline:
        raise TimeoutError('operator operation')
    service()
    if errors:
        raise errors[0]
    return values[0]
