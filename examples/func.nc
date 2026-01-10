# g:x = {
#     a = x^2
#     b = 2*x
#     c = 1
#     a + b + c
# }

print "this is a string not a comment"

f:x = {
    x^2 if x > 3
    2*x if x > 0
    1
}
f(4)
