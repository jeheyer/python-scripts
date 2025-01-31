#!/usr/bin/env python3

from sys import argv, platform
from os.path import realpath, dirname, join, exists, getmtime
from os import scandir, mkdir
from shutil import copyfile, copystat

PWD = realpath(dirname(__file__))
DST_DIR = "../private/ssl"

def main(mode = None):

    if "linux" in platform:
        src_dir = "/etc/letsencrypt/live"
    if "freebsd" in platform:
        src_dir = "/usr/local/etc/letsencrypt/live"
    sites = [ f.name for f in scandir(src_dir) if f.is_dir() ]
    dst_dir = join(PWD, DST_DIR)
    #print("Destination Directory is:", dst_dir)

    for site in sites:
        #print("Site:", site)
        files = { 'key': 'privkey.pem', 'crt': 'cert.pem', 'cer': 'fullchain.pem' }
        for file in files:
            src_file = join(src_dir, site, files[file])
            #print("Source file:", src_file)
            if not exists(dst_dir):
                print("Creating this directory", dst_dir)
                mkdir(dst_dir)
            _ = site.replace(".", "_")
            _ = f"{_}.{file}"
            dst_file = join(dst_dir, _)
            #print("Destination file", dst_file)
            if not exists(dst_file) or getmtime(src_file) > getmtime(dst_file):
                #print("COPYING", src_file, dst_file)
                if mode == "dry":
                    print(src_file, "->", dst_file)
                else:
                    copyfile(src_file, dst_file)
                    copystat(src_file, dst_file)

if __name__ == "__main__":
    if len(argv) > 1 and argv[1] == "-d":
        main(mode = "dry")
    else:
        main()
    quit()

