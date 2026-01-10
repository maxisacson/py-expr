from .common import TokenError, trace
from .expr import KEYWORDS, COMMANDS
import re


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
        if len(s) > 1 and s[1] != '.' or len(s) > 2 and s[1] == '.' and s[2] == '.':
            token += s[0]
            s = s[1:]
            type = float

    while len(s) > 0 and re.match('[0-9]', s[0]):
        token += s[0]
        s = s[1:]

    if len(s) > 0 and re.match('[eE]', s[0]):
        token += s[0]
        s = s[1:]
        type = float
        if len(s) > 0 and s[0] == '-':
            token += s[0]
            s = s[1:]

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

    if token in KEYWORDS:
        return Token(token, None), s

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


def tok_string(s):
    token = ''

    t, s = s[0], s[1:]
    if t != '"':
        raise TokenError(f"unexpected token: {t}")

    while len(s) > 0 and s[0] != '"':
        t, s = s[0], s[1:]
        token += t

    t, s = s[0], s[1:]

    if t != '"':
        raise TokenError(f"unexpected token: {t}")

    return Token('string', token), s


@trace
def tokenize(s):
    # 'space': \s -> skip
    # 'eol': \n
    # 'comment': # .*$
    # \0:
    #   | [<>=!]=?
    #   | [-+*/^%,\(\):;\[\]\{\}#]
    # 'number':
    #   | [0-9]+\.?[0-9]*([eE]-?)[0-9]*
    #   | \.[0-9]*([eE]-?)[0-9]*
    # 'string': (?<=").*(?=")

    tokens = []

    while len(s) > 0:
        if s[0] == '\n':
            s = s[1:]
            if not tokens or tokens[-1].type != 'eol':
                tokens.append(Token('eol', None))
            continue

        if re.match(r'\s', s[0]):
            s = s[1:]
            continue

        if s[0] == ';':
            if tokens and tokens[-1].type == ';':
                s = s[1:]
                continue

        if s[0] == '#' and len(s) > 1 and s[1] == ' ':
            while len(s) > 0 and s[0] != '\n':
                s = s[1:]
            continue

        if re.match(r'[-+*/^%,\(\):;\[\]\{\}#]', s[0]):
            t, s = s[0], s[1:]
            tokens.append(Token(t, None))
            continue

        if re.match('[<>=!]', s[0]):
            t, s = s[0], s[1:]
            if len(s) > 0 and s[0] == '=':
                t += s[0]
                s = s[1:]
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
            if len(s) > 1 and s[1] == '.':
                token, s = tok_range(s)
            else:
                token, s = tok_number("0" + s)
            tokens.append(token)
            continue

        if s[0] == '"':
            token, s = tok_string(s)
            tokens.append(token)
            continue

        raise TokenError(f"unexpected token: {s[0]}")

    return tokens
