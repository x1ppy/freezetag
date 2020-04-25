freezetag
=========

About
-----

`freezetag` is a tool that saves, strips, and restores file paths and music metadata. This metadata is written to a
freezetag file (usually just a few kB) that can transform downloaded music files between different filename/tag states.

Use cases:
1. Freezetags can be generated after a torrent finishes downloading to [freeze](#freeze) the directory state. Later,
   even after moving, retagging, and renaming those files, the original downloaded state can be restored
   ([thawed](#thaw)).

2. Additionally, these freezetags can be [mounted](#mount), allowing retagged music to coexist with the original
   downloaded music files without taking up extra disk space. This means you can retag your music and continue to seed
   in your torrent client from the same set of files. _Have your cake and eat it too!_

3. In the same vein, users can seed torrents between different trackers with just one copy of the music files, even if
   the music has been retagged and renamed between trackers.

4. Freezetags can also be generated for an entire music library *after* the music has been retagged to [back up](#--backup)
   your personal tags. These quick incremental backups will archive your tags and filenames, which can later be restored
   from the original torrents.

Requirements
------------

`freezetag` requires Python 3.5.2 or greater (older versions may technically work, but are untested).

A FUSE implementation must also be installed to use [`freezetag mount`](#mount):
* Windows users can install [WinFsp](https://github.com/billziss-gh/winfsp/releases/latest).
* Mac users can install FUSE for macOS via `brew cask install osxfuse` or
  [manually](https://github.com/osxfuse/osxfuse/releases/latest).
* Linux users can install `fuse2` from their package managers or
  [manually](https://github.com/libfuse/libfuse/releases/tag/fuse-2.9.9).

Installation
------------

    $> pip install git+https://github.com/x1ppy/freezetag

Usage
-----

~~~
usage: freezetag [-h] command ...

Saves, strips, and restores file paths and music metadata.

positional arguments:
  command
    freeze    Save paths and music metadata to a freezetag file.
    thaw      Restore paths and music metadata from a freezetag file.
    mount     Recursively mount a directory and its freezetags.
    shave     Strip metadata from all music files.
    show      Display the contents of a freezetag file.

optional arguments:
  -h, --help  show this help message and exit

Use "freezetag [command] --help" for more information about a command.
~~~

Supported Formats
-----------------

Currently, FLAC and MP3 formats are supported. Vorbis comments are supported for FLAC files, and ID3 tags are supported
for MP3 files.

Note that metadata will be frozen/thawed/shaved for supported music and metadata formats only.

Examples
--------

### `freeze`

Create a freezetag that stores paths and metadata for all files in this directory, saving the freezetag to a file
named F**a**-**b**-**c**.ftag (as described in [Freezetag ID](#freezetag-id)) to this directory:

    $> freezetag freeze

Same as above, except `downloads/Pink Floyd - Dark Side of the Moon (1973 MSFL UDCD 517) - FLAC` is used instead of the
current directory:

    $> freezetag freeze "downloads/Pink Floyd - Dark Side of the Moon (1973 MSFL UDCD 517) - FLAC"

If `--ftag` is passed, the freezetag will be written to that directory instead of the directory being frozen:

    $> freezetag freeze --ftag ~/ftags

Or, if the `--ftag` argument is a file, the freezetag will be explicitly named (`redacted-pink-floyd-the-wall.ftag` in
this case):

    $> freezetag freeze --ftag ~/ftags/redacted-pink-floyd-the-wall.ftag

These examples all freeze a single album's state. With the default usage, it's recommended that each album has its own
freezetag, as shown here. This way, other directories under `downloads` can be added/changed/removed without affecting
the freezetag corresponding to each individual download.

Freezetags are unique for a given group of files with the same metadata, so album-level freezetags can be shared among
users to recreate the exact torrent download state. In fact, if two users independently create freezetags for the same
downloaded directory, the freezetags (and their IDs) will be identical. In theory, trackers could even provide
freezetags alongside download links that match the given releases, and freezetag IDs could be an API-queryable
alternative to torrent info hashes.

#### `--backup`

`freezetag freeze` also includes an incremental backup mode, enabled with the `--backup` flag:

    $> freezetag freeze ~/music --backup

This mode is intended to be used on your top-level music directory, and allows you to export all of your personal tags.
`freezetag thaw` can later be used on the original torrent downloads in your `~/downloads` directory to fully recreate
your personal tagged library.

Unlike the default mode, backup mode writes last modified dates and file sizes to the freezetag. This enables
incremental backups, meaning that the original `freezetag freeze --backup` of your library can take awhile (minutes to
hours depending on the size of your library), but subsequent `freezetag freeze --backup`s can complete in mere seconds.
Only the most recent freezetag will be read for an incremental backup, and if the library is unchanged since the last
backup, a new freezetag will not be created.

Backup freezetags follow a different naming scheme, and will be named F**yyyy**-**MM**-**dd**\_**hh**-**mm**-**ss**.ftag
using the date of creation.

### `thaw`

Restore files in-place in the current directory to the freezetag state, using whatever freezetag is in the current
directory (prompting the user if multiple `.ftag`s exist):

    $> freezetag thaw

Same as above, except `downloads/Pink Floyd - Dark Side of the Moon (1973 MSFL UDCD 517) - FLAC` is used instead of the
current directory:

    $> freezetag thaw "downloads/Pink Floyd - Dark Side of the Moon (1973 MSFL UDCD 517) - FLAC"

For parity with `freeze`, `thaw` supports an `--ftag` flag that searches the given directory for a freezetag instead:

    $> freezetag thaw --ftag ~/ftags

Or, if a freezetag is explicitly passed with `--ftag`, that freezetag will be used to thaw. The following thaws files
in-place in the current directory using the given freezetag:
   
    $> freezetag thaw --ftag ~/ftags/redacted-pink-floyd-the-wall.ftag

By default, `thaw` will thaw files in-place, meaning files and directories will be moved/modified/created to match the
freezetag state. If the `--to` flag is passed, no files will be modified, but will instead be copied and thawed to the
given directory:

    $> freezetag thaw --to ~/out

The thawed files will be written to a subdirectory named according to the `root` directory from the freezetag. The
`root` is the name of the top directory when the files were frozen. So if we freeze a directory and thaw it with `--to`:

    $> cd "downloads/Pink Floyd - Dark Side of the Moon (1973 MSFL UDCD 517) - FLAC"
    $> freezetag freeze
    $> freezetag thaw --to ~/out

This will restore the freezetag state to `~/out/Pink Floyd - Dark Side of the Moon (1973 MSFL UDCD 517) - FLAC`.

As another example, say we regularly make backups of our music library state:

    $> freezetag freeze ~/music --backup --ftag ~/ftags

We could then recover this backed-up state from a directory of downloaded music:

    $> freezetag thaw ~/downloads --to ~ --ftag ~/ftags

This will restore our library from `~/downloads` to `~/music`, keeping `~/downloads` intact.

### `mount`

Recursively mount music files and freezetags in `~/music` to `~/freezefs`:

    $> freezetag mount ~/music ~/freezefs

Music files in `~/music` will appear under `~/freezefs` in their original frozen states (paths and tags) from
corresponding freezetag files found under `~/music`. A file in `~/music` will *not* be mapped to`~/freezefs` if there is
no freezetag matching that file. On the other hand, a file in `~/music` can be mapped to `~/freezefs` multiple times
under different paths (and possibly with different tags) if there are multiple freezetags referring to that same file.

`freezetag mount` enables renamed/retagged music to be seeded without requiring copies on disk. For example, let's say
we download a torrent to `~/downloads/Pink Floyd - Dark Side of the Moon (1973 MSFL UDCD 517) - FLAC`. Assuming our
personal tagged library is stored under `~/music` and mounted as shown above, we can then:
1. Run `freezetag freeze `~/downloads/Pink Floyd - Dark Side of the Moon (1973 MSFL UDCD 517) - FLAC` after the torrent
   finishes.
2. Retag/rename/move the files (e.g., to `~/music/Pink Floyd/Dark Side of the Moon`). Assuming we also move the
   freezetag from step 1 along with it, this will automatically make a new `Pink Floyd - Dark Side of the Moon (1973
   MSFL UDCD 517) - FLAC` directory appear under our mount point (`~/freezefs`).
3. Point our torrent client to seed the files from `~/freezefs/Pink Floyd - Dark Side of the Moon (1973 MSFL UDCD 517) -
   FLAC`.

Ideally, the above steps would be automated by your torrent client/music importer.

Mounts are read-only. Mounts are "live", meaning new files added to the source directory will automatically appear under
the mount point (assuming there's a matching freezetag), and deleted files will automatically disappear. Similarly,
changes in tags or freezetag files will be reflected automatically.

Note: The initial mount may take awhile depending on how large your library is. Mount metadata is cached on disk, so
subsequent mounts should activate in just a few seconds.

### `shave`

Strips all metadata from music files in the current directory:

    $> freezetag shave

Same as above, except `downloads/Pink Floyd - Dark Side of the Moon (1973 MSFL UDCD 517) - FLAC` is used instead of the
current directory:

    $> freezetag shave  "downloads/Pink Floyd - Dark Side of the Moon (1973 MSFL UDCD 517) - FLAC"

`freezetag shave` can be useful if you want to share the "bare" music files. This has the advantage of smaller overall
distribution size (especially if the music contains images), and it allows tags to be shared separately. That is, users
can create and distribute different freezetag files using the same bare music files, and the bare music files will
remain unchanged.

### `show`

Shows the contents of a freezetag file.

    $> freezetag show
    version: 1
    mode:    default
    id:      Fc58e43e83c0487f5-56ddb165-e8a1171b
    root:    Pink Floyd - Dark Side of the Moon (1973 MSFL UDCD 517) - FLAC
    96f5c1b465b263d5090deae5d177df47f0f36efa 01 - Speak To Me.flac
    dbd1dc0c8ad514d9641919bc52c99010f5cf3ad2 02 - Breathe.flac
    65cbc81d99b7ed68125b1652819e5fbec7e7a845 03 - On The Run.flac
    40af1c90071abc0d66dbbfad5be39fac25967b5e 04 - Time.flac
    a9fe89c25630794252aa3fe6b1e8078a4eb2308d 05 - The Great Gig In The Sky.flac
    1a3dfb4396cd1c0ccf7804fc66c0e512b65df65d 06 - Money.flac
    caeaf72fcee0df11c167bea2edffe4f7acbcec72 07 - Us And Them.flac
    3ed0c16c900d8430f470011ba877fbaa15a5f7ef 08 - Any Colour You Like.flac
    fee17fdb47c04037d57094ad14260f20cf8e7a83 09 - Brain Damage.flac
    f3539291afa214e7af868ff9b0f044a372cf9e9b 10 - Eclipse.flac
    25041f6026518a0e0a0aa4df3c5fdfd62f8001ea Pink Floyd - The Dark Side Of The Moon.log
    76e4c8325809583bca447ba2d0e9fdaa4b39fa1e Pink Floyd - The Dark Side Of The Moon.m3u
    15fdc9bc1bbe2646ba3cd076789c805f811f9b10 The Dark Side Of The Moon.cue

You can also use the `--json` flag to get parse-friendly output:

    $> freezetag show --json
    {
      "version": 1,
      "mode": "default",
      "id": "Fc58e43e83c0487f5-56ddb165-e8a1171b",
      "root": "Pink Floyd - Dark Side of the Moon (1973 MSFL UDCD 517) - FLAC",
      "files": [
        {
          "path": "01 - Speak To Me.flac",
          "checksum": "96f5c1b465b263d5090deae5d177df47f0f36efa"
        },
        {
          "path": "02 - Breathe.flac",
          "checksum": "dbd1dc0c8ad514d9641919bc52c99010f5cf3ad2"
        },
        {
          "path": "03 - On The Run.flac",
          "checksum": "65cbc81d99b7ed68125b1652819e5fbec7e7a845"
        },
        ...
      ]
    }

Freezetag ID
------------

By default, the freezetag file will be saved to the processed directory as F**a**-**b**-**c**.ftag, where:
* **a** is a 16-character hex string that uniquely identifies the music
* **b** is an 8-character hex string that uniquely identifies the metadata
* **c** is an 8-character hex string that uniquely identifies the freezetag

While this naming scheme might seem unusual, the uniqueness property lets you quickly see whether two freezetags are
identical simply by comparing their file names:

* The **a** and **b** segments do not change between freezes if any paths change or if any non-music files are modified.
Additionally, the **a** segment doesn't change if the music files are retagged.

* This means if two different .ftag files have the same **a** segment, they represent the same set of raw music. If they
have both the same **a** and **b** segments, they represent the same set of raw music *and* their metadata.

* If all three segments are the same, the two freezetag files are identical. Therefore, running `freezetag freeze` twice
will only result in a single freezetag file being created: since the ID will stay the same, the existing freezetag file
will be replaced on the second invocation.

If you use a custom naming scheme for your freezetags (by passing `--ftag` to `freeze`), the ID can still be found using
`freezetag show`.

Changelog
---------
### [1.2.0] - 2020-04-26
* Added `mount` command
* Refactored modules and API
### [1.1.1] - 2020-04-16
* Fixed `thaw` where multiple copies of the same file are frozen
### [1.1.0] - 2020-04-16
* Added `freeze --backup` for incremental backups
* Added `freeze --ftag` for custom output path
* Fixed `show --json` to properly dump JSON
* In-place `thaw` now deletes processed files immediately to reduce temporary disk usage
* Created safety checks and prompts for `thaw`
* Added `thaw --skip-checks` to allow skipping checks
### [1.0.4] - 2020-04-10
* Don't delete files on thaw if they aren't listed in ftag
### [1.0.3] - 2020-04-09
* Allow `show` to accept .ftag directly
### [1.0.2] - 2020-04-09
* Fixed directory argument parsing
### [1.0.1] - 2020-04-06
* Added selection prompt for multiple freezetags
### [1.0.0] - 2020-04-06
* Initial release

[1.2.0]: https://github.com/x1ppy/freezetag/compare/1.1.1...1.2.0
[1.1.1]: https://github.com/x1ppy/freezetag/compare/1.1.0...1.1.1
[1.1.0]: https://github.com/x1ppy/freezetag/compare/1.0.4...1.1.0
[1.0.4]: https://github.com/x1ppy/freezetag/compare/1.0.3...1.0.4
[1.0.3]: https://github.com/x1ppy/freezetag/compare/1.0.2...1.0.3
[1.0.2]: https://github.com/x1ppy/freezetag/compare/1.0.1...1.0.2
[1.0.1]: https://github.com/x1ppy/freezetag/compare/1.0.0...1.0.1
[1.0.0]: https://github.com/x1ppy/freezetag/releases/tag/1.0.0
