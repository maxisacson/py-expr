#!/usr/bin/env python3

import sys
import re
import subprocess
import math


class TokenError(RuntimeError):
    pass


class ParseError(RuntimeError):
    pass


FUNCTIONS = {
    'sin': math.sin,
    'cos': math.cos,
    'tan': math.tan,
    'asin': math.asin,
    'acos': math.acos,
    'atan': math.atan,
    'sqrt': math.sqrt,
    'exp': math.exp,
}


class Expr:
    ID = 0

    def __init__(self, type, left, right=None):
        self.type = type
        self.left = left
        self.right = right
        self.id = Expr.ID
        Expr.ID += 1

    def eval(self):
        if self.type is None:
            return self.left.eval()

        if self.type == 'const':
            return self.left

        if self.type == '+':
            return self.left.eval() + self.right.eval()

        if self.type == '-':
            if self.left is None:
                return -self.right.eval()
            return self.left.eval() - self.right.eval()

        if self.type == '*':
            return self.left.eval() * self.right.eval()

        if self.type == '/':
            return self.left.eval() / self.right.eval()

        if self.type == '^':
            return self.left.eval() ** self.right.eval()

        if self.type == '%':
            return self.left.eval() % self.right.eval()

        if self.type == 'fcall':
            fname = self.left
            params = self.right
            return FUNCTIONS[fname](*(p.eval() for p in params))

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


def tok_binop(s):
    t, s = s[0], s[1:]

    if not re.match('[-+*/^%]', t):
        raise TokenError(f"unexpected token: {t}")

    return Token(t, None), s


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


def tok_comma(s):
    t, s = s[0], s[1:]

    if t != ',':
        raise TokenError(f"unexpected token: {t}")

    return Token(t, None), s


def tokenize(s):
    tokens = []

    while len(s) > 0:
        if re.match(r'\s', s[0]):
            s = s[1:]
            continue

        if re.match('[0-9]', s[0]):
            token, s = tok_number(s)
            tokens.append(token)
            continue

        if re.match('[_a-zA-Z]', s[0]):
            token, s = tok_ident(s)
            tokens.append(token)
            continue

        if re.match('[-+*/^%]', s[0]):
            token, s = tok_binop(s)
            tokens.append(token)
            continue

        if re.match(r'[\(\)]', s[0]):
            token, s = tok_paren(s)
            tokens.append(token)
            continue

        if s[0] == ',':
            token, s = tok_comma(s)
            tokens.append(token)
            continue

        raise TokenError(f"unexpected token: {s[0]}")

    return tokens


def peek(tokens):
    if len(tokens) > 0:
        return tokens[0]

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

    return Expr('const', next.value), tokens


def parse_factor(tokens):
    if tokens[0].type == '-':
        tokens = tokens[1:]
        right, tokens = parse_factor(tokens)
        return Expr('-', None, right), tokens

    left, tokens = parse_atom(tokens)

    while len(tokens) > 0 and tokens[0].type == '^':
        type, tokens = tokens[0].type, tokens[1:]
        right, tokens = parse_atom(tokens)
        left = Expr(type, left, right)

    return left, tokens


def parse_term(tokens):
    left, tokens = parse_factor(tokens)

    while len(tokens) > 0 and tokens[0].type in ['*', '/', '%']:
        type, tokens = tokens[0].type, tokens[1:]
        right, tokens = parse_factor(tokens)
        left = Expr(type, left, right)

    return left, tokens


def parse_sum(tokens):
    left, tokens = parse_term(tokens)

    while len(tokens) > 0 and tokens[0].type in ['+', '-']:
        type, tokens = tokens[0].type, tokens[1:]
        right, tokens = parse_term(tokens)
        left = Expr(type, left, right)

    return left, tokens


def parse_expr(tokens):
    return parse_sum(tokens)


def parse(tokens):
    # expr: sum
    # sum: term, { '+' | '-', term }
    # term: factor, { '*' | '/' | '%', factor }
    # factor:
    #   | '-', factor
    #   | atom, { '^', atom }
    # atom:
    #   | '(', expr, ')'
    #   | 'number'

    root, tokens = parse_expr(tokens)

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
                if n.type == 'const':
                    f.write(f'v{n.id}[label="{n.eval()}"];\n')
                elif n.type == 'fcall':
                    f.write(f'v{n.id}[label="{n.left}()"];\n')
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

    expr = parse_expression(argv[1])
    draw_tree(expr)
    result = expr.eval()

    print(f"expr: {argv[1]}")
    print(f"result: {result}")


if __name__ == "__main__":
    main(sys.argv)
