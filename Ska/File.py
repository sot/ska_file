"""Ska file utilities"""
import os
import tempfile
import shutil
import re
import subprocess
import glob
import contextlib

__version__ = '3.4.1'


@contextlib.contextmanager
def chdir(dirname=None):
    """
    Context manager to run block within `dirname` directory.  The current
    directory is restored even if the block raises an exception.

     >>> with chdir(dirname):
     >>>     print "Directory within chdir() context:", os.getcwd()
     >>> print "Directory after chdir() context:", os.getcwd()

    :param dirname: Directory name
    """
    curdir = os.getcwd()
    try:
        if dirname is not None:
            os.chdir(dirname)
        yield
    finally:
        os.chdir(curdir)

class TempDir(object):
    """Create a temporary directory that gets automatically removed.  Any
    object initialization parameters are passed through to `tempfile.mkdtemp`_.

      >>> import Ska.File
      >>> tmpdir = Ska.File.TempDir(dir='.')
      >>> tmpdir.name
      './tmpcCH_l-'
      >>> del tmpdir

    .. _tempfile.mkdtemp: http://docs.python.org/library/tempfile.html#tempfile.mkdtemp 
    """
    def __init__(self, *args, **kwargs):
        self.__dirname = tempfile.mkdtemp(*args, **kwargs)
        self.name = self.__dirname      # "public" attribute
        
    def __del__(self):
        """Remove the temp directory when the object is destroyed."""
        shutil.rmtree(self.__dirname)

def get_globfiles(fileglob, minfiles=1, maxfiles=1):
    """
    Get file(s) matching ``fileglob``.  If the number of matching
    files is less than minfiles or more than maxfiles then an
    exception is raised.

    :param fileglob: Input file glob
    :param minfiles: Minimum matching files (None => no minimum)
    :param maxfiles: Maximum matching files (None => no maximum)
    """
    files = glob.glob(fileglob)
    nfiles = len(files)
    if minfiles is not None and nfiles < minfiles:
        raise ValueError('At least %d file(s) required for %s but %d found' % (minfiles, fileglob, nfiles))
    if maxfiles is not None and nfiles > maxfiles:
        raise ValueError('No more than %d file(s) required for %s but %d found' % (maxfiles, fileglob, nfiles))

    return files
    
def relpath(path, cwd=None):
    """ Find relative path from current directory to path.

    Example usage:
    
      >>> from Ska.File import relpath
      >>> relpath('/a/b/hello/there', cwd='/a/b/c/d')
      '../../hello/there'
      >>> relpath('/a/b/c/d/e/hello/there', cwd='/a/b/c/d')
      'e/hello/there'

      >>> # Special case - don't go up to root and back
      >>> relpath('/x/y/hello/there', cwd='/a/b/c/d')
      '/x/y/hello/there'

    :param path: Destination path
    :param cwd: Current directory (default: os.getcwd() )
    :rtype: Relative path

    """
    if cwd is None:
        cwd = os.getcwd()

    currpath = os.path.abspath(cwd)
    destpath = os.path.abspath(os.path.join(cwd, path))
    currpaths = currpath.split(os.sep)
    destpaths = destpath.split(os.sep)

    # Don't go up to root and back.  Since we split() on an abs path the
    # zero element is always ''
    if currpaths[1] != destpaths[1]:
        return destpath

    # Get rid of common path elements
    while currpaths and destpaths and currpaths[0] == destpaths[0]:
        currpaths.pop(0)
        destpaths.pop(0)

    # start with enough '..'s to get to top of common path then get
    # the rest of the destpaths.  Return '' if the list ends up being empty.
    relpaths = [os.pardir] * len(currpaths) + destpaths
    return os.path.join(*relpaths) if relpaths else ''

def make_local_copy(infile, outfile=None, copy=False, linkabs=False, clobber=True):
    """
    Make a local copy of or link to ``infile``, gunzipping if necessary.
    
    :param infile: Input file name
    :param outfile: Output file name (default: ``infile`` basename)
    :param copy: Always copy instead of linking when possible
    :param linkabs: Create link to absolute path instead of relative
    :param clobber: Clobber existing file
    :rtype: Output file name

      >>> import Ska.File
      >>> import random, tempfile
      >>> a = os.linesep.join([str(random.random()) for i in range(100)])
      >>> tmpfile = tempfile.mkstemp()[1]
      >>> open(tmpfile, 'w').write(a)
      >>> stat = subprocess.Popen(['gzip', '--stdout', tmpfile], stdout=open(tmpfile+'.gz','w')).communicate()
      >>> tmplocal = Ska.File.make_local_copy(tmpfile, clobber=True)
      >>> a == open(tmplocal).read()
      True
      >>> tmplocal = Ska.File.make_local_copy(tmpfile+'.gz', clobber=True)
      >>> a == open(tmplocal).read()
      True
      >>> os.unlink(tmpfile)
      >>> os.unlink(tmplocal)
    """
    
    if not os.path.exists(infile):
        raise IOError('Input file %s not found' % infile)

    if not outfile:
        outfile = re.sub(r'\.gz$', '', os.path.basename(infile))

    if os.path.exists(outfile):
        if clobber:
            os.unlink(outfile)
        else:
            raise IOError('Output file %s already exists and clobber is not set' % outfile)

    if infile.endswith('.gz'):
        cmds = ['gunzip', '--stdout', infile]
        subprocess.Popen(cmds, stdout=open(outfile, 'w')).communicate()
    elif copy:
        cmds = ['cp', '-p', infile, outfile]
        subprocess.Popen(cmds).communicate()
    else:                               # symbolic link
        infile_abs = os.path.abspath(infile)
        if linkabs:
            infile_link = infile_abs
        else:
            infile_link = relpath(infile_abs, cwd=os.path.dirname(outfile))
        os.symlink(infile_link, outfile)

    return outfile
    

def _reversed_blocks(file, blocksize=4096):
    "Generate blocks of file's contents in reverse order."
    file.seek(0, os.SEEK_END)
    here = file.tell()
    while 0 < here:
        delta = min(blocksize, here)
        here -= delta
        file.seek(here, os.SEEK_SET)
        yield file.read(delta)


def reversed_lines(filename):
    """
    Generate the lines of ``filename`` in reverse order.

    Adapted from: http://stackoverflow.com/questions/260273/most-efficient-way-to-search-the-last-x-lines-of-a-file-in-python/

    :param filename: file name
    :returns: generator of reversed file lines
    """
    with open(filename, 'r') as file:
        part = ''
        for block in _reversed_blocks(file):
            for c in reversed(block):
                if c == '\n' and part:
                    yield part[::-1]
                    part = ''
                part += c
        if part:
            yield part[::-1]
