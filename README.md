# FATX-on-a-snake
Small python utility to play with FATX partitions

This is an educational python utility that lets you walk around in a FATX partition and exporting/importing files from/to it.
The goal is to Understand, understand the concept of ~love~FATX, uh!

## REMEMBER TO MAKE A BACKUP OF YOUR PARTITION

## Status
At the moment, you can safely read files and meta data with this utility. It is missing only some documentation and I would love to add more options/methods to retrieve data in more useful ways in the future. 
Writing is possible but limited. You should *ALWAYS* make a backup of your data before even thinking about using my tool in write mode.

Stuff that works _great_:
- List files and folders
- Exporting of files / unpacking of partitions
- Creation of folders
- Import of files

Stuff that somewhat works:
- Creation of new partitions
- Packing of partitions

Stuff that I still work on:
- Documentation
- Some code clean-up
- Deleting files / freeing space
- Filesystem checks
- Time/Date meta information
- XMU support(they have a diffrent sector size)
- Support for working with blockdevices directly

Stuff thats still on my wishlist:
- in-place editing/replace of files
- exporting virtual file interfaces
- rewrite everything in Rust as a fusedriver 😇


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

Run `main.py` to verify everything checks out
```sh
python3 main.py /path/to/partition.img
```
where partition.img is a FATX partition. Not a Xbox harddrive image. Just a plain partition.
Note: Huge (>4 GB) partitions may take a while... I didn't bother with optimisations yet.

Run `unpack.py` to export all files & folders of a partition
```sh
mkdir tmp/
python3 unpack.py /path/to/partition.img tmp/
cd tmp && ls
```

Run `pack.py` to create new partitions based on a local folder. You must provide the target partition size in bytes, a src folder(can be empty, will result in an empty but valid image) and a name for the new partition. The volume ID is randomly generated.
```sh
python3 pack.py 524288000 src/ dest.img
```

Run `extract_blocks.py` to easily access the most important parts of a FATX partition. i.e. look at the exported binarys with a hexeditor. 
```sh
python3 extract_blocks.py /path/to/partition.img
cd partition.img.extract && ls
```

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
file = audio.get('MainAudio').get('Global A Button Select.wav')
f = open(file._name, 'wb')
f.write(file.export())
f.close()
```

Importing a file is as easy as this. Note that this writes to disk. Since I'm not yet confident enough it works flawless, the software ships read only. Go into `fatx/FATX.py` and change the `READ_ONLY = True` to `False` at the top of the file. But be aware, you may lose (all) data if you or FATX-on-a-snake do something stupid.
You can only import files into directories
```python
f = open("newAudio.wav", "rb")
audio.import_file("newAudio.wav", f.read())
f.close()
```

Renaming is done with the `rename()` method (obviously).
```python
newFile = audio.get('newAudio.wav')
newFile.rename('oldAudio.wav')
```

Inorder to delete a file, use the `delete()` method.
At the moment, only 'soft' deletion is supported, where the data remains on the disk but the file is marked as deleted. You can see such files with `ls(deleted=True)`.
```python
audio.get('oldAudio.wav').delete()
audio.ls(deleted=True)
```

The `parent()` method always returns the upper directory. If you call it on your root object, it returns itself.
```python
audio.ls() == newFile.parent().ls()
```
