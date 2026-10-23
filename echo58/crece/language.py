"""A bounded integer AST interpreter. Model text is never exec/eval/compiled."""
from __future__ import annotations
import ast
from dataclasses import dataclass
from . import runtime as R

MAX_INT, MAX_ITEMS, MAX_OPS = 2**31 - 1, 4096, 50000
FIELDS = {'pos', 'dir', 'hand', 'absolute', 'grid', 'progress', 'idle', 'steps', 'wall', 'floor'}
METHODS = {'picked', 'opened', 'visits', 'note', 'belief', 'reach', 'ids_near'}
CONTEXT = {'intent', 'drop_for', 'out', 'dropped_here', 'avoid'}
CONSTANTS = {name: getattr(R, name) for name in ('DECIDE', 'OUTCOME', 'DROP', 'IDLE', 'ENTER', 'PICK',
             'TOGGLE', 'DROP_ACTION', 'UNKNOWN', 'PASS', 'NOOP', 'HURT', 'PICKED', 'OPEN', 'GOAL',
             'EPISODE', 'HAND', 'ANY', 'DIRS')}
EFFECTS = {name: getattr(R, name) for name in ('BAN', 'BAN_UNTIL_PROGRESS', 'DROP_AT', 'GOTO', 'NOTE')}
BUILTINS = {'len', 'abs', 'min', 'max', 'sum', 'tuple', 'frozenset', 'sorted', 'range', 'int', 'all', 'any'}
ALLOWED = (ast.Module, ast.FunctionDef, ast.arguments, ast.arg, ast.Return, ast.Assign, ast.AugAssign,
           ast.If, ast.For, ast.Break, ast.Continue, ast.Pass, ast.Expr, ast.Name, ast.Load, ast.Store,
           ast.Constant, ast.Tuple, ast.List, ast.Set, ast.Subscript, ast.Slice, ast.Attribute, ast.Call,
           ast.keyword, ast.IfExp, ast.UnaryOp, ast.BinOp, ast.BoolOp, ast.Compare, ast.Lambda,
           ast.GeneratorExp, ast.ListComp, ast.SetComp, ast.comprehension,
           ast.Add, ast.Sub, ast.Mult, ast.FloorDiv, ast.Mod, ast.USub, ast.UAdd, ast.Not,
           ast.And, ast.Or, ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.In, ast.NotIn,
           ast.Is, ast.IsNot)


class InvalidProgram(ValueError):
    pass


class LimitExceeded(ValueError):
    pass


class Returned(Exception):
    def __init__(self, value):
        self.value = value


class BreakLoop(Exception):
    pass


class ContinueLoop(Exception):
    pass


@dataclass(frozen=True, eq=False)
class Closure:
    node: object
    env: dict


def checked(value, charge=None):
    remaining = MAX_ITEMS
    def visit(item, depth=0):
        nonlocal remaining
        remaining -= 1
        if charge is not None:
            charge()
        if remaining < 0 or depth > 32:
            raise LimitExceeded('nested collection size/depth')
        if isinstance(item, int):
            if abs(item) > MAX_INT:
                raise LimitExceeded('integer range')
        elif isinstance(item, (tuple, list, frozenset, range)):
            if len(item) > MAX_ITEMS:
                raise LimitExceeded('collection length')
            for child in item:
                visit(child, depth + 1)
        elif item is not None and not isinstance(item, slice):
            raise InvalidProgram('unsupported value')
    visit(value)
    return value


