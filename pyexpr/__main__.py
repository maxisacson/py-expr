#!/usr/bin/env python3

import sys
from .lexer import tokenize
from .parser import parse
from .expr import GLOBALS
from .common import TRACE, ExprError


def parse_expression(s):
    tokens = tokenize(s)
    expr = parse(tokens)
    return expr


def _main(argv):
    if len(argv) < 2:
        program = []

        if sys.stdin.isatty():
            for line in sys.stdin:
                exprs = parse_expression(line)
                result = None
                for expr in exprs:
                    result = expr.eval()
                if result is not None:
                    GLOBALS['_'] = result
                    GLOBALS['ans'] = result
                    print('=', result)
        else:
            input = sys.stdin.read()
            program = parse_expression(input)
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
        result = expr.eval()

    if result is not None:
        print(result)


def main():
    try:
        _main(sys.argv)
        return 0
    except ExprError as e:
        if TRACE:
            import traceback
            traceback.print_exception(e)
        else:
            print(f'Error: {e}')
        return 1


if __name__ == "__main__":
    sys.exit(main())
