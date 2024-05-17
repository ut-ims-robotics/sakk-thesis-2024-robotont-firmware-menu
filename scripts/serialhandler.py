import os # file descriptor reading
import select # file descriptor checking
import pty # pty creation
import serial # serial communication
import subprocess # command line program execution
import threading # subprocess creation
import time # debug info

TIMEOUT_10_MS = 0.01

def filter_data(raw_data):
	# got command packet
	if "CMD" in raw_data:
		try:
			# Run the command and capture its output
			output = subprocess.check_output(raw_data[4:].strip(), shell=True, text=True)
			# output = subprocess.check_output("dmesg | tail -1", shell=True, text=True)
			print(output)
		except subprocess.CalledProcessError as e:
			# Handle errors, if any
			print("Error:", e)
		return None
	elif raw_data == "":
		return None
	else:
		return raw_data

def serial_communication_tont():
	with serial.Serial(port='/dev/ttyUSB0', baudrate=9600, timeout=TIMEOUT_10_MS) as ser_tont:
		while True:
			# Read and filter incoming data
			try:
				raw_data = ser_tont.readline().decode()
				filtered_data = filter_data(raw_data)
				if filtered_data != None:
					# Write the filtered data to the master end of the PTY
					os.write(master, filtered_data.encode())
			except UnicodeDecodeError as e:
				print(e)
			
			# Read outgoing data 
			# TODO FILTERING
			try:
				readlist, writelist, exceptionlist = select.select([master], [], [], 0.1)
				if master in readlist:
					ser_tont.write(os.read(master, 1024))
				else:
					print("nothing available!" )
			except Exception as e:
				print(e)

		
def main():
	global master
	# Create a pair of pseudo-terminals
	master, slave = pty.openpty()
	print("created PTY")
	print("master: ", os.ttyname(master))
	print("slave: ", os.ttyname(slave))

	# Slave pty symlink
	symlink_robotont = "/tmp/robotont"

	try:
		os.symlink(os.ttyname(slave), symlink_robotont)
		print("Symlink created successfully.")
	except OSError as e:
		print(f"Error creating symlink: {e}")
	
	'''
	# Master
	symlink_supervisor = "/tmp/supervisor"
		
	try:
		os.symlink(os.ttyname(master), symlink_supervisor)
		print("Symlink created successfully.")
	except OSError as e:
		print(f"Error creating symlink: {e}")
	'''

	# Start a thread to continuously read from and send to Robotont
	# This emulates the supervisor 
	tont_comms_thread = threading.Thread(target=serial_communication_tont)
	tont_comms_thread.start()

	# Open the slave end of the PTY as a serial port
	# This emulates robotont_driver (ROS)
	try:
		while True:
			with serial.Serial(port=symlink_robotont, baudrate=9600, timeout=TIMEOUT_10_MS) as ser_virtual:
				# Read data from the virtual serial port
				data_virtual = ser_virtual.readline().decode().strip()
				if len(data_virtual) > 0:
					print("ROS rcv:", data_virtual, " at ", time.time())
				ser_virtual.write("VEL\n".encode())
				
	finally:
		# Close the master and slave ends of the PTY
		print("closed PTY")
		os.close(master)
		os.close(slave)


if __name__ == "__main__":
	main()