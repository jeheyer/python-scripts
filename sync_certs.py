#!/usr/bin/env python3

import sys, os
from os import path
import shutil
from shutil import copyfile

DST_DIR = "../ssl/"

def main(mode = None):

    if "linux" in sys.platform:
        src_dir = "/etc/letsencrypt/live"
    if "freebsd" in sys.platform:
        src_dir = "/usr/local/etc/letsencrypt/live"
    sites = [ f.name for f in os.scandir(src_dir) if f.is_dir() ]
    dst_dir = DST_DIR

    for site in sites:
        files = { 'key': 'privkey.pem', 'crt': 'cert.pem', 'cer': 'fullchain.pem' }
        for file in files:
            src_file = src_dir + "/" + site + "/" + files[file]
            dst_file = dst_dir + "/" + site.replace(".","_") + "." + file
            if not path.exists(dst_file) or os.path.getmtime(src_file) > os.path.getmtime(dst_file):
                if mode == "dry":
                    print(src_file, "->", dst_file)
                else:
                    copyfile(src_file, dst_file)
                    shutil.copystat(src_file, dst_file)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "-d":
        main(mode = "dry")
    else:
        main()
    quit()

