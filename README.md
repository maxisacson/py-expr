# nanocalc-py

Parse and evaluate simple mathematical expressions in pure python without
dependencies*.

(*) the `ast` command requires the `graphviz` program to be installed.

## Examples

Simple computation
```
$ nc 1+2*3
7
```

Trig functions and builtin constants
```
$ nc 'sin(3/4*pi)'
0.7071067811865476
```

Multiple expressions and variable assignment
```
$ nc x+2 x=7
9
```
altenatively
```
$ nc 'x=7; x+2'
9
```

User defined functions
```
$ nc 'f: x = x^2 + 2*x + 1' 'f(1.5)'
6.25
```

Read in scripts via stdin
```
$ cat script
a = 1
f: x = x^2
g: x = 3*x - a
f(5) + g(0.8*pi)
$ nc < script
31.539822368615503
```

Interactive mode
```
$ nc
1 + sqrt(5)
= 3.23606797749979
ans + 1
= 4.23606797749979
```
