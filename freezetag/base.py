import hashlib
import os
from freezetag import formats
from construct import *


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
            self._instance = self._make_instance()
        return self._instance

    def _make_instance(self):
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

    def checksum(self):
        return hashlib.sha1(self.format.build(self.value)).digest()

    def __iter__(self):
        raise NotImplementedError()


class MusicParsedFile(ParsedFile):
    def _make_instance(self):
        instance = self.format.parse_file(self.path)

        # Workaround for https://github.com/construct/construct/issues/852
        instance._io.close()

        return instance

    def checksum(self):
        b = self.format.build(self.instance)
        return hashlib.sha1(b).digest()

    def write(self, path):
        self.format.build_file(self.instance, path)
