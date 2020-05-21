#!/bin/env python3
import struct
import enum
from typing import List

SUPERBLOCK_SIZE = 4096
SECTOR_SIZE = 512
DIRECTORY_SIZE = 64

class SuperBlock():
	"""
	Offset	Size	Description
	0		4		"FATX" string (ASCII)
	4		4		Volume ID (int)
	8		4		Cluster size in (512 byte) sectors
	12		2		Number of FAT copies
	14		4		Unknown (always 0?)
	18		4078	Unused
	"""
	SUPERBLOCK_SIZE = 4096
	SECTOR_SIZE = 512
	SB_OFS_Name = 0
	SB_SIZE_Name = 4
	SB_OFS_VolumeId = 4
	SB_SIZE_VolumeId = 4
	SB_OFS_ClusterSize = 8
	SB_SIZE_ClusterSize = 4
	SB_OFS_FATCopies = 12
	SB_SIZE_FATCopies = 2
	SB_OFS_Unkown = 14
	SB_SIZE_Unkown = 4
	SB_OFS_Unused = 18
	SB_SIZE_Unused = 4078

	def __init__(self, sb):
		if(SUPERBLOCK_SIZE != len(sb)):
			raise BaseException('SuperBlock is not '+ str(SUPERBLOCK_SIZE) +' bytes long')
		self.name, self.volume, self.clusternum, self.fatcopies = struct.unpack('4sIIh4082x',sb)
		try:
			self.name = self.name.decode("ascii")
		except UnicodeDecodeError:
			raise BaseException("Can't decode 'FATX' signiture")

		self.clustersize = self.clusternum * SECTOR_SIZE
		assert("FATX" == self.name)
		assert(1 == self.fatcopies)
		assert(32 == self.clusternum)
		assert(16384 == self.clustersize)

	def __str__(self):
		return self.name


class EntryType(enum.Enum):
	FATX_CLUSTER_AVAILABLE = 0
	FATX_CLUSTER_RESERVED = 1
	FATX_CLUSTER_BAD = 2
	FATX_CLUSTER_DATA = 3
	FATX_CLUSTER_END = 4


