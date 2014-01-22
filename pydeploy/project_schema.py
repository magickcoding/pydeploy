#encoding:utf-8
"""
octopus.prj配置文件schema.
package(name,
        dirs = [('src_dir1, dst_dir'),('src_dir2', 'dst_dir2')],
        files = [(src, dest), (src, dest)],
        tpls = [
        (src, target, 'params'), 
        (src, target, 'params'), 
        ]
        )
        
"""
from configdata import ConfigData
CONFIG = ConfigData({
        'scripts' : {},
        'depends' : {
            'easy_install':[],
            'yum':[],
            'third' : [],
            'component' : [],
            'pylib' :[],
            'phpext' : [],
            },
        'package' : ConfigData({
            'dirs': [],
            'files' : [],
            'tpls' : []
        }),
        'packages' : {}
        })

__REPEAT_CHECK = ConfigData( {
    'easy_install' : {},
    'yum' : {},
    'third' : {},
    'component' : {},
    'pylib' : {},
    'phpext' : {}
    })

def check_repeat(kind, name):
    if name in __REPEAT_CHECK[kind]:
        raise Exception('repeated_%s(%s)' % (kind, name))
    __REPEAT_CHECK[kind][name] = 1

def parse_type(s):
    types=s.split(',')
    results = []
    for t in types:
        t = t.strip()
        if t!='compile' and t!='runtime':
            raise Exception('illegal_type(%s)' % (s))
        results.append(t)
    return results

def depend_easy_install(name, version='', type='runtime'):
    check_repeat('easy_install', name)
    CONFIG.depends['easy_install'].append(ConfigData({
        'name':name,
        'version':version,
        'type':parse_type(type)}))

def depend_yum(name, type='compile,runtime'):
    check_repeat('yum', name)
    CONFIG.depends['yum'].append(ConfigData({
        'name':name,
        'type':parse_type(type)}))

def depend_third(name, type='runtime,compile'):
    """ 依赖第三方的源码安装包或者编译好的zip包
    特征是必须有同名的安装脚本"""
    check_repeat('third', name)
    CONFIG.depends['third'].append(ConfigData({
        'name':name,
        'type':parse_type(type)}))

def depend_component(name, type="compile", version=None ):
    """
    依赖自己开发的模块.
    """
    check_repeat('component', name)
    CONFIG.depends['component'].append(
            ConfigData({
                'name':name,
                'version':version,
                'type':parse_type(type)})
            )
def depend_pylib(name, type="runtime", build_no=None ):
    """
    依赖自己开发的模块.
    """
    check_repeat('pylib', name)
    CONFIG.depends['pylib'].append(
            ConfigData({
                'name':name,
                'build_no':build_no,
                'type':parse_type(type)})
            )

def depend_phpext(name, type="runtime", build_no=None ):
    """
    依赖自己开发的模块.
    """
    check_repeat('phpext', name)
    CONFIG.depends['phpext'].append(
            ConfigData({
                'name':name,
                'build_no':build_no,
                'type':parse_type(type)})
            )

def script(step, cmd, role='', supervise=False, params=''):
    """ 
        supervise: 说明这个命令可以用supervise启动
    """
    if type(step) != str:
        raise ValueError('script, step must be string')
    if type(cmd) != str:
        raise ValueError('script command must be string')
    scripts = CONFIG.get('scripts', {})
    if not step in scripts:
        scripts[step] = {}
    if role in scripts[step]:
        raise ValueError('script(step:%s,role:%s) already specified' % (
            step, role))
    params_arr = []
    for p in params.split(','):
        p = p.strip()
        if p:
            params_arr.append(p)
    scripts[step][role] = {'cmd':cmd, 'supervise':supervise, 'params':params_arr}
def package_dir(src, to):
    CONFIG.package.dirs.append(ConfigData({'src':src, 'to':to}))
def package_file(src, to):
    CONFIG.package.files.append(ConfigData({'src':src, 'to':to}))
def package_tpl(src, to, params):
    p = [ s.strip() for s in  params.split(',')]
    CONFIG.package.tpls.append(ConfigData({'src':src, 'to':to, 'params':p}))
    pass
def package(id='', tpls=None, dirs=None, files=None, extends=None):
    """打包文件"""
    if id in CONFIG.packages:
        raise Exception('')
    p = ConfigData()
    p.id = id
    p.dirs = []
    p.tpls = []
    p.files = []
    p.extends = []
    if dirs:
        for d in dirs:
            p.dirs.append(ConfigData({'src':d[0], 'to':d[1]}))
    if tpls:
        for t in tpls:
            p.tpls.append(ConfigData({'src':t[0], 'to':t[1], 'params':[]}))
    if files:
        for item in files:
            p.files.append(ConfigData({'src':item[0], 'to':item[1]}))

    if extends:
        p.extends = [ s.strip() for s in  extends.split(',')]
    CONFIG.packages[id] = p
    pass

ENV = {
        'script' : script, 
        'depend_easy_install' : depend_easy_install,
        'depend_yum' : depend_yum,
        'depend_third' : depend_third,
        'depend_component' : depend_component,
        'depend_pylib' : depend_pylib,
        'depend_phpext' : depend_phpext,
        'package_dir' : package_dir, 
        'package_file' : package_file,
        'package_tpl' : package_tpl,
        'package' : package,
        '__config' : CONFIG
      }

