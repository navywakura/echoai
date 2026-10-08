"""Passive relation history on original native social executions, not transfer."""
from echoai.echo4.interaction_social import SocialSession
from echoai.echo4.relation_memory import RelationMemory


class RelationSession(SocialSession):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.relations = tuple(RelationMemory(a.cam) for a in self.all_agents)

    def step(self, **kwargs):
        frame = super().step(**kwargs)
        try:
            # Views are separate; no global frame or private incentive enters
            # the history API. Missing focal identity stays missing.
            heads = []
            for actor, observer in enumerate((0, frame["handle"])):
                packets = [tuple(bytes.fromhex(p) if p is not None else None for p in frame[field][actor])
                           for field in ("contexts", "outcomes")]
                raw = self.relations[observer].append(frame["tick"], *packets,
                                                      frame["paid"][actor], frame["output"][actor])
                heads.append(raw.hex())
            return {**frame, "relation_heads": heads}
        except Exception:
            self.failed = True
            self.stop()  # Preserve executed costs and any already-written receipt.
            raise

    def invariant(self):
        return bool(super().invariant()
                    and all(m.cam is a.cam and m.count == o.count and m.invariant()
                            for m, a, o in zip(self.relations, self.all_agents,
                                               (self.observer, *self.peer_models))))

    def stop(self):
        super().stop()
        for memory in self.relations:
            memory.stop()
