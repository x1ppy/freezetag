freezetag
=========

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
    freeze    Saves paths and music metadata in directory to a freezetag file.
    thaw      Restores paths and music metdata in directory from a freezetag file.
    shave     Strips metadata from all music files in directory.
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

First, let's prepare a minimal music set:

    $> mkdir beethoven-example && cd beethoven-example
    $> wget https://www.mfiles.co.uk/mp3-downloads/Beethoven-Symphony5-1.mp3
    $> wget https://www.mfiles.co.uk/mp3-downloads/fur-elise.mp3
    $> wget https://www.mfiles.co.uk/mp3-downloads/sugar-plum-fairy.mp3

and check the tags:

    $> id3ted -l *
    Beethoven-Symphony5-1.mp3
    ID3v1:
    Title  : Symphony No.5 - 1st movement    Track: 0
    Artist : Ludwig van Beethoven            Year :
    Album  : www.mfiles.co.uk                Genre: Classical (32)
    Comment: © Music Files Ltd

    fur-elise.mp3:
    ID3v1:
    Title  : Fur Elise (album leaf) - Piano  Track: 0
    Artist : Ludwig van Beethoven            Year :
    Album  : www.mfiles.co.uk                Genre: Classical (32)
    Comment: © Music Files Ltd

    sugar-plum-fairy.mp3:
    ID3v1:
    Title  : Sugar Plum Fairy (Nutcracker)   Track: 0
    Artist : Peter Tchaikovsky               Year :
    Album  : www.mfiles.co.uk                Genre: Classical (32)
    Comment: © Music Files Ltd

### freeze

To kick things off, run `freezetag freeze`:

    $> freezetag freeze
    455d965a07357826e76118a3c84ffbac0463fde0 Beethoven-Symphony5-1.mp3
    6f860819575aa0bef153b9d1477030bb9f91d27d fur-elise.mp3
    6fa39dfda7512e26a6dca13579a7739279e1d193 sugar-plum-fairy.mp3
    freezetag created at /home/x1ppy/beethoven-example/Ff347f70000e23124-863f2c3d-2675d4d7.ftag

If you check the contents of the directory, nothing has changed other than the new file
`Ff347f70000e23124-863f2c3d-2675d4d7.ftag`.

### thaw

Now, let's make things interesting by modifying our files:

    $> mv Beethoven-Symphony5-1.mp3 01-symphany.mp3
    $> mv fur-elise.mp3 02-fur-elise.mp3
    $> mv sugar-plum-fairy.mp3 03-sugar-plum-fairy.mp3
    $> id3ted 01-symphany.mp3 -A "Custom Album" -y 1808 -T 1
    $> id3ted 02-fur-elise.mp3 -A "Custom Album" -y 1808 -T 2
    $> id3ted 03-sugar-plum-fairy.mp3 -A "Custom Album" -y 1808 -T 3

and checking the tags again:

    $> id3ted -l *
    01-symphany.mp3:
    ID3v1:
    Title  : Symphony No.5 - 1st movement    Track: 1
    Artist : Ludwig van Beethoven            Year : 1808
    Album  : Custom Album                    Genre: Classical (32)
    Comment: © Music Files Ltd

    02-fur-elise.mp3:
    ID3v1:
    Title  : Fur Elise (album leaf) - Piano  Track: 2
    Artist : Ludwig van Beethoven            Year : 1808
    Album  : Custom Album                    Genre: Classical (32)
    Comment: © Music Files Ltd

    03-sugar-plum-fairy.mp3:
    ID3v1:
    Title  : Sugar Plum Fairy (Nutcracker)   Track: 3
    Artist : Peter Tchaikovsky               Year : 1808
    Album  : Custom Album                    Genre: Classical (32)
    Comment: © Music Files Ltd

At this point, we've renamed and retagged our album -- all standard stuff in the music world. At this point, our
original tags and filenames are long gone, so if we wanted to reset the tags and filenames (to share with others, for
example), we'd have to redownload the original files again. Or do we?

Let's run `freezetag thaw`:

    $> freezetag thaw
    455d965a07357826e76118a3c84ffbac0463fde0 Beethoven-Symphony5-1.mp3
        thawing /home/x1ppy/beethoven-example/01-symphany.mp3
    6f860819575aa0bef153b9d1477030bb9f91d27d fur-elise.mp3
        thawing /home/x1ppy/beethoven-example/02-fur-elise.mp3
    6fa39dfda7512e26a6dca13579a7739279e1d193 sugar-plum-fairy.mp3
        thawing /home/x1ppy/beethoven-example/03-sugar-plum-fairy.mp3

