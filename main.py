import json
import argparse
from fatx import FATX
from fatx.interface import DirectoryObject

def listfiles(root, path=''):
	for item in root.ls(deleted=False):
		print(path+'/'+item._name)
		if isinstance(item, DirectoryObject):
			listfiles(item, path+'/'+item._name)

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='Prints all file- and folderpaths inside a given image')
	parser.add_argument('--sector-size', dest='sector_size', default=512, type=int,
	                    help='sector size used for this image(default: 512)')
	parser.add_argument(dest='image', type=str, nargs=1, action='store',
	                    help='an FATX filesystem image')
	args = parser.parse_args()

	fs = FATX.Filesystem(args.image[0], args.sector_size)
	fs.status()
	root = fs.root
	listfiles(fs.root)
