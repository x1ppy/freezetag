import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="freezetag",
    version="1.2.1",
    author="x1ppy",
    author_email="",
    packages=[
        'freezetag',
        'freezetag.formats',
    ],
    entry_points={
        'console_scripts': [
            'freezetag = freezetag.__main__:main',
        ],
    },
    description="save, strip, and restore file paths and music metadata",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/x1ppy/freezetag",
    python_requires='>=3.5.2',
    install_requires=[
        'appdirs',
        'construct',
        'fusepy',
        'watchdog',
    ],
)
