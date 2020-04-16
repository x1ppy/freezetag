freezetag
=========

Installation
------------

    $> pip install git+https://github.com/x1ppy/freezetag

About
-----

`freezetag` is a tool that saves, strips, and restores file paths and music metadata. This metadata information is
written to a freezetag file (usually just a few kB) that can transform downloaded music files between different
filename/tag states.

Potential use cases:
1. Users can automatically generate freezetags when they download a torrent, before they import/rename/retag the music
into their library of choice. Later, if they want to restore the torrent (e.g., to reseed), they can use `freezetag` to
restore the original torrent state. Alternatively, rather than always generating freezetags on their own, users could
share freezetags amongst themselves or via some database.
2. Similarly, users can seed torrents between different trackers using a freezetag file, even if the torrents have been
renamed/retagged.
3. `freezetag` can separate the music from its metadata, letting users share bare, untagged music with a separate
freezetag file. Theoretically, these bare music files could be included in different distributions of the same music
across different trackers, where only the freezetag file would differ.
4. Since bare music files are uniquely identifiable, freezetag IDs could provide an alternative to torrent info hashes.
`freezetag` could theoretically be used to pair tracker releases to users' existing downloads that have already been
retagged and renamed. This would, for instance, allow users to automatically generate
[origin.yaml](https://github.com/x1ppy/gazelle-origin) files for their existing downloads that don't have origin files,
where there would otherwise be no way to link them.

In an ideal distant future, trackers could provide freezetags alongside their corresponding torrent download links, and
they could have an API to query freezetag IDs that would return a specific release (this would be a prerequisite to use
case #4 above).

Usage
-----

~~~
usage: freezetag [-h] command ...

Saves, strips, and restores file paths and music metadata.

positional arguments:
  command
    freeze    Saves paths and music metadata to a freezetag file.
    thaw      Restores paths and music metadata from a freezetag file.
    shave     Strips metadata from all music files.
    show      Displays the contents of a freezetag file.

optional arguments:
  -h, --help  show this help message and exit

Use "freezetag [command] --help" for more information about a command.
~~~

Supported Formats
-----------------

Currently, the following music formats are supported:
* FLAC
* MP3

The following metadata formats are supported:
* Vorbis comments
* ID3

Note that metadata will be frozen/thawed/shaved for supported music formats only. Likewise, only supported metadata
formats will be processed.

Examples
--------

### freeze

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
the freezetag corresponding to each individual download. Freezetags are unique for a given group of files with the same
metadata, so album-level freezetags can be shared among users to recreate the exact torrent download state. In fact, if
two users independently create freezetags for the same downloaded directory, the freezetags (and their IDs) will be
identical.

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

### thaw

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

Another example:

    $> freezetag thaw ~/downloads --to ~/music --ftag ~/backups

This could be used, for instance, if we wanted to recover our personal backed-up tags (i.e., using `freezetag freeze
--backup`) from a directory of downloaded music, using a freezetag saved in `~/backups`.

### shave

Strips all metadata from music files in the current directory:

    $> freezetag shave

Same as above, except `downloads/Pink Floyd - Dark Side of the Moon (1973 MSFL UDCD 517) - FLAC` is used instead of the
current directory:

    $> freezetag shave  "downloads/Pink Floyd - Dark Side of the Moon (1973 MSFL UDCD 517) - FLAC"

`freezetag shave` can be useful if you want to share the "bare" music files. This has the advantage of smaller overall
distribution size (especially if the music contains images), and it allows tags to be shared separately. That is, users
can create and distribute different freezetag files using the same bare music files, and the bare music files will
remain unchanged.

### show

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

The **a** and **b** segments do not change between freezes if any paths change or if any non-music files are modified.
Additionally, the **a** segment doesn't change if the music files are retagged.

This means if two different .ftag files have the same **a** segment, they represent the same set of raw music. If they
have both the same **a** and **b** segments, they represent the same set of raw music *and* their metadata.

If all three segments are the same, the two freezetag files are identical. Therefore, running `freezetag freeze` twice
will only result in a single freezetag file being created: since the ID will stay the same, the existing freezetag file
will be replaced on the second invocation.

Changelog
---------
### [1.1.0] - 2020-04-16
* Added `freeze --backup` for incremental backups
* Added `freeze --ftag` for custom output path
* Fixed `show --json` to properly dump JSON
* In-place now `thaw` deletes processed files immediately to reduce temporary disk usage
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

[1.1.0]: https://github.com/x1ppy/freezetag/compare/1.0.4...1.1.0
[1.0.4]: https://github.com/x1ppy/freezetag/compare/1.0.3...1.0.4
[1.0.3]: https://github.com/x1ppy/freezetag/compare/1.0.2...1.0.3
[1.0.2]: https://github.com/x1ppy/freezetag/compare/1.0.1...1.0.2
[1.0.1]: https://github.com/x1ppy/freezetag/compare/1.0.0...1.0.1
[1.0.0]: https://github.com/x1ppy/freezetag/releases/tag/1.0.0
