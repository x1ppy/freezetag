import hashlib
import os
from construct import *
from freezetag import base


class ParsedFile(base.ParsedFile):
    def __init__(self, path):
        super().__init__(path, None)

    def _make_instance(self):
        with open(self.path, 'rb') as f:
            return f.read()

    def strip(self):
        return None

    def restore_metadata(self, metadata):
        pass

    def checksum(self):
        return hashlib.sha1(self.instance).digest()
