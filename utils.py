import time

def bell_ring(n=5):
    for _ in range(n):   # ring 3 times
        print('\a')
        time.sleep(1)   

