import setuptools

with open('README.md', 'r') as fh:
    long_description = fh.read()

setuptools.setup(
    name='locdown',
    version='1.0.0',
    author='Spencer Michaels',
    author_email='spencer@spencermichaels.net',
    description='Fetch audio and metadata from the Library of Congress Jukebox (https://www.loc.gov/jukebox).',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/SpencerMichaels/locdown',
    packages=setuptools.find_packages(),
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    scripts=['bin/locdown'],
    package_data={'locdown': ['resources/DISCLAIMER.txt']},
    include_package_data=True,
)
