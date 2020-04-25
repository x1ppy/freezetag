import hashlib
from construct import *
from freezetag import base


class ParsedFile(base.ParsedFile):
    def __init__(self, path):
        super().__init__(path, None)

    def parse(self):
        with self.path.open('rb') as f:
            return f.read()

    def strip(self):
        return None

    def restore_metadata(self, metadata):
        pass

    def checksum(self):
        return hashlib.sha1(self.instance).digest()


class FuseFile(base.FuseFile):
    def read(self, length, offset):
        self.file.seek(offset, 0)
        return self.file.read(length)
