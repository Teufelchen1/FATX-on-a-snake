#!/bin/env python3
import struct
import os
import argparse
import json
from cmd import Cmd

SUPERBLOCK_SIZE = 4096
DIRECTORY_SIZE = 64
SECTOR_SIZE = 512


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
			print('SuperBlock is not '+ str(SUPERBLOCK_SIZE) +' bytes long')
			raise BaseException
		self.name, self.volume, self.clustersize, self.fatcopies = struct.unpack('4sIIh4082x',sb)
		self.name = self.name.decode("ascii") 
		assert("FATX" == self.name)
		assert(1 == self.fatcopies)
		assert(32 == self.clustersize)

	def __str__(self):
		return self.name


class FATX():
	class Cluster():
		def __init__(self, num, target):
			self.num = num
			self.target = target
			self.next = None

		def __str__(self):
			return str(self.num)+':'+str(self.target)

	def __init__(self, f, size):
		self.rawcluster = {}
		self.fat = f

		# slice up the fat table into Cluster objects(pff, we got the memory)
		while len(f) > 0:
			entry = int.from_bytes(f[:size], 'little')
			f = f[size:]
			i = len(self.rawcluster)
			if entry > 0xfff7:
				entry = None
			self.rawcluster[i] = self.Cluster(i, entry)

		# try to build some linked list and do a little sanity check
		for v in self.rawcluster.values():
			if v.target:
				try:
					v.next = self.rawcluster[v.target]
				except:
					print("invalid FAT entry: target out of scope: "+str(v))

	def __str__(self):
		return str(len(self.rawcluster)) + ' Clusters available'
		#return str([str(c) for c,v in self.rawcluster]) # prints all chunks that are in use


class DirectoryEntry():
	""" DirectoryEntry, byte representation
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

	"""Attributes, byte values/mask
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

	class Attributes():
		READONLY = False
		HIDDEN = False
		SYSTEM = False
		VOLUMELABEL = False
		DIRECTORY = False
		ARCHIVE = False


	def __init__(self, d):
		if(DIRECTORY_SIZE != len(d)):
			print('Directory is '+str(len(d))+' bytes long. Expected '+ str(self.DIRECTORY_SIZE) +' bytes.')
			raise BaseException
		raw = struct.unpack('BB42sII12x',d)
		self.namesize = raw[0]
		if self.namesize == 0xE5:
			# deletion
			self.filename = "DELETE"
			return
		if self.namesize == 0x00 or self.namesize == 0xFF:
			# end of list
			self.filename = "END"
			return
		
		self.attributes = raw[1]
		assert(43 > self.namesize) # The size of a name cannot exceed the actual byte length of the name field
		self.name = raw[2]
		self.cluster = raw[3] # first cluster of the file
		self.size = raw[4]

		self.atr = self.Attributes()
		self.atr.READONLY = bool(self.attributes & self.ATR_READONLY)
		self.atr.HIDDEN = bool(self.attributes & self.ATR_HIDDEN)
		self.atr.SYSTEM = bool(self.attributes & self.ATR_SYSTEM)
		self.atr.VOLUMELABEL = bool(self.attributes & self.ATR_VOLUMELABEL)
		self.atr.DIRECTORY = bool(self.attributes & self.ATR_DIRECTORY)
		self.atr.ARCHIVE = bool(self.attributes & self.ATR_ARCHIVE)
		self.filename = self.name[:self.namesize]
		self.filename = self.filename.decode("ascii")
		

	def __str__(self):
		return self.filename


