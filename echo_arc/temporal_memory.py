"""Bounded integer memories of observed entries, without simulator access."""
from collections import Counter, OrderedDict, deque


class OrderMemory:
    """Ordered pairs preceding an observed effect; correlations remain hypotheses."""
    MAX_RULES = 64

    def __init__(self):
        self.episode = 0
        self.history = deque(maxlen=16)
        self.rules = OrderedDict()

    def reset(self):
        self.episode += 1
        self.history.clear()

    def enter(self, kind, effect=False, evaluate=True):
        self.history.append(kind)
        if len(self.history) < 2 or self.history[-2] == kind:
            return None
        pair = (self.history[-2], kind)
        rule = self.rules.get(pair)
        if effect:
            if rule is None:
                if len(self.rules) >= self.MAX_RULES:
                    self.rules.popitem(last=False)
                rule = self.rules[pair] = {"supports": 0, "conflicts": 0, "last_episode": -1}
            if rule["last_episode"] != self.episode:
                rule["supports"] += 1
                rule["last_episode"] = self.episode
            return pair
        if rule is not None and evaluate:
            rule["conflicts"] += 1
        return None

    def candidates(self):
        useful = [p for p, r in self.rules.items() if r["supports"] > r["conflicts"]]
        return sorted(useful, key=lambda p: (-self.rules[p]["supports"],
                                            self.rules[p]["conflicts"], p))

    def report(self):
        return [{"sequence": list(p), "supports": r["supports"],
                 "conflicts": r["conflicts"],
                 "status": "repeated" if r["supports"] >= 2 else "proposed"}
                for p, r in self.rules.items()]


class CountMemory:
    """Count entries per instance/attempt; learn thresholds from complete episodes."""
    MAX_INSTANCES = 64
    MAX_COUNT = 255

    def __init__(self, complete=True):
        self.episode = 0
        self.thresholds = OrderedDict()
        self.reset(complete)

    def reset(self, complete=True):
        self.episode += 1
        self.complete = complete
        self.occupied = None
        self.counts = Counter()
        self.kinds = set()

    def position(self, instance, kind=None, effect=False, evaluate=True):
        """None means outside every marker. Staying on the same instance is inert."""
        if instance == self.occupied:
            return None
        self.occupied = instance
        if instance is None:
            return None
        if instance not in self.counts and len(self.counts) >= self.MAX_INSTANCES:
            return None
        self.counts[instance] = min(self.MAX_COUNT, self.counts[instance] + 1)
        count = self.counts[instance]
        self.kinds.add(kind)
        rules = self.thresholds.get(kind, {})
        # Multiple kinds or instances confound a single-object counting rule.
        clean = self.complete and len(self.kinds) == 1 and len(self.counts) == 1
        if effect and clean:
            if kind not in self.thresholds:
                if len(self.thresholds) >= self.MAX_INSTANCES:
                    self.thresholds.popitem(last=False)
                self.thresholds[kind] = OrderedDict()
            rules = self.thresholds[kind]
            if count not in rules:
                if len(rules) >= self.MAX_INSTANCES:
                    rules.popitem(last=False)
                rules[count] = {"supports": 0, "conflicts": 0, "last_episode": -1}
            r = rules[count]
            if r["last_episode"] != self.episode:
                r["supports"] += 1
                r["last_episode"] = self.episode
        elif not effect and clean and evaluate and count in rules:
            rules[count]["conflicts"] += 1
        return count

    def threshold(self, kind):
        rules = self.thresholds.get(kind, {})
        useful = [n for n, r in rules.items() if r["supports"] > r["conflicts"]]
        return min(useful, key=lambda n: (-rules[n]["supports"], n)) if useful else None

    def report(self):
        return [{"kind": k, "entries": n, "supports": r["supports"],
                 "conflicts": r["conflicts"],
                 "status": "repeated" if r["supports"] >= 2 else "proposed"}
                for k, rules in self.thresholds.items() for n, r in rules.items()]
