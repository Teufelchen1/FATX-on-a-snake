import json, sys
from fatx import fatx2
from fatx.interface2 import DirectoryObject

def listfiles(root, path=''):
	for item in root.ls():
		print(path+'/'+item._name)
		if isinstance(item, DirectoryObject):
			listfiles(item, path+'/'+item._name)

if __name__ == "__main__":
	fs = fatx2.Filesystem(sys.argv[1])
	fs.status()
	root = fs.root
	listfiles(root)
