#encoding:utf-8
import os
from setuptools import setup
from pydeploy.metainfo import Metainfo

USER_HOME=os.path.expanduser('~')
def get_version():
    if os.path.exists('METAINFO/build.inf'):
        metainfo = Metainfo()
        metainfo.load('METAINFO/build.inf')
        if metainfo.build_number > 0:
            return "0.1b%d" % (metainfo.build_number)
    return "0.1"
setup(
    name = "pydeploy",
    version = get_version(),
    author = "magickcoding",
    author_email = "xidianwlc@qq.com",
    description = ("ci tools"),
    license = "BSD",
    keywords = "",
    # url = "http://packages.python.org/an_example_pypi_project",
    packages=['pydeploy'],
    # long_description='haha',
    # classifiers=[
    #    "Development Status :: 3 - Alpha",
    #    "Topic :: Utilities",
    #    "License :: OSI Approved :: BSD License",
    #],
    install_requires=['fabric==1.4.3', 'jinja2==2.6', 'pexpect'],
    entry_points={
        'console_scripts': [
            'pydeploy = pydeploy.main:main',
            'cpplint = pydeploy.cpplint:main',
        ]   
    },  
    include_package_data=True,
    data_files = [
        ('config', ['config/pydeploy.conf.default']),
        ('METAINFO', ['METAINFO/build.inf']),

    ]
)
