from .common import ParseError, trace
from .lexer import Token
from .expr import Expr


GRAMMAR = """
END: ';' | 'eol'
program: 'eol'*, stmnts?, 'eol'*
stmnts: stmnt, { END, stmnt }, END?
stmnt:
  | 'for', 'identifier', 'in', expr, 'eol'?, stmnt
  | 'command', command_args?
  | simple_stmnt, [ 'if', expr, END ]
simple_stmnt:
  | 'identifier', '=', expr
  | 'identifier', ':', param_list?, '=', expr
  | expr
param_list: 'identifier', { ',', identifier }
expr:
  | disj, '..', disj, [ '..', ('+' | '-')?, disj ]
  | disj,
disj: conj, { 'or', conj }
conj: neg, { 'and', neg }
neg:
  | 'not', neg
  | comp
comp: sum, { '<' | '>' | '<=' | '>=' | '==' | '!=', sum }
sum: term, { '+' | '-', term }
term: factor, { '*' | '/' | '%', factor }
factor:
  | '-' | '#', factor
  | atom, [ '^', factor ]
atom:
  | 'identifier', '(', items?, ')'
  | 'identifier', '[', expr, ']'
  | 'identifier'
  | '(', expr, ')'
  | '[', items?, ']'
  | 'number'
  | 'string'
  | block
items: expr, { ',', expr }
command_args: stmnt, { ','?, stmnt }
block: '{', 'eol'?, stmnts?, '}'
"""


FIRST_block = {'{'}
FIRST_atom = {'identifier', '(', '[', '#', 'number', 'string'} | FIRST_block
FIRST_factor = {'-'} | FIRST_atom
FIRST_term = FIRST_factor
FIRST_sum = FIRST_term
FIRST_comp = FIRST_sum
FIRST_neg = {'not'} | FIRST_comp
FIRST_conj = FIRST_neg
FIRST_disj = FIRST_conj
FIRST_expr = FIRST_disj
FIRST_param_list = {'identifier'}
FIRST_simple_stmnt = {'identifier'} | FIRST_expr
FIRST_stmnt = {'for', 'command'} | FIRST_simple_stmnt
FIRST_stmnts = FIRST_stmnt
FIRST_program = {'eol'} | FIRST_stmnts
FIRST_command_args = FIRST_stmnt
FIRST_items = FIRST_expr

END = {';', 'eol'}


def peek(tokens, offset=0):
    if len(tokens) > offset:
        return tokens[offset]

    return Token(None, None)


@trace
def parse_items(tokens):
    items = []

    while True:
        e, tokens = parse_expr(tokens)
        items.append(e)
        if peek(tokens).type == ',':
            tokens.pop(0)
        else:
            break

    return items, tokens


@trace
def parse_command_args(tokens):
    args = []

    while tokens:
        p, tokens = parse_stmnt(tokens)
        args.append(p)
        if peek(tokens).type == ',':
            tokens.pop(0)
        elif peek(tokens).type in END:
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
    next = peek(tokens)

    if next.type == 'identifier':
        tokens.pop(0)
        if peek(tokens).type == '(':
            tokens.pop(0)
            if peek(tokens).type == ')':
                tokens.pop(0)
                return Expr('fcall', next.value, []), tokens

            params, tokens = parse_items(tokens)
            t = tokens.pop(0)
            if t.type != ')':
                raise ParseError(f"expected ) but found {t.type}")

            return Expr('fcall', next.value, params), tokens

        if peek(tokens).type == '[':
            tokens.pop(0)
            expr, tokens = parse_expr(tokens)

            if peek(tokens).type == ']':
                tokens.pop(0)
            else:
                raise ParseError("expected closing ]")

            return Expr('idx', next.value, expr), tokens

        return Expr('var', next.value), tokens

    if next.type == '(':
        tokens.pop(0)
        expr, tokens = parse_expr(tokens)

        if peek(tokens).type == ')':
            tokens = tokens[1:]
        else:
            raise ParseError("expected closing )")

        return expr, tokens

    if next.type == '[':
        tokens.pop(0)
        exprs, tokens = parse_items(tokens)
        if peek(tokens).type != ']':
            raise ParseError('expected closing ]')
        tokens.pop(0)
        return Expr('list', exprs), tokens

    if next.type == 'number':
        next = tokens.pop(0)
        return Expr('literal', next.value), tokens

    if next.type == 'string':
        next = tokens.pop(0)
        return Expr('literal', next.value), tokens

    if next.type in FIRST_block:
        return parse_block(tokens)

    raise ParseError(f"unexpected token: {next.type}")



