"""Private SELF-C executor: original physics, continuous life, no rescues."""
from echoai.echo4.adapter import DockEnv
from echoai.echo4.world import Body, DockRules, Transition, integer, transition


def physical_step(body, action, hc, tc, heat):
    active, wait = transition(body, action, DockRules()), transition(body, 2, DockRules())
    return Body(active.after.h if hc else wait.after.h,
                max(0, min(127, (active.after.temperature if tc else wait.after.temperature) + heat)))


class RecoveryEnv(DockEnv):
    def __init__(self, initial, *, h_coupled=True, temperature_coupled=True, heat=0):
        super().__init__(initial=initial)
        if type(h_coupled) is not bool or type(temperature_coupled) is not bool:
            raise ValueError("invalid coupling")
        integer(heat, -127, 127, "heat")
        self._hc, self._tc, self._heat = h_coupled, temperature_coupled, heat

    def step_homeostatic(self, action, h, temperature):
        if Body(h, temperature) != self.body:
            raise ValueError("physical registers disagree")
        result = self.advance(action)
        return result.reward, self.cell(), self.body.h, self.body.temperature

    def advance(self, action):
        before = self.body
        after = physical_step(before, action, self._hc, self._tc,
                              self._heat if self.life_steps == 0 else 0)
        energy = transition(before, action if self._hc else 2, self.rules)
        result = Transition(before, action, after, energy.resource_in,
                            energy.resource_used, energy.resource_spill)
        self.body = after
        self.last_transition = result
        self.life_steps += 1
        self.total_steps += 1
        self.resource_in += result.resource_in
        self.resource_used += result.resource_used
        self.resource_spill += result.resource_spill
        return result

    def reset(self):
        raise RuntimeError("no reset inside SELF-C recovery life")
