import json, sys, os
from fatx import FATX
from fatx.interface import FatxObject, DirectoryObject

def walkfs(fs):
	with os.scandir('.') as it:
		for entry in it:
			if entry.is_file():
				with open(entry.name, 'rb') as f:
					fs.import_file(entry.name, f.read())
			else:
				fs.create_dir(entry.name)
				os.chdir(entry.name)
				walkfs(fs.get(entry.name))
				os.chdir('..')
			

if __name__ == "__main__":
	if len(sys.argv) != 4:
		sys.exit("Usage: size src-dir destination.img")
	size = int(sys.argv[1])
	src = sys.argv[2]
	file = sys.argv[3]
	if not os.path.isdir(src):
		sys.exit("Fatal: src-dir is not a valid directory")
	if os.path.exists(file):
		sys.exit("Fatal: target file already exists")
	
	FATX.READ_ONLY = False
	fs = FATX.Filesystem.new(size, file)
	os.chdir(src)
	walkfs(fs.root)
	


