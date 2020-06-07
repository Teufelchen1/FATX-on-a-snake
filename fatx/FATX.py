import io, os, math
from .blocks import SuperBlock, FAT, DirectoryEntry, DirectoryEntryList
from .interface import RootObject, FatxObject

"""
This file mainly contains horrible code. Please don't look to much at it. 
It links the high abstraction (public) API form interface.py with 
the byte-representing objects in blocks.py. 
It should be the only place where data is read and written. 
"""

READ_ONLY = True

FATX16 = 2
FATX32 = 4

def writing_warning(func):
	def call(*args, **kwargs):
		print("Warning! Writing changes to the disk!")
		if not READ_ONLY:
			return func(*args, **kwargs)
		else:
			print("Skip saving changes to disk, change READ_ONLY to False")
			return None

	return call


class Filesystem():
	def __init__(self, file: str, sector_size: int = 512):
		self.f = open(file, 'r+b')
		self.sb = SuperBlock(self.f.read(SuperBlock.SUPERBLOCK_SIZE), sector_size)

		self.fat_size = self._calc_fat_size(os.stat(file).st_size, self.sb.cluster_size)
		self.fat = FAT(self.f.read(self.fat_size))

		# Sadly, sometimes the interfaces need to access the filesystem
		FatxObject.registerFilesystem(self)

		# Read the first(yes, 1, not zero) Cluster, it should contain the root DirectoryEntry list
		cluster = self._get_cluster(1)
		self.root = RootObject(DirectoryEntryList(cluster, 1))

	@classmethod
	def new(cls, size: int, file: str, sector_size: int = 512):
		self = cls.__new__(cls)
		self.f = open(file, 'w+b')

		self.sb = SuperBlock.new(sector_size)
		self.fat_size = self._calc_fat_size(size, self.sb.cluster_size)
		self.fat = FAT.new(self.fat_size)
		root_dl = DirectoryEntryList(b'\xFF'*64, 1)

		self.f.write(self.sb.pack())
		self.f.write(self.fat.pack())
		self.f.write(b'\x00'*(size - self.fat_size - SuperBlock.SUPERBLOCK_SIZE))
		self._write_directory_list(root_dl)

		FatxObject.registerFilesystem(self)

		cluster = self._get_cluster(1)
		self.root = RootObject(DirectoryEntryList(cluster, 1))
		return self

	# returns a DirectoryEntryList from the cluster assosiated in the given directoryentry
	def open_directory(self, de: DirectoryEntry):
		assert(de.atr.DIRECTORY)
		cluster = self._get_cluster(de.cluster)
		try:
			return DirectoryEntryList(cluster, de.cluster)
		except SystemError as e:
			print(e)
			self._print_debug(de)
			return None

	# Reads a File and returns it
	def read_file(self, de: DirectoryEntry):
		data = bytearray()
		if de.atr.DIRECTORY:
			raise ValueError("This is a directory, not a file")
		try:
			clusters = self.fat.clusterChain(de.cluster)
			for i in clusters:
				data += self._get_cluster(i)
			return data[:de.size]
		except Exception as e:
			print(e)
			self._print_debug(de)
			print("\tread {0} from {1} bytes".format(len(data), de.size))
			return data

	def rename_object(self, de: DirectoryEntry, name: str):
		de.rename(name)
		self._write_directory_entry(de)

	def create_folder(self, dl: DirectoryEntryList, name: str):
		de = DirectoryEntry.new_entry(name, dl)
		de.atr.DIRECTORY = True
		dl.append(de)
		chain = self.fat.getFreeClusterChain(1)
		de.cluster = chain[0]
		new_dl = DirectoryEntryList(b'\xFF'*64, chain[0])

		self.fat.linkClusterChain(chain)
		self._write_directory_list(dl)
		self._write_directory_list(new_dl)

	def import_file(self, dl: DirectoryEntryList, name: str, data: bytes):
		de = DirectoryEntry.new_entry(name, dl)
		de.size = len(data)
		# get a clusterchain(=list of free clusters we can write onto)
		# number of clusters needed to store a file size n
		nclusters = math.ceil(float(de.size)/float(self.sb.cluster_size))
		chain = self.fat.getFreeClusterChain(nclusters)
		de.cluster = chain[0]
		dl.append(de)

		self.fat.linkClusterChain(chain)
		self._write_data(chain, data)
		self._write_directory_list(dl)
		# ToDo: very inefficient, needs to be redone
		self._write_fat()

	def status(self):
		print(self.__str__())

	def _write_directory_entry(self, de: DirectoryEntry):
		# ToDo: Reduce to writing this single DirectoryEntry
		# i.e. position_of_de * de_size + base_address
		self._write_directory_list(de.origin)

	@writing_warning
	def _write_directory_list(self, dl: DirectoryEntryList):
		self.f.seek(self._cluster_id_offset(dl.cluster))
		data = dl.pack()
		# add padding
		data += (self.sb.cluster_size - len(data))*b'\xFF'
		self.f.write(data)

	@writing_warning
	def _write_fat(self):
		self.f.seek(SuperBlock.SUPERBLOCK_SIZE)
		self.f.write(self.fat.pack())

	@writing_warning
	def _write_data(self, clusterchain: [int], data):
		for i in clusterchain:
			self.f.seek(self._cluster_id_offset(i))
			self.f.write(data[:self.sb.cluster_size])
			data = data[self.sb.cluster_size:]

	def _get_cluster(self, ID: int):
		self.f.seek(self._cluster_id_offset(ID))
		return self.f.read(self.sb.cluster_size)

	# Calculates the offset for a given clusterID
	def _cluster_id_offset(self, ID: int):
		if ID == 0:
			raise ValueError("Cluster ID must be greater then 0")
		#(Number of your cluster -1) * cluster size + Superblock + FAT
		return (ID-1) * self.sb.cluster_size + SuperBlock.SUPERBLOCK_SIZE + self.fat_size

	@staticmethod
	def _calc_fat_size(partition_size: int, cluster_size: int):
		# ((partition size in bytes / cluster size) * cluster map entry size)
		# rounded up to nearest 4096 byte boundary.
		number_of_clusters = partition_size // cluster_size
		size = FATX16 if number_of_clusters <= 0xfff5 else FATX32 # deciding how big a fat entry is in bytes
		fat_size = number_of_clusters * size
		if fat_size % 4096:
			fat_size += 4096 - fat_size % 4096
		return int(fat_size)

	def _print_debug(self, de: DirectoryEntry):
		print("\tName: {0}".format(de.filename))
		print("\tCluster ID: {0}".format(de.cluster))
		try:
			print("\tOffset: 0x{0:X}".format(self._cluster_id_offset(de.cluster)))
		except:
			print("\tOffset: Failed calculating the offset")

	def __str__(self):
		return "{0} ~ {1}".format(str(self.sb), str(self.fat))