@trace
def parse_factor(tokens):
    if peek(tokens).type in ['-', '#']:
        op = tokens.pop(0).type
        left, tokens = parse_factor(tokens)
        return Expr(op, left), tokens

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
    left, tokens = parse_disj(tokens)

    if peek(tokens).type == '..':
        tokens.pop(0)
        right, tokens = parse_disj(tokens)

        if peek(tokens).type == '..':
            tokens.pop(0)
            if peek(tokens).type == '+':
                tokens.pop(0)
                type = 'incr'
            else:
                type = 'count'
            step, tokens = parse_disj(tokens)
            left = [left, right]
            right = [step, type]

        left = Expr('range', left, right)

    return left, tokens


@trace
def parse_disj(tokens):
    left, tokens = parse_conj(tokens)

    while tokens and peek(tokens).type == 'or':
        type = tokens.pop(0).type
        right, tokens = parse_conj(tokens)
        left = Expr(type, left, right)

    return left, tokens


@trace
def parse_conj(tokens):
    left, tokens = parse_neg(tokens)

    while tokens and peek(tokens).type == 'and':
        type = tokens.pop(0).type
        right, tokens = parse_neg(tokens)
        left = Expr(type, left, right)

    return left, tokens


@trace
def parse_neg(tokens):
    if peek(tokens).type == 'not':
        tokens.pop(0)
        left, tokens = parse_neg(tokens)
        return Expr('not', left), tokens

    return parse_comp(tokens)


@trace
def parse_comp(tokens):
    left, tokens = parse_sum(tokens)
    exprs = []
    while peek(tokens).type in ['<', '>', '<=', '>=', '==', '!=']:
        op = tokens.pop(0)
        right, tokens = parse_sum(tokens)
        expr = Expr(op.type, right)
        exprs.append(expr)

    if len(exprs) < 1:
        return left, tokens
    elif len(exprs) == 1:
        expr, = exprs
        return Expr(expr.type, left, expr.left), tokens

    root = Expr('lchain', left, exprs)

    return root, tokens


@trace
def parse_sum(tokens):
    left, tokens = parse_term(tokens)

    while tokens and tokens[0].type in ['+', '-']:
        type, tokens = tokens[0].type, tokens[1:]
        right, tokens = parse_term(tokens)
        left = Expr(type, left, right)

    return left, tokens


@trace
def parse_block(tokens):
    if peek(tokens).type != '{':
        raise ParseError("expected {")
    tokens.pop(0)

    while peek(tokens).type == 'eol':
        tokens.pop(0)

    if peek(tokens).type == '}':
        tokens.pop(0)
        return Expr('block', []), tokens

    block, tokens = parse_stmnts(tokens)

    if block.left[0].type == 'if':
        block.type = 'cases'
    else:
        block.type = 'block'

    if peek(tokens).type != '}':
        raise ParseError('expected }')
    tokens.pop(0)

    return block, tokens



@trace
def parse_stmnt(tokens):
    if peek(tokens).type == 'for':
        tokens.pop(0)

        if peek(tokens).type != 'identifier':
            raise ParseError("expected identifier")
        ident = Expr('var', tokens.pop(0).value)

        if peek(tokens).type != 'in':
            raise ParseError("expected 'in'")
        tokens.pop(0)

        expr, tokens = parse_expr(tokens)

        if peek(tokens).type == 'eol':
            tokens.pop(0)

        body, tokens = parse_stmnt(tokens)

        return Expr('for', [ident, expr], body), tokens

    elif peek(tokens).type == 'command':
        left = tokens.pop(0)
        next = peek(tokens)
        if next.type is None or next.type == ';':
            params = []
        else:
            params, tokens = parse_command_args(tokens)
        return Expr('cmd', left.value, params), tokens

    stmnt, tokens = parse_simple_stmnt(tokens)

    if peek(tokens).type == 'if':
        tokens.pop(0)
        expr, tokens = parse_expr(tokens)
        if peek(tokens).type not in END:
            raise ParseError(f"expected ; or newline")

        stmnt = Expr('if', stmnt, expr)

    return stmnt, tokens


@trace
def parse_simple_stmnt(tokens):
    if peek(tokens).type == 'identifier' and peek(tokens, 1).type in ['=', ':']:
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
    stmnt, tokens = parse_stmnt(tokens)

    stmnts = [stmnt]
    while peek(tokens).type in END:
        tokens.pop(0)
        if peek(tokens).type in FIRST_stmnt:
            stmnt, tokens = parse_stmnt(tokens)
            stmnts.append(stmnt)
        else:
            break

    return Expr('stmnts', stmnts), tokens


@trace
def parse_program(tokens):
    while peek(tokens).type == 'eol':
        tokens.pop(0)

    if peek(tokens).type in FIRST_stmnts:
        stmnts, tokens = parse_stmnts(tokens)
    else:
        stmnts = Expr('stmnts', [])

    while peek(tokens).type == 'eol':
        tokens.pop(0)

    return stmnts, tokens


def parse(tokens):
    root, tokens = parse_program(tokens)

    if tokens:
        raise ParseError(f"unexpected tokens: {tokens[0]}")

    return root


