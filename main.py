import json, sys
from fatx import FATX

def DirToDic(item):
		s = {}
		a = {}
		s['NAME'] = item.filename
		a['READONLY'] = item.atr.READONLY
		a['HIDDEN'] = item.atr.HIDDEN
		a['SYSTEM'] = item.atr.SYSTEM
		a['VOLUMELABEL'] = item.atr.VOLUMELABEL
		a['DIRECTORY'] = item.atr.DIRECTORY
		a['ARCHIVE'] = item.atr.ARCHIVE
		a['DELETED'] = item.atr.DELETED
		s['CLUSTER'] = item.cluster
		s['SIZE'] = item.size
		s['ATR'] = a
		return s

def tree(fs, root):
	out = {}
	for item in root.values():
		if not item.atr.DELETED:
			out[item.filename] = DirToDic(item)
			if item.atr.DIRECTORY:
				out[item.filename]['SUBDIR'] = tree(fs, fs.readDirectory(item))
	return out

def exportFile(fs, file):
	f = open(file.filename, 'wb')
	f.write(fs.readFile(file))
	f.close()

if __name__ == "__main__":
	fs = FATX.Filesystem(sys.argv[1])
	fs.status()
	#print(fs.root)
	print(DirToDic(fs.root['Autobahn.mp4']))
	exportFile(fs, fs.root['Autobahn.mp4'])
	#print(fs.readFile(fs.root['curWeather.xml']))
	#print(json.dumps(tree(fs, fs.root), sort_keys=True, indent=2))