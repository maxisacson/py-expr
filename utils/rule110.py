import numpy as np
import matplotlib.pyplot as plt
import subprocess
import io


def rule110():
    N, M = 512, 128
    data = np.zeros((N, M))
    data[0, -1] = 1

    for r in range(N - 1):
        for c in range(M):
            x = data[r, (c - 1) % M]
            y = data[r, c]
            z = data[r, (c + 1) % M]
            state = x, y, z

            if state == (1, 1, 1):
                data[r + 1, c] = 0

            elif state == (1, 1, 0):
                data[r + 1, c] = 1

            elif state == (1, 0, 1):
                data[r + 1, c] = 1

            elif state == (1, 0, 0):
                data[r + 1, c] = 0

            elif state == (0, 1, 1):
                data[r + 1, c] = 1

            elif state == (0, 1, 0):
                data[r + 1, c] = 1

            elif state == (0, 0, 1):
                data[r + 1, c] = 1

            elif state == (0, 0, 0):
                data[r + 1, c] = 0

            else:
                assert False

    return data


with open('examples/rule110.nc') as f:
    p = subprocess.run("nc", stdin=f, capture_output=True)

data1 = np.loadtxt(io.BytesIO(p.stdout))
data2 = rule110()
diff = data2 - data1
error = np.sum(np.abs(diff))
if error > 0:
    print("error:", error)

plt.subplot(121)
plt.title('nc')
plt.imshow(data1)
plt.subplot(122)
plt.title('python')
plt.imshow(data2)
plt.show()
