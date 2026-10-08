"""Bounded confirmation session; no executor, body readings or private labels."""
from echoai.echo4.boundary import integer
from echoai.echo4.self_attribution import CATALOG, ProbePlan, SelfAttributor

SCOPE = "WORLD1-binary-couplings-single-pulse-v1"


class SelfSession:
    """Confirm the existing model before lending it to the existing controller.

    Positive labels are conditional on SCOPE, never unrestricted causal truth.
    The reference and all learned tables remain owned by the original agent.
    """

    def __init__(self, model):
        if type(model) is not SelfAttributor or model.pending is not None or model.used:
            raise ValueError("requires a fresh SELF-B diagnostic model")
        self.model = model
        self.finished = False
        self.challenge_probes = 0

    def diagnosis(self):
        result = dict(self.model.diagnosis())
        result["scope"] = SCOPE
        result["confirmed"] = self.finished and result["label"] != "unknown"
        result["challenge_probes"] = self.challenge_probes
        if not self.finished:
            result["label"] = "unknown"
            result["reason"] = "confirmation_pending"
        return result

    def choose(self, token):
        integer(token, 1, (1 << 31) - 1)
        if token <= self.model.last_token:
            raise ValueError("non-increasing confirmation token")
        if self.model.pending is not None:
            raise RuntimeError("consume the pending probe first")
        if self.finished:
            return None
        plan = self.model.choose(token)
        if plan is not None:
            return plan
        # SELF-B stops at consensus. Confirm it with unused SAFE sequences,
        # using exactly its prior/forecast and receipt-consumption machinery.
        if not self.model.invalid_reason and self.model.diagnosis()["label"] != "unknown":
            for index in range(len(CATALOG)):
                if index in self.model.used:
                    continue
                prediction = self.model._prediction(index)
                if prediction is None:
                    continue
                score, hs, ts = prediction
                plan = ProbePlan(token, index, CATALOG[index], score[0], score[1])
                self.model.pending = (plan, hs, ts)
                self.model.used.add(index)
                self.model.last_token = token
                self.challenge_probes += 1
                return plan
        self.finished = True
        return None

    def consume(self, receipt):
        if self.finished:
            raise RuntimeError("diagnostic session is finished")
        self.model.consume(receipt)
        if self.model.invalid_reason:
            self.finished = True
        return self.diagnosis()

    def cancel(self):
        self.model.pending = None
        self.model.invalid_reason = "session_cancelled"
        self.finished = True

    def authorized_model(self):
        if not self.diagnosis()["confirmed"] or self.model.pending is not None:
            raise ValueError("unconfirmed/unknown diagnosis cannot authorize learning or recovery")
        return self.model

    def resources(self):
        return self.model.resources()
