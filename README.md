# FATX-on-a-snake
Small python utility to play with FATX partitions

This is an educational python utility that lets you walk around in a FATX partition and exporting/~~importing~~ files from/to it.
The goal is to Understand, understand the concept of ~love~FATX, uh!

## REMEMBER TO MAKE A BACKUP OF YOU PARTITION

## Status
At the moment, you can safely read files and meta data with this utility. It is missing only some documentation and I would love to add more options/methods to retrieve data in more useful ways in the future. 
~~Writing is possible but limited. You should *ALWAYS* make a backup of your data before even thinking about using my tool in write mode.~~
Stuff that I still work on:
- Documentation
- Some code clean-up
- Deleting files
- Filesystem checks
- General function enhancements
	- filtering
	- maybe in-place editing/replace of files
	- Cleaner exception handling in some areas
- packing and unpacking of entire partitions
- creation of fatx partitions


## Quick Usage:
To unpack an image run:
```sh
python3 unpack.py fatx.img /tmp
```
Which should result in something like this:
```
FATX ~ FAT: 313344 entrys of 4 bytes each
Unpacked 226 files.
```

## Usage:

Run
```sh
python3 main.py /path/to/partition.img
```
where partition.img is a FATX partition. Not a Xbox harddrive image. Just a plain partition.
Note: Huge (>4 GB) partitions may take a while... I didn't bother with optimisations.

## Example API usage:
Open your image file and print some information
```python
from fatx import FATX
fs = FATX.Filesystem("/home/mhamilton/fatx.img")
fs.status()
```

Access the root ('/') of your filesystem and list the files in it. We get back a list of FatxObjects, so we have to put some extra effort into printing it nicely
```python
root = fs.root
print([str(i) for i in root.ls()])
"['Audio','fonts', ...]"
```

Retrieve a file you like to take a close look at with `get()` or using its index
```python
audio = root.ls()[0]
audio = root.get('Audio')
print(audio.details())
```

Actually, Audio is a directory. Lets take a look at the files inside it
```python
print([str(i) for i in audio.ls()])
"['AmbientAudio', 'MainAudio', ...]"
print([str(i) for i in audio.get('MainAudio').ls()])
"['Global A Button Select.wav', 'Global B Button Back.wav', ...]"
```

That `Global A Button Select.wav` sounds interesting, lets export it. The `exportFile()` method returns the file as an array of bytes. So we have to write it to disk ourselves.
```python
file = audio.get('MainAudio/Global A Button Select.wav')
f = open(file._name, 'wb')
f.write(file.export())
f.close()
```

~~Importing a file is as easy as this. Note that this writes to disk. Since I'm not yet confident enough it works flawless, the software ships read only. Go into `fatx/FATX.py` and change the `READ_ONLY = True` to `False` at the top of the file. But be aware, you may lose (all) data if you or FATX-on-a-snake do something stupid.
You can only import files into directories~~
```python
audio.importFile("newAudio.wav")
```

Renaming is done with the `rename()` method (obviously)
```python
newFile = audio.get('newAudio.wav')
newFile.rename('oldAudio.wav')
```

The `parent()` method always returns the upper directory. If you call it on your root object, it returns itself.
```python
audio.ls() == newFile.parent().ls() 
```
