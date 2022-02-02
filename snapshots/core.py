# Standard library imports
import os
import shutil
from collections import namedtuple
from math import trunc


__all__ = [
    'Entry',
    'normalize',
    'relative',
    'remove_file',
    'remove_folder',
    'copy_file',
    'create_folder',
    'depth_sort',
    'take',
    'diff',
    'sync',
    'sync_bidirectional',
]


Entry = namedtuple('Entry', 'path relative_path isfile mtime')


def normalize(*parts):
    """Join and normalize file path parts."""

    path = os.path.normpath(os.path.join(*parts))
    return path.replace('\\', '/')


def relative(path, start):
    """Return path relative to root."""

    return os.path.relpath(path, start).replace('\\', '/')


def remove_file(path):
    """Remove a file."""

    try:
        os.remove(path)
    except Exception as e:
        print(e)


def remove_folder(path):
    """Remove a folder."""

    try:
        if not os.listdir(path):
            os.rmdir(path)
    except Exception as e:
        print(e)


def copy_file(src, dst):
    """Copy a file or folder to a new dst."""

    create_folder(os.path.dirname(dst))
    shutil.copy2(src, dst)


def create_folder(path):
    """Create a folder if it doesn't exist."""

    if not os.path.isdir(path):
        try:
            os.makedirs(path)
        except Exception as e:
            print(e)


def depth_sort(files):
    """Sort a list of files by folder depth."""

    return sorted(files, key=lambda x: x.count('/'), reverse=True)


def take(folder_or_file, depth=-1):
    """Return a dict mapping relative paths to Entry objects."""

    if os.path.isfile(folder_or_file):
        path = normalize(os.path.abspath(folder_or_file))
        relative_path = os.path.basename(path)
        mtime = os.path.getmtime(path)
        return {relative_path: Entry(path, relative_path, True, mtime)}

    if not os.path.isdir(folder_or_file):
        return {}

    snapshot = {}
    base_root = normalize(folder_or_file)
    base_depth = len(base_root.split('/'))

    for root, subdirs, files in os.walk(folder_or_file):

        path = normalize(root)
        relative_path = relative(path, base_root)
        mtime = os.path.getmtime(path)
        if depth > -1 and len(path.split('/')) - base_depth == depth:
            subdirs[:] = []

        snapshot[relative_path] = Entry(path, relative_path, False, mtime)
        for f in files:
            path = normalize(root, f)
            relative_path = relative(path, base_root)
            mtime = os.path.getmtime(path)
            snapshot[relative_path] = Entry(path, relative_path, True, mtime)

    return snapshot


def diff(prev_snapshot, next_snapshot):
    """Return a dict containing changes between two snapshots."""

    snapshot_diff = {
        'left_only': [],
        'right_only': [],
        'changed': [],
        'common': [],
    }

    for path in set(prev_snapshot.keys()) | set(next_snapshot.keys()):
        if path in prev_snapshot and path not in next_snapshot:
            snapshot_diff['left_only'].append(path)
        elif path not in prev_snapshot and path in next_snapshot:
            snapshot_diff['right_only'].append(path)
        elif next_snapshot[path].mtime != prev_snapshot[path].mtime:
            if next_snapshot[path].isfile:
                snapshot_diff['changed'].append(path)
        else:
            snapshot_diff['common'].append(path)

    return snapshot_diff


def sync(src, dst, replace_changed=False, delete_files=False, dry=False, reporter=None):
    """Sync two folders.

    Properties:
        - Files are copied from the src location to the dst location.
        - Files that exist in dst but not src are deleted when delete_files is
          True.
        - If a file is in both locations, the dst file is replaced with the
          src file when replace_changed is True.
    """

    reporter = reporter or Reporter('Sync')
    src = normalize(src)
    dst = normalize(dst)
    src_snapshot = take(src)
    dst_snapshot = take(dst)
    snapshot_diff = diff(src_snapshot, dst_snapshot)

    # Calculate total number of operations
    number_of_operations = 0
    number_of_operations += len(snapshot_diff['left_only'])
    if delete_files:
        number_of_operations += len(snapshot_diff['right_only'])
    if replace_changed:
        number_of_operations += len(snapshot_diff['changed'])

    # Start reporting
    reporter.set_total(number_of_operations)
    if number_of_operations:
        reporter.start('{} --> {}'.format(src, dst))
        reporter.info('Syncing {} files.'.format(number_of_operations))
    else:
        reporter.start('{} --> {}'.format(src, dst))
        reporter.done('Done! Nothing to sync.')
        return

    # Copy files unique to src to dst
    for path_key in snapshot_diff['left_only']:
        entry = src_snapshot[path_key]
        dst_path = normalize(dst, entry.relative_path)
        reporter.step(1, 'R-> Copy {}'.format(entry.relative_path))

        if dry:
            continue

        if entry.isfile:
            copy_file(entry.path, dst_path)
        else:
            create_folder(dst_path)

    # Copy files unique to dst to src
    if delete_files:
        for path_key in depth_sort(snapshot_diff['right_only']):
            entry = dst_snapshot[path_key]
            reporter.step(1, 'R-> Delete {}'.format(entry.relative_path))

            if dry:
                continue

            if entry.isfile:
                remove_file(entry.path)
            else:
                remove_folder(entry.path)

    # Replace changed files with newer version
    if replace_changed:
        for path_key in snapshot_diff['changed']:
            src_entry = src_snapshot[path_key]
            dst_entry = dst_snapshot[path_key]
            reporter.step(1, 'R-> Replace {}'.format(dst_entry.relative_path))

            if dry:
                continue

            if src_entry.isfile:
                copy_file(src_entry.path, dst_entry.path)

    reporter.done('Done!')


