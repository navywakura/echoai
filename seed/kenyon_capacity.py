"""Experimental sparse 500k-unit guide for ECHO-SEED's existing DSL search.

This is an associative feature bank, not 500k LIF cells or an ARC solver.
It can order primitive families, but it cannot approve programs or see test labels.
Frozen S6 and NEXUS-0 never import it.
"""

from copy import deepcopy
from hashlib import blake2b

from echoai.seed import dsl
from echoai.seed.learn import Library


class SparsePrimitiveGuide:
    """Fixed sparse projection, trainable unsigned one-byte activation weights."""

    def __init__(self, units=500_000, names=None):
        if type(units) is not int or not 640 <= units <= 500_000:
            raise ValueError("capacity must be between 640 and 500000")
        self.names = tuple(names or sorted(dsl.NO_ARG | dsl.ONE_COLOR | dsl.TWO_COLOR))
        if not self.names or len(set(self.names)) != len(self.names):
            raise ValueError("primitive names must be unique")
        self.units = units
        self.weights = bytearray(units)
        self.examples = 0

    @staticmethod
    def features(task):
        """Only public demonstration pairs; colours are represented relationally."""
        pairs = task.get("train", ())
        if not pairs or len(pairs) > 10:
            raise ValueError("one to ten demonstrations required")
        groups = []
        for pair in pairs:
            a, b = dsl.G(pair["input"]), dsl.G(pair["output"])
            ha, wa, hb, wb = len(a), len(a[0]), len(b), len(b[0])
            same_shape = (ha, wa) == (hb, wb)
            changed = sum(x != y for ra, rb in zip(a, b) for x, y in zip(ra, rb)) if same_shape else -1
            size = ha * wa
            counts_a = sorted(sum(v == color for row in a for v in row) for color in dsl.palette(a))
            counts_b = sorted(sum(v == color for row in b for v in row) for color in dsl.palette(b))
            groups.append((
                f"size:{min(ha, 10)}:{min(wa, 10)}",
                f"out:{min(hb, 10)}:{min(wb, 10)}",
                f"ratio:{hb-ha}:{wb-wa}",
                f"shape:{int(same_shape)}:{int((ha,wa)==(wb,hb))}",
                f"change:{-1 if changed < 0 else min(8, 8*changed//size)}",
                f"colours:{len(counts_a)}:{len(counts_b)}",
                f"hist:{int(counts_a==counts_b)}",
                f"objects:{min(len(dsl.objects(a)), 8)}:{min(len(dsl.objects(b)), 8)}",
            ) + tuple(
                f"geom:{name}:{min(8, 8 * sum(x == y for ra, rb in zip(candidate, b) for x, y in zip(ra, rb)) // (hb * wb))}"
                for name in ("rot90", "rot180", "rot270", "fliplr", "flipud", "transpose")
                for candidate in (getattr(dsl, name)(a),)
                if (len(candidate), len(candidate[0])) == (hb, wb)
            ))
        return tuple(sorted(set.intersection(*(set(group) for group in groups))))

    def _indices(self, feature, name):
        token = (feature + "\0" + name).encode("utf-8")
        digest = blake2b(token, digest_size=32, person=b"ECHO45-KENYON").digest()
        return tuple(int.from_bytes(digest[i:i+4], "little") % self.units for i in range(0, 32, 4))

    def observe(self, task, program, library=None):
        """Learn only a program that replays every demonstration exactly."""
        library = library or Library()
        pairs = task.get("train", ())
        if not pairs or not program:
            raise ValueError("verified nonempty program required")
        for pair in pairs:
            result = dsl.G(pair["input"])
            for item in program:
                result = library.apply(result, item)
            if result != dsl.G(pair["output"]):
                raise ValueError("program does not fit every demonstration")
        labels = {Library.key(step) for item in program for step in library.expand(item)}
        labels = {name for name in labels if name in self.names}
        if not labels:
            raise ValueError("program has no recognized primitive")
        features = self.features(task)
        for name in labels:
            for feature in features:
                for index in self._indices(feature, name):
                    self.weights[index] = min(255, self.weights[index] + 1)
        self.examples += 1

    def probs(self, task):
        """Return a ranking hint in the existing Library.guide format."""
        features = self.features(task)
        scores = {name: sum(self.weights[index] for feature in features
                            for index in self._indices(feature, name)) for name in self.names}
        peak = max(scores.values())
        if not peak:
            return {name: 0.05 for name in self.names}
        return {name: 0.05 + 0.55 * score / peak for name, score in scores.items()}

    def guided_library(self, task, library=None):
        """Isolated optional attachment; original library and verifier unchanged."""
        result = deepcopy(library or Library())
        result.guide = self.probs(task)
        return result
