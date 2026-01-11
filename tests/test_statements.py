import pytest
import sys

from nanocalc.lexer import tokenize
from nanocalc.parser import parse


def parse_expression(input):
    tokens = tokenize(input)
    program = parse(tokens)
    return program


def test_assignment():
    code = "x = 14"

    e = parse_expression(code)
    v = e.eval()

    assert v == 14

def test_block():
    code = """
    {
        x = 1
        y = 2
        x + 2*y
    }
    """

    e = parse_expression(code)
    v = e.eval()

    assert v == 5


def test_cases():
    code = """
    x = -10
    {
        1 if x > 0
        -1 if x < 0
        0
    }
    """

    e = parse_expression(code)
    v = e.eval()

    assert v == -1


def test_function():
    code = """
    f(x) = {
        x^2 + 2*x + 10
    }
    """

    e = parse_expression(code)
    v = e.eval()

    assert v is None

    e = parse_expression("f(0)")
    v = e.eval()
    assert v == 10

    e = parse_expression("f(3)")
    v = e.eval()
    assert v == 25


def test_function2(capsys):
    code = """
    f(x) = {
        0 if x < 0
        x^2
    }
    x = [-2, -1, 0, 1, 2]
    table x f(x)
    """

    e = parse_expression(code)
    e.eval()

    cap = capsys.readouterr()
    assert cap.out == "-2 0\n-1 0\n0 0\n1 1\n2 4\n"

def test_loop(capsys):
    code = """
    x = ["foo", "bar", "baz"]
    for s in x print s
    """

    e = parse_expression(code)
    e.eval()

    cap = capsys.readouterr()
    assert cap.out == "foo\nbar\nbaz\n"


def test_loop2():
    code = """
    s = 0
    for i in 1..4
        s = s + i
    s
    """

    e = parse_expression(code)
    v = e.eval()

    assert v == 10


def test_loop3(capsys):
    code = """
    s = 0
    for i in 1..4 {
        s = s + i
        print i
    }
    s
    """

    e = parse_expression(code)
    v = e.eval()

    assert v == 10

    cap = capsys.readouterr()
    assert cap.out == "1\n2\n3\n4\n"


"""
# Simple statements
x
42
"hello"
(x + y)

# Assignments
x = 5
f: x = 10
x = 5 if y > 0;

# Expressions
a + b * c
2..10..+2
-x^2
not a and b or c

# Blocks
{}
{ x = 1; y = 2 }
{ x; { y; z } }

# Loops
for i in 0..10 x = i;
for x in list { print x }

# Commands
command x
command x y z
command x { y } z
command a b c

# Nested / complex block
{
  x = 10;
  y = 20 if x > 5;
  command print x y;
  for i in 0..x {
    z = i * 2;
  }
}

# Edge cases
{}
{ ; }
x if y > 0
x = (a + b) * c
command
"""
