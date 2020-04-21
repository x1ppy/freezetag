import hashlib
import os
from freezetag import base
from construct import *


BLOCK_TYPES = [
    'STREAMINFO',
    'PADDING',
    'APPLICATION',
    'SEEKTABLE',
    'VORBIS_COMMENT',
    'CUESHEET',
    'PICTURE',
]

MetadataFormat = Struct(
    'info' / BitStruct(
        'last' / Flag,
        'block_type' / BitsInteger(7),
    ),
    'size' / Int24ub,
    'data' / Bytes(this.size),
)

FrozenMetadataFormat = PrefixedArray(Int8ub, MetadataFormat)

Format = Struct(
    'signature' / Const(b'fLaC'),
    'metadata' / RepeatUntil(lambda metadata, *_: metadata.info.last, MetadataFormat),
    'audio' / GreedyBytes,
)


class MusicMetadata(base.MusicMetadata):
    def __init__(self, value):
        super().__init__(FrozenMetadataFormat, value)

    def __iter__(self):
        for item in self.value:
            yield BLOCK_TYPES[item.info.block_type], item.size


class ParsedFile(base.MusicParsedFile):
    def __init__(self, path):
        super().__init__(path, Format)

    def strip(self):
        streaminfo = self.instance.metadata[0]
        streaminfo.info.last = True
        metadata = self.instance.metadata[1:]
        self.instance.metadata = [streaminfo]
        return MusicMetadata(metadata)

    def restore_metadata(self, metadata):
        self.strip()

        # Append the frozen metadata to the stripped media.
        self.instance.metadata[0].info.last = not len(metadata)
        self.instance.metadata += metadata
