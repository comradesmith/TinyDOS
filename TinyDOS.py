#!/usr/bin/python3
'''
TinyDOS : A tiny wee Disk Operating System

	===========================
	CompSci 340 - Assignment 2
	2016-09-23
	===========================
	Author:	Cam Smith
	UPI:	csmi928
	ID:		706899195
	===========================

	Imports

	Classes:
		-TinyDOS

'''

from drive import Drive
from volume import *
import os
import readline
import shlex
import sys

class TinyDOS:
	'''
	This class contains all of the TinyDOS functionality
	'''

	def __init__(self):
		os.system("clear")
		self.connectedvolume = None
		self.bannedcharacters = set('/" ')
		self.methods = {}
		self.methods["append"] = self.append
		self.methods["deldir"] = self.removefromtree
		self.methods["delfile"] = self.removefromtree
		self.methods["format"] = self.format
		self.methods["ls"] = self.ls
		self.methods["mkdir"] = self.mkdir
		self.methods["mkfile"] = self.mkfile
		self.methods["print"] = self.print
		self.methods["quit"] = self.quit
		self.methods["reconnect"] = self.reconnect


	def main(self):
		while True:
			try:
				raw = input("> ")
				args = raw.split()
				command = args.pop(0)
				if command != "append":
					self.methods[command](*args)
				else:
					self.append(args[0], raw)
			except EOFError:
				self.quit()
			except IndexError :
				# user has hit enter, no-op
				pass
			except IOError as e:
				print(args[0], "does not exist")
			except KeyError as e :
				print(e, "is not a valid command")
			except KeyboardInterrupt:
				print()
				self.quit()
			except TypeError as e:
				print(self.methods[command].__doc__.strip())
			except TinyException as e:
				print(e)
			except ValueError as e:
				raise e
	

	def addtotree(self, path, isdir):
		'''
		Used internally by TinyDOS, adds a node to a tree, takes a boolean 'isdir' to
		determine if it should create a Directory or a File as the new leaf
		'''
		# TODO
		# make sure path starts with '/'		

		dirpath = path.split("/")
		filename = dirpath.pop()
		if len(dirpath) == 1:
		# example: /file => ["", "file1"] (pop) => [""]
			dirpath = [""] + dirpath
		dirpath = "/".join(dirpath)

		if len(set(filename) & self.bannedcharacters) != 0:
			raise TinyException(filename + " contains banned characters")
		if filename == "":
		# example	mkfile /
			raise TinyException("Invalid filename")
		if not self.connectedvolume.pathexists(dirpath):
			raise TinyException("The directory " + dirpath + " does not exist")
			
		parentnode = self.connectedvolume.traversepath(dirpath)
		if isdir:
			newnode = Directory(filename, self.connectedvolume, parentnode, populated= True)
		else:
			newnode = File(filename, self.connectedvolume, parentnode, populated= True)
		parentnode.addchild(newnode)


	def append(self, filepath, fullcommand):
		'''
		Usage is: append fullFilePathname "data"
		'''
		self.checkconnection()

		data = shlex.split(fullcommand)
		data = data[-1]
		data = bytes(data, "utf-8").decode("unicode_escape")

		if not self.connectedvolume.pathexists(filepath):
			raise TinyException(filepath + " does not exist")
		
		filenode = self.connectedvolume.traversepath(filepath)
		filenode.append(data)


	def checkconnection(self):
		if self.connectedvolume == None:
			raise TinyException("No volume is connected")
	

	def format(self, volumename):
		'''
		Usage is: format volumeName
		'''
		self.connectedvolume = Volume(volumename)
		self.connectedvolume.format()
		
	
	def ls(self, directorypath):
		'''
		Usage is: ls fullDirectoryPathname
		'''
		self.checkconnection()
		if not self.connectedvolume.pathexists(directorypath):
			raise TinyException(directorypath + " does not exist")
		currentnode = self.connectedvolume.traversepath(directorypath)
		if type(currentnode).__name__ != "Directory":
			raise TinyException(directorypath + " is not a directory")
		
		print("Directory:", directorypath)
		print("\033[7mName    \033[27m  ", end="")
		print("\033[7mType\033[27m  ", end="")
		print("\033[7mSize\033[27m  ", end="")
		print("\033[7mBlocks                                          \033[27m")
		print("\033[7m--------\033[27m", end="  ")
		print("\033[7m----\033[27m  \033[7m----\033[27m", end="  ")
		print("\033[7m", "-" * 48, "\033[27m", sep="")
		for child in currentnode.children:
			if child != None:
				print(child.name.ljust(8, " "), end="  ")
				if type(child).__name__ == "Directory":
					print("dir ", end="  ")
				else:
					print("file", end="  ")
				print(str(child.length).rjust(4, " "), end="  ")
				for block in child.blocks:
					print(str(block).zfill(3), end=" ")
				print()
		print()

		
	def mkdir(self, directorypath):
		'''
		Usage is: mkdir fullDirectoryPathname
		'''
		self.checkconnection()
		self.addtotree(directorypath, True)

	
	def mkfile(self, filepath):
		'''
		Usage is: mkfile fullFilePathname
		'''
		self.checkconnection()
		self.addtotree(filepath, False)


	def print(self, filepath):
		'''
		Usage is: print fullFilePathname
		'''
		self.checkconnection()
		if not self.connectedvolume.pathexists(filepath):
			raise TinyException(filepath + " does not exist")
		
		filenode = self.connectedvolume.traversepath(filepath)
		if type(filenode).__name__ != "File":
			raise TinyException("Cannot print a directory!")
		print(filenode.data)
		
	def quit(self):
		'''
		Usage is: quit
		'''
		sys.exit()

	def reconnect(self, volumename):
		'''
		Usage is: reconnect volumeName
		'''
		self.connectedvolume = Volume(volumename)
		self.connectedvolume.reconnect()

	def removefromtree(self, filepath):
		'''
		Usage is: delfile fullFilePathname
		'''
		self.checkconnection()
		if not self.connectedvolume.pathexists(filepath):
			raise TinyException(filepath + " does not exist")

		dirpath = filepath.split("/")
		filename = dirpath.pop()
		if len(dirpath) == 1:
		# example: /file => ["", "file1"] (pop) => [""]
			dirpath = [""] + dirpath
		dirpath = "/".join(dirpath)
			
		parentnode = self.connectedvolume.traversepath(dirpath)	# FIXME, not needed
		deletee = self.connectedvolume.traversepath(filepath)
		deletee.killself()
	

if __name__ == "__main__":
	TinyDOS().main()
