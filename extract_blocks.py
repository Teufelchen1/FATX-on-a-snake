import os
import sys
from fatx import FATX
from fatx.blocks import SuperBlock

if __name__ == "__main__":
    cwd = os.getcwd()
    size = os.stat(sys.argv[1]).st_size
    fs = open(sys.argv[1], "rb")
    os.mkdir(os.path.split(sys.argv[1])[1] + ".extract")
    os.chdir(os.path.split(sys.argv[1])[1] + ".extract")
    with open("superblock.bin", "w+b") as f:
        f.write(fs.read(SuperBlock.SUPERBLOCK_SIZE))
    with open("fat.bin", "w+b") as f:
        fat_size = FATX.Filesystem._calc_fat_size(size, 512*32)
        f.write(fs.read(fat_size))
    for i in range(0, 10):
        with open("chunk({0}).bin".format(i), "w+b") as f:
            f.write(fs.read(32 * 512))
