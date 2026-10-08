"""Explicit MAINT-B model-assisted proposal; original Q/T/CAM/gate still run."""
from echoai.echo4.maintain_agent import MaintenanceAgent
from echoai.echo4.maintain_model import MaintainModel, MaintainStop


class MaintainControl(MaintenanceAgent):
    def __init__(self, env, *, mode="adaptive"):
        super().__init__(env)
        self.maintenance = MaintainModel(self.observation(env.cell()), mode=mode)

    def _propose(self, slot, turn_i, greedy=False):
        proposed = super()._propose(slot, turn_i, greedy=greedy)
        return self.maintenance.choose(self.cam.slot[slot].wsp, self.q.row(slot), proposed)

    def _predict(self, slot, action):
        self.maintenance.prepare(self.cam.slot[slot].wsp, action, self.last_gate_decision)
        return super()._predict(slot, action)

    def turn(self, turn_i, greedy=False):
        if self.maintenance.stopped:
            raise MaintainStop(self.maintenance.stopped)
        before = self.observation(self.env.cell())
        applied = super().turn(turn_i, greedy=greedy)
        self.maintenance.observe(before, applied, self.observation(self.env.cell()), self.episode_terminal)
        return applied
