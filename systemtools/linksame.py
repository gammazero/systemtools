"""
Replace identical files with links to one real file.

Search recursively through the top level directory to find identical files.
For each set of identical files, keep only the file with the longest name and
replace all other copies with symlinks to the longest-named file.  The use of
hardlinks or symlinkss can be specified.  Symlinks are created when hardlinks
fail.

This is useful when there are multiple copies of files in different in
different locations of a directory tree, and all copies of each file should
remain identical.  Converting all the files into links to the same file ensures
that the files remain the same as well as saves the space used by multiple
copies.

The linksame utility is also useful when different names for a shared lib
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

import fnmatch
import hashlib
import os
import shutil
import sys
import threading
try:
    import queue
except ImportError:
    import Queue as queue


def link_same_files(root_dir, pattern=None, link=False, symlink=False,
                    absolute=False, quiet=False, silent=False):
    """Replace copies of files with links to a single file.

    If identical files are found, then the file with the longest path name is
    kept and the other files are replaced by links to that name.

    If a hardlink cannot be created, then a symlink is created.  If
    symlink it True, then only symlinks are created.

    Setting absolute=True creates absolute symlinks instead of relative
    symlinks.  Generally, relative (the default) symlinks are preferred as this
    permits links to maintain their validity regardless of the mount point used
    for the filesystem.

    """
    root_dir = os.path.normpath(os.path.expanduser(root_dir))
    if not os.path.isdir(root_dir):
        return '%s is not a directory' % (root_dir,)

    if not quiet:
        print('Linking identical files in', root_dir)

    # Walk directory and create map, {size: filepath, ..}.  This allows files,
    # that do not match another file in size, to be eliminated without having
    # to calculate a hash of the file.
    size_file_map = {}
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for fname in filenames:
            fpath = os.path.join(dirpath, fname)
            if not os.path.isfile(fpath) or os.path.islink(fpath):
                continue
            fsize = os.path.getsize(fpath)
            if fsize == 0:
                continue
            if pattern and not fnmatch.fnmatch(fname, pattern):
                continue
            size_file_map.setdefault(fsize, []).append(fpath)

    statsq = queue.Queue()

    def check_and_link(filepaths):
        links = 0
        saved = 0
        sameLists = _check_same(filepaths)
        for files in sameLists:
            l, s = _link_files(files, root_dir, link, symlink, absolute, quiet)
            links += l
            saved += s

        statsq.put((links, saved))

    wait_count = 0
    for same_size_files in size_file_map.itervalues():
        if len(same_size_files) < 2:
            # Skip unique files
            continue
        wait_count += 1
        t = threading.Thread(target=check_and_link, args=(same_size_files,))
        t.start()

    link_count = 0
    size_saved = 0
    while wait_count:
        l, s = statsq.get()
        wait_count -= 1
        link_count += l
        size_saved += s

    if not silent:
        print()
        if not link:
            print('If writing links (-w), would have...')
        print('Replaced', link_count, 'files with links')
        print('Reduced storage by', size_str(size_saved))

    return None


def link_same_update(update_file, root_dir, pattern=None, link=False,
                     symlink=False, absolute=False, quiet=False, silent=False):
    """Replace copies of a specified file with links to a single file."""
    if not update_file:
        return "Update file not specified"
    root_dir = os.path.normpath(os.path.expanduser(root_dir))
    if not os.path.isdir(root_dir):
        return '%s is not a directory' % (root_dir,)
    if not os.path.isfile(update_file):
        return '%s is not a file' % (update_file,)
    update_size = os.path.getsize(update_file)
    if update_size == 0:
        return '%s is empty' % (update_file,)
    update_hash = _hash_file(update_file)

    if not quiet:
        print('Linking', update_file, 'to identical files in', root_dir)

    # Walk directory and find files that are identical to the update file.
    same = [update_file]
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for fname in filenames:
            fpath = os.path.join(dirpath, fname)
            if not os.path.isfile(fpath) or os.path.islink(fpath):
                continue
            if os.path.getsize(fpath) != update_size:
                continue
            if pattern and not fnmatch.fnmatch(fname, pattern):
                continue
            if _hash_file(fpath) != update_hash:
                continue
            same.append(fpath)

    link_count = 0
    size_saved = 0
    if len(same) > 1:
        # Link files that are identical to the update file.
        link_count, size_saved = _link_files(same, root_dir, link, symlink,
                                             absolute, quiet)

    if not silent:
        print()
        if not link:
            print('If writing links (-w), would have...')
        print('Replaced', link_count, 'files with links')
        print('Reduced storage by', size_str(size_saved))

    return None


def _hash_file(filename):
    """Calculate SHA1 hash of file."""
    BLOCKSIZE = 65536
    hasher = hashlib.sha1()
    with open(filename, 'rb') as afile:
        buf = afile.read(BLOCKSIZE)
        while len(buf) > 0:
            hasher.update(buf)
            buf = afile.read(BLOCKSIZE)

    return hasher.hexdigest()


def _check_same(filepaths):
    # For list of same size files, create a map {hash: filepath, ..}
    hash_file_map = {}
    for fpath in filepaths:
        hash_file_map.setdefault(_hash_file(fpath), []).append(fpath)

    # Prune unique files, return lists of identical files.
    return [files for files in hash_file_map.itervalues() if len(files) > 1]


def _link_files(files, root_dir, link, symlink, absolute, quiet):
    link_count = 0
    size_saved = 0

    def fkey(name):
        # Sort by shortest-basename, shortest-path
        return len(os.path.basename(name)), len(name)

    # Sort files and get file with longest name, or longest path if names are
    # the same.  This only matters for symlinks, but since a failed hardlink
    # can result in a symlink, do it anyway.
    files.sort(key=fkey)
    base_file = files.pop()
    base_size = os.path.getsize(base_file)

    # Iterate remaining files and replace with links.
    for f in files:
        if os.path.samefile(base_file, f):
            # If the files are already the same (hardlinked), then do not try
            # to link.
            continue

        if not link:
            size_saved += base_size
            link_count += 1
            if not quiet:
                print('link:', os.path.relpath(f, root_dir), '<-->',
                      os.path.relpath(base_file, root_dir))
            continue

        try:
            os.unlink(f)
        except OSError:
            print('cannot unlink file:', f, file=sys.stderr)
            continue

        create_symlink = symlink
        if not symlink:
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
            if absolute:
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
    return str(byte_size) + ' bytes'


def main():
    import argparse
    ap = argparse.ArgumentParser(
        description='Convert identical files to links to one real file')
    ap.add_argument('root', nargs='?', default=os.getcwd(),
                    help='Top-level directory to search for files to link. '
                    'Current directory if not specified.')
    ap.add_argument('--write', '-w', action='store_true',
                    help='Write links to filesystem')
    ap.add_argument('--symlink', '-s', action='store_true',
                    help='Link files using only symlinks')
    ap.add_argument('--absolute', '-a', action='store_true',
                    help='When creating symlink, use absolute instead of '
                    'relative link.')
    ap.add_argument('--pattern', '-p', help='Only link files matching pattern')
    ap.add_argument('--quiet', '-q', action='store_true',
                    help='Do not print individual link creation messages')
    ap.add_argument('--silent', '-qq', action='store_true',
                    help='Do not print results, implies --quiet')
    ap.add_argument('--update', '-u',
                    help='Only link files identical to specified update file')
    args = ap.parse_args()

    if args.update:
        err = link_same_update(
            args.update, args.root, args.pattern, args.write, args.symlink,
            args.absolute, args.quiet, args.silent)
    else:
        err = link_same_files(
            args.root, args.pattern, args.write, args.symlink, args.absolute,
            args.quiet, args.silent)

    if err:
        print(err, file=sys.stderr)
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
