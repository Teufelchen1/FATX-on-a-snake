import os, math
from .blocks import SuperBlock, FAT, DirectoryEntry, DirectoryEntryList
from .interface import *

"""
This file mainly contains horrible code. Please don't look to much at it. 
It links the high abstraction (public) API form interface.py with 
the byte-representing objects in blocks.py. 
It should be the only place where data is read and written. 
"""


READ_ONLY = True

SUPERBLOCK_SIZE = 4096
SECTOR_SIZE = 512
DIRECTORY_SIZE = 64

def writingWarning(func):
	def call(*args, **kwargs):
		print("Warning! writing changes to the disk!")
		if not READ_ONLY:
			return func(*args, **kwargs)
		else:
			raise SystemError("User abort, change READ_ONLY to False")

	return call

class Filesystem():

	def __init__(self, file):
		self.partition_size = os.stat(file).st_size
		self.f = open(file, 'r+b')
		self.sb = SuperBlock(self.f.read(SUPERBLOCK_SIZE))

		# ((partition size in bytes / cluster size) * cluster map entry size)
		#							 rounded up to nearest 4096 byte boundary. 0x2ee00000
		number_of_clusters = self.partition_size / self.sb.clusterSize()
		self.size = 2 if number_of_clusters <= 0xffff else 4 # deciding how big a fat entry is in bytes
		fat_size = number_of_clusters * self.size
		#fat_size = (self.partition_size / (self.sb.clustersize*SECTOR_SIZE)) * 2
		if fat_size % 4096:
			fat_size += 4096 - fat_size % 4096
		self.fat_size = fat_size
		self.fat = FAT(self.f.read(int(fat_size)), self.size)

		# Sadly, sometimes the interfaces need to access the filesystem
		FatxObject.registerFilesystem(self)

		# Read the first Cluster, it should contain the root DirectoryEntry list
		cluster1 = self.readClusterID(1)
		self.root = RootObject(DirectoryEntryList(cluster1, 1))

	def __str__(self):
		return "Type: FATX{0}\nNumber of clusters in map: {1}".format(8*self.size, self.fat.numberClusters())

	def status(self):
		print(self.__str__())

	# Calculates the offset for a given clusterID
	def getClusterOffset(self, clusterID):
		#(Number of your cluster -1) * cluster size + Superblock + FAT
		return int((clusterID-1) * self.sb.clusterSize() + SUPERBLOCK_SIZE + self.fat_size)

	def readClusterID(self, ID):
		return self.readCluster(self.getClusterOffset(ID))

	def readCluster(self, offset):
		self.f.seek(offset)
		return self.f.read(self.sb.clusterSize())

	# Should be moved into DirectoryEntryList object
	# Appends a DirectoryEntry to list
	def appendDirectoryEntryList(self, clusterID, directoryentry):
		def findNoOfEntrys(cluster):
			numentrys = 0
			while numentrys < 256:
				try:
					DirectoryEntry(cluster[numentrys*DIRECTORY_SIZE:][:DIRECTORY_SIZE], (clusterID, numentrys))
					numentrys += 1
				except StopIteration:
					break
					# end of list
				except ValueError:
					# I messed up
					raise ValueError
				except SystemError:
					# The filesystem messed up
					raise SystemError
			return numentrys

		cluster = self.readClusterID(clusterID)
		num = findNoOfEntrys(cluster)
		print(num)

	# Opens a directory and returns a DirectoryEntryList of the contents
	def openDirectory(self, directoryentry):
		if not directoryentry.atr.DIRECTORY:
			raise ValueError("This is not a directory, it is a file")
		# this cluster should contain a DirectoryEntryList
		cluster = self.readClusterID(directoryentry.cluster)
		return DirectoryEntryList(cluster, directoryentry.cluster)

	# Reads a File and returns it
	def readFile(self, directoryentry):
		data = bytearray()
		if directoryentry.atr.DIRECTORY:
			raise ValueError("This is a directory, not a file")
		clusters = self.fat.clusterChain(directoryentry.cluster)
		for i in clusters:
			data += self.readClusterID(i)
		return data[:directoryentry.size]

	# Re-Writes a directoryentry i.e. after some attributes changed
	@writingWarning
	def writeDirectoryEntry(self, directoryentry):
		delist = directoryentry.origin
		clusterID = delist.clusterID
		numentry = delist.list().index(directoryentry)
		offset = self.getClusterOffset(clusterID)
		offset += DIRECTORY_SIZE*numentry
		self.f.seek(offset)
		if DIRECTORY_SIZE != self.f.write(directoryentry.pack()):
			raise SystemError("Unsuccessfull write, your FS is broken now :( sorry!")

	# Deletes a directoryentry and re-writes it
	def delete(self, directoryentry):
		directoryentry.atr.DELETED = True
		self.writeDirectoryEntry(directoryentry)

	# Renames a directoryentry and re-writes it
	def rename(self, directoryentry, name):
		try:
			directoryentry.rename(name)
		except ValueError as e:
			raise e
		self.writeDirectoryEntry(directoryentry)

	# Warning: Ugly code ahead!
	@writingWarning
	def writeFile(self, file, size):
		# get a clusterchain(=list of free clusters we can write onto)
		# number of clusters needed to store a file size n
		nclusters = math.ceil(float(size)/float(self.sb.clusterSize()))
		try:
			cc = self.fat.getFreeClusterChain(nclusters)
		except ValueError:
			raise SystemError("Not enough free space left on the fs")
		# Make each entry point to the next one and mark the end of the chain
		self.fat.linkClusterChain(cc.copy())
		for i in cc:
			offset = self.getClusterOffset(i)
			self.f.seek(offset)
			self.f.write(file.read(self.sb.clusterSize()))
		return cc[0]

	# Writes a DirectoryEntryList to disk
	@writingWarning
	def writeDirectoryEntryList(self, dl):
		self.f.seek(self.getClusterOffset(dl.clusterID))
		self.f.write(dl.pack())

		





