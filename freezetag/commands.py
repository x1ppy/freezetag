#!/usr/bin/env python3
import hashlib
import json
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

from .base import ParsedFile, MusicMetadata
from .core import Freezetag

# Version 2 is used only for "freeze --backup" freezetags.
# All other freezetags are still created using version 1 so the bytes/IDs stay consistent.
# These can be unified in a future version if the schema is updated.
DEFAULT_VERSION = 1
VERSION = 2

DEFAULT_MODE = 0
BACKUP_MODE = 1

freeze_modes = ['default', 'backup']


class CommandException(Exception):
    pass


def get_version(is_backup):
    return VERSION if is_backup else DEFAULT_VERSION


def get_mode(is_backup):
    return BACKUP_MODE if is_backup else DEFAULT_MODE


class Reprinter():
    def __init__(self):
        self.last_width = 0

    def print(self, text):
        text = str(text)
        print(text.ljust(self.last_width, ' '), end='\r')
        self.last_width = len(text)


def hash_bytes(b):
    return hashlib.sha1(b).digest()


def find_ftag(path):
    if not path.exists():
        raise CommandException(f'Given ftag is not a file or directory: {path}')

    if path.is_file():
        return path

    freezetag_paths = [p for p in path.iterdir() if p.suffix.lower() == '.ftag']

    if not len(freezetag_paths):
        raise CommandException(f'No freezetag file found in {path}')

    index = 0

    if len(freezetag_paths) > 1:
        print(f'Multiple freezetags found in directory: {path.resolve()}')
        for i, path in enumerate(freezetag_paths):
            print(f'{i}: {path.name}')
        choice = ''
        while not choice.isdecimal() or int(choice) < 0 or int(choice) >= len(freezetag_paths):
            choice = input(f'Select freezetag [0-{len(freezetag_paths) - 1}], or q to quit: ')
            if choice.lower() == 'q':
                sys.exit(0)
        index = int(choice)

    return freezetag_paths[index]


def walk_dir(path):
    for dirpath, dirnames, filenames in os.walk(path):
        dirnames.sort()

        for filename in sorted(filenames):
            if filename.lower().endswith('.ftag'):
                continue

            p = Path(dirpath) / filename
            yield p, p.relative_to(path)


def shave(directory, **kwargs):
    root = Path(directory).resolve()
    if not root.exists():
        raise CommandException(f'Directory does not exist: {root}')

    for path, rel_path in walk_dir(root):
        file = ParsedFile.from_path(path)

        if not file.format:
            continue

        print(path.name)

        metadata = file.strip()

        if not next(iter(metadata), None):
            print('    no metadata found')
            continue

        print('    shaved {0}'.format(', '.join(f'{label} ({size})' for label, size in metadata)))

        file.write(path)


def prepare_thaw(root, frozen, thaw_in_place, checksum_to_item):
    paths = {}
    commonpath = None
    unrecognized_found = False
    reprinter = Reprinter()

    for path, rel_path in walk_dir(root):
        reprinter.print(f'Checking...{rel_path}')

        file = ParsedFile.from_path(path)
        file.strip()
        checksum = file.checksum()

        if checksum not in checksum_to_item:
            unrecognized_found = True
            reprinter.print(f'    Unrecognized file: {path}')
            print()
            continue

        checksum_to_item[checksum][1] = True
        paths[rel_path] = checksum_to_item[checksum]
        commonpath = os.path.commonpath(list(filter(None, [commonpath, path])))

    reprinter.print('Checking...done.')
    print()

    if thaw_in_place and unrecognized_found and Path(commonpath) != root:
        print(f'\nCommon path ({commonpath}) does not match thaw directory ({root}).')
        print(f"You're thawing in-place, so the structure of {root} will be changed.")
        print('This directory may be renamed, and unrecognized files will be left in their paths'
              ' relative to this directory.')
        print(f'Make sure that you didn\'t intend to thaw {commonpath} instead.')
        while True:
            choice = input('Continue anyway? (y/n): ').lower()
            if choice == 'y':
                break
            if choice == 'n':
                sys.exit(0)

    missing_music = False
    for file in frozen.files:
        if not checksum_to_item[file.checksum][1]:
            print(f'    Missing: {file.path} ({file.checksum.hex()})', file=sys.stderr)
            if file.format:
                missing_music = True

    if missing_music:
        print('One or more music files listed in freezetag are missing.')
        while True:
            choice = input('Continue anyway? (y/n): ').lower()
            if choice == 'y':
                break
            if choice == 'n':
                sys.exit(0)

    return paths


