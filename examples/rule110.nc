M = 256
state = 0..0..M
state[0] = 1

f(i) = {
    0 if state[i-1] == 1 and state[i] == 1 and state[i%M+1] == 1
    1 if state[i-1] == 1 and state[i] == 1 and state[i%M+1] == 0
    1 if state[i-1] == 1 and state[i] == 0 and state[i%M+1] == 1
    0 if state[i-1] == 1 and state[i] == 0 and state[i%M+1] == 0
    1 if state[i-1] == 0 and state[i] == 1 and state[i%M+1] == 1
    1 if state[i-1] == 0 and state[i] == 1 and state[i%M+1] == 0
    1 if state[i-1] == 0 and state[i] == 0 and state[i%M+1] == 1
    0 if state[i-1] == 0 and state[i] == 0 and state[i%M+1] == 0
}

print state
for i in 0..512 {
    next = 0..0..M
    for j in 1..#state {
        next[j] = f(j)
    }
    state = next
    print state
}
