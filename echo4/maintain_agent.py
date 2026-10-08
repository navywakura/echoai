"""Opt-in MAINT-A wiring. One original CAM/T/Q/gate, no new action policy."""
from echoai.echo4.maintain_world import MaintenanceEnv
from echoai.echo4.self_agent import SelfAgent


class MaintenanceAgent(SelfAgent):
    def __init__(self, env: MaintenanceEnv):
        if type(env) is not MaintenanceEnv:
            raise ValueError("requires a MAINT-A environment")
        if env.total_steps or env.stopped or env.body != env.initial:
            raise ValueError("attachment requires an unused, unstopped environment")
        super().__init__(initial=env.initial)
        # The base constructor starts sensory history at exactly this body's
        # original WSP. No physics is advanced and no CAM/T/Q is replaced.
        self.env = env

    def turn(self, turn_i: int, greedy: bool = False) -> int:
        # Reject stop *before* the inherited loop can modify Q/CAM/history.
        if self.env.stopped:
            raise RuntimeError("MAINTAIN stopped by operator")
        return super().turn(turn_i, greedy=greedy)

    def respawn(self) -> None:
        # Reject at the agent boundary as well as in the environment.
        raise RuntimeError("no respawn inside a MAINTAIN life")

    def operator_stop(self) -> None:
        self.env.stop()
