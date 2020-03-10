import json, sys
from fatx import FATX
from fatx.interface import DirectoryObject

def DirToDic(item):
		s = {}
		s['NAME'] = item._name
		s['ATR'] = item.details()
		return s

def tree(root, max_depth=10):
	out = {}
	for item in root.ls():
		out[item._name] = DirToDic(item)
		if isinstance(item, DirectoryObject):
			if max_depth > 0:
				out[item._name]['SUBDIR'] = tree(item, max_depth-1)
	return out

if __name__ == "__main__":
	fs = FATX.Filesystem(sys.argv[1])
	fs.status()
	root = fs.root
	# Prints the content of your filesystem starting at root and going one folder deep
	print(json.dumps(tree(root, 1), sort_keys=True, indent=2))
