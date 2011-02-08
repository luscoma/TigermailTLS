#! /usr/bin/python
# Simple Echo Server Used for Test

# Imports
import SocketServer
import socket
import sys

# Classes
class EchoHandler(SocketServer.StreamRequestHandler):
	"""
	SSL 302 Handler
	"""
	
	def handle(self):  
		recv = self.rfile.readline()
		self.wfile.write("ECHO: " + recv + '\n')
		
class EchoServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
	pass
	
# Main Script
if len(sys.argv) != 2:
	print "Usage: echoserver.py <port>"
	sys.exit(1)

HOST, PORT = "0.0.0.0", int(sys.argv[1])
	
#Create the server, binding to localhost on port 9999
server = EchoServer((HOST, PORT), EchoHandler)
	
# Serve Forever
print "Echo Server Initialized"
print "Port: " + sys.argv[1]
server.serve_forever()