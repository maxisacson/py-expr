#!/usr/bin/env python3

import sys
import re
import subprocess
import math
from functools import wraps

TRACE = False


def trace(f):
    if not TRACE:
        return f

    @wraps(f)
    def wrapper(*args, **kwargs):
        print(f"{f.__name__} <- {args} {kwargs}")
        ret = f(*args, **kwargs)
        print(f"{f.__name__} -> {ret}")
        return ret

    return wrapper


class ExprError(BaseException):
    pass


class TokenError(ExprError):
    pass


class ParseError(ExprError):
    pass


class EvalError(ExprError):
    pass


def _print(context, *args):
    p = [a.eval(context) for a in args]
    print(*p)


def _ast(_, *args):
    if len(args) != 1:
        raise EvalError("ast: expected 1 argument")

    expr = args[0]
    draw_tree(expr, "ast")
    subprocess.run(["xdg-open", "ast.svg"])


COMMANDS = {
    'print': _print,
    'ast': _ast,
}


GLOBALS = {
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

    def _eval(self, context):
        if self.type is None:
            return self.left._eval(context)

        elif self.type == 'literal':
            return self.left

        elif self.type == '+':
            return binop_reduce(lambda x, y: x + y, context, self.left, self.right)

        elif self.type == '-':
            if self.left is None:
                return unop_reduce(lambda x: -x, context, self.right)

            return binop_reduce(lambda x, y: x - y, context, self.left, self.right)

        elif self.type == '*':
            return binop_reduce(lambda x, y: x * y, context, self.left, self.right)

        elif self.type == '/':
            return binop_reduce(lambda x, y: x / y, context, self.left, self.right)

        elif self.type == '^':
            return binop_reduce(lambda x, y: x ** y, context, self.left, self.right)

        elif self.type == '%':
            return binop_reduce(lambda x, y: x % y, context, self.left, self.right)

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
            GLOBALS[vname] = value

            return None

        elif self.type == ":=":
            fname = self.left.left
            param_list = self.left.right
            body = self.right

            def f(*args):
                return body._eval({k:v for k,v in zip(param_list, args)})

            GLOBALS[fname] = f

            return None

        elif self.type == 'cmd':
            cname = self.left
            params = self.right
            cmd = COMMANDS[cname]
            return cmd(context, *params)

        elif self.type == 'range':
            left = self.left._eval(context)
            right = self.right._eval(context)

            return list(range(left, right+1))

        elif self.type == 'list':
            return [x._eval(context) for x in self.left]

        raise EvalError(f"unknown expression type: {self.type}")

    def __repr__(self):
        return f"Expr({self.type}, {self.left}, {self.right})"


class Token:
    def __init__(self, type, value):
        self.type = type
        self.value = value

    def __repr__(self):
        return f"Token('{self.type}', {self.value})"


def tok_number(s):
    token = ""
    type = int
    while len(s) > 0 and re.match('[0-9]', s[0]):
        token += s[0]
        s = s[1:]

    if len(s) > 0 and s[0] == '.':
        if len(s) == 1 or len(s) > 1 and s[1] != '.':
            token += s[0]
            s = s[1:]
            type = float

    while len(s) > 0 and re.match('[0-9]', s[0]):
        token += s[0]
        s = s[1:]

    return Token('number', type(token)), s


def tok_ident_or_keyword(s):
    t, s = s[0], s[1:]

    if not re.match('[_a-zA-Z]', t):
        raise TokenError(f"unexpected token: {t}")

    token = t
    while len(s) > 0 and re.match("[_a-zA-Z0-9']", s[0]):
        token += s[0]
        s = s[1:]

    if token in COMMANDS:
        return Token('command', token), s

    return Token('identifier', token), s


def tok_range(s):
    token = ''

    for _ in range(2):
        t, s = s[0], s[1:]
        if t != '.':
            raise TokenError(f"unexpected token: {t}")
        token += t

    return Token('..', token), s


@trace
def tokenize(s):
    tokens = []

    while len(s) > 0:
        if re.match(r'\s', s[0]):
            s = s[1:]
            continue

        if s[0] == ';':
            if tokens and tokens[-1].type == ';':
                s = s[1:]
                continue

        if re.match(r'[-+*/^%,=\(\):;\[\]]', s[0]):
            t, s = s[0], s[1:]
            tokens.append(Token(t, None))
            continue

        if re.match('[0-9]', s[0]):
            token, s = tok_number(s)
            tokens.append(token)
            continue

        if re.match('[_a-zA-Z]', s[0]):
            token, s = tok_ident_or_keyword(s)
            tokens.append(token)
            continue

        if s[0] == '.':
            token, s = tok_range(s)
            tokens.append(token)
            continue

        raise TokenError(f"unexpected token: {s[0]}")

    return tokens


def peek(tokens, offset=0):
    if len(tokens) > offset:
        return tokens[offset]

    return Token(None, None)


@trace
def parse_params(tokens):
    params = []

    while True:
        p, tokens = parse_expr(tokens)
        params.append(p)
        if peek(tokens).type == ',':
            tokens.pop(0)
        else:
            break

    return params, tokens


@trace
def parse_command_args(tokens):
    args = []

    while True:
        p, tokens = parse_simple_stmnt(tokens)
        args.append(p)
        if peek(tokens).type == ',':
            tokens.pop(0)
        else:
            break

    return args, tokens


@trace
def parse_param_list(tokens):
    param_list = []

    while True:
        p = tokens.pop(0)
        if p.type != 'identifier':
            raise ParseError(f"unexpected token {p.type}")
        param_list.append(p.value)
        if peek(tokens).type == ',':
            tokens.pop(0)
        else:
            break

    return param_list, tokens


@trace
def parse_atom(tokens):
    next = tokens.pop(0)

    if next.type == 'identifier':
        if peek(tokens).type != '(':
            return Expr('var', next.value), tokens

        tokens.pop(0)
        if peek(tokens).type == ')':
            tokens.pop(0)
            return Expr('fcall', next.value, []), tokens

        params, tokens = parse_params(tokens)
        t = tokens.pop(0)
        if t.type != ')':
            raise ParseError(f"expected ) but found {t.type}")

        return Expr('fcall', next.value, params), tokens

    if next.type == '(':
        expr, tokens = parse_expr(tokens)

        if peek(tokens).type == ')':
            tokens = tokens[1:]
        else:
            raise ParseError("expected closing )")

        return expr, tokens

    if next.type == '[':
        exprs, tokens = parse_params(tokens)
        if peek(tokens).type != ']':
            raise ParseError('expected ]')
        tokens.pop(0)
        return Expr('list', exprs), tokens

    if next.type != 'number':
        raise ParseError("expected number")

    return Expr('literal', next.value), tokens


@trace
def parse_range(tokens):
    left, tokens = parse_expr(tokens)

    if peek(tokens).type != '..':
        raise ParseError('expected range expression')

    tokens.pop(0)

    right, tokens = parse_expr(tokens)

    return Expr('range', left, right), tokens


@trace
def parse_factor(tokens):
    if peek(tokens).type == '-':
        tokens = tokens[1:]
        right, tokens = parse_factor(tokens)
        return Expr('-', None, right), tokens

    left, tokens = parse_atom(tokens)

    if peek(tokens).type == '^':
        type, tokens = tokens[0].type, tokens[1:]
        right, tokens = parse_factor(tokens)
        left = Expr(type, left, right)

    return left, tokens


@trace
def parse_term(tokens):
    left, tokens = parse_factor(tokens)

    while tokens and tokens[0].type in ['*', '/', '%']:
        type, tokens = tokens[0].type, tokens[1:]
        right, tokens = parse_factor(tokens)
        left = Expr(type, left, right)

    return left, tokens


@trace
def parse_expr(tokens):
    left, tokens = parse_simple_expr(tokens)
    if peek(tokens).type == '..':
        tokens.pop(0)
        right, tokens = parse_expr(tokens)
        left = Expr('range', left, right)

    return left, tokens


@trace
def parse_simple_expr(tokens):
    left, tokens = parse_term(tokens)

    while tokens and tokens[0].type in ['+', '-']:
        type, tokens = tokens[0].type, tokens[1:]
        right, tokens = parse_term(tokens)
        left = Expr(type, left, right)

    return left, tokens


@trace
def parse_stmnt(tokens):
    stmnt, tokens = parse_simple_stmnt(tokens)
    if peek(tokens).type == ';':
        tokens.pop(0)
    return stmnt, tokens


@trace
def parse_simple_stmnt(tokens):
    if peek(tokens).type == 'command':
        left = tokens.pop(0)
        next = peek(tokens)
        if next.type is None or next.type == ';':
            params = []
        else:
            params, tokens = parse_command_args(tokens)
        return Expr('cmd', left.value, params), tokens

    elif peek(tokens).type == 'identifier' and peek(tokens, 1).type in ['=', ':']:
        ident = tokens.pop(0)
        if ident.type != 'identifier':
            raise ParseError(f"unexpected token: {ident.type}")

        left = Expr('var', ident.value)

        t = tokens.pop(0)
        if t.type == '=':
            expr, tokens = parse_expr(tokens)

            return Expr('=', left, expr), tokens

        elif t.type == ':':
            if peek(tokens).type == '=':
                param_list = []
            else:
                param_list, tokens = parse_param_list(tokens)

            left.right = param_list

            t = tokens.pop(0)
            if t.type != '=':
                raise ParseError(f"unexpected token: {t.type}")

            expr, tokens = parse_expr(tokens)

            return Expr(':=', left, expr), tokens

        raise ParseError(f"unexpected token: {t.type}")

    return parse_expr(tokens)


@trace
def parse_stmnts(tokens):
    roots = []
    while tokens:
        stmnt, tokens = parse_stmnt(tokens)
        roots.append(stmnt)

    return roots, tokens


def parse(tokens):
    # stmnts: stmnt+
    # stmnt: simple_stmnt, ';'?
    # simple_stmnt:
    #   | 'command', command_args?
    #   | 'identifier', '=', expr
    #   | 'identifier', ':', param_list?, '=', expr
    #   | expr
    # param_list: 'identifier', { ',', identifier }
    # expr:
    #   | simple_expr, [ '..', simple_expr ]
    # simple_expr:
    #   | term, { '+' | '-', term }
    # term: factor, { '*' | '/' | '%', factor }
    # factor:
    #   | '-', factor
    #   | atom, [ '^', factor ]
    # atom:
    #   | 'identifier', [ '(', params?, ')' ]
    #   | '(', expr, ')'
    #   | '[', params?, ']'
    #   | 'number'
    # params: expr, { ',', expr }
    # command_args: simple_stmnt, { ',', simple_stmnt }

    roots, tokens = parse_stmnts(tokens)

    if tokens:
        raise ParseError(f"unexpected tokens: {tokens[0]}")

    return roots


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
                else:
                    f.write(f'v{n.id}[label="{n.type}"];\n')

            if n.type == 'fcall':
                children = n.right
            elif n.type == 'list':
                children = n.left
            elif n.type == 'cmd':
                children = n.right
            else:
                children = [n.left, n.right]

            for m in children:
                if not isinstance(m, Expr):
                    continue

                f.write(f'v{n.id} -- v{m.id};\n')
                queue.append(m)

        f.write("}\n")

    subprocess.run(["dot", "-Tsvg", f"-o{fname}.svg", f"{fname}.dot"])


def parse_expression(s):
    tokens = tokenize(s)
    expr = parse(tokens)
    return expr


def _main(argv):
    if len(argv) < 2:
        program = []
        for line in sys.stdin:
            exprs = parse_expression(line)

            if sys.stdin.isatty():
                for expr in exprs:
                    result = expr.eval()
                    if result is not None:
                        GLOBALS['_'] = result
                        GLOBALS['ans'] = result
                        print('=', result)
            else:
                program += exprs
    else:
        assignments = []
        expressions = []

        for e in argv[1:]:
            exprs = parse_expression(e)
            if len(exprs) == 1 and exprs[0].type == '=':
                assignments += exprs
            else:
                expressions += exprs

        program = assignments + expressions

    result = None
    for expr in program:
        draw_tree(expr)
        result = expr.eval()

    if result is not None:
        print(result)


def main(argv):
    try:
        _main(argv)
    except ExprError as e:
        print(f'Error: {e}')
        exit(1)


if __name__ == "__main__":
    main(sys.argv)
