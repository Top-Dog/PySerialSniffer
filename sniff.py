# The goal of this project is to be able to 'sniff' serial traffic (full-duplex)
# between an external target device and some application running on the host OS.
# This fully-virtual solution requires no hardware setup changes. The solution 
# is to splice the serial port on the host OS, add a HardwarePort listener to 
# the physical COM port, sniff and process the traffic, then pass the traffic 
# to a virtual COM port SoftwarePort. This requires a null-modem emulator 
# (com0com). In com0com create a new COM port pair (tick 'use port class' 
# and 'emulate baud rate' for both virtual COM ports).
#
# Requires multi-processing to avoid GIL limitations. Still only one process can
# access a serial port at one time.
#
#
# //////////////////////      Physical COM1     ///////////////////       //////////////////       //////////////////     Virtual COMx     ////////////////////      Virtual COMy      ///////////////////
# // Embedded Machine // RX <--------------- TX // (PC) COM Port // <---- // Python App   // <---- // Python App   //  <--------------- TX // (com0com)      // RX <--------------- TX // (PC) Software //
# //			      // TX ---------------> RX //				 // ----> // HardwarePort // ----> // SoftwarePort //  ---------------> RX // vCOM Crossover // TX ---------------> RX // vCOMy		    //
# //////////////////////						///////////////////       //////////////////       //////////////////  				       ////////////////////  				       ///////////////////
#                                      
# 

import serial, time, colorama
from multiprocessing import Process, Pipe

BAUD_RATE = 115200
HARDWARE_COM_PORT = "COM5"
SOFTWARE_COM_PORT = "COM8"


def HardwarePort(pipe):
	"""Read/Write serial data to a hardware	device."""
	colorama.init()
	t = time.time()
	serialport = serial.Serial(HARDWARE_COM_PORT, BAUD_RATE)

	while True:
		if serialport.inWaiting() > 0:
			# Read a byte from the HW COM port and send it to the other (SW) process with the pipe
			data = serialport.read(size=1)
			pipe.send(data)

			# Manually add newline if there's been a pause for at least two seconds
			if time.time() - t > 2:
				print ()
			t = time.time()

			# Print the byte we received from the HW
			print ('\033[32m' + data.hex() + '\033[30m', end="")
		
		# Send all the data we have from the SW process straight to the physical COM port.
		if pipe.poll():
			data = pipe.recv()
			serialport.write(data)
		
def SoftwarePort(pipe):
	"""Read/Write serial data to a software port (null modem emulator)."""
	colorama.init()
	t = time.time()
	serialport = serial.Serial(SOFTWARE_COM_PORT, BAUD_RATE)

	while True:
		if serialport.inWaiting() > 0:
			# Read a byte from the SW COM port and send it to the other (HW) process with the pipe
			data = serialport.read(size=1)
			pipe.send(data)

			# Manually add newline if there's been a pause for at least two seconds
			if time.time() - t > 2:
				print ()
			t = time.time()

			# Print the byte we received from the SW
			print ('\033[35m' + data.hex() + '\033[30m', end="")

		# Send all the data we have from the HW process straight to the virtual COM port.
		if pipe.poll():
			data = pipe.recv()
			serialport.write(data)



if __name__ == '__main__':
	# Fake a terminal (Unix Only)
	# Open a new pseudo-terminal pair
	#master, slave = pty.openpty()
	#ser = serial.Serial(os.ttyname(slave), BAUD_RATE)
	#ser.write("Going out")
	#os.read(master, 1000)

	HardwareSidePipe1, SoftwareSidePipe1 = Pipe()
	p_hardware = Process(target=HardwarePort, args=(HardwareSidePipe1,))
	p_software = Process(target=SoftwarePort, args=(SoftwareSidePipe1,))

	p_hardware.start()
	p_software.start()

	p_hardware.join()
	p_software.join()
