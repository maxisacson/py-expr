N = 512
M = 128
state = 0..0..M
state[0] = 1

f(i) = {
    0 if state[i-1..i+1] == [1, 1, 1]
    1 if state[i-1..i+1] == [1, 1, 0]
    1 if state[i-1..i+1] == [1, 0, 1]
    0 if state[i-1..i+1] == [1, 0, 0]
    1 if state[i-1..i+1] == [0, 1, 1]
    1 if state[i-1..i+1] == [0, 1, 0]
    1 if state[i-1..i+1] == [0, 0, 1]
    0 if state[i-1..i+1] == [0, 0, 0]
}

write state " "
write "\n"
for i in 2..N {
    next = 0..0..M
    for j in 1..#state {
        next[j] = f(j)
    }
    state = next
    write state " "
    write "\n"
}
