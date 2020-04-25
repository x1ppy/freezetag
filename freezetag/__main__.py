#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path
from . import commands


def parse_args():
    parent = argparse.ArgumentParser(add_help=False)
    main = argparse.ArgumentParser(parents=[parent],
        epilog='Use "freezetag [command] --help" for more information about a command.',
        description='Saves, strips, and restores file paths and music metadata.',
        formatter_class=argparse.RawTextHelpFormatter)
    sub = main.add_subparsers(metavar='command', dest='command')
    sub.required = True

    def add_subparser(command, help, description=''):
        return sub.add_parser(command, help=help, description=help + description,
                              formatter_class=argparse.RawTextHelpFormatter, parents=[parent])

    freeze = add_subparser('freeze',
            'Save paths and music metadata to a freezetag file.',
        '\n\nMusic files with supported extensions (.mp3, .flac) will have their metadata'
          '\nsaved in the .ftag file. All files will have their paths saved in the .ftag'
          '\nfile. Metadata and path state can be restored using "freezetag thaw".'
        '\n\nThe freezetag file will be saved in `directory`. Unless --backup is used, the'
          '\nfreezetag file will be named Fa-b-c.ftag, where:'
          '\n  a is a 16-character segment that uniquely identifies the music'
          '\n  b is an 8-character segment that uniquely identifies the metadata'
          '\n  c is an 8-character segment that uniquely identifies the freezetag'
        '\n\nThe "a" and "b" segments do not change between freezes if any paths change or'
          '\nif any non-music files are modified. Additionally, the "a" segment doesn\'t'
          '\nchange if the music files are retagged.'
        '\n\nThis means if two different .ftag files have the same "a" segment, they'
          '\nrepresent the same set of raw music. If they have both the same "a" and "b"'
          '\nsegments, they represent the same set of raw music AND their metadata.'
    )

    thaw = add_subparser('thaw', 'Restore paths and music metadata from a freezetag file.',
        '\n\nBy default, the files will be renamed and restored in-place inside `directory`.'
           '\nNote that `directory` itself will be renamed to the "root" saved in the'
           '\nfreezetag file.'
           '\n\nIf --to is used, files will instead be copied and restored to a subdirectory'
           '\n(named "root" from the freezetag file) under the `to` directory, leaving the'
           '\nfiles in the source `directory` untouched.')

    mount = add_subparser('mount',
        help='Recursively mount a directory and its freezetags.')
    mount.add_argument('directory',
        help='Directory to mount.'
         '\n\nThis directory will be scanned for freezetags and matching files. Any matches'
           '\nwill then be mounted as their original state under `mount_point`.'
        '\n\nMounts are read-only. Mounts are "live", meaning new files added to the source'
          '\ndirectory will automatically appear under the mount point (assuming there\'s a'
          '\nmatching freezetag), and deleted files will automatically disappear. Similarly,'
          '\nchanges in tags or freezetag files will be reflected automatically.'
        '\n\nNote: The initial mount may take awhile depending on how large your library is.'
          '\nMount metadata is cached on disk, so subsequent mounts should activate in just'
          '\na few seconds.')
    mount.add_argument('--verbose', '-v', action='store_true', help='Verbose mode.')
    mount.add_argument('mount_point', help='Mount destination.')

    shave = add_subparser('shave', 'Strip metadata from all music files.',
            '\n\nOnly music files with supported extensions (.mp3, .flac) will be modified,'
              '\nand only supported metadata (Vorbis comments, ID3) will be stripped.')

    show = add_subparser('show', 'Display the contents of a freezetag file.')

    for parser in [freeze, thaw, shave]:
        parser.add_argument('directory', nargs='?', default=Path.cwd(),
            help='Directory to process (default: current directory).')

    show.add_argument('path', nargs='?', metavar='path', default=Path.cwd(),
        help='Directory containing .ftag file, or the .ftag file itself\n'
             '(default: current directory)')
    show.add_argument('--json', action='store_true', help='Prints JSON output.')

    thaw.add_argument('--ftag', metavar='path',
        help='Path to Freezetag file to use.'
         '\n\nIf path is a directory, the .ftag in this directory will be'
           '\nused. Otherwise, path must be an .ftag file that will be used'
           '\nto thaw.'
         '\n\nIf --ftag is not specified, the .ftag in `directory` will be'
           '\nused.')
    thaw.add_argument('--to', metavar='directory',
        help='Directory to which thawed files will be copied and restored.'
           '\nIf omitted, files will be renamed and restored in-place.')
    thaw.add_argument('--skip-checks', action='store_true',
        help='Skips safety checks.'
         '\n\nBy default, thaw verifies that (1) all music files in the'
           '\nfreezetag are in `directory`, and (2) `directory` doesn\'t'
           '\ncontain unrecognized files when the common music path doesn\'t'
           '\nmatch `directory`. The user will be prompted if either of'
           '\nthese conditions is not met.'
         '\n\nThese checks help prevent unintentional file/directory changes'
           '\nif thaw is called with the wrong `directory`; however, the'
           '\nthaw will take longer and requires user interaction for prompts.'
           '\nPass --skip-checks to disable these checks.')

    freeze.add_argument('--backup', action='store_true',
        help='Freeze in incremental backup mode.'
        '\n\nThis mode is optimized for repeated incremental backups of the'
          '\nsame directory.'
        '\n\nIn backup mode, the freezetag file will be saved as'
          '\nFyyyy-MM-dd_hh-mm-ss.ftag. File sizes and last modified times'
          '\nwill be written to the freezetag file. On subsequent incremental'
          '\nbackups, the last created freezetag in this directory will be'
          '\nread. Any files whose names haven\'t changed will not have their'
          '\nhashes recalculated, making the freeze operation significantly'
          '\nfaster.')
    freeze.add_argument('--ftag', metavar='path',
        help='Path to output freezetag file.'
        '\n\nIf path is a directory, the freezetag file will be written to'
          '\nthis directory, following the naming specifications outlined'
          '\nabove. Otherwise, the freezetag file will be named and saved'
          '\naccording to the given path.'
       '\n\nIf --ftag is not specified, the freezetag file will be written'
         '\nto `directory`.')

    return main.parse_args()


def main():
    try:
        args = parse_args()
        getattr(commands, args.command)(**vars(args))
    except commands.CommandException as e:
        print(e, file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
