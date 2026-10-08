"""Native one-step laboratory trials and read-only reuse of the same T."""
from echoai.echo4.boundary import integer
from echoai.echo4.self_recovery_agent import SelfRecoveryAgent
from echoai.echo4.self_reuse import choose_from_memory, validate_target


class _FrozenLearning:
    def observe_step(self, slot, action, next_slot):
        return False


class SelfReuseAgent(SelfRecoveryAgent):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.trial_phase = ""
        self.trial_active = False
        self.trial_token = 0
        self.scripted_action = None
        self.reuse_target = None
        self.reuse_use_t = True
        self.reuse_decision = None

    def _validate_trial(self, token, restored):
        integer(token, 1, (1 << 31) - 1)
        if restored is not True or token <= self.trial_token:
            raise ValueError("invalid or repeated restoration receipt")
        if self.trial_active or self.life_turns or self.sensation.pending is not None:
            raise RuntimeError("executor must restore a finished trial before arming")

    def arm_school(self, action, *, token, restored):
        self._validate_trial(token, restored)
        integer(action, 0, 2)
        if self.trial_phase not in ("", "school"):
            raise RuntimeError("nominal school cannot resume after exposure")
        self.recovery = self.self_model = None
        self._arm("school", token, action=action)

    def arm_exposure(self, diagnosis, action, *, mode, token, restored, same_context):
        self._validate_trial(token, restored)
        integer(action, 0, 2)
        if self.trial_phase == "reuse":
            raise RuntimeError("exposure cannot resume after the frozen exam")
        modes = {"selective": "selective", "unprotected": "no_protection",
                 "freeze_all": "all_self", "no_t": "selective"}
        if mode not in modes:
            raise ValueError("unknown exposure arm")
        # Validate before replacing the completed prior trial's observer.
        from echoai.echo4.self_recovery import RecoveryBelief
        belief = RecoveryBelief(diagnosis, restored=restored, same_context=same_context, mode=modes[mode])
        if belief.current != self.observation(self.env.cell()):
            raise ValueError("restored observation differs from diagnostic reference")
        from echoai.echo4.self_recovery_agent import _LearningPermission
        self.recovery = belief
        self.self_model = _LearningPermission(self)
        self._arm("exposure", token, action=action)

    def arm_reuse(self, target, *, token, restored, nominal_body_confirmed, use_t=True):
        self._validate_trial(token, restored)
        validate_target(target)
        if nominal_body_confirmed is not True or type(use_t) is not bool:
            raise ValueError("requires recommissioning receipt and boolean ablation")
        initial = self.observation(self.env.cell())
        if any(initial[j] != target[j] for j in range(16) if j not in (8, 9)):
            raise ValueError("goal outside the calibrated semantic context")
        self.recovery = None
        self.self_model = _FrozenLearning()
        self._arm("reuse", token, target=target)
        self.reuse_use_t = use_t
        self.sensation.frozen = True

    def _arm(self, phase, token, *, action=None, target=None):
        self.trial_phase, self.trial_token, self.trial_active = phase, token, True
        self.scripted_action, self.reuse_target = action, target
        self.reuse_decision = None
        self.sensation.frozen = False

    def _propose(self, slot, turn_i, greedy=False):
        if self.trial_phase in ("school", "exposure"):
            return self.scripted_action
        proposed = super()._propose(slot, turn_i, greedy=greedy)
        if self.trial_phase == "reuse":
            self.reuse_decision = choose_from_memory(self.cam, self.t, self.q, slot,
                                                   self.reuse_target, proposed, use_t=self.reuse_use_t)
            return self.reuse_decision.action
        return proposed

    def turn(self, turn_i, greedy=False):
        if not self.trial_phase:
            return super().turn(turn_i, greedy=greedy)
        if not self.trial_active:
            raise RuntimeError("one action per explicitly restored laboratory trial")
        try:
            return super().turn(turn_i, greedy=greedy)
        finally:
            self.trial_active = False

    def respawn(self):
        if self.trial_phase:
            raise RuntimeError("restoration belongs to the experiment, not the policy")
        super().respawn()
