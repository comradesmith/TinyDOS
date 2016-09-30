'''
Volume : A file system for TinyDOS

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
		-Volume
		-Directory
		-File
		-TinyException
'''

from drive import Drive
from copy import copy
import os
import sys

class Volume:
	'''
	This class acts as a go-between for TinyDOS and the drive class,
	as the drive will only write in single blocks at a time, we must
	use volume to segment large writes into the correct number of 
	block writes.

	The Volume class has the important job of maintaining the volume
	information on block 0.
	'''
	MAX_NAME = 8	# Do these belong in Volume or in Record??
	MAX_BLOCKS = 12	#
	MAX_FILESIZE = MAX_BLOCKS * Drive.BLK_SIZE
	RECORD_LEN = 64	#
	

	def __init__(self, volumename):
		self.drivecontroller = Drive(volumename)
		self.bitmap = []
		self.root = None


	def allocateblocks(self, n):
		freeblocks = self.bitmap.count("-")
		blocks = []
		if freeblocks < n:
			raise TinyException("Inadequate space on drive")
	
		while n > 0:
			i = self.bitmap.index("-")
			blocks += [i]
			self.bitmap[i] = "+"
			n -= 1	
			
		return blocks


	def deallocateblocks(self, blocks):

		for block in blocks:
			self.bitmap[block] = "-"


	def format(self):
		'''
		Creates a new directory tree and assigns that to self.root
		'''
		self.drivecontroller.format()

		self.bitmap = ["+"] + (["-"] * (Drive.DRIVE_SIZE - 1))
		self.root = Directory(name= "/", volume= self, parent= None, length= 512, rootflag= True, populated= True)
		self.root.commit()

	
	def pathexists(self, path):
		'''
		Returns True or False based on if a given path exists, depends on traversepath()
		'''
		try:
			self.traversepath(path)	
			return True
		except :
			return False


	def readblocks(self, blocks):
		'''
		gets given a list of blocks and will return as a single string all of the 
		data stored in those blocks.
		'''
		data = ""
	
		self.drivecontroller.reconnect()
		
		for block in blocks:
			data += self.drivecontroller.read_block(block)
		
		self.drivecontroller.disconnect()	
		
		return data	


	def reconnect(self):
		self.drivecontroller.reconnect()

		self.root = Directory(name= "/", volume= self, parent= None, length= 512, rootflag= True)
		bitmap = self.root.populate()
		self.bitmap = list(bitmap)

	
	def traversepath(self, path):
		'''
		Starting at root, this method follows all links mentioned in the path until it
		hits the final node
		'''
		current = self.root
		pathlist = path.split("/")
		pathlist.pop(0)

		if path == "/":
		# special case for root
			targetname = "/"
		elif pathlist[-1] == "":
		# example /dir/	=>	["dir", ""]
			targetname = pathlist[-2]
		else:
		# example /file =>	["file"]
			targetname = pathlist[-1]
	
		for pathnode in pathlist:
			if pathnode == "":
			# we are done
				break
				# go check it
			if pathnode not in current.getchildnames():
			# this is the correct consistency check, the other may be removed later on
				raise TinyException("The node " + pathnode + " does not exist") 
			for child in current.children:
				if child != None and pathnode == child.name:
				# we found a matching pathnode
					if pathnode != pathlist[-1] and type(child).__name__ != "Directory":
						raise TinyException(pathnode + "is not a Directory!")
					if not child.populated:
					# we will read disk on traversal
						child.populate()
					# check type
					current = child

		if current.name != targetname:		
		# this check does not guarantee that we have successfully parsed the entire tree.
		# we may remove this later on
		# if what we are about to return isn't right..
			raise TinyException(path + " does not exist")
		
		return current


	def writeblocks(self, blocks, data):
		'''
		behaviour is to be determined.
		'''
		self.drivecontroller.reconnect()
		if len(data) > len(blocks) * Drive.BLK_SIZE:
			raise TinyException("Uh-oh R-Rick.. L--looks like your file is too big huh?\nWh-what do you, what, what do you think about th-that?")

		chunks = [data[i:i+Drive.BLK_SIZE] for i in range(0, len(data), Drive.BLK_SIZE)]
		#go get all of the data which fits neatly into a block, and put these in temporary chunks

		for i in range(len(blocks)):
			self.drivecontroller.write_block(blocks[i], chunks[i])

		self.drivecontroller.disconnect()

	