class FAT():
	"""
	| 	0x0000		| This cluster is free for use 
	| 	0x0001		| Usually used for recovery after crashes(unkown if used by the xbox) 
	|0x0002 - 0xFFEF| This cluster is part of a chain and points to the next cluster 
	|0xFFF0 - 0xFFF5| Reserved(unkown if used by the xbox) 
	| 	0xfff7		| Bad sectors in this cluster - this cluster should not be used 
	|0xfff8 - 0xffff| Marks the end of a cluster chain 
	"""

	def __init__(self, raw_clustermap):
		self.f = raw_clustermap
		# number of bytes per cluster entry
		# usually 2(FATX16) or 4(FATX32) bytes
		self.size = 2 if len(raw_clustermap) < (0xfff5 * 2) else 4
		self.clustermap = []

		# ToDo use memory view for zerocopy magic
		# slice up the fat table
		while len(self.f) > 0:
			entry = int.from_bytes(self.f[:self.size], 'little')
			self.f = self.f[self.size:]
			self.clustermap.append(entry)

	def numberClusters(self):
		return len(self.clustermap)

	def getEntryType(self, entry):
		if entry == 0x0000:
			return EntryType.FATX_CLUSTER_AVAILABLE
		if entry == 0x0001:
			return EntryType.FATX_CLUSTER_RESERVED
		if self.size == 2:
			if entry == 0xFFF7:
				return EntryType.FATX_CLUSTER_BAD
			if entry > 0xFFF7:
				return EntryType.FATX_CLUSTER_END
		else:
			if entry == 0xFFFFFFF7:
				return EntryType.FATX_CLUSTER_BAD
			if entry > 0xFFFFFFF7:
				return EntryType.FATX_CLUSTER_END
		return EntryType.FATX_CLUSTER_DATA

	# Warning: Ugly code ahead!
	# set an entry in the FAT to either a special type or pointer
	def setEntryType(self, pos, entrytype):
		if self.size == 2:
			if entrytype == EntryType.FATX_CLUSTER_AVAILABLE:
				t = 0x0000
			elif entrytype == EntryType.FATX_CLUSTER_RESERVED:
				t = 0x0001
			elif entrytype == EntryType.FATX_CLUSTER_BAD:
				t = 0xFFF7
			elif entrytype == EntryType.FATX_CLUSTER_END:
				t = 0xFFFF
			else:
				# Just to be sure nobody is being stupid
				assert(self.getEntryType(self.clustermap[pos]) == EntryType.FATX_CLUSTER_AVAILABLE)
				t = entrytype
		if self.size == 4:
			if entrytype == EntryType.FATX_CLUSTER_AVAILABLE:
				t = 0x00000000
			elif entrytype == EntryType.FATX_CLUSTER_RESERVED:
				t = 0x00000001
			elif entrytype == EntryType.FATX_CLUSTER_BAD:
				t = 0xFFFFFFF7
			elif entrytype == EntryType.FATX_CLUSTER_END:
				t = 0xFFFFFFFF
			else:
				# Just to be sure nobody is being stupid
				assert(self.getEntryType(self.clustermap[pos]) == EntryType.FATX_CLUSTER_AVAILABLE)
				t = entrytype
		self.clustermap[pos] = t

	# collects the IDs/No. of clusters of a chain of a given start cluster 
	def clusterChain(self, pointer):
		l = []
		l.append(pointer)

		# Your first pointer should always point to either the next 
		# clusterchain element or mark the end of a chain
		nvalue = self.getEntryType(self.clustermap[pointer])
		if nvalue not in [EntryType.FATX_CLUSTER_DATA, EntryType.FATX_CLUSTER_END]:
			raise ValueError("Start cluster is not part of a chain")

		# We are not at the end of the chain
		while nvalue != EntryType.FATX_CLUSTER_END:
			# get the next pointer
			pointer = self.clustermap[pointer]
			l.append(pointer)
			# lookup the pointer, so we can check if it is the end of the chain
			nvalue = self.getEntryType(self.clustermap[pointer])
			if nvalue in [EntryType.FATX_CLUSTER_BAD, EntryType.FATX_CLUSTER_RESERVED, EntryType.FATX_CLUSTER_AVAILABLE]:
				raise SystemError("One chain element is invalid", nvalue)
		return l

	# frees a given chain, setting all cluster free
	def freeClusterChain(self, chain: List[int]):
		for cluster in chain:
			self.setEntryType(cluster, EntryType.FATX_CLUSTER_AVAILABLE)

	# collects a list of IDs/No. of clusters that are free
	def getFreeClusterChain(self, nclusters):
		# l shall store the list of free clusters
		l = []
		pos = 1
		for i in range(nclusters):
			# Dirty, FIXME!				   MagicValue :(
			l.append(self.clustermap.index(0x0000, pos))
			pos = l[-1]+1
		return l

	# links a number of clusters together and terminates the list
	def linkClusterChain(self, clusterchain):
		clusterchain = clusterchain.copy()
		index = clusterchain.pop(0)
		while len(clusterchain) > 0:
			pointer = clusterchain.pop(0)
			self.setEntryType(index, pointer)
			index = pointer
		self.setEntryType(index, EntryType.FATX_CLUSTER_END)

	def pack(self):
		data = b''
		for i in self.clustermap:
			if self.size == 2:
				data += struct.pack('H', i)
			else:
				data += struct.pack('I', i)
		if len(data) % 4096:
			data += (4096 - len(data) % 4096)*b'\x00'
		return data

	def __str__(self):
		return "FAT: {0} entrys of {1} bytes each".format(self.numberClusters(), self.size)


