from setuptools import setup
from setuptools import find_packages
from os import path

this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.txt'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='pywindowframes',
    version='0.13',
    packages=find_packages(
        where='pywindowframes_base',
        include=['pywindowframes']),
    package_dir={"pywindowframes_base": "pywindowframes"},
    url='',
    license='MIT',
    author='Anton Filip Melin',
    author_email='antonfilipmelin@gmail.com',
    description='Window-based GUI for pygame 2.x',
    long_description=long_description,
    download_url=""
)
