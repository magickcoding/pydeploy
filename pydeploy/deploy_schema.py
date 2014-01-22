#encoding:utf-8
"""
deploy.conf配置文件schema.
instance('172.16.0.83', 'goodsapi', 'work')
instance('172.16.0.84', 'goodsapi', 'work', package='gz')
"""
from configdata import ConfigData
CONFIG = {
        'instance' : []
        }
def instance(host, name, user, package=None, **kwargs):
    """ 
    解析出来一个instance.
    instance为 {
       'host' : host
       'name' : name
       'user' : user
       'roles' [role1, role2]
    """
    if 'env' in kwargs:
        raise Exception('env is preserved ')
    one = ConfigData()
    one['host'] = host
    one['name'] = name
    one['user'] = user
    one['package'] = package
    one['roles'] = [] 
    have_role = False
    if 'role' in kwargs:
        role_str = kwargs['role']
        del kwargs['role']
        have_role = True
        role_arr = role_str.split(',')
        for s in role_arr:
            s = s.strip()
            one['roles'].append(s)

    one['args'] = kwargs
    if not have_role:
        one['roles'].append('')
    CONFIG['instance'].append(one)
def role(**kwargs):
    return kwargs
ENV = {
        'instance' : instance, 
        'role' : role,
        '__config' : CONFIG
      }