def thaw(directory, to, ftag, skip_checks, **kwargs):
    root = Path(directory).resolve()
    if not root.exists():
        raise CommandException(f'Directory does not exist: {root}')

    ftag = find_ftag(Path(ftag or root))
    freezetag = Freezetag.from_path(ftag)

    if freezetag.data.version > VERSION:
        raise CommandException('Freezetag file version greater than freezetag version ({0} > {1}).\n'
                               'Update freezetag and try again.'.format(freezetag.data.version, VERSION))

    frozen = freezetag.data.frozen
    to_dir = Path(to).resolve() / frozen.root if to else root
    tmp_dir = root / ftag.with_suffix('.ftag-tmp').name
    thaw_in_place = root == to_dir

    # Map each checksum to an array of files in case multiple files with identical checksums were frozen.
    checksum_to_item = {}
    for f in frozen.files:
        if f.checksum not in checksum_to_item:
            checksum_to_item[f.checksum] = [[], False, False]
        checksum_to_item[f.checksum][0].append(f)

    print(f'Processing {root}...')

    # First pass: verify directory and calculate checksums.
    path_to_item = None
    if not skip_checks:
        path_to_item = prepare_thaw(root, frozen, thaw_in_place, checksum_to_item)

    reprinter = Reprinter()
    import_fn = shutil.move if thaw_in_place else shutil.copy2

    # Second pass: move (or copy) files to tmp_dir and update their metadata.
    for path, rel_path in walk_dir(root):
        file = None

        if path_to_item:
            if rel_path not in path_to_item:
                continue
            item = path_to_item[rel_path]
        else:
            file = ParsedFile.from_path(path)
            file.strip()
            checksum = file.checksum()
            if checksum not in checksum_to_item:
                continue
            item = checksum_to_item[checksum]

        reprinter.print(f'Thawing metadata...{rel_path}')

        if item[2]:
            continue

        item[2] = True

        for state in item[0]:
            to_path = tmp_dir / state.path
            to_path.parent.mkdir(parents=True, exist_ok=True)

            if not state.format:
                try:
                    if len(item[0]) == 1:
                        import_fn(path, to_path)
                    else:
                        shutil.copy2(path, to_path)
                except shutil.SameFileError:
                    pass
                continue

            if not file:
                file = ParsedFile.from_path(path)

            file.restore_metadata(state.metadata)
            file.write(to_path)

        if thaw_in_place and rel_path.parts[0] != tmp_dir.name and path.exists():
            path.unlink()
            parent = path.parent
            while not len(os.listdir(parent)):
                parent.rmdir()
                parent = parent.parent

    reprinter.print('Thawing metadata...done.')
    print()

    # Third pass: move files from tmp_dir to their final destinations.
    for path, rel_path in walk_dir(tmp_dir):
        reprinter.print(f'Restoring files...{rel_path}')
        to_path = to_dir / rel_path
        to_path.parent.mkdir(parents=True, exist_ok=True)
        path.rename(to_path)

    reprinter.print('Restoring files...done.')
    print()

    shutil.rmtree(tmp_dir)

    if thaw_in_place:
        new_root = root.parent / frozen.root
        if root != new_root:
            print(f'Renaming {root} to {new_root}')
            root.rename(new_root)


