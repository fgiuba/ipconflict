from setuptools import setup, find_packages


setup(
    name='ipconflict',
    version='0.3.0',
    description='Check for conflicts between network subnets',
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
    packages=find_packages(),
    install_requires=[
        'netaddr==0.7.19',
    ],
    entry_points={
        'console_scripts': [
            'ipconflict=ipconflict:main',
        ],
    },
)
