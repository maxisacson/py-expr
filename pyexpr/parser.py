from .common import ParseError, trace
from .lexer import Token
from .expr import Expr


END = {';', 'eol'}


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
        p, tokens = parse_stmnt(tokens)
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

    if next.type == '{':
        if peek(tokens).type == 'eol':
            tokens.pop(0)
        cases, tokens = parse_cases(tokens)
        if peek(tokens).type != '}':
            raise ParseError('expected }')
        tokens.pop(0)
        return cases, tokens

    if next.type != 'number':
        raise ParseError("expected number")

    return Expr('literal', next.value), tokens


@trace
def parse_factor(tokens):
    if peek(tokens).type == '-':
        tokens = tokens[1:]
        left, tokens = parse_factor(tokens)
        return Expr('-', left), tokens

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

    if peek(tokens).type in ['<', '>', '<=', '>=', '==', '!=']:
        op = tokens.pop(0)
        right, tokens = parse_sum(tokens)
        left = Expr(op.type, left, right)

    return left, tokens


@trace
def parse_sum(tokens):
    left, tokens = parse_term(tokens)

    while tokens and tokens[0].type in ['+', '-']:
        type, tokens = tokens[0].type, tokens[1:]
        right, tokens = parse_term(tokens)
        left = Expr(type, left, right)

    return left, tokens


@trace
def parse_cases(tokens):
    cases = []
    lastcase, tokens = parse_stmnt(tokens)
    while peek(tokens).type == 'if':
        type = tokens.pop(0).type
        cond, tokens = parse_expr(tokens)
        case = Expr(type, lastcase, cond)
        cases.append(case)
        if peek(tokens).type not in END :
            raise ParseError("expected ; or eol")
        tokens.pop(0)
        lastcase, tokens = parse_stmnt(tokens)

    if peek(tokens).type in END:
        tokens.pop(0)

    cases = Expr('cases', cases, lastcase)

    return cases, tokens


@trace
def parse_stmnt(tokens):
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
    stmnts = []

    while tokens:
        s, tokens = parse_stmnt(tokens)
        stmnts.append(s)
        if peek(tokens).type in END:
            tokens.pop(0)
        else:
            break

    if peek(tokens).type == END:
        tokens.pop(0)

    return stmnts, tokens


def parse(tokens):
    # END: ';' | 'eol'
    # stmnts: stmnt, { END, stmnt }, END?
    # stmnt:
    #   | 'command', command_args?
    #   | 'identifier', '=', expr
    #   | 'identifier', ':', param_list?, '=', expr
    #   | expr
    # param_list: 'identifier', { ',', identifier }
    # expr:
    #   | disj, '..', disj, [ '..', ('+' | '-')?, disj ]
    #   | disj,
    # disj: conj, { 'or', conj }
    # conj: neg, { 'and', neg }
    # neg:
    #   | 'not', neg
    #   | comp
    # comp:
    #   | sum, [ ( '<' | '>' | '<=' | '>=' | '==' | '!=' ), sum ]
    # sum:
    #   | term, { '+' | '-', term }
    # term: factor, { ( '*' | '/' | '%' ), factor }
    # factor:
    #   | '-', factor
    #   | atom, [ '^', factor ]
    # atom:
    #   | 'identifier', [ '(', params?, ')' ]
    #   | '(', expr, ')'
    #   | '[', params?, ']'
    #   | '{', 'eol'?, cases, '}'
    #   | 'number'
    # params: expr, { ',', expr }
    # command_args: stmnt, { ',', stmnt }
    # cases: { stmnt, 'if', expr, END }, stmnt, END?

    roots, tokens = parse_stmnts(tokens)

    if tokens:
        raise ParseError(f"unexpected tokens: {tokens[0]}")

    return roots


