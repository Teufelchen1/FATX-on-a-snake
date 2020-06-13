import os
import sys
import argparse
from fatx import FATX


def check_for_superblock(path):
    # check if a superblock is given, if so, prepare to re-import it
    path = os.path.join(path, ".FATX-on-a-snake/superblock.bin")
    if os.path.exists(path):
        with open(path, 'rb') as f:
            sb = f.read()
            return sb
    else:
        return None


def walkfs(fs):
    with os.scandir(".") as it:
        for entry in it:
            if entry.is_file():
                with open(entry.name, "rb") as f:
                    fs.import_file(entry.name, f.read())
            else:
                if entry.name != ".FATX-on-a-snake":
                    fs.create_dir(entry.name)
                    os.chdir(entry.name)
                    walkfs(fs.get(entry.name))
                    os.chdir("..")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Imports all files and folder from a given path into a new image"
    )
    parser.add_argument(
        "--sector-size",
        dest="sector_size",
        default=512,
        type=int,
        help="sector size used for this image(default: 512)",
    )
    parser.add_argument(dest="size", type=int, help="size of the new partition")
    parser.add_argument(
        dest="src",
        type=str,
        nargs=1,
        action="store",
        help="src directory for the content of the new image",
    )
    parser.add_argument(
        dest="image",
        type=str,
        nargs=1,
        action="store",
        help="an FATX filesystem image"
    )
    args = parser.parse_args()

    size = args.size
    src = args.src[0]
    file = args.image[0]
    sb = None
    FATX.READ_ONLY = False

    if not os.path.isdir(src):
        sys.exit("Fatal: src-dir is not a valid directory")
    if os.path.exists(file):
        sys.exit("Fatal: target file already exists")

    sb = check_for_superblock(src)
    fs = FATX.Filesystem.new(size, file, args.sector_size, sb)
    os.chdir(src)
    walkfs(fs.root)
