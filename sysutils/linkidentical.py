"""
Replace identical files with links to one real file.

Search recursively through the top level directory to find identical files.
For each set of identical files, keep only the file with the longest name and
replace all other copies with symlinks to the longest-named file.  The use of
hardlinks or symlinkss can be specified.  Symlinks will be used when hardlinks
fail.

This is useful when there are multiple copies of files in different in
different locations of a directory tree, and all copies of each file should
remain identical.  Converting all the files into links to the same file ensures
that the files remain the same as well as saves the space used by multiple
copies.

The linkidentical utility is also useful when different names for a shared lib
should be links, but were perhaps turned into files.  Each copy has a different
name.  For example:

    libexample.so.1.0
    libexample.so.1
    libexample.so

will be changed so that there is only one instance of the file:

    libexample.so.1.0
    libexample.so.1 --> libexample.so.1.0
    libexample.so --> libexample.so.1.0

"""
from __future__ import print_function

import sys
import os
import hashlib
import shutil


def hash_file(filename):
    """Calculate SHA1 hash of file."""
    BLOCKSIZE = 65536
    hasher = hashlib.sha1()
    with open(filename, 'rb') as afile:
        buf = afile.read(BLOCKSIZE)
        while len(buf) > 0:
            hasher.update(buf)
            buf = afile.read(BLOCKSIZE)

    return hasher.hexdigest()


def link_same_files(root_dir, name_prefix=None, always_symlink=False,
                    absolute_symlink=False, quiet=False, no_stats=False):
    """Keep longest-named file and replace copies with links.

    If identical files are found, then the file with the longest path name is
    kept and the other files are replaced by links to that name.

    If a hardlink cannot be created, then a symlink is created.  If
    always_symlink is True, then only symlinks are created.

    Setting absolute_symlink creates absolute symlinks instead of relative
    symlinks.  Generally, relative (the default) symlinks are preferred as this
    permits links to maintain their validity regardless of the mount point used
    for the filesystem.

    """
    root_dir = os.path.normpath(os.path.expanduser(root_dir))

    # Walk directory and create map, {size: filepath, ..}.  This allows files,
    # that do not match another file in size, to be eliminated without having
    # to calculate a hash of the file.
    size_file_map = {}
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for fname in filenames:
            if name_prefix and not fname.startswith(name_prefix):
                continue
            fpath = os.path.join(dirpath, fname)
            if os.path.isfile(fpath) and not os.path.islink(fpath):
                fsize = os.path.getsize(fpath)
                if fsize > 0:
                    size_file_map.setdefault(fsize, []).append(fpath)

    # Prune unique files, leaving files having another file of the same size.
    # From remaining files, create a map {hash: filepath, ..}
    hash_file_map = {}
    for filepaths in (v for v in size_file_map.itervalues() if len(v) > 1):
        for fpath in filepaths:
            hash_file_map.setdefault(hash_file(fpath), []).append(fpath)

    # Prune unique files
    hash_file_map = {k: v for k, v in hash_file_map.iteritems() if len(v) > 1}

    link_count = 0
    size_saved = 0

    def fkey(name):
        # Sort by shortest-basename, shortest-path
        return len(os.path.basename(name)), len(name)

    # Link files with shorter names to file with longest name.
    for k, files in hash_file_map.iteritems():
        # Sort files and get file with longest name, or longest path if names
        # are the same.  This only matters for symlinks, but since a failed
        # hardlink can result in a symlink, do it anyway.
        files.sort(key=fkey)
        base_file = files.pop()
        base_size = os.path.getsize(base_file)

        # Iterate remaining files and replace with links.
        for f in files:
            if os.path.samefile(base_file, f):
                # If the files are already the same (hardlinked), then do not
                # try to link.
                continue

            try:
                os.unlink(f)
            except OSError:
                print('cannot unlink file:', f, file=sys.stderr)
                continue

            if always_symlink:
                create_symlink=True
            else:
                create_symlink=False
                try:
                    os.link(base_file, f)
                    if not quiet:
                        print('hardlink:', os.path.relpath(f, root_dir),
                              '<-->', os.path.relpath(base_file, root_dir))
                except OSError:
                    create_symlink=True
                    print('could not create hardlink, symlink instead',
                          file=sys.stderr)

            if create_symlink:
                if absolute_symlink:
                    source = base_file
                else:
                    rp = os.path.relpath(os.path.dirname(f),
                                         os.path.dirname(base_file))
                    if rp == '.':
                        source = os.path.basename(base_file)
                    else:
                        source = os.path.join(rp, os.path.basename(base_file))

                try:
                    os.symlink(source, f)
                    if not quiet:
                        print('symlink:', os.path.relpath(f, root_dir), '--->',
                              os.path.relpath(base_file, root_dir))
                except OSError as e:
                    print('faile create symlink for %s: %s'
                          % (os.path.relpath(base_file, root_dir), e),
                          file=sys.stderr)
                    # Restore file.
                    shutil.copy2(base_file, f)
                    continue # skip stats update

            size_saved += base_size
            link_count += 1

    if not no_stats:
        print('\nReplaced', link_count, 'files with links')
        print('Reduced storage by', size_str(size_saved))

    return link_count, size_saved


def size_str(byte_size):
    """Truncate number to highest significant power of 2 and add suffix."""
    KB = 1024
    MB = KB*1024
    GB = MB*1024
    if byte_size > GB:
        return str(round(float(byte_size) / GB, 1)) + 'G'
    if byte_size > MB:
        return str(round(float(byte_size) / MB, 1)) + 'M'
    if byte_size > KB:
        return str(round(float(byte_size) / KB, 1)) + 'K'
    return str(byte_size)


def main():
    import argparse
    ap = argparse.ArgumentParser(
        description='Convert identical files to links to one real file')
    ap.add_argument('root',
                    help='Top-level directory to search for files to link')
    ap.add_argument('--symlink', '-s', action='store_true',
                    help='Use symlinks only to link files')
    ap.add_argument('--absolute', '-a', action='store_true',
                    help='When creating symlink, use absolute instead of '
                    'relative link.')
    ap.add_argument('--prefix', '-p',
                    help='Match only files starting with given prefix.')
    ap.add_argument('--quiet', '-q', action='store_true',
                    help='Do not print link creation output')
    ap.add_argument('--nostats', '-ns', action='store_true',
                    help='Do not print stats')
    args = ap.parse_args()

    link_same_files(args.root, args.prefix, args.symlink, args.absolute,
                    args.quiet, args.nostats)
    return 0


if __name__ == '__main__':
    sys.exit(main())