class DirectoryEntry():
	""" 
	DirectoryEntry, byte representation
	Offset	Size	Description
	0		1		Size of filename (max. 42)
	1		1		Attribute as on FAT
	2		42		Filename in ASCII, padded with 0xff (not zero-terminated)
	44		4		First cluster
	48		4		File size in bytes
	52		2		Modification time
	54		2		Modification date
	56		2		Creation time
	58		2		Creation date
	60		2		Last access time
	62		2		Last access date
	"""
	DIRECTORY_SIZE = 64
	D_OFS_NAMESIZE = 0
	D_SIZE_NAMESIZE = 1
	D_OFS_ATTRIBUT = 1
	D_SIZE_ATTRIBUT = 1
	D_OFS_NAME = 2
	D_SIZE_NAME = 42
	D_OFS_CLUSTER = 44
	D_SIZE_CLUSTER = 4
	D_OFS_FILESIZE = 48
	D_SIZE_FILESIZE = 4

	"""
	Attributes, byte values/mask
	0x01 - Indicates that the file is read only.
	0x02 - Indicates a hidden file. Such files can be displayed if it is really required.
	0x04 - Indicates a system file. These are hidden as well.
	0x08 - Indicates a special entry containing the disk's volume label, instead of describing a file. This kind of entry appears only in the root directory.
	0x10 - The entry describes a subdirectory.
	0x20 - This is the archive flag. This can be set and cleared by the programmer or user, but is always set when the file is modified. It is used by backup programs.
	0x40 - Not used; must be set to 0.
	0x80 - Not used; must be set to 0.
	"""
	ATR_READONLY = 0x01
	ATR_HIDDEN = 0x02
	ATR_SYSTEM = 0x04
	ATR_VOLUMELABEL = 0x08
	ATR_DIRECTORY = 0x10
	ATR_ARCHIVE = 0x20

	# ToDo: Add pack method
	class Attributes():
		def __init__(self):
			self.READONLY = False
			self.HIDDEN = False
			self.SYSTEM = False
			self.VOLUMELABEL = False
			self.DIRECTORY = False
			self.ARCHIVE = False
			self.DELETED = False


	def __init__(self, d, origin):
		# Size of the name
		self.namesize = 0
		# The name(all 42 bytes)
		self.name = 0
		# the cluster number where the file/directory is saved 
		self.cluster = 1
		# size of file
		self.size = 0
		# The name in ascii (less or equal to 42 bytes)
		self.filename = ""
		# DirectoryEntryList where this DirectoryEntry was read from
		self.origin = origin
		self.atr = self.Attributes()

		if(DIRECTORY_SIZE != len(d)):
			raise ValueError('Directory is '+str(len(d))+' bytes long. Expected '+ str(self.DIRECTORY_SIZE) +' bytes.')
		raw = struct.unpack('BB42sII12x',d)
		self.namesize = raw[0]

		# This is not a real entry, it may mark the end of the entry list
		if 0xFF == self.namesize or 0x00 == self.namesize:
			raise SystemError("Invalid directory entry")

		# This file is deleted(but we will try to recover the name a bit)
		if 0xE5 == self.namesize:
			self.atr.DELETED = True
			self.namesize = 42

		# The size of a name cannot exceed the actual byte length of the name field
		if(42 < self.namesize):
			raise SystemError("Namesize is longer("+hex(self.namesize)+")then max length("+hex(42)+").")

		self.attributes = raw[1]
		self.name = raw[2]
		self.cluster = raw[3] # first cluster of the file
		self.size = raw[4]
		self.atr.READONLY = bool(self.attributes & self.ATR_READONLY)
		self.atr.HIDDEN = bool(self.attributes & self.ATR_HIDDEN)
		self.atr.SYSTEM = bool(self.attributes & self.ATR_SYSTEM)
		self.atr.VOLUMELABEL = bool(self.attributes & self.ATR_VOLUMELABEL)
		self.atr.DIRECTORY = bool(self.attributes & self.ATR_DIRECTORY)
		self.atr.ARCHIVE = bool(self.attributes & self.ATR_ARCHIVE)
		self.filename = "".join([chr(i) for i in self.name[:self.namesize] if i > 0x1F and i < 0x7F])

	def rename(self, name):
		if len(name) > 42:
			raise ValueError('Name is to long (max 42 character)')
		self.name = bytearray(name, 'ascii')+((42-len(name))*b'\xFF')
		self.filename = name
		self.namesize = len(name)

	def pack(self):
		def set_bit(boolvalue, bit):
			if boolvalue:
				return bit
			return 0
		self.attributes = 0
		self.attributes |= set_bit(self.atr.READONLY, self.ATR_READONLY)
		self.attributes |= set_bit(self.atr.HIDDEN, self.ATR_HIDDEN)
		self.attributes |= set_bit(self.atr.SYSTEM, self.ATR_SYSTEM)
		self.attributes |= set_bit(self.atr.VOLUMELABEL, self.ATR_VOLUMELABEL)
		self.attributes |= set_bit(self.atr.DIRECTORY, self.ATR_DIRECTORY)
		self.attributes |= set_bit(self.atr.ARCHIVE, self.ATR_ARCHIVE)
		if self.atr.DELETED:
			self.namesize = 0xE5
		raw = struct.pack('BB42sII12x', self.namesize,
										self.attributes,
										self.name,
										self.cluster,
										self.size)
		return raw

	# ToDo: switch into to functions for either file or directory
	@classmethod
	def new(cls, size, name):
		self = cls.__new__(cls)
		try:
			self.rename(name)
		except ValueError as e:
			raise e
		self.size = size
		self.cluster = 0
		self.atr = self.Attributes()
		return self

	def __str__(self):
		return self.filename


class DirectoryEntryList():
	# Cluster is the raw binary block containing one ore more DirectoryEntrys
	# ToDo: use memoryview and aim for zero-copy
	def __init__(self, data, clusterID):
		self.clusterID = clusterID
		self.l = []

		if len(data) % 64 != 0:
			raise ValueError("Invalid datasize")

		for offset in range(0, len(data), 64):
			if data[offset] == 0xFF:
				data = data[:offset]
				break
		else:
			# in case break wasn't tiggerd
			raise SystemError("Missing termination of directory entry list")

		for offset in range(0, len(data), 64):
			try:
				de = DirectoryEntry(data[offset:offset+DIRECTORY_SIZE], self)
				self.l.append(de)
			except ValueError as e:
				# I messed up
				raise e
			except SystemError as e:
				# The filesystem messed up
				raise e

	def list(self):
		return self.l

	def append(self, directoryentry):
		self.l.append(directoryentry)

	def pack(self):
		data = b''
		for i in self.l:
			data += i.pack()
		data += b'\xFF'+b'\x00'*(DIRECTORY_SIZE-1)
		return data

	
