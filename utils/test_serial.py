from serial import Serial

PORT = "COM8"
BAUDRATE = 921600

with Serial(PORT, BAUDRATE) as port:
    while True:
        try:
            data = port.read(32)
            print(" ".join(["{:02x}".format(x) for x in data]))
        except KeyboardInterrupt:
            break

