import json, sys, os
from fatx import FATX
from fatx.interface import FatxObject, DirectoryObject

def iterate(obj: FatxObject):
	count = 0
	for item in obj.ls():
		if isinstance(item, DirectoryObject):
			os.mkdir(str(item))
			os.chdir(str(item))
			count += iterate(item)
			os.chdir('..')
		else:
			f = open(str(item),'wb')
			f.write(item.exportFile())
			f.close()
			count += 1
	return count
			

if __name__ == "__main__":
	if len(sys.argv) != 3:
		sys.exit("Usage: <fatx-image> <destination-dir>")
	dest = sys.argv[2]
	file = sys.argv[1]
	if not os.path.isdir(dest):
		sys.exit("Fatal: destination-dir is not a valid directory")
	if not os.path.isfile(file):
		sys.exit("Fatal: fatx-image is not a valid file")

	fs = FATX.Filesystem(file)
	fs.status()
	root = fs.root
	os.chdir(dest)
	print("Unpacked {0} files.".format(iterate(root)))