class Directory:
	'''
	An object of the type Directory represents a directory on the disk. It holds information
	about its children, its parents, its blocks on the disk, and more.
	'''
	def __init__(self, name, volume, parent, length=0, children= [], blocks= [], populated= False,  rootflag= False):
		self.name = name
		self.volume = volume
		self.parent = parent
		self.length = length
		self.children = copy(children) ## NOTE! children can be Directories or Files
		self.blocks = copy(blocks)
		self.populated = populated
		self.rootflag = rootflag

		if self.rootflag:
			self.blocks = [0]
			self.spareslots = 6
			self.children = [None for i in range(self.spareslots)]
		else:
			# spare slots is equal to the dir's length divided by record length
			# minus any assigned children and files.
			self.spareslots = (length // Volume.RECORD_LEN) - len(children)

		if len(children) == 0:
		## all empty dir
			self.children = [None for i in range(self.spareslots)]
			# we need to keep our dirs in a particular spot in our child list
			# so as to make it easy when we want to delete files and such
		
		if len(blocks) > Volume.MAX_BLOCKS:
			raise TinyException("Constructing directory " + name + " failed MAX_BLOCKS exceeded")

		if len(name) > Volume.MAX_NAME:
			raise TinyException("Permitted name length exceeded")
		
		if length > len(self.blocks) * Drive.BLK_SIZE:
			raise TinyException("Given length does not match allocated blocks")


	def addchild(self, child):
		'''
		Adds a given child to the current Directory's list of children, expanding if nessecary,
		and calling commit after a successful addition
		'''	
		for sibling in self.children:
			if sibling != None and sibling.name == child.name:
				raise TinyException(child.name + " is already taken")

		if self.spareslots > 0:
		# easy life, easy add
			i = 0
			while self.children[i] != None:
				i += 1
			# now we have the index of an empty slot in our list of children
			self.children[i] = child
			self.spareslots -= 1

			self.commit()
		else:
		# expand dir
			if self.rootflag:
			# expansion failed because we are root
				raise TinyException("Root cannot contain more than 6 children")
			self.expand()
			self.addchild(child)


	def commit(self):
		'''
		Creates a string representation of the current Directory object, then writes
		that to disk via the volume.writeblocks()
		'''
		emptyrecord = "f:         0000:000 000 000 000 000 000 000 000 000 000 000 000 "

		if self.rootflag:
			representation = "".join(self.volume.bitmap)
		else:
			representation = ""
		
		for child in self.children:
			if child != None:
				if type(child).__name__ == "Directory":
					recordtype = "d:"
				else:
					recordtype = "f:"
				name = child.name.ljust(Volume.MAX_NAME + 1, " ")
				length = str(child.length).zfill(4)
				blocks = ""
				for block in child.blocks:
					block = str(block).zfill(3)
					block += " "
					blocks += block
				for i in range(Volume.MAX_BLOCKS - len(child.blocks)):
					blocks += "000 "
		
				record = recordtype + name + length + ":" + blocks	
				representation += record
			else:
				representation += emptyrecord

		self.volume.writeblocks(self.blocks, representation)
		
		if self.parent != None:
			self.parent.commit()


	def expand(self):
		'''
		Asks the volume for a new block, and sets its attributes accordingly, then it
		commits those changes to disk
		'''
		self.blocks += self.volume.allocateblocks(1)
		self.length += Drive.BLK_SIZE
		self.spareslots += 8
		self.children += [None for i in range(8)]

		### TODO
		# commit() on parent, part of the commit restructure
		self.commit()
	
	def getchildnames(self):
		'''
		Returns as a list the names of all the children of this Directory instance
		'''
		names = []
		for child in self.children:
			if child != None:
				names += [child.name]
		return names

	def killself(self):
		'''
		Directories may not be deleted if they have children, so killself() checks for those,
		and will deallocate its blocks if it can. It will call removechild() on its parent
		'''
		for child in self.children:
			if child != None:
				raise TinyException("Cannot remove, " + self.name + " is not empty")
		
		self.volume.deallocateblocks(self.blocks)
		self.parent.removechild(self)

	def populate(self):
		'''
		When populate() is called the Directory object will read all of its associated blocks,
		and from that it will work out its own statistics, and instantiate its children
		'''	
		# TODO
		# remove the slice objects, put slices where they belong
	
		typeslice = slice(1)
		nameslice = slice(2, 11)
		lengthslice = slice(11, 15)
		blockslice = slice(16, -1)
		children = []
		childcount = 0

		records = self.volume.readblocks(self.blocks)

		if self.rootflag:
			bitmap = records[:128]
			records = records[128:]
		
		n = len(records)
		records = [records[i:i+Volume.RECORD_LEN] for i in range(0, n, Volume.RECORD_LEN)]
		
		for record in records:
			name = record[nameslice].strip()
			length = int(record[lengthslice])
			blocks = record[blockslice]
			blocks = [int(x) for x in blocks.split() if int(x) != 0]
			if name == "":
				children += [None]
			else:
				childcount += 1
				if record[typeslice] == "d":
					child = Directory(name, self.volume, self, length, blocks= blocks)
					#child.populate() # FIXME This is the oldway brothers!
					children += [child]
				else:
					children += [File(name, self.volume, self, length, blocks)]
		
		self.children = children
		self.spareslots = (self.length // Volume.RECORD_LEN) - childcount
		self.populated = True
		
		if self.rootflag:
			self.spareslots -= 2
			return bitmap

	def removechild(self, child):
		'''
		Removes a given child from its list of children, and calls self.commit(), writing
		those changes to disk
		'''
		### TODO
		#	unexpand if possible

		if child not in self.children:
			raise TinyException(child.name + " is not my child")
		
		for i in range(len(self.children)):
			if self.children[i] == child:
				self.children[i] = None
		self.spareslots += 1
		self.commit()	

class File:
	'''
	This object represents a file on the file system
	'''
	def __init__(self, name, volume, parent, length=0, blocks=[], populated= False):
		self.name = name
		self.volume = volume
		self.parent = parent
		self.length = length
		self.blocks = copy(blocks)
		self.populated = False
		self.freespace = 0
		self.data = ""
	
		if len(name) > Volume.MAX_NAME:
			raise TinyException("Permitted name length exceeded")
	
	def append(self, data):
		'''
		Appends data to the File objects data field, will expand the File object if
		nessecary
		'''
		if len(data + self.data) > Volume.MAX_FILESIZE:
			raise TinyException("File is not tiny enough for TinyDOS")
		if len(data) <= self.freespace:
			self.data += data
			self.length += len(data)
			self.freespace -= len(data)
			self.commit()	
		else:
			self.expand()
			self.append(data)

	def commit(self):
		'''
		makes a string representation of the File objects data and then writes this
		via the Volume.writeblocks() method
		'''
		representation = self.data
	
		justifiedlength = len(self.blocks) * Drive.BLK_SIZE
		representation = representation.ljust(justifiedlength, " ")
		self.volume.writeblocks(self.blocks, representation)
		
		self.parent.commit()
		# TODO
		# investigate removing this

	def expand(self):
		'''
		Expands by one block and sets the freespace field as nessecary
		'''
		self.blocks += self.volume.allocateblocks(1)
		self.freespace += Drive.BLK_SIZE

	def killself(self):
		'''
		Deallocates all of the blocks for this File and has its parent directory
		remove it from its listing.
		'''
		self.volume.deallocateblocks(self.blocks)
		self.parent.removechild(self)

	def populate(self):
		if len(self.blocks) > 0:
			self.data =	self.volume.readblocks(self.blocks)[:self.length]
			self.freespace = (len(self.blocks) * Drive.BLK_SIZE) - len(self.data)
		self.populated = True

class TinyException(Exception):
	'''
	A class to represent all of the filesystem specific errors and unwanted situaitons
	'''
	pass
