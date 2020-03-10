# FATX-on-a-snake
Small python utility to play with FATX partitions

This is an educational python utility that lets you walk around in a FATX partion and exporting/importing files from/to it.
The goal is to Understand, understand the concept of ~love~FATX, uh!

## REMEBER TO MAKE A BACKUP OF YOU PARTITION BEFORE YOU READ ANY FURTHER

## Status
At the moment, you can safely read files and meta data with this utility. Its missing only some documentation and I would love to add more options/methodes to retrieve data in more usefull ways in the future. 
Writing is possible but limited. You should *ALWAYS* make a backup of your data before even thinking about using my tool in write mode.
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


## Quik Usage:
Run
```sh
python3 main.py /path/to/partition.img
```
where partition.img is a FATX partition. Not a Xbox harddrive image. Just a plain partition.
Note: Huge(>8GB) partitions may take a while...I didn't bother with optimisations.

## Example API usage:
Open your image file and print some information
```python
from fatx import FATX
fs = FATX.Filesystem("/home/mhamilton/fatx.img")
fs.status()
```

Access the root('/') of your filesystem and list the files in it. We get back a list of FatxObjects, so we have to put some extra afford into printing it nicely
```python
root = fs.root
print([str(i) for i in root.ls()])
"['Audio','fonts', ...]"
```

Retrieve a file you like to take a close look at with `get()`
```python
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

That `Global A Button Select.wav` sounds interesting, lets export it. The `exportFile()` methode returns the file as an array of bytes. So we have to write it to disk our self.
```python
file = audio.get('MainAudio/Global A Button Select.wav')
f = open(file._name, 'wb')
f.write(file.exportFile())
f.close()
```

Importing a file is as easy as this. Note that this writes to disk. Since I'm not yet confident enough it works flawless, the software shipps read only. Go into `fatx/FATX.py` and change the `READ_ONLY = True` to `False` at the top of the file. But be aware, you may loose (all) data if you or FATX-on-a-snake do something stupid.
You can only import files into directorys
```python
audio.importFile("newAudio.wav")
```

Renaming is done with the `rename()` methode(obviously)
```python
newFile = audio.get('newAudio.wav')
newFile.rename('oldAudio.wav')
```

The `parent()` methode alway returns the upper directory. If you call it on your root object, it returns itself.
```python
audio.ls() == newFile.parent().ls() 
```
