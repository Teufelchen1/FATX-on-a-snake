import json, sys
from fatx import FATX

def DirToDic(item, atr=False):
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
		s['ORIGIN'] = item.origin
		if atr:
			s['ATR'] = a
		return s

def tree(fs, root, max_depth=10):
	out = {}
	for item in root.values():
		if not item.atr.DELETED:
			out[item.filename] = DirToDic(item)
			if item.atr.DIRECTORY:
				if max_depth > 0:
					out[item.filename]['SUBDIR'] = tree(fs, fs.readDirectory(item), max_depth-1)
	return out

def exportFile(fs, file):
	f = open(file.filename, 'wb')
	f.write(fs.readFile(file))
	f.close()

if __name__ == "__main__":
	fs = FATX.Filesystem(sys.argv[1])
	fs.status()
	#print(fs.root)
	obj = fs.root['Autobahn.mp4']
	#fs.writeDirectoryEntry(obj)
	print(json.dumps(DirToDic(obj, True), sort_keys=True, indent=2))
	fs.delete(obj)
	fs.rename(obj, "Strasse.mp4")
	print(json.dumps(DirToDic(obj, True), sort_keys=True, indent=2))
	#exportFile(fs, fs.root['Autobahn.mp4'])
	#print(fs.readFile(fs.root['curWeather.xml']))
	#print(json.dumps(tree(fs, fs.root, 0), sort_keys=True, indent=2))

