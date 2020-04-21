#!/usr/bin/env python3
import construct
import hashlib
import json
import os
import re
import shutil
import sys
from construct import *
from datetime import datetime
from freezetag.base import ParsedFile, MusicMetadata
from freezetag.formats import flac, generic, mp3
from pathlib import Path

# Version 2 is used only for "freeze --backup" freezetags.
# All other freezetags are still created using version 1 so the bytes/IDs stay consistent.
# These can be unified in a future version if the schema is updated.
DEFAULT_VERSION = 1
VERSION = 2

DEFAULT_MODE = 0
BACKUP_MODE = 1

# Used for FrozenFormat > files > format.
generic.ParsedFile.format_id = 0
flac.ParsedFile.format_id = 1
mp3.ParsedFile.format_id = 2

freeze_modes = ['default', 'backup']


class Reprinter():
    def __init__(self):
        self.last_width = 0

    def print(self, text):
        text = str(text)
        print(text.ljust(self.last_width, ' '), end='\r')
        self.last_width = len(text)


def get_version(is_backup):
    return VERSION if is_backup else DEFAULT_VERSION


def get_mode(is_backup):
    return BACKUP_MODE if is_backup else DEFAULT_MODE


FrozenFormatV1 = Struct(
    'mode' / Computed(0),
    'music_checksum' / Bytes(8),
    'metadata_checksum' / Bytes(4),
    'root' / CString('utf8'),
    'files' / Compressed(PrefixedArray(Int16ub, Struct(
        'path' / CString('utf8'),
        'format' / Int8ub,
        'checksum' / Bytes(20),
        'metadata' / Switch(this.format, {
            1: flac.FrozenMetadataFormat,
            2: mp3.FrozenMetadataFormat,
        }),
    )), 'lzma'),
)

FrozenFormatV2 = Struct(
    'mode' / Int8ub,
    'music_checksum' / Bytes(8),
    'metadata_checksum' / Bytes(4),
    'root' / CString('utf8'),
    'files' / Compressed(PrefixedArray(Int16ub, Struct(
        'path' / CString('utf8'),
        'format' / Int8ub,
        'checksum' / Bytes(20),
        'stat' / If(this._._.mode == 1, Struct(
            'mtime' / Double,
            'size' / Long,
        )),
        'metadata' / Switch(this.format, {
            1: flac.FrozenMetadataFormat,
            2: mp3.FrozenMetadataFormat,
        }),
    )), 'lzma'),
)

FreezeFormat = Struct(
    'signature' / Const(b'freezetag'),
    'version'/ Int8ub,
    'frozen' / Switch(this.version, {
        1: FrozenFormatV1,
        2: FrozenFormatV2,
    }, GreedyBytes),
    Terminated,
)


class Freezetag:
    @staticmethod
    def from_bytes(b):
        data = FreezeFormat.parse(b)
        # Workaround for https://github.com/construct/construct/issues/852
        data._io.close()
        freezetag = Freezetag(data)
        freezetag._bytes = b
        return freezetag

    @staticmethod
    def from_path(path):
        with open(path, 'rb') as f:
            return Freezetag.from_bytes(f.read())

    def __init__(self, data):
        self.data = data
        self._bytes = None

    # Call this manually if data is changed.
    def data_updated(self):
        self._bytes = None

    def bytes(self):
        if not self._bytes:
            self._bytes = FreezeFormat.build(self.data)
        return self._bytes

    def get_id(self):
        checksum = hash_bytes(self.bytes())[0:4]
        return 'F' + '-'.join([self.data['frozen']['music_checksum'].hex(),
                               self.data['frozen']['metadata_checksum'].hex(),
                               checksum.hex()])

    def write(self, path):
        with open(path, 'wb') as f:
            f.write(self.bytes())


class FreezetagException(Exception):
    pass


def hash_bytes(b):
    return hashlib.sha1(b).digest()


def hash_file(path):
    with open(path, 'rb') as f:
        return hash_bytes(f.read())


def get_id(freezetag, freezetag_bytes):
    checksum = hash_bytes(freezetag_bytes)[0:4]
    return 'F' + '-'.join([freezetag['frozen']['music_checksum'].hex(),
                           freezetag['frozen']['metadata_checksum'].hex(),
                           checksum.hex()])


def find_ftag(path):
    if not path.exists():
        raise FreezetagException('Given ftag is not a file or directory: {0}'.format(path))

    if path.is_file():
        return path

    freezetag_paths = [p for p in path.iterdir() if p.suffix.lower() == '.ftag']

    if not len(freezetag_paths):
        raise FreezetagException('No freezetag file found in {0}'.format(path))

    index = 0

    if len(freezetag_paths) > 1:
        print('Multiple freezetags found in directory: {0}'.format(path.resolve()))
        for i, path in enumerate(freezetag_paths):
            print('{0}: {1}'.format(i, path.name))
        choice = ''
        while not choice.isdecimal() or int(choice) < 0 or int(choice) >= len(freezetag_paths):
            choice = input('Select freezetag [0-{0}], or q to quit: '.format(len(freezetag_paths)-1))
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
        raise FreezetagException('Directory does not exist: {0}'.format(root))

    for path, rel_path in walk_dir(root):
        file = ParsedFile.from_path(path)

        if not file.format:
            continue

        print(path.name)

        metadata = file.strip()

        if not next(iter(metadata), None):
            print('    no metadata found')
            continue

        print('    shaved {0}'.format(', '.join('{0} ({1})'.format(label, size)
            for label, size in metadata)))

        file.write(path)


