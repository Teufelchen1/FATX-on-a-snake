import os
import sys
import argparse
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
	parser = argparse.ArgumentParser(description='Imports all files and folder from a given path into a new image')
	parser.add_argument('--sector-size', dest='sector_size', default=512, type=int,
	                    help='sector size used for this image(default: 512)')
	parser.add_argument(dest='size', type=int,
	                    help='size of the new partition')
	parser.add_argument(dest='src', type=str, nargs=1, action='store',
	                    help='src directory for the content of the new image')
	parser.add_argument(dest='image', type=str, nargs=1, action='store',
	                    help='an FATX filesystem image')
	args = parser.parse_args()

	size = args.size
	src = args.src[0]
	file = args.image[0]
	if not os.path.isdir(src):
		sys.exit("Fatal: src-dir is not a valid directory")
	if os.path.exists(file):
		sys.exit("Fatal: target file already exists")
	
	FATX.READ_ONLY = False
	fs = FATX.Filesystem.new(size, file, args.sector_size)
	os.chdir(src)
	walkfs(fs.root)
	


