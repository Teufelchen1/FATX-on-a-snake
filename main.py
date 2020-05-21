import json, sys
from fatx import fatx2
from fatx.interface2 import DirectoryObject

def listfiles(path, root):
	for item in root.ls():
		print(path+'/'+item._name)
		if isinstance(item, DirectoryObject):
			listfiles(path+'/'+item._name, item)

if __name__ == "__main__":
	fs = fatx2.Filesystem(sys.argv[1])
	fs.status()
	root = fs.root
	# Prints the content of your filesystem starting at root and going one folder deep
	listfiles('', root)