class Program:
    def __init__(self, source):
        if type(source) is not str or len(source) > 12000:
            raise InvalidProgram('source size')
        self.source = source
        try:
            tree = ast.parse(source)
        except (SyntaxError, RecursionError) as exc:
            raise InvalidProgram('syntax') from exc
        nodes = list(ast.walk(tree))
        parents = {child: node for node in nodes for child in ast.iter_child_nodes(node)}
        if len(nodes) > 2000:
            raise InvalidProgram('AST size')
        def depth(node):
            return 1 + max((depth(child) for child in ast.iter_child_nodes(node)), default=0)
        if depth(tree) > 32:
            raise InvalidProgram('AST depth')
        if len(tree.body) != 1 or not isinstance(tree.body[0], ast.FunctionDef):
            raise InvalidProgram('one function required')
        self.function = tree.body[0]
        f = self.function
        if (f.name != 'piece' or f.decorator_list or f.returns or f.type_comment or f.type_params
                or [a.arg for a in f.args.args] != ['moment', 'v', 'c'] or f.args.posonlyargs
                or f.args.kwonlyargs or f.args.defaults or f.args.vararg or f.args.kwarg):
            raise InvalidProgram('signature must be piece(moment, v, c)')
        for node in nodes:
            if not isinstance(node, ALLOWED):
                raise InvalidProgram('unsupported AST node: ' + type(node).__name__)
            if isinstance(node, ast.FunctionDef) and node is not f:
                raise InvalidProgram('nested function')
            if isinstance(node, ast.arg) and (node.annotation or node.arg.startswith('_')):
                raise InvalidProgram('invalid argument')
            if isinstance(node, ast.Constant) and (node.value is not None and type(node.value) not in (int, bool)):
                raise InvalidProgram('only integer constants')
            if isinstance(node, ast.Constant):
                checked(node.value)
            if isinstance(node, ast.Name):
                if node.id.startswith('_') or len(node.id) > 48:
                    raise InvalidProgram('invalid identifier')
                if isinstance(node.ctx, ast.Store) and node.id in set(CONSTANTS) | set(EFFECTS) | BUILTINS | {'v', 'c', 'moment'}:
                    raise InvalidProgram('reserved binding')
            if isinstance(node, ast.Attribute):
                if not isinstance(node.value, ast.Name):
                    raise InvalidProgram('attribute chaining')
                allowed = FIELDS | METHODS if node.value.id == 'v' else CONTEXT if node.value.id == 'c' else set()
                if node.attr not in allowed or not isinstance(node.ctx, ast.Load):
                    raise InvalidProgram('attribute forbidden')
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id not in set(EFFECTS) | BUILTINS:
                        raise InvalidProgram('call forbidden')
                elif isinstance(node.func, ast.Attribute):
                    if not isinstance(node.func.value, ast.Name) or node.func.value.id != 'v' or node.func.attr not in METHODS:
                        raise InvalidProgram('method forbidden')
                else:
                    raise InvalidProgram('dynamic call forbidden')
                if any(k.arg is None for k in node.keywords):
                    raise InvalidProgram('keyword expansion forbidden')
            if isinstance(node, (ast.Assign, ast.AugAssign, ast.For, ast.comprehension)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    if any(not isinstance(n, (ast.Name, ast.Tuple, ast.List, ast.Store)) for n in ast.walk(target)):
                        raise InvalidProgram('mutation target forbidden')
            if isinstance(node, ast.comprehension) and node.is_async:
                raise InvalidProgram('async forbidden')
            if isinstance(node, ast.Lambda) and (node.args.defaults or node.args.vararg or node.args.kwarg
                                                or node.args.kwonlyargs or node.args.posonlyargs):
                raise InvalidProgram('lambda signature')
            if isinstance(node, ast.Lambda):
                keyword = parents.get(node)
                call = parents.get(keyword)
                if (not isinstance(keyword, ast.keyword) or keyword.arg != 'key'
                        or not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name)
                        or call.func.id not in ('sorted', 'min', 'max')):
                    raise InvalidProgram('lambda only as direct selection key')

    def __call__(self, moment, view, context):
        runner = Evaluator(view, context)
        try:
            runner.block(self.function.body, {'moment': moment})
        except Returned as result:
            return checked(result.value)
        return None


