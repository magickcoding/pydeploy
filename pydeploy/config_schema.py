#encoding:utf-8
class ConfigData(dict):
    def __getattr__(self, name):
        return self[name]
    def __setattr__(self, name, val):
        self[name] = val

CONFIG = ConfigData({
        })
def artifactory(type, host, user, passwd):
    v = ConfigData()
    v.type = type
    v.host = host
    v.user = user
    v.passwd = passwd
    CONFIG.artifactory = v
def easy_install(link, local):
    CONFIG.easy_install = ConfigData({
        'link' : link,
        'local' : local
        })
    CONFIG.easy_install.local = local
def third_source(prefix, build_dir):
    CONFIG.third_source = ConfigData({
        'prefix' : prefix,
        'build_dir' : build_dir
        })

ENV = {
        'artifactory' : artifactory, 
        'easy_install' : easy_install,
        'third_source' : third_source,
        '__config' : CONFIG
      }
if __name__ == '__main__':
    artifactory('ftp', '127.0.0.1', 'haha', 'xx')
    print CONFIG
