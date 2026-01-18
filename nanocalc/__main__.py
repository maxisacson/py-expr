#!/usr/bin/env python3

import sys
import argparse
import subprocess

from .lexer import tokenize
from .parser import parse
from .expr import GLOBALS, draw_tree
from .common import TRACE, ExprError


def repl(args):
    for line in sys.stdin:
        tokens = tokenize(line)
        if args.tokens:
            print(tokens)
        expr = parse(tokens)
        result = expr.eval()
        if result is not None:
            GLOBALS['_'] = result
            GLOBALS['ans'] = result
            print('=', result)


def _main(args):
    if args.file is not None:
        with open(args.file) as f:
            input = f.read()
    elif len(args.input) > 0:
        input = '\n'.join(args.input)
    elif not sys.stdin.isatty():
        input = sys.stdin.read()
    else:
        repl(args)
        return

    tokens = tokenize(input)
    if args.tokens:
        print(tokens)
    program = parse(tokens)
    result = program.eval()
    if result is not None:
        print(result)

    if args.ast:
        draw_tree(program, "ast")
        subprocess.run(["xdg-open", "ast.svg"])


def main():
    argp = argparse.ArgumentParser(prog='nc')
    argp.add_argument('input', nargs='*')
    argp.add_argument('-f', '--file', type=str)
    argp.add_argument('--ast', action='store_true')
    argp.add_argument('--tokens', action='store_true')
    args = argp.parse_args()

    try:
        _main(args)
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
