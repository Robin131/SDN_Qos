import time


if __name__ == '__main__':
    t = time.time()
    print(t)
    print(int(round(t * 1000)))
    for i in range(1000):
        print(int(round(t * 1000)))