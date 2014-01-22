#coding:utf-8
import os
from ftp_util import FtpClient
import pkg_resources
class Artifactory(object):
    def __init__(self, config):
        if config.type != 'ftp':
            raise Exception("unsupported artifactory:" + config.type)
        self.ftp_config = config
        # self.ftp_client = FtpClient(config.host, config.user, config.passwd)
        self.local_cache = os.path.expanduser('~/.octopus/artifactory')
        if not os.path.exists(self.local_cache):
            os.makedirs(self.local_cache)
        pass
    def get_program(self, program, build_no):
        try:
            ftp_client = FtpClient(self.ftp_config.host, self.ftp_config.user,
                    self.ftp_config.passwd)
        except Exception, e:
            raise Exception('failed to connect to %s ' % (self.ftp_config.host))
        ftp_path = 'component/' + program
        if not build_no:
            items = ftp_client.list(ftp_path)
            build_no = 0
            for item in items:
                if int(item) > build_no:
                    build_no = int(item)
        if not build_no:
            raise Exception('get build_no fail')
        program_path = '%s/%d' % (ftp_path, build_no)
        local_path = ((self.local_cache+'/%s/%d') % (
            program, build_no))
        
        ftp_client.download(program_path, local_path)
        return local_path

    def get_third(self, name):
        """
        """
        ftp_client = FtpClient(self.ftp_config.host, self.ftp_config.user,
                self.ftp_config.passwd)
        local_file = self.local_cache + '/' + name
        ftp_client.download('third/'+name, self.local_cache)
        if os.path.isfile(local_file):
            return local_file
        raise Exception("can't get "+name)

    def get_pylib(self, name, build_no):
        """ 
        从本地库下载pylib
        """
        ftp_client = FtpClient(self.ftp_config.host, self.ftp_config.user,
                self.ftp_config.passwd)
        ftp_path = 'pylib/' + name
        if not build_no:
            items = ftp_client.list(ftp_path)
            build_no = 0
            for item in items:
                if int(item) > build_no:
                    build_no = int(item)
        if not build_no:
            raise Exception('get build_no fail')
        program_path = '%s/%d' % (ftp_path, build_no)
        items = ftp_client.list(program_path)
        tar_path = program_path + '/' + items[0]
        local_path = (self.local_cache+'/%s/%d/%s') % (name, build_no, items[0])
        ftp_client.download(tar_path, os.path.dirname(local_path))
        return local_path
    
    def get_phpext(self, name, build_no):
        """ 
        从本地库下载pylib
        """
        ftp_client = FtpClient(self.ftp_config.host, self.ftp_config.user,
                self.ftp_config.passwd)
        ftp_path = 'phpext/' + name
        if not build_no:
            items = ftp_client.list(ftp_path)
            build_no = 0
            for item in items:
                if int(item) > build_no:
                    build_no = int(item)
        if not build_no:
            raise Exception('get build_no fail')
        program_path = '%s/%d' % (ftp_path, build_no)
        items = ftp_client.list(program_path)
        tar_path = program_path + '/' + items[0]
        local_path = (self.local_cache+'/%s/%d/%s') % (name, build_no, items[0])
        ftp_client.download(tar_path, os.path.dirname(local_path))
        return local_path


if __name__ == '__main__':
    from configdata import ConfigData
    cfg = ConfigData()
    cfg.type = 'ftp'
    cfg.host = '192.168.1.157'
    cfg.user = 'prod'
    cfg.passwd = 'prod'
    art = Artifactory(cfg)
    art.get_pylib('tornado')
    art.get_pylib('cc')
    v = pkg_resources.parse_version('2.4.1b1')
    print v
