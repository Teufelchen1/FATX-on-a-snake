from fatx import FATX

if __name__ == "__main__":
	fs = FATX.Filesystem("../xboxfat/part/part0.img")
	print(fs.fat)
	for v in fs.root.values():
		if not v.atr.DELETED:
			print(v.filename)