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
from pathlib import Path
from .base import ParsedFile, MusicMetadata
from .formats import generic, flac, mp3


# Used for FrozenFormat > files > format.
generic.ParsedFile.format_id = 0
flac.ParsedFile.format_id = 1
mp3.ParsedFile.format_id = 2

# Used for freezetag mount cache.
DB_VERSION = 1


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

DBItemFormat = Struct(
    'device' / Int32ub,
    'inode' / Int64ub,
    'mtime' / Double,
    'checksum' / Bytes(20),
    'metadata_len' / Int32ub,
    'metadata_info' / PrefixedArray(Int8ub, Struct(
        'type' / CString('ascii'),
        'size' / Int32ub,
    )),
)

DBFormat = Struct(
    'version' / Const(DB_VERSION, Int8ub),
    'entries' / GreedyRange(DBItemFormat),
)


class ChecksumDBAdapter(Adapter):
    def _decode(self, obj, context, path):
        dict = {}
        for item in obj.entries:
            if item.device not in dict:
                dict[item.device] = {}
            metadata_info = [(m.type, m.size) for m in item.metadata_info]
            dict[item.device][item.inode] = (item.checksum, metadata_info, item.metadata_len, item.mtime)
        return dict

    def _encode(self, obj, context, path):
        entries = []
        for device, inodes in obj.items():
            for inode, (checksum, metadata_info, metadata_len, mtime) in inodes.items():
                entries.append({
                    'device': device,
                    'inode': inode,
                    'mtime': mtime,
                    'checksum': checksum,
                    'metadata_len': metadata_len,
                    'metadata_info': [{'type': m[0], 'size': m[1]} for m in metadata_info],
                })

        return {'version': DB_VERSION, 'entries': entries}


class ChecksumDB:
    def __init__(self, path):
        self.path = path
        self._flush_counter = 0
        self._format = ChecksumDBAdapter(DBFormat)
        try:
            self._db = self._format.parse_file(str(path))
            print('using existing database {0}'.format(path))
        except:
            print('creating database at {0}'.format(path))
            self._db = {}

    def get(self, device, inode, mtime):
        dict = self._db.get(device)
        if not dict:
            return
        item = dict.get(inode)
        if not item or item[3] != mtime:
            return
        return item

    def add(self, device, inode, mtime, checksum, metadata_info, metadata_len):
        if device not in self._db:
            self._db[device] = {}
        self._db[device][inode] = (checksum, metadata_info, metadata_len, mtime)
        self._try_flush()

    def _try_flush(self):
        self._flush_counter += 1
        if self._flush_counter < 50:
            return
        self.flush()

    def flush(self):
        self._flush_counter = 0
        self._format.build_file(self._db, str(self.path))


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
        with path.open('rb') as f:
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
        checksum = hashlib.sha1(self.bytes()).digest()[0:4]
        return 'F' + '-'.join([self.data['frozen']['music_checksum'].hex(),
                               self.data['frozen']['metadata_checksum'].hex(),
                               checksum.hex()])

    def write(self, path):
        with path.open('wb') as f:
            f.write(self.bytes())
