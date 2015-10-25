"""
Remote sensing and processing server

Useful for receiving data coming in from remote sensors over the network 
and live-plotting it.
"""

import socket
from Queue import Queue
from threading import Thread
import time

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation

SERVER_IP = '192.168.1.149'
TCP_PORT = 5500
BUFFER_SIZE = 1024

SENSOR_TC = 0
SENSOR_INTERNAL = 1
SENSORS = {SENSOR_TC: 'Thermocouple',
          SENSOR_INTERNAL: 'Internal'}

class Server(Thread):
    """
    Server to receive data from client sensors
    """
    def __init__(self, dataQueue):
        Thread.__init__(self)
        serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        serversocket.bind((SERVER_IP, TCP_PORT))
        self.serverSocket = serversocket
        self.dataQueue = dataQueue
        self._stopped = False

    def run(self):
        """
        Loop that listens for and processes client connections
        """
        print 'Starting Server Thread'
        self.serverSocket.listen(1) 
        while True and not self._stopped:
            # accept connections from outside
            clientSocket, address = self.serverSocket.accept()
            # open a thread to handle this connection
            data = receive(clientSocket, address)
            self.dataQueue.put(data)
            
    def close(self):
        self._stopped = True
        self.serverSocket.close()
    
def receive(clientSocket, addr):
    """
    Receive data from a client. 
    """
    allData = []
    while True:
        # get data in possible buffer-sized chunks
        data = clientSocket.recv(BUFFER_SIZE)
        allData.append(data)
        if not data: 
            break
        clientSocket.send(data)  # echo
    clientSocket.close()
    return ''.join(allData)
    
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
        plt.legend()
                
        self.temperatures = temperatures # the Queue. 
        self._stopped=False
        
    def stop(self):
        self._stopped=True
        
    def getData(self):
        """
        Consume data in the thread-safe Queue as fast as it becomes available
        
        This parses the data from the Queue. Multiple sensors, etc. could be handled
        by putting a sensorID on the Queue tuples as well. 
        """
        while True:
            if self._stopped:
                break
            data = self.temperatures.get()
            if data and ',' in data:
                sensorID, timeVal, tempInC = data.split(',')
                print sensorID, timeVal, tempInC
                
                yield int(sensorID), float(timeVal), float(tempInC)
            else:
                continue
        
    def addNewDataPoint(self, frameData):
        """
        update plot with new data point
        """
        sensorID, dataTime, dataTemperature = frameData
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
        if y >= ymax:
            ax.set_ylim(xmin, 1.1*ymax)
            ax.figure.canvas.draw()
    
    def run(self):
        print 'Starting Plotting Thread'
        ani = animation.FuncAnimation(self.fig, self.addNewDataPoint, self.getData, 
                                      blit=False, interval=1, repeat=False)
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
    temperatures = Queue()
    server, queueMonitor, plotter = (None, None, None)
    try:
        server = Server(temperatures)
        server.start()
        plotter = Plotter(temperatures)
        plotter.run()
        raw_input('Press ENTER to quit')
    finally:
        if server:
            server.close()
        if plotter:
            plotter.stop()
        
        
        
    