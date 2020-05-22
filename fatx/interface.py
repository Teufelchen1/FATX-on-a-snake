import os
from .blocks import DirectoryEntry, DirectoryEntryList

"""
This file contains four classes which are used as the main interface for 
the user of FATX-on-a-snake. 
Actually, I lied, you are only supposed to interact with three
of them, since FatxObject is the common baseclass from wich the others
extend. My reasoning behind this is, that in FATX you only interact with
"DirectoryEntrys" which are always the same, no matter if they are a file
or a directory. So it makes sense to me that they should share a similar
interface which subclasses extend to implement specific behavior. 
The functions of the classes are described in the README, how ever since 
you are already here, take a look at FatxObject and read the comments on 
the methodes. :)

"""


class FatxObject():
	_filesystem = None

	@classmethod
	def registerFilesystem(cls, fs):
		cls._filesystem = fs

	# Note: type hinting with selfreference(for parent) is possible but ugly :(
	def __init__(self, directoryentry: DirectoryEntry, parent): 
		self._de = directoryentry
		self._name = self._de.filename
		self.attributes = self._de.atr
		self._parent = parent

	def details(self):
		"""
		Prints its own attributes
		"""
		return self._de.atr.__dict__

	def parent(self):
		"""
		parent() should return the FatxObject that can point to
		this object(parent dir)
		"""
		return self._parent

	def rename(self, name: str):
		"""
		renames this object and safes the change to disk
		"""
		try:
			self._filesystem.rename_object(self._de, name)
			self._name = self._de.filename
		except ValueError as e:
			print(e)

	def delete(self):
		"""
		Marks this object as deleted and safes change to disk
		"""
		raise NotImplementedError("Override this in the subclass")

	def __str__(self):
		return self._name

	def __repr__(self):
		return str(self.__class__)+ ': ' + str(self)


class FileObject(FatxObject):
	def export(self):
		"""
		returns all bytes belonging to this file
		"""
		return self._filesystem.read_file(self._de)


class DirectoryObject(FatxObject):
	"""
	 This class represents directorys of the filesystem. 
	"""
	def __init__(self, directoryentry: DirectoryEntry, parent): # directorylist: DirectoryEntryList):
		super().__init__(directoryentry, parent)

		# get a list of all files in the subdir, note: You'll get a DirectoryEntryList(DEL) in return
		# This DEL enables you to append files and writing them to disk
		self._dl = self._filesystem.open_directory(directoryentry)
		
		# Prepare a list of FatxObjects for easy access later on
		self._elements = None

	def ls(self, deleted=False):
		"""
		list all items in this directory
		"""
		if self._elements is None:
			self._elements = self._create_obj_list()
		return [i for i in self._elements if (not i.attributes.DELETED or deleted)]

	def get(self, name: str):
		"""
		returns the FatxObject for a given filename
		"""
		if self._elements is None:
			self._elements = self._create_obj_list()

		for i in self._elements:
			if i._name == name:
				return i
		raise IndexError()

	def import_file(self, filename: str, data: bytes):
		"""
		imports a given bytearray to filename into this folder
		"""
		try:
			self._filesystem.import_file(self._dl, filename, data)
			self._elements = self._create_obj_list()
		except ValueError as e:
			print(e)

	def create_dir(self, dirname: str):
		try:
			self._filesystem.create_folder(self._dl, dirname)
			self._elements = self._create_obj_list()
		except ValueError as e:
			print(e)

	def _create_obj_list(self):
			elements = []
			if self._dl is not None:
				for i in self._dl.list():
					if i.atr.DIRECTORY:
						elements.append(DirectoryObject(i, self))
					else:
						elements.append(FileObject(i, self))
			else:
				print("Warning this Folder errored while reading: "+self._name)
			return elements


class RootObject(DirectoryObject):
	"""
	 This class should only be instantiated once, as it is the root of the entire filesystem
	 Only the init behaves diffrent compared to a regular DirectoryObject, as the root does
	 not have its own DirectoryEntry
	"""
	def __init__(self, directorylist: DirectoryEntryList):
		self._parent = self
		self._dl = directorylist
		self._elements = None

	def details(self):
		raise TypeError("This is your root!")

	def rename(self, name):
		raise TypeError("You can't rename the filesystem root")

	def __str__(self):
		return "Root of the filesystem"

