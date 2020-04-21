from freezetag import base
from construct import *


class Id3SyncSafeIntAdapter(Adapter):
    def _decode(self, obj, context, path):
        return obj[0]*2097152 + obj[1]*16384 + obj[2]*128 + obj[3]

    def _encode(self, obj, context, path):
        return list(obj >> 7 * i & 0x7f for i in reversed(range(4)))


Id3SyncSafeInt = Id3SyncSafeIntAdapter(Int8ub[4])

Id3v1Format = Struct(
    'signature' / Const(b'TAG'),
    'data' / Bytes(125),
)

Id3v2HeaderFormat = Struct(
    'signature' / OneOf(Bytes(3), [b'ID3', b'3DI']),
    'version_major' / Int8ub,
    'version_rev' / Int8ub,
    'flags' / BitStruct(
        'unsynchronization' / Flag,
        'extended' / Flag,
        'experimental' / Flag,
        'footer' / Flag,
        'unused' / BitsInteger(4)),
    'size' / Id3SyncSafeInt,
)

Id3v2Format = Struct(
    'header' / Id3v2HeaderFormat,
    'extended_header' / If(this.header.flags.extended, Struct(
        'size' / IfThenElse(this._.header.version_major == 3, Int, Id3SyncSafeInt),
        'data' / Bytes(this.header.size))),
    'body' / FixedSized(this.header.size, Struct(
        'frames' / RepeatUntil((this.next == 0 or this.next == None), Struct(
            'id' / PaddedString(4, 'ascii'),
            'size' / IfThenElse(this._._.header.version_major == 3, Int, Id3SyncSafeInt),
            'flags' / Int16ub,
            'data' / Bytes(this.size),
            'next' / Peek(Int8ub),
        )),
        'padding' / GreedyBytes)),
    'footer' / If(this.header.flags.footer, Id3v2HeaderFormat),
)

class FormatAdapter(Adapter):
    def _decode(self, obj, context, path):
        return Struct(
            'id3v2_head' / Optional(Id3v2Format),
            'offset' / Tell,
            'try_id3v1' / Pointer(-128, Optional(RawCopy(Id3v1Format))),
            'try_id3v2' / Pointer(-138 if this.try_id3v1 else -10, Optional(RawCopy(Id3v2HeaderFormat))),
            'audio' / IfThenElse(this.try_id3v2, Bytes(this.try_id3v2.offset1 - this.try_id3v2.size - 10 - this.offset),
                                 IfThenElse(this.try_id3v1, Bytes(this.try_id3v1.offset1 - this.offset), GreedyBytes)),
            'id3v2_tail' / If(this.try_id3v2, Id3v2Format),
            'id3v1' / If(this.try_id3v1, Id3v1Format),
            Terminated,
        ).parse(obj)

    def _encode(self, obj, context, path):
        return Struct(
            'id3v2_head' / Optional(Id3v2Format),
            'audio' / GreedyBytes,
            'id3v2_tail' / Optional(Id3v2Format),
            'id3v1' / Optional(Id3v1Format),
            Terminated,
        ).build(obj)

Format = FormatAdapter(GreedyBytes)

FrozenMetadataFormat = Struct(
    'flags' / BitStruct(
        'has_id3v2_head' / Flag,
        'has_id3v2_tail' / Flag,
        'has_id3v1' / Flag,
        Padding(5),
    ),
    'id3v2_head' / If(this.flags.has_id3v2_head, Id3v2Format),
    'id3v2_tail' / If(this.flags.has_id3v2_tail, Id3v2Format),
    'id3v1' / If(this.flags.has_id3v1, Id3v1Format),
)


class MusicMetadata(base.MusicMetadata):
    def __init__(self, value):
        super().__init__(FrozenMetadataFormat, value)

    def __iter__(self):
        if self.value['flags']['has_id3v2_head']:
            header = self.value['id3v2_head'].header
            yield 'ID3v2.{0}'.format(header.version_major), header.size
        if self.value['flags']['has_id3v2_tail']:
            header = self.value['id3v2_tail'].header
            yield 'ID3v2.{0} (end)'.format(header.version_major), header.size
        if self.value['flags']['has_id3v1']:
            yield 'ID3v1', 128

class ParsedFile(base.MusicParsedFile):
    def __init__(self, path):
        super().__init__(path, Format)

    def strip(self):
        metadata = {
            'flags': {
                'has_id3v2_head': self.instance.id3v2_head != None,
                'has_id3v2_tail': self.instance.id3v2_tail != None,
                'has_id3v1': self.instance.id3v1 != None,
            },
            'id3v2_head': self.instance.id3v2_head,
            'id3v2_tail': self.instance.id3v2_tail,
            'id3v1': self.instance.id3v1,
        }
        self.instance.id3v2_head = None
        self.instance.id3v2_tail = None
        self.instance.id3v1 = None
        return MusicMetadata(metadata)

    def restore_metadata(self, metadata):
        self.instance.id3v2_head = None
        self.instance.id3v2_tail = None
        self.instance.id3v1 = None
        self.instance.id3v2_head = metadata.id3v2_head
        self.instance.id3v2_tail = metadata.id3v2_tail
        self.instance.id3v1 = metadata.id3v1
