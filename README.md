# py-expr

Parse and evaluate simple mathematical expressions in pure python without
dependencies*.

(*) the `ast` command requires the `graphviz` program to be installed.

## Examples

Simple computation
```
$ ./pyexpr.py 1+2*3
7
```

Trig functions and builtin constants
```
$ ./pyexpr.py 'sin(3/4*pi)'
0.7071067811865476
```

Multiple expressions and variable assignment
```
$ ./pyexpr.py x+2 x=7
9
```
altenatively
```
$ ./pyexpr.py 'x=7; x+2'
9
```

User defined functions
```
$ ./pyexpr.py 'f: x = x^2 + 2*x + 1' 'f(1.5)'
6.25
```

Read in scripts via stdin
```
$ cat script
a = 1
f: x = x^2
g: x = 3*x - a
f(5) + g(0.8*pi)
$ ./pyexpr.py < script
31.539822368615503
```

Interactive mode
```
$ ./pyexpr.py
1 + sqrt(5)
= 3.23606797749979
ans + 1
= 4.23606797749979
```
