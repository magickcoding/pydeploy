#encoding:utf-8
import ftplib, sys, os 
import string
# import define
import metainfo
from fabric.api import local

write_file = lambda filename: open(filename, 'w').write 
getcwd = lambda curwd: curwd == '/' and '/' or (curwd + '/') 
createDir = lambda dirname: not os.path.exists(dirname) and os.makedirs(dirname) 

class FtpClient(ftplib.FTP) :
    def __init__(self, host, user, passwd):
        ftplib.FTP.__init__(self, host, user, passwd, timeout=500)
        self.host = host
        self.user = user
        self.passwd = passwd
        self.ftpurl = 'ftp://%s:%s@%s' % (user, passwd, host)

    def download(self, remote_path, local_path):
        """
        模仿cp -r实现从ftp下载文件. 
        TODO: 改成wget下载:wget --tries=3 --timeout=3 -P goodsapi -nH --cut-dirs=3 -m ftp://prod:prod@192.168.1.157/component/goodsapi/84
        """
        
        if self.isdir(remote_path):
            remote_path += '/'
        local('wget --tries=3 --timeout=4 -P {dir} -nH --cut-dirs={cut_count} -N -r -l inf ftp://{user}:{passwd}@{host}/{remote_path}'.format(
            dir=local_path, remote_path=remote_path,
            cut_count=remote_path.count('/'),
            user=self.user, passwd=self.passwd, host=self.host))
    def list(self, remote_path):
        """
        实现类似ls的功能，返回remote_path下的文件.
        @return [item1, item2, ]
        """
        items = self.nlst(remote_path)
        return [os.path.basename(item) for item in items] 
    def stat(self, path):
        """
        返回文件{'type': 'd|f', 'size':12345}
        """
        raise NotImplementedError('stat not implemented')
       
    def download_file(self, remote_path, local_path):
        """
        local_path存在且是一个目录，拷贝到目录底下

        """
        if os.path.exists(local_path) and os.path.isdir(local_path):
            if not local_path.endswith('/'):
                local_path += '/'
            local_path += os.path.basename(remote_path)
        dir = os.path.dirname(local_path)
        if dir == '':
            dir = '.'
        if not os.path.isdir(dir):
            os.makedirs(dir)
        self.retrbinary('RETR '+ remote_path, write_file(local_path))
        #local('wget %s/%s -O %s' % (self.ftpurl, remote_path, local_path))
        local('wget --tries=3 --timeout=4 -P {dir} -nH ftp://{user}:{passwd}@{host}/{remote}'.format(
            dir=dir, user=self.user, passwd=self.passwd, host=self.host, remote=remote_path))
        pass
    def path_append(self, path, s):
        if path.endswith('/'):
            return path + s
        else:
            return path + '/' + s
    def download_directory(self, remote_path, local_path):
        """
        @remote_path:ftp路径，如goodsapi/2/
        @local_path: 本地路径
        """
        pwd_old = self.pwd()
        self.cwd(remote_path)
        items = self.nlst()
        for item in items:
            print 'process ' + remote_path + '/' + item
            item_path = self.path_append(local_path, item)
            if self.isdir(item):
                if not os.path.exists(item_path):
                    os.makedirs(item_path)
                self.download_directory(item, item_path)
            else:
                item_dir = os.path.dirname(item_path)
                if not os.path.isdir(item_dir):
                    os.makedirs(item_dir)
                self.download_file(item, item_path)
        self.cwd(pwd_old)

    def isdir(self, path) :
        pwd_old = self.pwd()
        try: 
            self.cwd(path)
            self.cwd(pwd_old)
            return True 
        except Exception,e:
            return False 


        
if __name__ == '__main__': 
    #sys.path.append(os.getcwd() + "/" + "build")
    #sys.path.append(os.getcwd())
    #import conf
    #fu = FtpUtil("/home/work") 
    #fu.login()
    #fu.download_alldependency("build")
    #fu.logout()
    ftp = FtpClient('127.0.0.1', 'jenkins', '123456')
    print ftp.list('thirdsrc/curl-7.27.0.tar.gz')
    ftp.download('thirdsrc/curl-7.27.0.build.tpl', './')
    #local('rm -f a')
    # print ret
    # print ftp.size('repos/batchrpc/repos/meilishuo/middleware/batchrpc')

    #fu = FtpUtil("/home/work")
    #fu.login()
    #fu.download_program("test","test",0)
    #fu.logout()

