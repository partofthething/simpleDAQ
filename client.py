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
    while True:
        timeNow = time.time()
        timeVal = timeNow-timeStart
        tempInC = sensor.readTempC()
        internalTempInC = sensor.readInternalC()
        sendDataPoint(SENSOR_TC, timeVal, tempInC)
        sendDataPoint(SENSOR_INTERNAL, timeVal, internalTempInC)
        time.sleep(0.05)

def sendDataPoint(sensorID, timeVal, temperature):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((TCP_IP, TCP_PORT))
    s.send('{0:d},{1:.5f},{2:.5f}'.format(sensorID, timeVal, temperature))
    data = s.recv(BUFFER_SIZE)
    s.close()

if __name__=='__main__':
    senseTemperatures()
        