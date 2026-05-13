# -*- coding: utf-8 -*-
"""Setup module."""
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


def get_requires() -> list:
    """Read requirements.txt."""
    requirements = open("requirements.txt", "r").read()
    return list(filter(lambda x: x != "", requirements.split()))


def read_description() -> str:
    """Read README.md and CHANGELOG.md."""
    try:
        with open("README.md") as r:
            description = "\n"
            description += r.read()
        with open("CHANGELOG.md") as c:
            description += "\n"
            description += c.read()
        return description
    except Exception:
        return '''Minimal cross-platform DNS changer'''


setup(
    name='dnx',
    packages=[
        'dnx', ],
    version='0.1',
    description='Minimal cross-platform DNS changer',
    long_description=read_description(),
    long_description_content_type='text/markdown',
    author='OpenSciLab Development Team',
    author_email='dnx@openscilab.com',
    url='https://github.com/openscilab/dnx',
    download_url='https://github.com/openscilab/dnx/tarball/v0.1',
    keywords="dns network cli cross-platform",
    project_urls={
            'Source': 'https://github.com/openscilab/dnx',
    },
    install_requires=get_requires(),
    python_requires='>=3.7',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: MacOS',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        'Topic :: Internet :: Name Service (DNS)',
        'Topic :: System :: Networking',
        'Topic :: Utilities',
    ],
    license='MIT',
    entry_points={
        'console_scripts': [
            'dnx = dnx.cli:main',
        ]}
)