class Filesystem():
	def __init__(self, file):
		self.partition_size = os.stat(file).st_size
		self.f = open(file, 'rb')
		self.sb = SuperBlock(self.f.read(SUPERBLOCK_SIZE))

		# ((partition size in bytes / cluster size) * cluster map entry size)
		#							 rounded up to nearest 4096 byte boundary. 0x2ee00000
		number_of_clusters = self.partition_size / (self.sb.clustersize*SECTOR_SIZE)
		self.size = 2 if number_of_clusters <= 0xffff else 4 # deciding how big a fat entry is in bytes
		fat_size = number_of_clusters * self.size
		#fat_size = (self.partition_size / (self.sb.clustersize*SECTOR_SIZE)) * 2
		if fat_size % 4096:
			fat_size += 4096 - fat_size % 4096
		self.fat_size = fat_size
		self.fat = FATX(self.f.read(int(fat_size)), self.size)

		self.rootdir = {}
		self.rootdir = self.readInDir()

	def readInDir(self):
		# this function assumes that the offset in the file is already prepared and points to some directory entrys
		# it returns the list of all directory entrys found as Dict of DirectoryEntrys
		readDir = {}
		d = DirectoryEntry(self.f.read(DIRECTORY_SIZE))
		while d.filename != "END" and d.filename != "DELETE":
			readDir[d.filename] = d
			d = DirectoryEntry(self.f.read(DIRECTORY_SIZE))
		return readDir

	def calcClusterOffset(self, clusternummer):
		# returns the byte offset of a given cluster
		# each cluster is clustersize(from the superblock) times sectorsize big
		# since its an offset, the superblock and the fat are added
		return int((clusternummer - 1)*self.sb.clustersize*SECTOR_SIZE + self.fat_size + SUPERBLOCK_SIZE)

	def chdir(self, path):
		# this function should yield either a list of all files & directorys in the specified `path`
		# or None, if the `path` points to a file, is not found or an error occoured
		segs = path.split('/')
		segs = [seg for seg in segs if seg] # remove empty strings
		cwd = self.rootdir
		for seg in segs:
			if seg not in cwd.keys():
				return None, "Path not found"

			# fetch the first file/folder as d from the rootdir/current dir
			d = cwd[seg]

			# check if d is a File
			if not d.atr.DIRECTORY: 
				# undesired behavior: cd /folderA/file.txt/folderB/ would return node of file.txt
				# return the file as DirectoryEntry without an error
				return None, path+" is a file"

			# check if the corresponding cluster has a target, 
			# therefore is not the last element of the linked list -> The file spans more then one chunk 
			if self.fat.rawcluster[d.cluster].target:
				return None, "Huge files not supported / multicluster files"
			offset = self.calcClusterOffset(d.cluster)
			self.f.seek(offset)
			cwd = self.readInDir()
			# go to folder ... 
		return cwd, None

	def getFileEntry(self, path):
		# this function returns the DirectoryEntry of a file
		path, filename = path.rsplit('/', 1)
		cwd, err = self.chdir(path)
		if err:
			print(err)
			return None
		if filename not in cwd.keys():
			print("File not found")
			return None
		file = cwd[filename]
		return file

	def getFileContent(self, file):
		# this function should return a byte array of the content of the file
		if file.atr.DIRECTORY:
			print(file.filename+" is a directory")
			return None
		offset = self.calcClusterOffset(file.cluster)
		self.f.seek(offset)
		print(hex(offset))
		return self.f.read(file.size)

	def __str__(self):
		return self.sb.name


