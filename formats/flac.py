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

FlacMetadataFormat = Struct(
    'info' / BitStruct(
        'last' / Flag,
        'block_type' / BitsInteger(7),
    ),
    'size' / Int24ub,
    'data' / Bytes(this.size),
)

FlacFormat = Struct(
    'signature' / Const(b'fLaC'),
    'metadata' / RepeatUntil(lambda metadata, *_: metadata.info.last, FlacMetadataFormat),
    'audio' / GreedyBytes,
)

class FlacFile:
    extension = '.flac'
    format = FlacFormat
    metadata_format = PrefixedArray(Int8ub, FlacMetadataFormat)

    def iter_metadata(metadata):
        for item in metadata:
            yield BLOCK_TYPES[item.info.block_type], item.size

    def __init__(self, file_bytes):
        self.instance = FlacFormat.parse(file_bytes)

    def strip(self):
        streaminfo = self.instance.metadata[0]
        streaminfo.info.last = True
        metadata = self.instance.metadata[1:]
        self.instance.metadata = [streaminfo]
        return metadata

    def restore_metadata(self, metadata):
        # Append the frozen metadata to the stripped media.
        self.instance.metadata[0].info.last = not len(metadata)
        self.instance.metadata += metadata
