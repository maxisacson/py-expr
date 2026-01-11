from .common import EvalError, trace
import subprocess
import math


def _table(context, *args):
    cols = []
    rows = 0
    for a in args:
        y = a.eval(context)
        if isinstance(y, list):
            cols.append(y)
        else:
            cols.append([y])

        n = len(cols[-1])
        if rows > 1 and n != rows and n != 1:
            raise EvalError("print: arguments have to be either size 1 or size N")

        rows = max(rows, n)

    for i,c in enumerate(cols):
        if len(c) < rows:
            cols[i] = [c[0]] * rows

    for row in zip(*cols):
        print(*row)


def _print(context, *args):
    p = [a.eval(context) for a in args]
    print(*p)


def _sum(context, *args):
    if len(args) == 1:
        expr, = args
    else:
        init, expr, = args
        init.eval(context)

    v = expr.eval(context)

    if isinstance(v, list):
        return sum(v)
    return v


def _prod(context, *args):
    if len(args) == 1:
        expr, = args
    else:
        init, expr, = args
        init.eval(context)

    v = expr.eval(context)

    if isinstance(v, list):
        return math.prod(v)
    return v


COMMANDS = {
    'print': _print,
    'table': _table,
    'sum': _sum,
    'prod': _prod,
}

KEYWORDS = {
    'if',
    'and',
    'or',
    'not',
    'for',
    'in',
}


GLOBALS = {
    'nil': None,
    'sin': math.sin,
    'cos': math.cos,
    'tan': math.tan,
    'asin': math.asin,
    'acos': math.acos,
    'atan': math.atan,
    'sqrt': math.sqrt,
    'exp': math.exp,
    'pi': math.pi,
    'e': math.e,
}


def binop_reduce(op, context, left, right):
    if isinstance(left, Expr):
        return binop_reduce(op, context, left.eval(context), right)

    if isinstance(right, Expr):
        return binop_reduce(op, context, left, right.eval(context))

    if isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            raise EvalError('expected lists to have the same length')
        return [op(x, y) for (x, y) in zip(left, right)]
    elif isinstance(left, list):
        return [op(x, right) for x in left]
    elif isinstance(right, list):
        return [op(left, x) for x in right]

    return op(left, right)


def unop_reduce(op, context, right):
    if isinstance(right, Expr):
        return unop_reduce(op, context, right.eval(context))

    if isinstance(right, list):
        return [op(x) for x in right]

    return op(right)


def func_reduce(f, context, *args):
    for i,arg in enumerate(args):
        if isinstance(arg, Expr):
            return func_reduce(f, context, *args[:i], arg.eval(context), *args[i+1:])

    k = 0
    count = 0
    for i,arg in enumerate(args):
        if isinstance(arg, list):
            k = i
            count += 1

    if count == 0:
        return f(*args)

    if count == 1:
        return [f(*args[:k], x, *args[k+1:]) for x in args[k]]

    if count == len(args):
        return [f(*a) for a in zip(*args)]

    raise EvalError('expected 0, 1, or all arguments to be list')