class Evaluator:
    def __init__(self, view, context):
        self.view, self.context, self.ops = view, context, 0

    def value(self, value):
        return checked(value, self.tick)

    def tick(self, n=1):
        self.ops += n
        if self.ops > MAX_OPS:
            raise LimitExceeded('operation budget')

    def seq(self, value):
        if not isinstance(value, (tuple, list, frozenset, range)):
            raise InvalidProgram('not a collection')
        self.value(value)
        self.tick(len(value))
        return value

    def bind(self, target, value, env):
        self.value(value)
        if isinstance(target, ast.Name):
            env[target.id] = value
        else:
            value = self.seq(value)
            if len(target.elts) != len(value):
                raise InvalidProgram('unpack length')
            for t, v in zip(target.elts, value):
                self.bind(t, v, env)

    def binary(self, op, a, b):
        if isinstance(op, ast.Add):
            if isinstance(a, (tuple, list)) and isinstance(b, type(a)) and len(a) + len(b) > MAX_ITEMS:
                raise LimitExceeded('collection sum')
            result = a + b
        elif isinstance(op, ast.Mult):
            seq, count = (a, b) if isinstance(a, (tuple, list)) else (b, a)
            if isinstance(seq, (tuple, list)) and isinstance(count, int) and len(seq) * max(0, count) > MAX_ITEMS:
                raise LimitExceeded('collection product')
            result = a * b
        elif isinstance(op, ast.Sub):
            result = a - b
        elif isinstance(op, ast.FloorDiv):
            result = a // b
        elif isinstance(op, ast.Mod):
            result = a % b
        else:
            raise InvalidProgram('operator')
        return self.value(result)

    def expression(self, node, env):
        self.tick()
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            return env[node.id] if node.id in env else CONSTANTS[node.id]
        if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
            values = tuple(self.expression(n, env) for n in node.elts)
            return self.value(frozenset(values) if isinstance(node, ast.Set) else values)
        if isinstance(node, ast.Attribute):
            obj = self.view if node.value.id == 'v' else self.context
            if node.attr in METHODS:
                raise InvalidProgram('method cannot be retained as a value')
            return self.value(getattr(obj, node.attr))
        if isinstance(node, ast.Subscript):
            value = self.expression(node.value, env)
            index = self.expression(node.slice, env)
            return self.value(value[index])
        if isinstance(node, ast.Slice):
            return slice(*(self.expression(n, env) if n is not None else None for n in (node.lower, node.upper, node.step)))
        if isinstance(node, ast.UnaryOp):
            value = self.expression(node.operand, env)
            return self.value(not value if isinstance(node.op, ast.Not) else -value if isinstance(node.op, ast.USub) else +value)
        if isinstance(node, ast.BinOp):
            return self.binary(node.op, self.expression(node.left, env), self.expression(node.right, env))
        if isinstance(node, ast.BoolOp):
            result = None
            for n in node.values:
                result = self.expression(n, env)
                if (isinstance(node.op, ast.And) and not result) or (isinstance(node.op, ast.Or) and result):
                    break
            return result
        if isinstance(node, ast.Compare):
            a = self.expression(node.left, env)
            for op, right in zip(node.ops, node.comparators):
                b = self.expression(right, env)
                if isinstance(op, (ast.In, ast.NotIn)):
                    self.seq(b)
                result = (a == b if isinstance(op, ast.Eq) else a != b if isinstance(op, ast.NotEq)
                          else a < b if isinstance(op, ast.Lt) else a <= b if isinstance(op, ast.LtE)
                          else a > b if isinstance(op, ast.Gt) else a >= b if isinstance(op, ast.GtE)
                          else a in b if isinstance(op, ast.In) else a not in b if isinstance(op, ast.NotIn)
                          else a is b if isinstance(op, ast.Is) else a is not b)
                if not result:
                    return False
                a = b
            return True
        if isinstance(node, ast.IfExp):
            return self.expression(node.body if self.expression(node.test, env) else node.orelse, env)
        if isinstance(node, ast.Lambda):
            return Closure(node, dict(env))
        if isinstance(node, (ast.GeneratorExp, ast.ListComp, ast.SetComp)):
            output = []
            def visit(index, local):
                if index == len(node.generators):
                    if len(output) >= MAX_ITEMS:
                        raise LimitExceeded('comprehension length')
                    output.append(self.expression(node.elt, local))
                    return
                gen = node.generators[index]
                for value in self.seq(self.expression(gen.iter, local)):
                    self.tick()
                    child = dict(local)
                    self.bind(gen.target, value, child)
                    if all(self.expression(cond, child) for cond in gen.ifs):
                        visit(index + 1, child)
            visit(0, dict(env))
            return self.value(frozenset(output) if isinstance(node, ast.SetComp) else tuple(output))
        if isinstance(node, ast.Call):
            args = [self.expression(a, env) for a in node.args]
            kwargs = {k.arg: self.expression(k.value, env) for k in node.keywords}
            if isinstance(node.func, ast.Attribute):
                self.tick(len(self.view.grid) * len(self.view.grid[0]))
                return self.value(getattr(self.view, node.func.attr)(*args, **kwargs))
            name = node.func.id
            if name in EFFECTS:
                return self.value(EFFECTS[name](*args, **kwargs))
            return self.builtin(name, args, kwargs)
        raise InvalidProgram('expression unsupported')

    def key(self, closure, value):
        if not isinstance(closure, Closure) or len(closure.node.args.args) != 1:
            raise InvalidProgram('key must be a unary lambda')
        env = dict(closure.env)
        env[closure.node.args.args[0].arg] = value
        return self.expression(closure.node.body, env)

    def builtin(self, name, args, kwargs):
        if name in ('sorted', 'min', 'max'):
            if set(kwargs) - {'key', 'default', 'reverse'}:
                raise InvalidProgram('invalid selection argument')
            values = self.seq(args[0]) if len(args) == 1 else self.seq(tuple(args))
            self.tick(len(values) * max(1, len(values).bit_length()))
            key = (lambda x: self.key(kwargs['key'], x)) if 'key' in kwargs else None
            if name == 'sorted':
                return self.value(tuple(sorted(values, key=key, reverse=bool(kwargs.get('reverse', False)))))
            if not values and 'default' in kwargs:
                return kwargs['default']
            return self.value((min if name == 'min' else max)(values, key=key))
        if kwargs:
            raise InvalidProgram('unexpected keyword')
        if name == 'range':
            value = range(*args)
            if len(value) > 256:
                raise LimitExceeded('range length')
            return value
        if name in ('tuple', 'frozenset'):
            return self.value((tuple if name == 'tuple' else frozenset)(self.seq(args[0])))
        if name in ('sum', 'all', 'any'):
            values = self.seq(args[0])
            if name == 'sum':
                total = args[1] if len(args) > 1 else 0
                for value in values:
                    total = self.binary(ast.Add(), total, value)
                return total
            return (all if name == 'all' else any)(values)
        if len(args) != 1:
            raise InvalidProgram('builtin arity')
        return self.value(len(self.seq(args[0])) if name == 'len' else abs(args[0]) if name == 'abs' else int(args[0]))

    def block(self, statements, env):
        for node in statements:
            self.tick()
            if isinstance(node, ast.Return):
                raise Returned(self.expression(node.value, env) if node.value else None)
            if isinstance(node, ast.Assign):
                value = self.expression(node.value, env)
                for target in node.targets:
                    self.bind(target, value, env)
            elif isinstance(node, ast.AugAssign):
                if not isinstance(node.target, ast.Name):
                    raise InvalidProgram('augmented target')
                self.bind(node.target, self.binary(node.op, env[node.target.id], self.expression(node.value, env)), env)
            elif isinstance(node, ast.If):
                self.block(node.body if self.expression(node.test, env) else node.orelse, env)
            elif isinstance(node, ast.For):
                broken = False
                for value in self.seq(self.expression(node.iter, env)):
                    self.tick()
                    self.bind(node.target, value, env)
                    try:
                        self.block(node.body, env)
                    except ContinueLoop:
                        continue
                    except BreakLoop:
                        broken = True
                        break
                if not broken:
                    self.block(node.orelse, env)
            elif isinstance(node, ast.Break):
                raise BreakLoop()
            elif isinstance(node, ast.Continue):
                raise ContinueLoop()
            elif isinstance(node, ast.Expr):
                self.expression(node.value, env)
            elif not isinstance(node, (ast.Pass, ast.Assign)):
                raise InvalidProgram('statement unsupported')
