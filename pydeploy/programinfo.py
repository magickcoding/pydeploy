#coding:utf-8

import os
import pyetc
import project_schema
from  metainfo import Metainfo
class ConfigFormatError(Exception):
    def __init__(self, line, msg):
        self.msg = msg
        self.line = line
    def __str__(self):
        return 'config_format_error:'+self.msg + ' '+self.line

def read_deploy(path):
    """
    读取deploy文件中的模块版本信息.
    格式:DEPENDS:repos/meilishuo/middleware/tornado, 1
    """
    depends = {}
    try:
        f = open(path, 'r')
    except IOError:
        return depends
    for line in f:
        line = line.strip()
        if line.startswith('#'):
            continue
        if not line.startswith('DEPENDS'):
            continue
        key, val = line.split(':', 1)
        val = val.strip()
        try:
            mod, build_no = val.split(',')
        except ValueError, e:
            raise ConfigFormatError(line, 'DEPENDS:path,build_no')
        depends[mod] = int(build_no)
    return depends

class ProgramInfo(object):
    def __init__(self, program_path):
        self.depends = {}
        self.load(program_path)
        pass
    def load(self, program_path):
        # 加载依赖信息
        self.path = program_path
        project_file = self.path + '/octopus.prj'
        prj_conf = pyetc.load(project_file, project_schema.ENV)
        self.depends = prj_conf.CONFIG.depends
        self.package = prj_conf.CONFIG.package
        self.packages = prj_conf.CONFIG.packages
        # 从部署信息中加载版本信息.
        deploy_metainfo = self.path + '/METAINFO/deploy.inf'
        module2ver = read_deploy(deploy_metainfo)
        for (mod_name, mod_ver) in module2ver.items():
            if mod_name in self.depends:
                self.depends[mod_name]['build'] = mod_ver
        self.scripts = prj_conf.CONFIG.scripts

        build_metainfo_file = self.path + '/METAINFO/build.inf'
        self.buildmeta = Metainfo()
        if os.path.exists(build_metainfo_file):
            self.buildmeta.load(build_metainfo_file)

    def get_depends(self):
        return self.depends
    def get_scripts(self):
        return self.scripts
    def get_buildmeta(self):
        return self.buildmeta

if __name__ == '__main__':
    pi = ProgramInfo('/home/rick/meilishuo/middleware/goodsapi/trunk')
    print pi.get_depends()
