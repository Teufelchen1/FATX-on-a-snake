import os
import sys
import argparse
from fatx import FATX
from fatx.interface import FatxObject, DirectoryObject


def walkfs(obj: FatxObject):
    count = 0
    for item in obj.ls():
        if isinstance(item, DirectoryObject):
            os.mkdir(str(item))
            os.chdir(str(item))
            count += walkfs(item)
            os.chdir("..")
        else:
            f = open(str(item), "wb")
            f.write(item.export())
            f.close()
            count += 1
    return count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extracts all files and folder from a given image"
    )
    parser.add_argument(
        "--sector-size",
        dest="sector_size",
        default=512,
        type=int,
        help="sector size used for this image(default: 512)",
    )
    parser.add_argument(
        "--export-superblock",
        dest="export_superblock",
        type=str,
        help="destination directory for the superblock export",
    )
    parser.add_argument(
        dest="image", type=str, nargs=1, action="store", help="an FATX filesystem image"
    )
    parser.add_argument(
        dest="dest",
        type=str,
        nargs=1,
        action="store",
        help="destination directory for the content of the image",
    )
    args = parser.parse_args()

    dest = args.dest[0]
    file = args.image[0]
    if not os.path.isdir(dest):
        sys.exit("Fatal: destination-dir is not a valid directory")
    if not os.path.isfile(file):
        sys.exit("Fatal: fatx-image is not a valid file")

    fs = FATX.Filesystem(file, args.sector_size)
    fs.status()

    if args.export_superblock:
        try:
            head, tail = os.path.split(args.export_superblock)
            if tail == "":
                f = open(os.path.join(head, "superblock.bin"), "wb")
            else:
                f = open(args.save_superblock, "wb")
            f.write(fs.sb.pack())
            print("Exported the superblock into {0}".format(f.name))
            f.close()
        except Exception as e:
            sys.exit("Fatal: could not export the superblock: " + str(e))

    root = fs.root
    os.chdir(dest)
    print("Unpacked {0} files.".format(walkfs(root)))
