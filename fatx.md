
# Understanding the FATX filesystem

This a short summary of the work from various people.
The goal is to educate myself about FATX by documenting it.

## Superblock
When you open up a filesystem containing FATX, the first thing you will encounter is the Superblock. It contains basic information about its partition. It is always 4096bytes/4KB in size.

Size and Offset in Bytes
| Offset | Size |Typical Value  |Description           |
|--------|------|---------------|----------------------|
| 0x0000 |4     | "FATX"  		| ASCII String, for identification? |
| 0x0004 |4     | 				| Volume ID |
| 0x0008 |4     | 32			| Cluster size in number of sectors (512bytes) |
| 0x000C |2     | 1 			| Number of FAT copies |
| 0x000E |4     | 0 			| Unknown, maybe padding |
| 0x0012 |4078  |  				| Unused/padding |

## File Allocation Table
On a typical FATX partition, there is only one FAT that starts at offset 0x1000(4KB). They work the same way as in a typical FAT16/32, take a look at [wikipedia](https://en.wikipedia.org/wiki/Design_of_the_FAT_file_system#File_Allocation_Table).\
On the Xbox, there are five partitions, those who are smaller than 1GB (Drive X,Y,Z and C) are FATX16 otherwise (Drive E) they will use FATX32. The exact transition happends when you need more than 65325 clusters(32 * 512 bytes * 65325 = 1023 MB). The size of the FAT(sometimes called cluster map) depends on the size of the partition. Your FAT needs one entry (2 bytes with FATX16, 4 bytes with FATX32) per cluster. Therefore you can calculate the size of the FAT: ((partition size / cluster size) * entry size). Additionally, the size is rounded to the next 4096 byte boundary.\
Imagine having a partion that is 21 MB (= 22020096 bytes) in size. Since it is small, we will use FATX16, resulting in a cluster entry size of 2 bytes. The size of a cluster is defined in the superblock, we will use the typical value: \
32 * 512 bytes = 16 384 bytes. \
We can start with calculating how many clusters we need to address every byte on the partition: 22020096 bytes/16384 bytes = 1344
Because FATX16 requires two bytes per cluster entry:\
1344 * 2 bytes = 2688 bytes.\
Now, we can conclude that the 21 MB partition has a FAT with 1344 entrys and a size of 2688 bytes. Round that up to 4096 bytes and we are good to go.\
Each entry in the FAT has its own corresponding cluster. Since the FAT is ordered, the calculation of the offset of a cluster is easy:\
 (Number of your cluster - 1) * cluster size + Superblock + FAT\
In our example, the offset of the first cluster(Number 1) is:\
(1-1) * 16 384 bytes + 4096 bytes + 4096 bytes = 8192 bytes.

Let's take a look at the values a cluster entry can have(taken from [wikipedia](https://en.wikipedia.org/wiki/Design_of_the_FAT_file_system#File_Allocation_Table)).
| Example Value | Description          |
|---------------|----------------------|
| 	0x0000		| This cluster is free for use |
| 	0x0001		| Usually used for recovery after crashes (unknown if used by the xbox) |
|0x0002 - 0xFFEF| This cluster is part of a chain and points to the next cluster |
|0xFFF0 - 0xFFF5| Reserved (unknown if used by the xbox) |
| 	0xfff7		| Bad sectors in this cluster - this cluster should not be used |
|0xfff8 - 0xffff| Marks the end of a cluster chain |

As you can see, we only have three values (ranges) that are important: \
If a cluster entry is 0x0000 we can use it to store data. Any value between 0x0002 and 0xFFEF is part of a cluster chain (i.e. a file that spans multiple clusters). An entry that is greater or equal to 0xfff7 is either bad and/or ends a chain. 

## Directories and files
So, you have opened the first cluster, containing the root of the filesystem, how do you read it? You'll start with looking for so called directory entries. One directory entry is 64 bytes in size hence you can have up to 256 directories in a single cluster(16 KB/64 = 256). 
Size and Offset in Bytes
| Offset | Size |Description           |
|--------|------|----------------------|
| 0x0000 |1     | Length of file/directory name, not more than 42 |
| 0x0001 |1     | Attribute flags |
| 0x0002 |42    | Filename, padding with 0xff |
| 0x002C |4     | Start cluster of corresponding cluster-chain |
| 0x0030 |4     | Size of file in bytes |
| 0x0034 |2     | Time? |
| 0x0036 |2     | Date? |
| 0x0038 |2     | Time? |
| 0x003A |2     | Date? |
| 0x003C |2     | Time? |
| 0x003E |2     | Date? |

Deleted directories and files have set their name-length attribute set to 0xE5. The last entry is either complete 0x00 or 0xFF.

The flags are the same as on regular FAT16/32:
| Bit		| Flag | Description |
|-----------|------|-------------|
| 0000 0001 | 0x01 | File is read only |
| 0000 0010 | 0x02 | File is hidden |
| 0000 0100 | 0x04 | File is a system file |
| 0000 1000 | 0x08 | Volume label (unknown if used by the xbox) |
| 0001 0000 | 0x10 | File is a subdirectory |
| 0010 0000 | 0x20 | File is an archive |
| 0100 0000 | 0x40 | File is a device (unknown if used by the xbox) |
| 1000 0000 | 0x80 | Reserved |


## Sources
- [Xbox-linux wiki](https://web.archive.org/web/20100617022009/http://www.xbox-linux.org/wiki/Differences_between_Xbox_FATX_and_MS-DOS_FAT)
- [lucien](https://web.archive.org/web/20020617181617/http://www.tardis.ed.ac.uk:80/~lucien/computing/projects/xbox/XBOX-disk-layout.htm)
- [FAT on wikipedia](https://en.wikipedia.org/wiki/Design_of_the_FAT_file_system#File_Allocation_Table)

## Thanks for your work
- Michael Steil
- Andrew de Quincey
- Lucien Murray-Pitts