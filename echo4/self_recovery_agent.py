"""SELF-C on the existing loop's self_model hook, with one CAM/T/Q."""
from echoai.echo4.self_probe_agent import SelfProbeAgent
from echoai.echo4.self_attribution import SelfAttributor
from echoai.echo4.self_recovery import RecoveryBelief, RecoveryStop


class _LearningPermission:
    def __init__(self, agent):
        self.agent = agent

    def observe_step(self, slot, action, next_slot):
        agent = self.agent
        allowed = agent.recovery.observe(agent.cam.slot[slot].wsp, action,
                                          agent.cam.slot[next_slot].wsp)
        # The superclass subsequently consumes SENSATION once. Suppress its
        # model writes on exactly the same transitions that do not train T.
        # History and scoring continue. The flag is restored by turn's finally.
        agent.sensation.frozen = agent.sensation.frozen or not allowed
        return allowed


class SelfRecoveryAgent(SelfProbeAgent):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.recovery = None

    def start_recovery(self, diagnosis, *, restored, same_context, mode="selective"):
        if type(diagnosis) is not SelfAttributor:
            raise ValueError("requires a SELF-B diagnostic model")
        if self.recovery is not None or self.life_turns or self.sensation.pending is not None:
            raise RuntimeError("recovery attachment requires a fresh experimental life")
        if diagnosis.initial != self.observation(self.env.cell()):
            raise ValueError("restored observation mismatch")
        belief = RecoveryBelief(diagnosis, restored=restored, same_context=same_context, mode=mode)
        self.recovery = belief
        self.self_model = _LearningPermission(self)

    def _propose(self, slot, turn_i, greedy=False):
        proposed = super()._propose(slot, turn_i, greedy=greedy)
        if self.recovery is None:
            return proposed
        return self.recovery.choose(self.cam.slot[slot].wsp, self.q.row(slot), proposed)

    def _predict(self, slot, action):
        if self.recovery is not None:
            self.recovery.prepare(self.cam.slot[slot].wsp, action, self.last_gate_decision)
        return super()._predict(slot, action)

    def turn(self, turn_i, greedy=False):
        if self.recovery is None:
            return super().turn(turn_i, greedy=greedy)
        if self.recovery.stopped:
            raise RecoveryStop(self.recovery.stopped)
        frozen = self.sensation.frozen
        try:
            return super().turn(turn_i, greedy=greedy)
        finally:
            self.sensation.frozen = frozen

    def respawn(self):
        if self.recovery is not None:
            raise RecoveryStop("no respawn inside a recovery trial")
        super().respawn()
