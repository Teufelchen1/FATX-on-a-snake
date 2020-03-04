from .blocks import DirectoryEntry, DirectoryEntryList

class FatxObject():
	filesystem = None

	@classmethod
	def registerFilesystem(cls, fs):
		cls.filesystem = fs

	# Note: static typing with selfreference(for parent) is possible but ugly :(
	def __init__(self, directoryentry: DirectoryEntry, parent): 
		self._de = directoryentry
		self.attributes = self._de.atr
		self._parent = parent

	def ls(self, deleted=False):
		"""
		if self is a directory, this should list all items
		in this directory
		"""
		raise NotImplementedError("Override this in the subclass")

	def details(self):
		"""
		Prints its own attributes
		"""
		raise NotImplementedError("Override this in the subclass")

	def parent(self):
		"""
		parent() should return the FatxObject that can point to
		this object(parent dir)
		"""
		return self._parent

	def get(self, path):
		"""
		returns the FatxObject for a given path(or file)
		"""
		raise NotImplementedError("Override this in the subclass")

	def rename(self, name):
		"""
		renames this object and safes the change to disk
		"""
		raise NotImplementedError("Override this in the subclass")

	def exportFile(self):
		"""
		returns all bytes belonging to this file
		"""
		raise NotImplementedError("Override this in the subclass")

	def importFile(self, data, filename):
		"""
		imports a given data-bytearray to filename into this folder
		"""
		raise NotImplementedError("Override this in the subclass")

	def delete(self):
		"""
		Marks this object as deleted and safes change to disk
		"""
		raise NotImplementedError("Override this in the subclass")

	def __str__(self):
		return self._de.filename

	def __repr__(self):
		return str(self.__class__)+ ': ' + str(self)


class FileObject(FatxObject):
	pass


class DirectoryObject(FatxObject):
	def __init__(self, directoryentry: DirectoryEntry, parent: FatxObject): # directorylist: DirectoryEntryList):
		super().__init__(directoryentry, parent)

		# get a list of all files in the subdir, note: You'll get a DirectoryEntryList(DEL) in return
		# This DEL enables you to append files and writing them to disk
		self._dl = self.filesystem.openDirectory(directoryentry)
		
		# Prepare a list of FatxObjects for easy access later on
		self._elements = []
		self.createFatxObjectList()

	def createFatxObjectList(self):
		for i in self._dl.list():
			if i.atr.DIRECTORY:
				self._elements.append(DirectoryObject(i, self))
			else:
				self._elements.append(FileObject(i, self))

	def ls(self, deleted=False):
		return [ i for i in self._elements if (not i.attributes.DELETED or deleted)]


class RootObject(DirectoryObject):
	def __init__(self, directorylist: DirectoryEntryList):
		self._parent = self
		self._dl = directorylist
		self._elements = []
		self.createFatxObjectList()

	def __str__(self):
		return "Root of the filesystem"

