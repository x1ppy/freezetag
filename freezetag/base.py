import hashlib
import os
from construct import *
from . import formats


class ParsedFile:
    @staticmethod
    def from_path(path):
        suffix = path.suffix.lower()
        if suffix == '.flac':
            return formats.flac.ParsedFile(path)
        if suffix == '.mp3':
            return formats.mp3.ParsedFile(path)
        return formats.generic.ParsedFile(path)

    def __init__(self, path, format):
        self.path = path
        self.format = format
        self._instance = None

    @property
    def instance(self):
        if not self._instance:
            self._instance = self.parse()
        return self._instance

    def parse(self):
        raise NotImplementedError()

    def strip(self):
        raise NotImplementedError()

    def restore_metadata(self, metadata):
        raise NotImplementedError()

    def checksum(self):
        raise NotImplementedError()


class MusicMetadata:
    @staticmethod
    def from_state(state):
        if state.format == 1:
            return formats.flac.MusicMetadata(state.metadata)
        if state.format == 2:
            return formats.mp3.MusicMetadata(state.metadata)
        return None

    def __init__(self, format, value):
        self.format = format
        self.value = value
        self.size = sum(m[1] for m in self)

    def checksum(self):
        return hashlib.sha1(self.format.build(self.value)).digest()

    def __iter__(self):
        raise NotImplementedError()


class MusicParsedFile(ParsedFile):
    def parse(self):
        instance = self.format.parse_file(self.path)

        # Workaround for https://github.com/construct/construct/issues/852
        instance._io.close()

        return instance

    def checksum(self):
        b = self.format.build(self.instance)
        return hashlib.sha1(b).digest()

    def write(self, path):
        self.format.build_file(self.instance, path)


class FuseFile:
    fh = 0

    @staticmethod
    def from_info(file_path, *args):
        suffix = file_path.suffix.lower()
        if suffix == '.flac':
            return formats.flac.FuseFile(file_path, *args)
        if suffix == '.mp3':
            return formats.mp3.FuseFile(file_path, *args)
        return formats.generic.FuseFile(file_path, *args)

    def __init__(self, file_path, flags, metadata, file_metadata_info, file_metadata_len, frozen_metadata_len):
        self.file = file_path.open('rb')
        self.metadata = metadata
        self.fh = FuseFile.fh
        FuseFile.fh += 1

    def read(self, length, offset):
        raise NotImplementedError()

    def close(self):
        self.file.close()
