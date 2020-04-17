import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="freezetag",
    version="1.1.1",
    author="x1ppy",
    author_email="",
    packages=['formats'],
    scripts=['freezetag'],
    description="save, strip, and restore file paths and music metadata",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/x1ppy/freezetag",
    python_requires='>=3.6',
    install_requires=[
        "construct",
    ],
)