def sync_bidirectional(src, dst, replace_changed=False, dry=False, reporter=None):
    """Sync two folders bidirectionally.

    Properties:
        - Files in only one location are copied to the opposite location.
        - If both locations have a file in common, the older file is replaced
            with the newer file when replace_changed is True.
    """

    reporter = reporter or Reporter('Sync')
    src = normalize(src)
    dst = normalize(dst)
    src_snapshot = take(src)
    dst_snapshot = take(dst)
    snapshot_diff = diff(src_snapshot, dst_snapshot)

    # Calculate total number of operations
    number_of_operations = 0
    number_of_operations += len(snapshot_diff['left_only'])
    number_of_operations += len(snapshot_diff['right_only'])
    if replace_changed:
        number_of_operations += len(snapshot_diff['changed'])

    # Start reporting
    reporter.set_total(number_of_operations)
    if number_of_operations:
        reporter.start('{} <-> {}'.format(src, dst))
        reporter.info('Syncing {} files.'.format(number_of_operations))
    else:
        reporter.start('{} <-> {}'.format(src, dst))
        reporter.done('Done! Nothing to sync.')
        return

    # Copy files unique to src to dst
    for path_key in snapshot_diff['left_only']:
        entry = src_snapshot[path_key]
        dst_path = normalize(dst, entry.relative_path)
        reporter.step(1, 'R-> Copy {}'.format(entry.relative_path))

        if dry:
            continue

        if entry.isfile:
            copy_file(entry.path, dst_path)
        else:
            create_folder(dst_path)

    # Copy files unique to dst to src
    for path_key in snapshot_diff['right_only']:
        entry = dst_snapshot[path_key]
        src_path = normalize(src, entry.relative_path)
        reporter.step(1, '<-L Copy {}'.format(entry.relative_path))

        if dry:
            continue

        if entry.isfile:
            copy_file(entry.path, src_path)
        else:
            create_folder(src_path)

    # Replace changed files with newer version
    if replace_changed:
        for path_key in snapshot_diff['changed']:
            src_entry = src_snapshot[path_key]
            dst_entry = dst_snapshot[path_key]
            if src_entry.mtime > dst_entry.mtime:
                reporter.step(1, 'R-> Replace {}'.format(dst_entry.relative_path))

                if dry:
                    continue

                if src_entry.isfile:
                    copy_file(src_entry.path, dst_entry.path)
            else:
                reporter.step(1, '<-L Replace {}'.format(src_entry.relative_path))

                if dry:
                    continue

                if dst_entry.isfile:
                    copy_file(dst_entry.path, src_entry.path)

    reporter.done('Done!')


class Reporter(object):
    '''A Reporter class used to log the progress of a sync operation.'''

    def __init__(self, name, total=100):
        self.name = name
        self.total = total
        self.amount = 0
        self.percent = 0

    def set_total(self, value):
        """Set the maximum value of this Reporter.

        The total is used to calculate percent when step is called.
        """

        self.total = value

    def info(self, message):
        self.on_info(message)

    def on_info(self, message):
        """Subclasses should override this method to customize logging."""

        print('[{}] {}'.format(self.name, message))

    def start(self, message):
        self.on_start(message)

    def on_start(self, message):
        """Subclasses should override this method to customize logging."""

        print('[{}] {}'.format(self.name, message))

    def step(self, amount, message):

        self.amount += amount
        self.percent = self.amount / self.total * 100
        self.on_step(message)

    def on_step(self, message):
        """Subclasses should override this method to customize logging."""

        print('[{}] Progress {:>3d}% {}'.format(
            self.name,
            trunc(self.percent),
            message,
        ))

    def done(self, message):
        self.on_done(message)

    def on_done(self, message):
        """Subclasses should override this method to customize logging."""

        print('[{}] {}'.format(self.name, message))
