"""
Remote sensing and processing server

Useful for receiving data coming in from remote sensors over the network 
and live-plotting it.

CALIBRATION INFO:

ICE WATER mixed nicely gives 2.5/2.25 C
Boiling water gives: 99.25

NOTE: Very much EXPERIMENTAL!!

See Also
--------
client : a client that sends data to this. 
"""

import socket
from Queue import Queue
import threading
from threading import Thread
import time

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation

SERVER_IP = None
TCP_PORT = 5500
BUFFER_SIZE = 1024

SENSOR_TC = 0
SENSOR_INTERNAL = 1
SENSORS = {SENSOR_TC: 'Thermocouple',
          SENSOR_INTERNAL: 'Internal'}

stopEvent = threading.Event()

class Server(Thread):
    """
    Server to receive data from client sensors. 
    
    Handles one or many clients
    """
    def __init__(self, dataQueue):
        Thread.__init__(self)
        serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        serversocket.bind((SERVER_IP, TCP_PORT))
        self.serverSocket = serversocket
        self.dataQueue = dataQueue
        self._stopped = False
        self._receivers = []

    def run(self):
        """
        Loop that listens for and processes client connections
        """
        print 'Starting Server Thread'
        self.serverSocket.listen(1) 
        while not stopEvent.isSet():
            # accept connections from outside
            clientSocket, address = self.serverSocket.accept()
            receiver = Receiver(clientSocket, address, self.dataQueue, self)
            receiver.start()
            
    def close(self):
        self._stopped = True
        stopEvent.set()
        self.serverSocket.close()

class Receiver(Thread):
    """
    Get data from a single client
    """
    
    def __init__(self, clientSocket, address, dataQueue, server):
        Thread.__init__(self)
        self.clientSocket = clientSocket
        self.address = address
        self.dataQueue = dataQueue
        self.noDataCount = 0
        self._stopped = False
        self._server = server
        
    def run(self):
        """
        Receive data from a client. 
        """
        while not stopEvent.isSet():
            self.getOneDataPoint()
            if self.noDataCount > 400:
                print 'Ending due to lack of data'
                self.stop()
        
    def getOneDataPoint(self):
        allData = []
        while not stopEvent.isSet():
            # get data in possible buffer-sized chunks
            data = self.clientSocket.recv(BUFFER_SIZE)
            self.clientSocket.send(data)  # echo
            allData.append(data)
            if '\n' in data: 
                break
            if not data:
                self.noDataCount +=1
                time.sleep(0.01)
                break
                
        self.dataQueue.put(''.join(allData))
        self.postReceive()
        
        return ''.join(allData)
    
    def postReceive(self):
        pass
    
    def stop(self):
        self._stopped = True
        self.close()
        self._server.close()
        stopEvent.set()
    
    def close(self):
        self.clientSocket.close()
        
class ReceiverMultiSocket(Receiver):
    """
    One socket open/close per client communication. 
    
    This is inefficient and slows down when the data rate is high. 
    """
    def run(self):
        self.getOneDataPoint()
        
    def postReceive(self):
        self.close()
    
    
class Plotter():
    """
    Plot window that updates as data becomes available
    """
    def __init__(self, temperatures):
        self.fig, self.ax = plt.subplots()
        self.lines = {}
        self.xdata, self.ydata = {}, {}
        for sensorID, sensorLabel in SENSORS.items():
            line, = self.ax.plot([], [], lw=2, label=sensorLabel)
            self.lines[sensorID] = line
            self.xdata[sensorID], self.ydata[sensorID] = [], []
        
        self.ax.set_ylim(0, 30)
        self.ax.set_xlim(0, 5)
        self.ax.grid()
        plt.xlabel('Time (s)')
        plt.ylabel(r'Temperature ($^\circ$C)')
        plt.legend(loc ='lower left')
                
        self.temperatures = temperatures # the Queue. 
        self._stopped=False
        
    def stop(self):
        self._stopped=True
        stopEvent.set()
        
    def getData(self):
        """
        Consume data in the thread-safe Queue as fast as it becomes available
        
        This parses the data from the Queue. Multiple sensors, etc. could be handled
        by putting a sensorID on the Queue tuples as well. 
        """
        while not stopEvent.isSet():
            if self._stopped:
                break
            dataPoints = []
            while not self.temperatures.empty() and not self._stopped:
                data = self.temperatures.get()
                if data and ',' in data:
                    sensorID, timeVal, tempInC = data.split(',')
                    sensorID = int(sensorID)
                    timeVal = float(timeVal)
                    tempInC = float(tempInC)
                    if sensorID == -1:
                        # end signaled
                        self.stop()
                    else:
                        
                        if sensorID==SENSOR_TC:
                            print tempInC
                        dataPoints.append((sensorID, timeVal, tempInC))
            if dataPoints:
                yield dataPoints
            
    def addNewDataPoints(self, frameData):
        """
        update plot with new data point
        """
        for sensorID, dataTime, dataTemperature in frameData: 
            self.xdata[sensorID].append(dataTime)
            self.ydata[sensorID].append(dataTemperature)
            self._updateAxisLimits(dataTime, dataTemperature)
            self.lines[sensorID].set_data(self.xdata[sensorID], self.ydata[sensorID])
    
        return self.lines[sensorID],
    
    def _updateAxisLimits(self, x, y):
        """
        Update axes if data goes out of bounds
        """
        ax = self.ax
        xmin, xmax = ax.get_xlim()
        ymin, ymax = ax.get_ylim()
        if x >= xmax:
            ax.set_xlim(xmin, 2*xmax)
            ax.figure.canvas.draw()
        if x < xmin:
             ax.set_xlim(0.9*x, xmax)
             ax.figure.canvas.draw()
        if y >= ymax:
            ax.set_ylim(ymin, 1.1*ymax)
            ax.figure.canvas.draw()
        if y<ymin:
            ax.set_ylim(y-2, ymax)
            ax.figure.canvas.draw()
    
    def run(self):
        print 'Starting Plotting Thread'
        ani = animation.FuncAnimation(self.fig, self.addNewDataPoints, self.getData, 
                                      blit=False, interval=100, repeat=False)
        plt.show()
        
class QueueMonitor(Thread):
    def __init__(self, queue):
        Thread.__init__(self)
        self.queue = queue
        self._stopped = False
        
    def run(self):
        while not self._stopped:
            time.sleep(10)
            print 'Queue Length is {0}'.format(self.queue.qsize())
    
    def stop(self):
        self._stopped = True
    
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('serverip', 
                       help='hostname or ip addressof the server to connect to')
   
    
    args = parser.parse_args()
    SERVER_IP = args.serverip
    
    temperatures = Queue()
    server, queueMonitor, plotter = (None, None, None)
    try:
        server = Server(temperatures)
        server.start()
        plotter = Plotter(temperatures)
        plotter.run()
    finally:
        if server:
            server.close()
        if plotter:
            plotter.stop()
        
        
        
    