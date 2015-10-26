import socket
import time

import Adafruit_GPIO.SPI as SPI
import Adafruit_MAX31855.MAX31855 as MAX31855

SPI_PORT   = 0
SPI_DEVICE = 0
TCP_IP = '192.168.1.149'
TCP_PORT = 5500
BUFFER_SIZE = 1024

SENSOR_TC = 0
SENSOR_INTERNAL = 1


def senseTemperatures():
    sensor = MAX31855.MAX31855(spi=SPI.SpiDev(SPI_PORT, SPI_DEVICE))
    timeStart = time.time()
    transmitter = TransmitterSingleSocket()
    try:
        while True:
            timeNow = time.time()
            timeVal = timeNow-timeStart
            tempInC = sensor.readTempC()
            internalTempInC = sensor.readInternalC()
            transmitter.sendDataPoint(SENSOR_TC, timeVal, tempInC)
            transmitter.sendDataPoint(SENSOR_INTERNAL, timeVal, internalTempInC)
            time.sleep(0.05)
    except KeyboardInterrupt:
        transmitter.signalEnd()
        transmitter.close()

class Transmitter(object):
    
    def connect(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((TCP_IP, TCP_PORT))
        
    def sendDataPoint(self, sensorID, timeVal, temperature):
        self.preSend()
        self.socket.send('{0:d},{1:.5f},{2:.5f}\n'.format(sensorID, timeVal, temperature))
        data = self.socket.recv(BUFFER_SIZE)
        self.postSend()
    
    def signalEnd(self):
        self.sendDataPoint(-1,0,0)
        
    def close(self):
        self.socket.close()
        
    def preSend(self):
        pass
    
    def postSend(self):
        pass
    
class TransmitterSingleSocket(Transmitter):
    def __init__(self):
        Transmitter.__init__(self)
        self.connect()

class TransmitterMultiSocket(Transmitter):
    
    def preSend(self):
        self.connect()
    
    def postSend(self):
        self.close()

if __name__=='__main__':
    
    senseTemperatures()
        