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
        return '''TODO'''


setup(
    name='TODO',
    packages=[
        'TODO', ],
    version='0.1',
    description='TODO',
    long_description=read_description(),
    long_description_content_type='text/markdown',
    author='TODO Development Team',
    author_email='TODO@openscilab.com',
    url='https://github.com/openscilab/TODO',
    download_url='https://github.com/openscilab/TODO/tarball/v0.1',
    keywords="TODO TODO TODO",
    project_urls={
            'Source': 'https://github.com/openscilab/TODO',
    },
    install_requires=get_requires(),
    python_requires='>=3.7',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Natural Language :: English',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        'Intended Audience :: TODO',
        'Intended Audience :: TODO',
        'Topic :: TODO',
        'Topic :: TODO',
    ],
    license='MIT',
)
