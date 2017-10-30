import time, threading

def funct():
    while True:
        print("hmhm")
        time.sleep(1)

threading.Thread(target=funct).start()


while True:
    print("ahahahahahah")
    time.sleep(10)