class Expr:
    ID = 0

    def __init__(self, type, left, right=None):
        self.type = type
        self.left = left
        self.right = right
        self.id = Expr.ID
        Expr.ID += 1

    def eval(self, context={}):
        return self._eval(context)

    @trace
    def _eval(self, context):
        if self.type is None:
            return self.left._eval(context)

        elif self.type == 'stmnts' or self.type == 'block':
            result = None
            for s in self.left:
                result = s._eval(context)
            return result

        elif self.type == 'literal':
            return self.left

        elif self.type == '+':
            return binop_reduce(lambda x, y: x + y, context, self.left, self.right)

        elif self.type == '-':
            if self.right is None:
                return unop_reduce(lambda x: -x, context, self.left)

            return binop_reduce(lambda x, y: x - y, context, self.left, self.right)

        elif self.type == '*':
            return binop_reduce(lambda x, y: x * y, context, self.left, self.right)

        elif self.type == '/':
            return binop_reduce(lambda x, y: x / y, context, self.left, self.right)

        elif self.type == '^':
            return binop_reduce(lambda x, y: x ** y, context, self.left, self.right)

        elif self.type == '%':
            return binop_reduce(lambda x, y: x % y, context, self.left, self.right)

        elif self.type == '<':
            return binop_reduce(lambda x, y: x < y, context, self.left, self.right)

        elif self.type == '>':
            return binop_reduce(lambda x, y: x > y, context, self.left, self.right)

        elif self.type == '<=':
            return binop_reduce(lambda x, y: x <= y, context, self.left, self.right)

        elif self.type == '>=':
            return binop_reduce(lambda x, y: x >= y, context, self.left, self.right)

        elif self.type == '==':
            return binop_reduce(lambda x, y: x == y, context, self.left, self.right)

        elif self.type == '!=':
            return binop_reduce(lambda x, y: x != y, context, self.left, self.right)

        elif self.type == '#':
            value = self.left._eval(context)
            return len(value)

        elif self.type == 'fcall':
            fname = self.left
            params = self.right

            if fname in context:
                func = context[fname]
            else:
                func = GLOBALS[fname]

            return func_reduce(func, context, *params)

        elif self.type == 'var':
            vname = self.left

            if vname in context:
                value = context[vname]
            else:
                value = GLOBALS[vname]

            return value

        elif self.type == '=':
            vname = self.left.left
            value = self.right._eval(context)
            if vname in context:
                context[vname] = value
            else:
                GLOBALS[vname] = value

            return value

        elif self.type == ":=":
            fname = self.left.left
            plist = self.left.right
            body = self.right

            if not all(map(lambda p: p.type == 'var', plist)):
                raise EvalError("expected parameter names")

            def f(*args):
                ctx = {p.left: a for p, a in zip(plist, args)}
                return body._eval(ctx)

            GLOBALS[fname] = f

            return None

        elif self.type == 'cmd':
            cname = self.left
            params = self.right
            cmd = COMMANDS[cname]
            return cmd(context, *params)

        elif self.type == 'range':
            if isinstance(self.left, list):
                left = self.left[0]._eval(context)
                right = self.left[1]._eval(context)
                step = self.right[0]._eval(context)
                type = self.right[1]
            else:
                left = self.left._eval(context)
                right = self.right._eval(context)
                step = 'auto'
                type = 'count'

            if isinstance(left, int) and isinstance(right, int):
                if type == 'count' and step == 'auto':
                    return list(range(left, right+1, 1))
                elif type == 'incr' and isinstance(step, int):
                    return list(range(left, right+1, step))
                elif type == 'count' and isinstance(step, int):
                    count = step
                    if (right - left) % (count - 1) == 0:
                        step = (right - left) // (count - 1)
                        return list(range(left, right+1, step))

            if type == 'count':
                if step == 'auto':
                    count = 50
                else:
                    count = step
                step = (right - left) / (count - 1)
                return [left + i*step for i in range(count)]
            elif type == 'incr':
                if step == 'auto':
                    count = 50
                    step = (right - left) / (count - 1)
                    return [left + i*step for i in range(count)]
                else:
                    def g():
                        x = left
                        while x <= right:
                            yield x
                            x += step
                    return list(g())

            raise EvalError(f"Error: unknown range type: {type}")

        elif self.type == 'list':
            return [x._eval(context) for x in self.left]

        elif self.type == 'if':
            cond = self.right._eval(context)
            if cond:
                return self.left._eval(context)

            return None

        elif self.type == 'cases':
            cases = self.left
            for x in cases:
                result = x._eval(context)
                if result is not None:
                    return result

            return None

        elif self.type == 'or':
            return self.left._eval(context) or self.right._eval(context)

        elif self.type == 'and':
            return self.left._eval(context) and self.right._eval(context)

        elif self.type == 'not':
            return not self.left._eval(context)

        elif self.type == 'idx':
            vname = self.left
            idx = self.right._eval(context)

            if vname in context:
                value = context[vname][idx-1]
            else:
                value = GLOBALS[vname][idx-1]

            return value

        elif self.type == 'lchain':
            lhs = self.left

            result = True

            left = lhs._eval(context)
            for rhs in self.right:
                right = rhs.left._eval(context)
                expr = Expr(rhs.type, left, right)
                result = result and expr._eval(context)
                left = right

            return result

        elif self.type == 'for':
            var, expr = self.left
            vname = var.left
            body = self.right

            if vname in context:
                ctx = context
            else:
                ctx = GLOBALS

            values = expr._eval(context)
            for value in values:
                ctx[vname] = value
                body._eval(context)

            return None


        else:
            raise EvalError(f"unknown expression type: {self.type}")

    def __repr__(self):
        return f"Expr({self.type}, {self.left}, {self.right})"


def draw_tree(root, fname="tree"):
    ids = set()

    with open(f"{fname}.dot", 'w') as f:
        f.write("graph {\n")

        queue = [root]
        while queue:
            n = queue.pop()
            if n.id not in ids:
                if n.type == 'literal':
                    f.write(f'v{n.id}[label="{n.left}"];\n')

                elif n.type == 'fcall':
                    f.write(f'v{n.id}[label="{n.left}()"];\n')

                elif n.type == 'var':
                    f.write(f'v{n.id}[label="{n.left}"];\n')

                elif n.type == 'cmd':
                    f.write(f'v{n.id}[label="{n.left}"];\n')

                elif n.type == 'range':
                    if isinstance(n.right, list) and n.right[1] == 'incr':
                        f.write(f'v{n.id}[label="{n.type}+"];\n')
                    else:
                        f.write(f'v{n.id}[label="{n.type}"];\n')

                elif n.type == 'idx':
                    f.write(f'v{n.id}[label="{n.left}[]"];\n')

                else:
                    f.write(f'v{n.id}[label="{n.type}"];\n')

            if n.type == 'fcall':
                children = n.right
            elif n.type == 'list':
                children = n.left
            elif n.type == 'cmd':
                children = n.right
            elif n.type == 'range':
                if isinstance(n.left, list):
                    children = n.left + n.right
                else:
                    children = [n.left, n.right]
            elif n.type == 'cases':
                children = n.left + [n.right]
            elif n.type == 'idx':
                children = [n.right]
            elif n.type == 'stmnts':
                children = n.left
            elif n.type == 'block':
                children = n.left
            elif n.type == 'lchain':
                children = [n.left] + n.right
            elif n.type == 'for':
                children = n.left + [n.right]
            else:
                children = [n.left, n.right]

            for m in children:
                if not isinstance(m, Expr):
                    continue

                f.write(f'v{n.id} -- v{m.id};\n')
                queue.append(m)

        f.write("}\n")

    subprocess.run(["dot", "-Tsvg", f"-o{fname}.svg", f"{fname}.dot"])
