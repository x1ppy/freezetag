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
            yield BLOCK_TYPES[item.info.block_type], item.size + 4


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


class FuseFile(base.FuseFile):
    def __init__(self, file_path, flags, metadata, file_metadata_info, file_metadata_len, frozen_metadata_len):
        super().__init__(file_path, flags, metadata, file_metadata_info, file_metadata_len, frozen_metadata_len)
        self.file_metadata_len = file_metadata_len
        self.frozen_metadata_len = frozen_metadata_len
        self._metadata_bytes = None

    def metadata_bytes(self):
        if self._metadata_bytes == None:
            self._metadata_bytes = b''.join(MetadataFormat.build(m) for m in self.metadata)
        return self._metadata_bytes

    def read(self, length, offset):
        f = self.file
        buf = b''

        if offset < 42:
            f.seek(0, 0)
            head = f.read(42)
            if head[4] >= 128:
                head = head[0:4] + bytes([head[4] - 128]) + head[5:]
            end = min(42, offset + length)
            buf = head[offset:end]
            length -= len(buf)
            if not length:
                return buf
            offset = 42
        offset -= 42

        metadata_len = self.frozen_metadata_len
        if offset < metadata_len:
            metadata_bytes = self.metadata_bytes()
            end = min(metadata_len, offset + length)
            tmp = metadata_bytes[offset:end]
            length -= len(tmp)
            buf += tmp
            if not length:
                return buf
            offset = metadata_len
        offset -= metadata_len

        offset += 42 + self.file_metadata_len
        f.seek(offset, 0)
        return buf + f.read(length)