Now, if we list the directory contents, we see that the files are back to their original names:

    $> ls
    Beethoven-Symphony5-1.mp3  Ff347f70000e23124-863f2c3d-2675d4d7.ftag  fur-elise.mp3  sugar-plum-fairy.mp3

And if we check the tags one last time:

    $> id3ted -l *
    Beethoven-Symphony5-1.mp3:
    ID3v1:
    Title  : Symphony No.5 - 1st movement    Track: 0
    Artist : Ludwig van Beethoven            Year :
    Album  : www.mfiles.co.uk                Genre: Classical (32)
    Comment: © Music Files Ltd

    fur-elise.mp3:
    ID3v1:
    Title  : Fur Elise (album leaf) - Piano  Track: 0
    Artist : Ludwig van Beethoven            Year :
    Album  : www.mfiles.co.uk                Genre: Classical (32)
    Comment: © Music Files Ltd

    sugar-plum-fairy.mp3:
    ID3v1:
    Title  : Sugar Plum Fairy (Nutcracker)   Track: 0
    Artist : Peter Tchaikovsky               Year :
    Album  : www.mfiles.co.uk                Genre: Classical (32)
    Comment: © Music Files Ltd

we see that everything is back to its original, untouched state.

### shave

Strips all metadata from music files in the directory.

Before:

    $> id3ted -l *
    Beethoven-Symphony5-1.mp3:
    ID3v1:
    Title  : Symphony No.5 - 1st movement    Track: 0
    Artist : Ludwig van Beethoven            Year :
    Album  : www.mfiles.co.uk                Genre: Classical (32)
    Comment: © Music Files Ltd

    fur-elise.mp3:
    ID3v1:
    Title  : Fur Elise (album leaf) - Piano  Track: 0
    Artist : Ludwig van Beethoven            Year :
    Album  : www.mfiles.co.uk                Genre: Classical (32)
    Comment: © Music Files Ltd

    sugar-plum-fairy.mp3:
    ID3v1:
    Title  : Sugar Plum Fairy (Nutcracker)   Track: 0
    Artist : Peter Tchaikovsky               Year :
    Album  : www.mfiles.co.uk                Genre: Classical (32)
    Comment: © Music Files Ltd

After:

    $> freezetag shave
    Beethoven-Symphony5-1.mp3
        shaved ID3v1 (128)
    fur-elise.mp3
        shaved ID3v1 (128)
    sugar-plum-fairy.mp3
        shaved ID3v1 (128)
    $> id3ted -l *
    (no output)

`freezetag shave` can be useful if you want to share the "bare" music files. This has the advantage of smaller overall
distribution size (especially if the music contains images), and it also has the advantage of separation of concerns.
That is, users can create and distribute their own freezetag files with bare music files, and the bare music files will
remain unchanged.

### show

Shows the contents of a freezetag file.

    $> freezetag show
    version: 1
    id:      Ff347f70000e23124-863f2c3d-2675d4d7
    root:    beethoven-example
    455d965a07357826e76118a3c84ffbac0463fde0 Beethoven-Symphony5-1.mp3
    6f860819575aa0bef153b9d1477030bb9f91d27d fur-elise.mp3
    6fa39dfda7512e26a6dca13579a7739279e1d193 sugar-plum-fairy.mp3

You can also use the `--json` flag to get parse-friendly output:

    $> freezetag show --json
    {'files': [{'checksum': '455d965a07357826e76118a3c84ffbac0463fde0',
                'path': 'Beethoven-Symphony5-1.mp3'},
               {'checksum': '6f860819575aa0bef153b9d1477030bb9f91d27d',
                'path': 'fur-elise.mp3'},
               {'checksum': '6fa39dfda7512e26a6dca13579a7739279e1d193',
                'path': 'sugar-plum-fairy.mp3'}],
     'id': 'Ff347f70000e23124-863f2c3d-2675d4d7',
     'root': 'beethoven-example',
     'version': 1}

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

[1.0.5]: https://github.com/x1ppy/freezetag/compare/1.0.4...1.1.0
[1.0.4]: https://github.com/x1ppy/freezetag/compare/1.0.3...1.0.4
[1.0.3]: https://github.com/x1ppy/freezetag/compare/1.0.2...1.0.3
[1.0.2]: https://github.com/x1ppy/freezetag/compare/1.0.1...1.0.2
[1.0.1]: https://github.com/x1ppy/freezetag/compare/1.0.0...1.0.1
[1.0.0]: https://github.com/x1ppy/freezetag/releases/tag/1.0.0
