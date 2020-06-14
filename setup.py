import sys
from setuptools import setup, find_packages

if sys.version_info[0] == 3:
    with open("README.md", "r", encoding="utf-8") as fh:
        long_description = fh.read()
else:
    with open("README.md", "r") as fh:
        long_description = fh.read()

setup(
    name='ipconflict',
    version='0.5.0',
    description='Check for conflicts between network subnets',
    long_description=long_description,
    long_description_content_type="text/markdown",
    author='Federico Giuba',
    author_email='federico.giuba@gmail.com',
    url='https://github.com/fgiuba/ipconflict',
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    packages=find_packages(exclude=['tests*']),
    install_requires=[
        'netaddr', 'py-radix', 'tqdm'
    ],
    entry_points={
        'console_scripts': [
            'ipconflict=ipconflict:main',
        ],
    },
)