def freeze(directory, backup, ftag, **kwargs):
    root = Path(directory).resolve()
    if not root.exists():
        raise CommandException(f'Directory does not exist: {root}')

    tmp_paths = [p for p in root.iterdir() if p.suffix.lower() == '.ftag-tmp']

    # We're trying to create a new freeze state, but we found existing freezetag tmp
    # directories. We almost certainly don't want tmp directories to be frozen, so
    # abort and have the user fix it first.
    if len(tmp_paths):
        raise CommandException(
            f'Unrestored freezetag data found at {tmp_paths[0]}.\n'
            'Run freezetag thaw again to finish processing.')

    to_path = Path(ftag or root)
    existing = {}
    files = []
    music_checksums = []
    metadata_checksums = []
    last_ftag = (None, 0)
    reprinter = Reprinter()

    reprinter.print('Collecting metadata...')

    if backup:
        to_dir = to_path if to_path.is_dir() else to_path.parent
        for f in to_dir.iterdir():
            if not re.match('F\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}\.ftag', f.name):
                continue
            mtime = os.stat(f).st_mtime
            if mtime > last_ftag[1]:
                last_ftag = (f, mtime)
        if last_ftag[0]:
            last_frozen = Freezetag.from_path(last_ftag[0]).data.frozen
            for f in last_frozen.files:
                existing[f.path] = f

    existing_path_count = 0

    for path, rel_path in walk_dir(root):
        checksum = None

        if str(rel_path) in existing:
            stat = os.stat(path)
            state = existing[str(rel_path)]
            if stat.st_size == state.stat.size and abs(stat.st_mtime - state.stat.mtime) < 1e-3:
                files.append(f)
                existing_path_count += 1
                metadata = MusicMetadata.from_state(state)
                checksum = state.checksum

        file = ParsedFile.from_path(path)

        if not checksum:
            metadata = file.strip()
            checksum = file.checksum()

            dict = {
                'path': rel_path.as_posix(),
                'format': file.format_id,
                'checksum': checksum,
                'metadata': metadata.value if metadata else None,
            }

            if backup:
                stat = os.stat(path)
                dict['stat'] = {
                    'mtime': stat.st_mtime,
                    'size': stat.st_size,
                }
            else:
                dict['stat'] = None

            files.append(dict)

        if file.format:
            music_checksums.append(checksum)
            metadata_checksum = metadata.checksum()
            metadata_checksums.append(metadata_checksum)

        reprinter.print(f'Collecting metadata...{rel_path}')

    reprinter.print('Collecting metadata...done.')
    print()

    if not len(music_checksums):
        raise CommandException('No music files found.')

    if existing_path_count == len(existing) and existing_path_count == len(files) \
            and last_frozen.root == root.name:
        print(f'No changes since last freezetag ({last_ftag[0].name}).')
        return

    print('Building freezetag...')

    freezetag = Freezetag({
        'signature': b'freezetag',
        'version': get_version(backup),
        'frozen': {
            'mode': get_mode(backup),
            'music_checksum': hash_bytes(b''.join(sorted(music_checksums)))[0:8],
            'metadata_checksum': hash_bytes(b''.join(sorted(metadata_checksums)))[0:4],
            'root': root.name,
            'files': files,
        },
    })

    if to_path.is_dir():
        filename = 'F' + datetime.now().strftime('%Y-%m-%d_%H-%M-%S') if backup else freezetag.get_id()
        to_path = to_path / f'{filename}.ftag'

    freezetag.write(to_path)

    print(f'Freezetag created at {to_path}')


def show(path, as_json, **kwargs):
    ftag = find_ftag(Path(path))

    freezetag = Freezetag.from_path(ftag)
    version = freezetag.data.version

    if version > VERSION:
        raise CommandException('Freezetag file version greater than freezetag version ({0} > {1}).\n'
                               'Update freezetag and try again.'.format(version, VERSION))

    frozen = freezetag.data.frozen

    if as_json:
        print(json.dumps({
            'version': version,
            'mode': freeze_modes[frozen.mode],
            'id': freezetag.get_id(),
            'root': frozen.root,
            'files': [{
                'path': f.path,
                'checksum': f.checksum.hex(),
            } for f in frozen.files],
        }, indent=2))
    else:
        print(f'version: {version}')
        print(f'mode:    {freeze_modes[frozen.mode]}')
        print(f'id:      {freezetag.get_id()}')
        print(f'root:    {frozen.root}')
        for f in frozen.files:
            print(f'{f.checksum.hex()} {f.path}')


def mount(directory, mount_point, verbose, **kwargs):
    from .freezefs import FreezeFS
    FreezeFS(verbose).mount(directory, mount_point)