class CLI(Cmd):
	wd = []
	parent = {}
	path = ""

	def setupFS(self, file):
		self.fs = Filesystem(file)
		self.wd = self.fs.rootdir.values()
		self.parent = self.wd
		self.path = "/"
		self.do_info()

	def autocomplete(self, text):
		names = [i.filename for i in self.wd]
		return [i for i in names if i.startswith(text)]

	def do_info(self, args=None):
		"""Print information about the current FATX filesystem"""
		print("Name: " + self.fs.sb.name)
		print("Volume Id: " + str(self.fs.sb.volume))
		print("Clustersize: " + str(self.fs.sb.clustersize))
		print("FAT Copies: " + str(self.fs.sb.fatcopies))
		if(self.fs.size == 4):
			print("Type: FATX32")
		elif(self.fs.size == 2):
			print("Type: FATX16")

	def do_ls(self, args):
		"""Lists current dir"""
		out = ""
		if "-l" in args or "--list" in args:
			for item in self.wd:
				if item.atr.DIRECTORY:
					out += 'd'
				else:
					out += '-'
				if item.atr.READONLY:
					out += 'r- '
				else:
					out += 'rw '
				out += str(item.size).rjust(7)
				out += ' '+item.filename+"\n"
		else:
			for item in self.wd:
				out += item.filename+"\t"

		print(out)

	def do_pwd(self, args):
		"""print working directory"""
		print(self.path)

	def complete_cd(self, text, line, begidx, endidx):
		return self.autocomplete(text)

	def do_cd(self, args):
		"""change directory"""
		if args == '':
			args = '/'
		if args == ".":
			pass
		elif args == "..":
			# don't @ me
			self.path = self.path[:-len(self.path.split("/")[-2])-1]
			if len(self.path) == 0:
				self.path = '/'
			chdir, err = self.fs.chdir(self.path)
			if err:
				print(err)
				self.path = '/'
				self.prompt = self.path+' > '
				return
			self.wd = chdir.values()
		else:
			if '/' != args[0]:
				args = self.path+args
			if '/' != args[-1]:
				args += '/'
			chdir, err = self.fs.chdir(args)
			if err:
				print(err)
			else:
				self.path = args
				self.wd = chdir.values()
		self.prompt = self.path+' > '

	def do_tree(self, args):
		'tree [depth=10]'
		max_depth = 10
		if args:
			try:
				max_depth = int(args[0])
			except:
				print("Can not convert %s into int", args)
				return

		def tree(path, max_depth=10):
			out = {}
			chdir, err = self.fs.chdir(path)
			if err:
				print(err)
				return {}
			for d in chdir.values():
				if d.atr.DIRECTORY:
					if max_depth != 0:
						out[d.filename] = tree(path+'/'+d.filename, max_depth - 1)
					else:
						out[d.filename] = '{}'
				else:
					out[d.filename] = d.filename
			return out
		print(json.dumps(tree(self.path, max_depth), sort_keys=True, indent=2))

	def complete_cat(self, text, line, begidx, endidx):
		return self.autocomplete(text)

	def do_cat(self, args):
		"""Print content of a file"""
		if '/' != args[0]:
			args = self.path+args
		print(self.fs.getFileContent(self.fs.getFileEntry(args)))

	def complete_export(self, text, line, begidx, endidx):
		return self.autocomplete(text)

	def do_export(self, args):
		"""Exports <source> from the FATX to <destination> on you host"""
		args = args.split(' ')
		if(len(args) != 2):
			print("Usage:export <source> <destination>")
			return
		f = open(args[1],'wb')
		if '/' != args[0][0]:
			args[0] = self.path+args[0]
		f.write(self.fs.getFileContent(self.fs.getFileEntry(args[0])))
		print(str(f.tell()) + "bytes written.")
		f.close()

	def do_q(self, args):
		"""Quits the program."""
		self.do_quit(args)

	def do_quit(self, args):
		"""Quits the program."""
		print("Quitting.")
		raise SystemExit


if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("file", type=str, help="filesystem image")
	parser.add_argument("--cl", action='store_true', help="interactive command line")
	parser.add_argument("--show", action='store_true', help="show informations about the fs")
	args = parser.parse_args()
	if args.cl:
		prompt = CLI()
		prompt.prompt = '> '
		prompt.setupFS(args.file)
		prompt.cmdloop('This is just minimal prompt, not a shell!')
	elif args.show:
		fs = Filesystem(args.file)
		print("Name: " + fs.sb.name)
		print("Volume Id: " + str(fs.sb.volume))
		print("Clustersize: " + str(fs.sb.clustersize))
		print("FAT Copies: " + str(fs.sb.fatcopies))
		if(fs.size == 4):
			print("Type: FATX32")
		elif(fs.size == 2):
			print("Type: FATX16")
		print("FAT size: " + str(int(fs.fat_size)))
		print("Partition size: " + str(fs.partition_size))


	else:
		print('Nothing to do')




