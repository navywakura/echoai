"""CONT-B closed graph codec. CONT-A's source-pinned codec stays untouched.

This is executor serialization, not another agent/memory implementation.
Only statically supplied inert classes may be reconstructed. No code imports
or object constructors are selected by checkpoint contents.
"""
from echoai.echo4.boundary import integer
from echoai.echo4.continuity import MAX_OBJECTS, MAX_VALUES, _attributes


class GraphCodec:
    def __init__(self, registry):
        self.registry = dict(registry)
        self.tags = {cls: tag for tag, (cls, _) in self.registry.items()}
        if len(self.tags) != len(self.registry):
            raise ValueError("duplicate class registration")

    def encode(self, root):
        records, identities, containers = [], {}, set()
        count = 0

        def visit(value, depth=0):
            nonlocal count
            count += 1
            if depth > 64 or count > MAX_VALUES:
                raise ValueError("graph exceeds structural budget")
            kind = type(value)
            if value is None or kind in (str, bool):
                return value
            if kind is int:
                if value.bit_length() > 64:
                    raise ValueError("integer exceeds budget")
                return value
            if kind in (list, dict, set, bytearray):
                if id(value) in containers:
                    raise ValueError("aliased/cyclic mutable container")
                containers.add(id(value))
            if kind in (bytes, bytearray):
                return {kind.__name__: value.hex()}
            if kind in (list, tuple):
                data = [visit(item, depth + 1) for item in value]
                return data if kind is list else {"tuple": data}
            if kind is set:
                if any(type(item) is not int for item in value):
                    raise ValueError("only integer sets are supported")
                return {"set": [visit(item, depth + 1) for item in sorted(value)]}
            if kind is dict:
                return {"map": [[visit(k, depth + 1), visit(v, depth + 1)]
                                for k, v in value.items()]}
            if kind not in self.tags:
                raise ValueError("unsupported graph class")
            if id(value) not in identities:
                if len(records) >= MAX_OBJECTS:
                    raise ValueError("too many graph objects")
                index = len(records)
                identities[id(value)] = index
                tag = self.tags[kind]
                record = {"type": tag, "fields": {}}
                records.append(record)
                record["fields"] = {k: visit(v, depth + 1) for k, v in
                                    _attributes(value, self.registry[tag][1]).items()}
            return {"ref": identities[id(value)]}

        encoded = visit(root)
        return {"root": encoded, "objects": records}

    def decode(self, graph):
        if type(graph) is not dict or set(graph) != {"root", "objects"}:
            raise ValueError("invalid graph envelope")
        records = graph["objects"]
        if type(records) is not list or not 1 <= len(records) <= MAX_OBJECTS:
            raise ValueError("invalid object budget")
        objects = []
        for record in records:
            if type(record) is not dict or set(record) != {"type", "fields"}:
                raise ValueError("invalid object record")
            tag = record["type"]
            if type(tag) is not str or tag not in self.registry:
                raise ValueError("unknown graph class")
            cls, names = self.registry[tag]
            if type(record["fields"]) is not dict or set(record["fields"]) != set(names):
                raise ValueError("invalid class fields")
            objects.append(object.__new__(cls))
        count = 0

        def visit(value, depth=0):
            nonlocal count
            count += 1
            if depth > 64 or count > MAX_VALUES:
                raise ValueError("graph exceeds structural budget")
            kind = type(value)
            if value is None or kind in (str, bool):
                return value
            if kind is int:
                if value.bit_length() > 64:
                    raise ValueError("integer exceeds budget")
                return value
            if kind is list:
                return [visit(v, depth + 1) for v in value]
            if kind is not dict or len(value) != 1:
                raise ValueError("invalid value tag")
            tag, item = next(iter(value.items()))
            if tag == "ref":
                integer(item, 0, len(objects) - 1)
                return objects[item]
            if tag in ("bytes", "bytearray") and type(item) is str:
                raw = bytes.fromhex(item)
                return raw if tag == "bytes" else bytearray(raw)
            if tag == "tuple" and type(item) is list:
                return tuple(visit(v, depth + 1) for v in item)
            if tag == "set" and type(item) is list:
                if any(type(v) is not int for v in item) or item != sorted(set(item)):
                    raise ValueError("noncanonical integer set")
                return {visit(v, depth + 1) for v in item}
            if tag == "map" and type(item) is list:
                result = {}
                for pair in item:
                    if type(pair) is not list or len(pair) != 2:
                        raise ValueError("invalid map pair")
                    key, val = (visit(v, depth + 1) for v in pair)
                    if key in result:
                        raise ValueError("duplicate map key")
                    result[key] = val
                return result
            raise ValueError("invalid graph value")

        for obj, record in zip(objects, records):
            for name, value in record["fields"].items():
                object.__setattr__(obj, name, visit(value))
        root = visit(graph["root"])
        if self.encode(root) != graph:
            raise ValueError("noncanonical/unreachable graph objects")
        return root