def prepare_thaw(root, frozen, thaw_in_place, checksum_to_item):
    paths = {}
    commonpath = None
    unrecognized_found = False
    reprinter = Reprinter()

    for path, rel_path in walk_dir(root):
        reprinter.print('Checking...{0}'.format(rel_path))

        file = ParsedFile.from_path(path)
        file.strip()
        checksum = file.checksum()

        if checksum not in checksum_to_item:
            unrecognized_found = True
            reprinter.print('    Unrecognized file: {0}'.format(path))
            print()
            continue

        checksum_to_item[checksum][1] = True
        paths[rel_path] = checksum_to_item[checksum]
        commonpath = os.path.commonpath(list(filter(None, [commonpath, path])))

    reprinter.print('Checking...done.')
    print()

    if thaw_in_place and unrecognized_found and Path(commonpath) != root:
        print('\nCommon path ({0}) does not match thaw directory ({1}).'.format(commonpath, root))
        print("You're thawing in-place, so the structure of {0} will be changed.".format(root))
        print('This directory may be renamed, and unrecognized files will be left in their paths'
              ' relative to this directory.')
        print('Make sure that you didn\'t intend to thaw {0} instead.'.format(commonpath))
        while True:
            choice = input('Continue anyway? (y/n): ').lower()
            if choice == 'y':
                break
            if choice == 'n':
                sys.exit(0)

    missing_music = False
    for file in frozen.files:
        if not checksum_to_item[file.checksum][1]:
            print('    Missing: {0} ({1})'.format(file.path, file.checksum.hex()), file=sys.stderr)
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
        raise FreezetagException('Directory does not exist: {0}'.format(root))

    ftag = find_ftag(Path(ftag or root))
    freezetag = Freezetag.from_path(ftag)

    if freezetag.data.version > VERSION:
        raise FreezetagException('Freezetag file version greater than freezetag version ({0} > {1}).\n'
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

    print('Processing {0}...'.format(root))

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

        reprinter.print('Thawing metadata...{0}'.format(rel_path))

        if item[2]:
            continue

        item[2] = True
        num_files = len(item[0])

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
        reprinter.print('Restoring files...{0}'.format(rel_path))
        to_path = to_dir / rel_path
        to_path.parent.mkdir(parents=True, exist_ok=True)
        path.rename(to_path)

    reprinter.print('Restoring files...done.'.format(rel_path))
    print()

    shutil.rmtree(tmp_dir)

    if thaw_in_place:
        new_root = root.parent / frozen.root
        if root != new_root:
            print('Renaming {0} to {1}'.format(root, new_root))
            root.rename(new_root)


def freeze(directory, backup, ftag, **kwargs):
    root = Path(directory).resolve()
    if not root.exists():
        raise FreezetagException('Directory does not exist: {0}'.format(root))

    tmp_paths = [p for p in root.iterdir() if p.suffix.lower() == '.ftag-tmp']

    # We're trying to create a new freeze state, but we found existing freezetag tmp
    # directories. We almost certainly don't want tmp directories to be frozen, so
    # abort and have the user fix it first.
    if len(tmp_paths):
        raise FreezetagException(
            'Unrestored freezetag data found at {0}.\n'
            'Run freezetag thaw again to finish processing.'.format(tmp_paths[0]))

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

        reprinter.print('Collecting metadata...{0}'.format(rel_path))

    reprinter.print('Collecting metadata...done.')
    print()

    if not len(music_checksums):
        raise FreezetagException('No music files found.')

    if existing_path_count == len(existing) and existing_path_count == len(files)\
            and last_frozen.root == root.name:
        print('No changes since last freezetag ({0}).'.format(last_ftag[0].name))
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
        to_path = to_path / '{0}.ftag'.format(filename)

    freezetag.write(to_path)

    print('Freezetag created at {0}'.format(to_path))


def show(path, json, **kwargs):
    ftag = find_ftag(Path(path))

    freezetag = Freezetag.from_path(ftag)
    version = freezetag.data.version

    if version > VERSION:
        raise FreezetagException('Freezetag file version greater than freezetag version ({0} > {1}).\n'
                                 'Update freezetag and try again.'.format(version, VERSION))

    frozen = freezetag.data.frozen

    if json:
        print(json.dumps({
            'version': version,
            'mode': freeze_modes[frozen.data.mode],
            'id': freezetag.get_id(),
            'root': frozen.root,
            'files': [{
                'path': f.path,
                'checksum': f.checksum.hex(),
            } for f in frozen.files],
        }, indent=2))
    else:
        print('version: {0}'.format(version))
        print('mode:    {0}'.format(freeze_modes[frozen.mode]))
        print('id:      {0}'.format(freezetag.get_id()))
        print('root:    {0} '.format(frozen.root))
        for f in frozen.files:
            print('{0} {1}'.format(f.checksum.hex(), f.path))
