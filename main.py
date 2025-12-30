#!/usr/bin/env python3

import sys
import re
import subprocess
import math


class TokenError(RuntimeError):
    pass


class ParseError(RuntimeError):
    pass


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


class Expr:
    ID = 0

    def __init__(self, type, left, right=None):
        self.type = type
        self.left = left
        self.right = right
        self.id = Expr.ID
        Expr.ID += 1

    def eval(self, context={}):
        if self.type is None:
            return self.left.eval(context)

        if self.type == 'literal':
            return self.left

        if self.type == '+':
            return self.left.eval(context) + self.right.eval(context)

        if self.type == '-':
            if self.left is None:
                return -self.right.eval(context)
            return self.left.eval(context) - self.right.eval(context)

        if self.type == '*':
            return self.left.eval(context) * self.right.eval(context)

        if self.type == '/':
            return self.left.eval(context) / self.right.eval(context)

        if self.type == '^':
            return self.left.eval(context) ** self.right.eval(context)

        if self.type == '%':
            return self.left.eval(context) % self.right.eval(context)

        if self.type == 'fcall':
            fname = self.left
            params = self.right

            if fname in context:
                func = context[fname]
            else:
                func = GLOBALS[fname]

            return func(*(p.eval() for p in params))

        if self.type == 'var':
            vname = self.left

            if vname in context:
                value = context[vname]
            else:
                value = GLOBALS[vname]

            return value

        if self.type == 'assign':
            vname = self.left
            value = self.right.eval()
            GLOBALS[vname] = value

            return value

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
        token += s[0]
        s = s[1:]
        type = float

    while len(s) > 0 and re.match('[0-9]', s[0]):
        token += s[0]
        s = s[1:]

    return Token('number', type(token)), s


def tok_paren(s):
    t, s = s[0], s[1:]

    if not re.match(r'[\(\)]', t):
        raise TokenError(f"unexpected token: {t}")

    return Token(t, None), s


def tok_ident(s):
    t, s = s[0], s[1:]

    if not re.match('[_a-zA-Z]', t):
        raise TokenError(f"unexpected token: {t}")

    token = t
    while len(s) > 0 and re.match('[_a-zA-Z0-9]', s[0]):
        token += s[0]
        s = s[1:]

    return Token('identifier', token), s


def tokenize(s):
    tokens = []

    while len(s) > 0:
        if re.match(r'\s', s[0]):
            s = s[1:]
            continue

        if re.match(r'[-+*/^%,=\(\)]', s[0]):
            t, s = s[0], s[1:]
            tokens.append(Token(t, None))
            continue

        if re.match('[0-9]', s[0]):
            token, s = tok_number(s)
            tokens.append(token)
            continue

        if re.match('[_a-zA-Z]', s[0]):
            token, s = tok_ident(s)
            tokens.append(token)
            continue

        raise TokenError(f"unexpected token: {s[0]}")

    return tokens


def peek(tokens, offset=0):
    if len(tokens) > offset:
        return tokens[offset]

    return Token(None, None)


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


def parse_atom(tokens):
    next = tokens.pop(0)

    if next.type == 'identifier':
        if peek(tokens).type != '(':
            return Expr('var', next.value), tokens

        tokens.pop(0)
        if peek(tokens) == ')':
            tokens.pop(0)
            return Expr('fcall', next.value, []), tokens

        params, tokens = parse_params(tokens)
        t = tokens.pop(0)
        if t.type != ')':
            raise ParseError(f"expected ) but found {t.type}")

        return Expr('fcall', next.value, params), tokens

    if next.type == '(':
        expr, tokens = parse_expr(tokens)

        if tokens[0].type == ')':
            tokens = tokens[1:]
        else:
            raise ParseError("expected closing )")

        return expr, tokens

    if next.type != 'number':
        raise ParseError("expected number")

    return Expr('literal', next.value), tokens


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


def parse_term(tokens):
    left, tokens = parse_factor(tokens)

    while len(tokens) > 0 and tokens[0].type in ['*', '/', '%']:
        type, tokens = tokens[0].type, tokens[1:]
        right, tokens = parse_factor(tokens)
        left = Expr(type, left, right)

    return left, tokens


def parse_expr(tokens):
    left, tokens = parse_term(tokens)

    while len(tokens) > 0 and tokens[0].type in ['+', '-']:
        type, tokens = tokens[0].type, tokens[1:]
        right, tokens = parse_term(tokens)
        left = Expr(type, left, right)

    return left, tokens


def parse_asgn(tokens):
    ident = tokens.pop(0)
    if ident.type != 'identifier':
        raise ParseError(f"unexpected token: {ident.type}")

    t = tokens.pop(0)
    if t.type != '=':
        raise ParseError(f"unexpected token: {t.type}")

    expr, tokens = parse_expr(tokens)

    return Expr('assign', ident.value, expr), tokens


def parse_stmnt(tokens):
    if peek(tokens).type == 'identifier' and peek(tokens, 1).type == '=':
        root, tokens = parse_asgn(tokens)
    else:
        root, tokens = parse_expr(tokens)

    return root, tokens


def parse(tokens):
    # stmnt: asgn | expr
    # asgn: 'identifier', '=', expr
    # expr: term, { '+' | '-', term }
    # term: factor, { '*' | '/' | '%', factor }
    # factor:
    #   | '-', factor
    #   | atom, [ '^', factor ]
    # atom:
    #   | 'identifier', [ '(', params?, ')' ]
    #   | '(', expr, ')'
    #   | 'number'
    # params: expr, { ',', expr }

    root, tokens = parse_stmnt(tokens)

    if len(tokens) != 0:
        raise ParseError("unexpected tokens")

    return root


def draw_tree(root):
    ids = set()

    with open("tree.dot", 'w') as f:
        f.write("graph {\n")

        queue = [root]
        while len(queue) > 0:
            n = queue.pop()
            if n.id not in ids:
                if n.type == 'literal':
                    f.write(f'v{n.id}[label="{n.left}"];\n')
                elif n.type == 'fcall':
                    f.write(f'v{n.id}[label="{n.left}()"];\n')
                elif n.type == 'var':
                    f.write(f'v{n.id}[label="{n.left}"];\n')
                else:
                    f.write(f'v{n.id}[label="{n.type}"];\n')

            if n.type == 'fcall':
                children = n.right
            else:
                children = [n.left, n.right]

            for m in children:
                if not isinstance(m, Expr):
                    continue

                f.write(f'v{n.id} -- v{m.id};\n')
                queue.append(m)

        f.write("}\n")

    subprocess.run(["dot", "-Tsvg", "-otree.svg", "tree.dot"])


def parse_expression(s):
    tokens = tokenize(s)
    expr = parse(tokens)
    return expr


def main(argv):
    if len(argv) < 2:
        exit(1)

    assignments = []
    expressions = []

    for e in argv[1:]:
        expr = parse_expression(e)
        if expr.type == 'assign':
            assignments.append(expr)
        else:
            expressions.append(expr)

    for expr in assignments:
        expr.eval()

    for expr in expressions:
        draw_tree(expr)
        result = expr.eval()

    print(result)


if __name__ == "__main__":
    main(sys.argv)
