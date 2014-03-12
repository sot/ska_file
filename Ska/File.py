"""Ska file utilities"""
import os
import tempfile
import shutil
import re
import subprocess
import glob
import contextlib

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


def prune_dirs(dirs, regex):
    """
    Prune directories (in-place) that do not match ``regex``.
    """
    prunes = [x for x in dirs if not re.match(regex, x)]
    for prune in prunes:
        dirs.remove(prune)

# get_mp_files is slow, so cache results (mostly for testing)
get_mp_files_cache = {}


def get_mp_files(file_basename_regex, subdir=None, mpdir='', mproot='/data/mpcrit1/mplogs'):
    """
    Get all files within the specified SOT MP directory ``mpdir``
    matching the requested regex.  The optional 'subdir' specifies if the
    file is found within a fixed name subdirectory (such as ``mps/or``).

    Returns a list of dicts [{name, date},..]
    """
    from Chandra.Time import DateTime
    import logging
    logger = logging.getLogger('Ska.File')

    rootdir = os.path.join(mproot, mpdir)
    try:
        return get_mp_files_cache[rootdir + str(subdir) + file_basename_regex]
    except KeyError:
        pass

    logger.info('Looking for files in {}'.format(rootdir))

    year_re = re.compile(r'\d{4}$')
    week_re = re.compile(r'[A-Z]{3}\d{4}$')
    vers_re = re.compile(r'ofls[a-z]$')

    subdirs = None
    last_subdir = None

    mpfiles = []
    for root, dirs, files in os.walk(rootdir):
        logger.debug('get_mp_files: root={}'.format(root))
        root = root.rstrip('/')
        parent, tail = os.path.split(root)
        if root == mproot.rstrip('/'):
            prune_dirs(dirs, year_re)
        elif year_re.match(tail):
            prune_dirs(dirs, week_re)
        elif week_re.match(tail):
            prune_dirs(dirs, vers_re)
        # if there is one or more subdirectory specified, start pruning by them when
        # os.walk reaches the ofls? directory matched by vers_re
        elif vers_re.match(tail) and subdir is not None:
            subdirs = subdir.rstrip('/').split('/')
            last_subdir = None
            if len(subdirs):
                prune_dirs(dirs, subdirs[0])
                last_subdir = subdirs.pop(0)
        # If there is more than one subdirectory, loop through them by storing the last
        # one in 'last_subdir' and removing the directory from the subdirs list
        elif last_subdir is not None and tail == last_subdir and len(subdirs):
            prune_dirs(dirs, subdirs[0])
            last_subdir = subdirs.pop(0)
        else:
            mps = [x for x in files if re.match(file_basename_regex, x)]
            if len(mps) == 0:
                logger.info('NO file found in {}'.format(root))
            else:
                logger.info('Located file {}'.format(os.path.join(root, mps[0])))
                mpfiles.append(os.path.join(root, mps[0]))
            while dirs:
                dirs.pop()

    files = []
    for mpfile in mpfiles:
        daymatch = re.search(r'([A-Z]{3})(\d{2})(\d{2})/ofls(\w)', mpfile)
        if not daymatch:
            continue
        oflsv = daymatch.group(4)
        mon = daymatch.group(1)
        dd = daymatch.group(2)
        yy = int(daymatch.group(3))
        yyyy = 1900 + yy if yy > 95 else 2000 + yy
        caldate = '{}{}{} at 12:00:00.000'.format(yyyy, mon, dd)
        files.append((mpfile,
                      DateTime(caldate).date[:8] + oflsv,
                      DateTime(caldate).date))

    files = sorted(files, key=lambda x: x[1])
    out = [{'name': x[0], 'date': x[2]} for x in files]
    # store the results in the cache both by directory / subdir / regex
    get_mp_files_cache[rootdir + mpdir + str(subdir) + file_basename_regex] = out
    return out
