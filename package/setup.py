from setuptools import setup, find_packages
import os


def get_file_content(file_name):
    with open(file_name) as f:
        return f.read()

setup(
    name='cloudshell-octopus-deploy',
    version='4.1.55',
    description="Orchestrate Octopus Deploy releases through Cloudshell",
    long_description="Orchestrate Octopus Deploy releases through Cloudshell",
    author="Nahum Timerman",
    author_email='ntimerman@gmail.com',
    url='https://github.com/QualiSystems/cloudshell-octopus-deploy',
    packages=['cloudshell', 'cloudshell.octopus'],
    package_data={'': ['requirements.txt']},
    include_package_data=True,
    install_requires=get_file_content('requirements.txt'),
    license="Apache Software License 2.0",
    zip_safe=False,
    keywords='cloudshell quali sandbox cloud octopus deploy')
