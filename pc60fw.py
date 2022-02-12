#!/usr/bin/env python
import sys
import libscrc
import bluepy
import csv
from datetime import datetime
import os


if len(sys.argv) == 1:
    print ("Not enough arguments.")
    print ("Usage: ./pc60fw.py <Device MAC> [SpO2 logging threshold]")
    print ("Logs are written to ~/Pulseoxymeter/ .")
    exit()

# Parse SpO2 logging threshold
if len(sys.argv) == 3:
    spo2thr = int(sys.argv[2])
else:
    spo2thr = 100

stream = bytearray()

# Create log directory (if doesn't exist yet)
logdir = os.path.expanduser("~") + '/Pulseoxymeter'
try:
    os.mkdir(logdir, mode = 0o770)
except FileExistsError:
    pass

# Create time-stamped logfile
logfilename = logdir + '/' + datetime.now().strftime("%Y-%m-%d_%H-%M") + '.csv'
logfile = open(logfilename, 'w')
logwriter = csv.writer(logfile, delimiter=";")

# Write header in it
logwriter.writerow(['Timestamp', 'SpO2', 'PR', 'PI', 'Battery'])


class MyDelegate(bluepy.btle.DefaultDelegate):
    def __init__(self):
        bluepy.btle.DefaultDelegate.__init__(self)
        self.battery = 0

    def handleNotification(self, cHandle, data):
        stream.extend(bytearray(data))
        while(True):
            if(len(stream) == 0):
                break

            # search for sync sequence
            idx = stream.find(b'\xaa\x55')

            # gather more bytes if the sync sequence not found
            if(idx < 0):
                break

            # check if there are enough bytes to read the message length
            # otherwise skip and gather more bytes
            if(len(stream) < idx + 4):
                break

            length = stream[idx + 3]
            # check whether all the bytes of the message available
            # otherwise skip and gather more bytes
            if(len(stream) < idx + 4 + length):
                break

            # remove the bytes from the stream prior sync
            # (if any - as this should not happen except in case of the firs message)
            del stream[0 : idx]

            # copy the whole message 
            message = stream[0 : idx + 4 + length]

            # the last byte of the message is a CRC8/MAXIM 
            # the CRC sum for the whole message (including the CRC) must be 0
            if(libscrc.maxim8(message) != 0):
                print("CRC error")

            # remove the sync bytes and the CRC
            message =  message[2 : idx + 3 + length]

            # remove the processed bytes from the stream
            del stream[0 : idx + 4 + length]

            # messages with 0x08 on the second spot contains values appear on the OLED display
            if(message[2] == 0x01):
                print("SpO2: %d PR: %d PI: %1.1f" % (message[3], message[4], message[6] / 10))
                # Ignore samples from uninitialized device
                if (message[3] != 0 and message[3] <= spo2thr):
                    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    logwriter.writerow([ts, message[3], message[4], message[6]/10, self.battery])

            if(message[2] == 0x03):
                print("Battery Level: %d/3" % (message[3]))
                self.battery = message[3]

# Connections often fail randomly at the beginning. This will retry until it works.
Connection = False
while(Connection == False):
    try:
        pulseoximeter = bluepy.btle.Peripheral(sys.argv[1], "random")
        Connection = True
    except bluepy.btle.BTLEDisconnectError:
        print ("Connection failed, retrying...")


try:
    pulseoximeter.setDelegate(MyDelegate())

    # enable notification
    setup_data = b"\x01\x00"
    notify = pulseoximeter.getCharacteristics(uuid='6e400003-b5a3-f393-e0a9-e50e24dcca9e')[0]
    notify_handle = notify.getHandle() + 1
    pulseoximeter.writeCharacteristic(notify_handle, setup_data, withResponse = True)

    # wait for answer
    while True:
        if pulseoximeter.waitForNotifications(1.0):
            continue

#Handle disconnection gracefully
except bluepy.btle.BTLEDisconnectError:
    print ("Pulseoximeter disconnected.")

finally:
    logfile.close()
    pulseoximeter.disconnect()
