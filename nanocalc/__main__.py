#!/usr/bin/env python3

import sys
from .lexer import tokenize
from .parser import parse
from .expr import GLOBALS
from .common import TRACE, ExprError


def parse_expression(s):
    tokens = tokenize(s)
    root = parse(tokens)
    return root


def _main(argv):
    if len(argv) < 2:
        if sys.stdin.isatty():
            for line in sys.stdin:
                expr = parse_expression(line)
                result = expr.eval()
                if result is not None:
                    GLOBALS['_'] = result
                    GLOBALS['ans'] = result
                    print('=', result)
            return

        input = sys.stdin.read()
    elif argv[1] == 'file':
        with open(argv[2]) as f:
            input = f.read()
    else:
        input = '\n'.join(argv[1:])

    program = parse_expression(input)
    result = program.eval()
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
