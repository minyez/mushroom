#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Helper script to distribute mushroom through SSH (rsync) to remote servers.

The destination of target should be defined in a dict `dist_remotes` in .mushroomrc.
For example, a key-value pair

    `'A': 'B'`

will sync mushroom distribution to `A:B/`. B must be absolute path
"""
import pathlib
import subprocess as sp
import warnings
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from mushroom import __version__
try:
    from mushroom.__config__ import dist_remotes
except ImportError:
    dist_remotes = {}

rsync_cmd = ["rsync", "-qazrul", "--inplace"]
tar_cmd = ["tar", "-zxp"]
homerc = pathlib.Path("~/.mushroomrc").expanduser().resolve()

def rsync_and_untar(tarball: pathlib.PosixPath, remote_ip: str, dirpath: str, verbose=False):
    """distribute mushroom tarball to dirpath on remote_ip by rsync"""
    try:
        cmds = rsync_cmd + [str(tarball), "{}:{}/".format(remote_ip, dirpath)]
        if verbose:
            print("running commands:", " ".join(cmds))
        sp.call(cmds)
    except sp.CalledProcessError:
        warnings.warn("fail to rsync {} to {}:{}/".format(tarball, remote_ip, dirpath))
        return
    
    try:
        # following cmds create bash error: No such file or directory
        #cmds = ["ssh", remote_ip] + ["\"cd", dirpath + ";"] + tar_cmd + ["-f", tarball.name, "\""]
        cmds = ["ssh", remote_ip] + tar_cmd + \
               ["-f", "{}/{}".format(dirpath, tarball.name), "-C", dirpath]
        if verbose:
            print("running commands:", " ".join(cmds))
        sp.call(cmds)
    except sp.CalledProcessError:
        warnings.warn("fail to extract {} at {}:{}".format(tarball.name, remote_ip, dirpath))
    print("Done rsyncing", str(tarball), "to", "{}:{}".format(remote_ip, dirpath))

def rsync_rc(remote_ip: str, verbose=False):
    """distribute home rc file to remote_ip"""
    try:
        cmds = rsync_cmd + [str(homerc), "{}:~/.mushroomrc".format(remote_ip)]
        if verbose:
            print("running commands:", " ".join(cmds))
        sp.call(cmds)
    except sp.CalledProcessError:
        warnings.warn("fail to rsync home rcfile to {}:~/".format(remote_ip))
    print("Done rsyncing homerc to", "{}:~/.mushroomrc".format(remote_ip))

def _parser():
    """the parser"""
    p = ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    p.add_argument("--tar", dest="tarball", type=str,
                   default=None, help="tgz tarball to distribute")
    p.add_argument("--dest", dest="remotes", type=str, default=None, choices=list(dist_remotes),
                   help="remote servers to distribute. Left out to distribute to all")
    p.add_argument("-v", dest="verbose", action="store_true", help="verbose mode for debug")
    p.add_argument("--rc", dest="sync_rc", action="store_true", help="sync home rcfile")
    return p.parse_args()


def dist_rsync():
    """the main flow"""
    args = _parser()
    tarball = args.tarball
    if not tarball:
        tarball = pathlib.Path(__file__).parent / ".." / "dist" / f"mushroom-{__version__}.tar.gz"
    else:
        tarball = pathlib.Path(tarball)
    if not tarball.is_file or not tarball.name.endswith(".tar.gz"):
        raise ValueError("{:s} is not a tgz file".format(tarball))
    remotes = [args.remotes,]
    if args.remotes is None:
        remotes = list(dist_remotes)

    for r in remotes:
        dirpath = dist_remotes.get(r)
        if dirpath.startswith("~"):
            print("Relative path detected for {}. Skip".format(r))
            continue
        rsync_and_untar(tarball, r, dirpath, verbose=args.verbose)
        if args.sync_rc:
            rsync_rc(r, args.verbose)


if __name__ == "__main__":
    dist_rsync()
