#encoding:utf-8
import os
import sys
import time
from jinja2 import Template
from fabric.api import env as fabric_env,  put, run, local, settings, cd

# from builder import Builder
# from deployer import Deployer
from svn_util import SVNUtil
from metainfo import Metainfo
from artifactory import  Artifactory
import pyetc
import project_schema
import deploy_schema
import config_schema
from programinfo import ProgramInfo
import getpass
import pyshell




class CITool(object):
    def __init__(self, config_file):
        conf = pyetc.load(config_file, config_schema.ENV)
        self.easy_install = config_schema.ConfigData({
                'local' : '~/.octopus/easy_install/'
                })
        self.third_source = config_schema.ConfigData({
                'prefix' : '~/third',
                'build_dir' : '~/third/source'
                })

        etc = conf.CONFIG
        if etc.has_key('easy_install') :
            self.easy_install = etc.easy_install
        if etc.has_key('third_source'):
            self.third_source = etc.third_source
        #self.artifactory_etc = etc.artifactory
        self.artifactory = Artifactory(etc.artifactory)
    # def __getitem__(self, name):
    #     if name == 'artifactory':
    #         return Artifactory(object.__getitem__(self, 'artifactory_etc'))
    #     else:
    #         return object.__getitem__(self, name)

    def make_package(self, instance, program_info, program_path, deploy_env,
            default_runpath, remote_program_path):
        """将文件打包，方便拷贝. """
        # TODO :打包的时候排除掉.svn文件.
        package = program_info.package
        print 'make_package instance=%s' % (instance)
        if instance['package']:
            package = program_info.packages[instance['package']]
            print 'make_package package=%s' % (package)
            for ext in package.extends:
                ext_package = program_info.packages[ext]
                package.dirs.extend(ext_package.dirs)
                package.files.extend(ext_package.files)
                package.tpls.extend(ext_package.tpls)
            
        current_dir = os.getcwd()
        pkg_file = '%s.tar.gz' % (instance['name'])
        pkg_file_full_path = current_dir + '/' + pkg_file
        os.chdir(program_path)
        local('[ ! -d __instance ] || rm -rf __instance')
        local('mkdir __instance')
        local(' if [ -d METAINFO ] ;then cp -r METAINFO __instance/;fi')
        common_args = instance['args']
        common_args['env'] = deploy_env
        common_args['name'] = instance['name']
        if not 'run_path' in common_args:
            common_args['run_path'] = default_runpath
        for d in package.dirs:
            src = Template(d.src.decode('utf-8')).render(common_args).encode('utf-8')
            local('cp -r %s __instance/%s' % (src, d.to))
        for d in package.files:
            src = Template(d.src.decode('utf-8')).render(common_args).encode('utf-8')
            to_dir = '__instance/' + os.path.dirname(d.to)
            if not os.path.isdir(to_dir):
                print 'mkdir ' , to_dir
                os.makedirs(to_dir)
            local('cp  %s __instance/%s' % (src, d.to))
        print 'start prepare template'
        for d in package.tpls:
            src = Template(d.src.decode('utf-8')).render(common_args).encode('utf-8')
            s = open(src, 'r').read()
            #params = {}
            #for k in d.params:
            #    params[k] = common_args[k]
            out = Template(s.decode('utf-8')).render(common_args)
            target_file = '__instance/'+d.to
            to_dir = os.path.dirname(target_file)
            if not os.path.isdir(to_dir):
                os.makedirs(to_dir)
            local('cp  %s %s' % (src, target_file))
            open(target_file, 'w').write(out.encode('utf-8'))

        role_str = ','.join(instance['roles'])
        local('[ -d __instance/METAINFO ] || mkdir __instance/METAINFO')
        local('echo roles:%s >> __instance/METAINFO/deploy.inf' % (role_str))
        os.chdir('__instance')
        self.create_start_scripts(instance['name'], instance['roles'],
            program_info.get_scripts(), remote_program_path,
            default_runpath, common_args)
        os.chdir(program_path)
        local('echo `pwd` && cd __instance && tar -zcf %s *' % ( pkg_file_full_path))
        local('rm -rf __instance')
        os.chdir(current_dir)
        return pkg_file_full_path


    def deploy(self, program_path, deploy_env):
        """
        @program_path: 程序在本地的地址.
        @env: 要部署环境
        pre-condition:当前工作目录处在要部署的模块下.
        从octopus.prj文件中读取依赖哪些库.
        从METAINFO/deploy.inf中读取依赖的版本，如果没有该文件，则都用最新版本(build号最大的).
        从deploy.conf文件中读取部署到哪里
        拷贝模块自身到目标位置
        拷贝依赖模块到目标位置（这个不好弄，依赖模块的路径怎么设定定?)
        在远程机器上运行setup 脚本
        在本机运行冒烟测试脚本(smoketest)
        """
        print 'start deploy ' + program_path + ', env=' + deploy_env
        REMOTE_PROGRAM_BASE = '~/program'
        REMOTE_RUN_BASE =  '~/service'
        program_info = ProgramInfo(program_path)
        depends = program_info.get_depends()
        build_no = program_info.get_buildmeta().build_number
        scripts = program_info.get_scripts()
        # 读取部署位置文件,将文件拷贝过去.    
        deploy_conf_file = program_path + '/config/%s/deploy.conf' % (deploy_env)
        deploy_conf  = pyetc.load(deploy_conf_file, deploy_schema.ENV)
        instances = deploy_conf.CONFIG['instance']
        for instance in instances:
            instance_name = instance['user'] + '@' + instance['host'] + ':'
            instance_name = instance_name + instance['name']
            fabric_env.host_string = instance['host']
            print '=================start deploy %s =========' % (instance_name)
            fabric_env.user = instance['user']
            # 生成模版文件，打包成tar.gz.
            homedir = CITool.get_homedir(pyshell.remote_shell)
            run_path = REMOTE_RUN_BASE + '/' + instance['name']
            run_path = CITool.normalize_path(run_path, homedir)
            print run_path
            remote_program_path = REMOTE_PROGRAM_BASE + '/' + instance['name']
            if build_no > 0:
                remote_program_path = '%s-%d' % (remote_program_path, build_no)
            else:
                # 如果取不到build号，则取当前时间.
                cur_time = time.strftime('%Y%m%d%H%M%S', time.localtime(time.time()))
                remote_program_path = '%s-%s' % (remote_program_path, cur_time)

            shell_ret = pyshell.remote_shell('if [ -d %s ] ;then exit 1;fi' % (
                            remote_program_path), warn_only=True)
            
            if shell_ret.return_code == 0: 
                # 目录不存在，则重新打包拷贝.
                pkg_file_full_path = self.make_package(instance, program_info,
                    program_path, deploy_env, run_path, remote_program_path)
                run('mkdir -p %s' % (remote_program_path))
                put(pkg_file_full_path, remote_program_path)
                local('rm -f ' + pkg_file_full_path)
                run('cd %s && tar -zxf %s' % (
                    remote_program_path, os.path.basename(pkg_file_full_path)))
            # 安装依赖的模块.
            print '===================<<%s>> start install depends========' % (
                    instance_name)
            self.install_depends(depends, 'runtime', {'host':instance['host'],
                'user':instance['user']})
            # 按顺序执行脚本 install, stop,  switch,  start,check
            # install - 
            print '===================<<%s>> start scripts:install========' % (
                    instance_name)
            try:
                self.run_script(instance, 'install', scripts,
                        remote_program_path, pyshell.remote_shell)
            except Exception, e:
                print 'step=install host=%s program=%s e=%s' % (
                        instance['host'], remote_program_path, e)
                raise e
            print '===================<<%s>> stop ========' % ( instance_name )
            self.stop(run_path)
            # switch - unlink link, ln -s install_path link
            print '===================<<%s>> switch link========' % (
                instance_name)
            run('[ -d %s ] || mkdir -p %s' % (run_path, run_path))
            run(('cd %s ;  if [ -h program_old ]; then mv program_old program_old2;fi;'
                +'  if [ -h program ] ;then  mv program program_old; fi ;'
                +' ln -s %s program') % (
                run_path, remote_program_path))
            # 启动新的
            print '===================<<%s>> start ========' % (
                    instance_name)
            try:
                self.start(run_path)
                # 进行线上检查
                print '===================<<%s>> check ========' % (
                        instance_name)
                self.run_script(instance, 'check', scripts, remote_program_path,
                        run_path)
                # 删除program_old2
                print '===================<<%s>> delete old version ========' % (
                        instance_name)
                ret = pyshell.remote_shell(('cd %s;'
                        +' if [ -h program_old2 ] ;then '
                        +'old2=`readlink program_old2`;'
                        +'old=`readlink program_old`;'
                        +'pp=`readlink program`;'
                        + ' if [ "$old2" = "$old" -o "$old2" = "$pp" ];then rm -f program_old2;'
                        +'else rm -rf $old2 program_old2; fi;fi') % (run_path))
            except Exception,e:
                # 如果失败，回滚.回滚怎么重启老版本的服务？octopus.prj文件中的脚本可能发生了变化.
                # 解决方案1:
                # 1) 脚本不在octopus中配置，必须写死,但是解决不了多role问题
                # 2) 或者重新读远程目录的octopus.prj文件, 仍然解决不了多role问题。
                # 3) 必须生成一个部署meta文件,放在METAINFO/deploy.inf中，将role信息写入
                # 另外依赖库怎么办？需要重新安装一遍吗？
                # 看来最好的办法还是将所有的依赖库都放在自己的目录下.
                # 1.一些第三方库整个维持一个版本(即depend_third每个程序只能有一个版本)
                # 2. 模块下有个lib目录，放依赖的库和程序.
                # 这样回滚的时候只需要修改链接就行.
                print e
                print '===================<<%s>> rollback ========' % (
                        instance_name)
                # stop 正在部署的服务
                self.stop(run_path)
                run(('cd %s ;  if [ -h program_fail ];then old_fail=`readlink program_fail`;pp=`readlink program`;'
                    +' if [ "$old_fail" = "$pp" ];then unlink program_fail; else rm -rf $old_fail program_fail;fi;'
                    +'fi; mv program program_fail; '
                   +'if [ -h program_old ] ; then  mv program_old program; fi;'
                   +'if [ -h program_old2 ];then mv program_old2 program_old; fi') % (run_path))
                # 切换目录,启动老版本的服务
                try:
                    self.start(run_path)
                except Exception, e:
                    print 'rollback faied ,reson=%s' % (e)
                # 抛异常，停止后面的部署.
                raise Exception('%s deploy failed, rollback' % (instance_name))

    def __stop_old(self, name, roles, scripts, program_path, runcmd):
        for role in roles:
            start_script = scripts['start'][role]
            stop_script = scripts['stop'][role]
            start_command = start_script['cmd']
            stop_command = stop_script['cmd']
            if start_script['supervise']:
                supervise_name = 'supervise_%s_%s' % (name, role)
                # if supervise进程存在, 如果进程存在，kill pid
                cmd = 'pid=`ps ux |  grep "supervise %s"|grep -v grep | awk \'{print $2}\'`; for p in $pid ; do kill $p; done' % (
                        supervise_name)
                cmd_result = runcmd(cmd, warn_only=True)
                runcmd('cd %s && %s' % (program_path, stop_command),
                        warn_only=True)
            else:
                # 不用supervise
                runcmd('cd %s && %s' % (program_path, stop_command),
                        warn_only=True)

    def run_script(self, instance, step, scripts, program_path, runcmd):
        print 'run_script:step=%s ' % (step)
        for role in instance['roles']:
            script = scripts.get(step, None)
            if script is None:
                break
            script = script.get(role, None)
            if script is None:
                break
            if 'cmd' in script:
                cmd = script['cmd']
                ret = runcmd('cd %s && %s ' % (program_path, cmd),
                        warn_only=True)
                if ret.return_code != 0:
                    raise Exception('%s fail' % (step))

    def create_start_scripts(self, name, roles, scripts, program_path,
            run_path, common_args):
        """无supervise:stop, start,需要注意start是否会阻塞，如果阻塞，用nohup后台启动.
           有supervise: 脚本如果是非阻塞的则不行, 1) supervise进程已经启动的情况下，stop一下
                         2) supervise进程没有启动的情况下，创建run脚本, nohup supervise 'name' &
        """
        run_path = '~/service/' + name
        start_cmd_tpl = """#!/bin/bash
LOG_PATH={{run_path}}/log
LOG_FILE=$LOG_PATH/{{role}}_octopus.log
[ -d $LOG_PATH ] || mkdir -p $LOG_PATH 
{{cmd}} 
ret=$?
curtime=`date`
echo $curtime finish execute {{role}} start, ret=$ret  >> $LOG_FILE
echo $curtime finish execute {{role}} start, ret=$ret
if [ $ret -ne 0 ]
then
    exit 1
fi
exit 0"""
        stop_cmd_tpl = """#!/bin/bash
LOG_PATH={{run_path}}/log
LOG_FILE=$LOG_PATH/{{role}}_octopus.log
[ -d $LOG_PATH ] || mkdir -p $LOG_PATH 
{{cmd}}
curtime=`date`
echo $curtime finish execute {{role}} stop
echo $curtime finish execute {{role}} stop >> $LOG_FILE """

        SUPERVISE_RUN = """#!/bin/bash
LOG_DIR={{run_path}}/log
LOG_FILE=$LOG_DIR/{{role}}_octopus.log
cd {{program_path}} 
curtime=`date`
echo $curtime `pwd` - supervise start program >> $LOG_FILE
{{cmd}} > /dev/null 2>&1"""

        SUPERVISE_START = """#!/bin/bash
LOG_DIR={{run_path}}/log
LOG_FILE=$LOG_DIR/{{role}}_octopus.log
SUPERVISE_NAME=supervise_{{name}}_{{role}}
[ -d $LOG_DIR ] || mkdir -p $LOG_DIR
cd {{program_path}}
try_count=3
tried=0
ret=1
curtime=`date`
svok $SUPERVISE_NAME
ret=$?
if [ $ret -eq 0 ]
then
    echo $curtime ERROR start supervise already started>> $LOG_FILE
    echo $curtime ERROR start supervise already started
    exit 1
fi

while [ $tried -ne $try_count ]
do
    curtime=`date`
    let tried=$tried+1
    rm -f supervise.log
    nohup supervise $SUPERVISE_NAME > supervise.log 2>&1 &
    supervise_pid=$!
    usleep 500000
    supervise_out=`cat supervise.log`
    svok $SUPERVISE_NAME
    ret=$?
    if [ $ret -ne 0 ]
    then
        echo $curtime ERROR start supervise pid=$supervise_pid svok=fail out=$supervise_out>> $LOG_FILE
        echo $curtime ERROR start supervise pid=$supervise_pid svok=fail out=$supervise_out
    else
        break
    fi
done
if [ $ret -ne 0 ]
then
    exit 1
fi
echo $supervise_pid > {{run_path}}/$SUPERVISE_NAME.pid
echo $curtime start supervise pid=$supervise_pid >> $LOG_FILE
echo $curtime start supervise pid=$supervise_pid
exit 0"""
    
        SUPERVISE_STOP = """#!/bin/bash
LOG_DIR={{run_path}}/log
LOG_FILE=$LOG_DIR/{{role}}_octopus.log
SUPERVISE_NAME=supervise_{{name}}_{{role}}
[ -d $LOG_DIR ] || mkdir -p $LOG_DIR
SUPERVISE_PID_FILE={{run_path}}/$SUPERVISE_NAME.pid
curtime=`date`
pids=`ps ux | grep "supervise $SUPERVISE_NAME" | grep -v grep | awk '{print $2}'`
for pid in $pids
do
    echo kill $pid
    kill $pid
    echo $curtime stop $SUPERVISE_NAME pid=$pid 
    echo $curtime stop $SUPERVISE_NAME pid=$pid >> $LOG_FILE
done
usleep 1000
for pid in $pids
do
    ps -p $pid
    if [ $? -eq 0 ]
    then
        kill -9 $pid
        echo $curtime force stop $SUPERVISE_NAME pid=$pid 
        echo $curtime force stop $SUPERVISE_NAME pid=$pid >> $LOG_FILE
    fi
done
{{cmd}}
echo $curtime stop service cmd={{cmd}}
echo $curtime stop service cmd={{cmd}} >> $LOG_FILE
"""

        local('echo #!/bin/bash > __start_all.sh')
        local('echo #!/bin/bash > __stop_all.sh')
        start_all_cmd = '#!/bin/bash\n'
        stop_all_cmd = '#!/bin/bash\n'

        for role in roles:
            start_script = scripts['start'][role]
            stop_script = scripts['stop'][role]
            start_command = Template(start_script['cmd'].decode('utf-8')).render(
                    common_args).encode('utf-8')
            stop_command = Template(stop_script['cmd'].decode('utf-8')).render(
                    common_args).encode('utf-8')
            if start_script['supervise']:
                supervise_name = 'supervise_%s_%s' % (name, role)
                supervise_start_file = 'supervise_%s_start.sh' % (role)
                supervise_stop_file = 'supervise_%s_stop.sh' % (role)

                cmd = '[ -d {dir} ] || mkdir {dir}'.format(dir=supervise_name)
                local(cmd)
                supervise_run = Template(SUPERVISE_RUN).render(
                        program_path=program_path, run_path=run_path, 
                        role=role, cmd=start_command)
                open(supervise_name+'/run', 'w').write(supervise_run)
                local('chmod +x ' + supervise_name + '/run')
                supervise_start = Template(SUPERVISE_START).render(
                        program_path=program_path, run_path=run_path,
                        role=role, name=name)
                open(supervise_start_file, 'w').write(supervise_start)
                supervise_stop = Template(SUPERVISE_STOP).render(
                        program_path=program_path, run_path=run_path,
                        role=role, name=name, cmd=stop_command)
                open(supervise_stop_file, 'w').write(supervise_stop)
                local('chmod +x ' + supervise_start_file)
                local('chmod +x ' + supervise_stop_file)
                start_all_cmd = start_all_cmd + 'sh %s\nret=$?\nif [ $ret -ne 0 ];then exit 1;fi\n' % (
                        supervise_start_file)
                stop_all_cmd = stop_all_cmd + 'sh %s\n' % (supervise_stop_file)
            else:
                # 不用supervise
                start_file_content = Template(start_cmd_tpl).render(role = role, 
                        run_path = run_path, cmd=start_command)
                open(role+'_start.sh', 'w').write(start_file_content)
                stop_file_content = Template(stop_cmd_tpl).render(role = role, 
                        run_path = run_path, cmd=stop_command)
                open(role+'_stop.sh', 'w').write(stop_file_content)
                start_all_cmd = start_all_cmd + 'sh %s\nret=$?\nif [ $ret -ne 0 ];then exit 1;fi\n' % (
                        role+'_start.sh')
                stop_all_cmd = stop_all_cmd + 'sh %s\n' % (role+'_stop.sh')
            open('__start_all.sh', 'w').write(start_all_cmd)
            open('__stop_all.sh', 'w').write(stop_all_cmd)
            local('chmod +x __start_all.sh')
            local('chmod +x __stop_all.sh')



    def get_program(self, program, build_no = None):
        return self.artifactory.get_program(program, build_no)
    @staticmethod    
    def gen_build_metainfo(work_path, build_no):
        """
        在当前位置下生成METAINFO/
        """
        svn = SVNUtil()
        svn_info = svn.info()
        metainfo = Metainfo()
        metainfo.svn = '%s@%d' % (svn_info['svn'], svn_info['revision'])
        metainfo.build_number = build_no 
        
        if work_path.endswith('/'):
            target_dir = work_path + 'METAINFO/'
        else:
            target_dir = work_path + '/METAINFO/'

        if not os.path.isdir(target_dir):
            os.makedirs(target_dir)
        metainfo.save(target_dir + '/build.inf')
    def gen_depends_install_script(self, depends, output):
        """
        生成用于安装依赖模块的脚本.
        depends: {
                'yum': [{ 'name':name}, {'name':name],
                'easy_install' : [{'name':name, {'version':version}]
                }
        output: 输出文件位置.
        """
        install_depend_file = output
        dir = os.path.dirname(install_depend_file)
        if dir and not os.path.exists(dir):
            os.path.makedirs(dir)
        f = open(install_depend_file, 'w')
        f.write('#!/bin/bash\n')
        for m in depends['yum'].values():
            cmd = 'sudo yum -y install ' + m['name']
            f.write(cmd+'\n')
        for m in depends['easy_install'].values():
            if 'version' in m and m['version']:
                cmd = 'easy_install -U \'%s==%s\'' % (m['name'], m['version'])
            else:
                cmd = 'easy_install ' +  m['name']
            f.write(cmd+'\n')
        f.close()


    @staticmethod
    def parse_zip_filename(file):
        """
        将mysql-5.1.58.tar.gz, mysql-5.1.58.tgz等形式的文件名拆分成
        base=mysql-5.1.58, tar='tar|', zip='gz|tgz'
        """
        last_dot = file.rfind('.')
        if last_dot < 0:
            return (file, '', '')
        zip = file[last_dot+1:]
        if zip.lower() == 'tgz' or zip.lower() == 'zip':
            base = file[0:last_dot]
            tar = ''
            return (base, tar, zip)
        elif zip.lower() != 'gz' and zip.lower() != 'bz2':
            return (file, '', '')
        pre_dot = file.rfind('.', 0, last_dot)
        if pre_dot < 0:
            pre_dot = last_dot
        tar = file[pre_dot+1:last_dot]
        base = file[0:pre_dot]
        return (base, tar, zip)
        
    @staticmethod
    def get_homedir(runcmd):
        ret = runcmd('echo $HOME', capture=True, warn_only=True)
        return ret.stdout.strip()

    @staticmethod
    def normalize_path(path, homedir):
        if path.startswith('~/'):
            path = homedir + path[1:]
        return path

    @staticmethod
    def need_install_by_type(type, depends_type):
        """ 根据安装的type和depends本身的type判断是否要安装"""
        if type=='all':
            return True
        for s in depends_type:
            if type == s:
                return True
        return False
        
    @staticmethod
    def localput(src, dest):
        local('cp -r %s %s' % (src, dest))
    def install_depends(self, depends, type, target = None):
        """
        depends: 从project文件分析得到的.
        type : all, compile, runtime
        target: dict, {'host'=>, 'user'=> }
        """
        # 指定fabric的环境以操纵远程机器.
        user = ''
        if target is None:
            myrun = pyshell.shell
            myput = CITool.localput
            user = getpass.getuser()
        else:
            myrun = pyshell.remote_shell
            myput = put
            fabric_env.host_string = target['host']
            if 'user' in target:
                fabric_env.user = target['user']
                user = target['user']
            else:
                fabric_env.user = ''
                user = getpass.getuser()
        homedir = CITool.get_homedir(myrun)
        prefix = CITool.normalize_path(self.third_source['prefix'], homedir)
        build_dir = CITool.normalize_path(self.third_source['build_dir'], homedir)
        # 使用yum安装软件包, 只有运行时才需要安装.
        if depends['yum']:
            # 防止本地cache没有更新，不能找到安装包.
            myrun('sudo yum makecache --disablerepo=* --enablerepo=mls-pt')
        for m in depends['yum']:
            if CITool.need_install_by_type(type, m.type):
                myrun('sudo yum -y install %s' % ( m.name))

        # 安装第三方包.
        for m in depends['third']:
            if CITool.need_install_by_type(type, m.type):
                self.install_third(m.name, prefix, build_dir, myrun, myput)
        # # 安装thirdlib
        # for m in depends['thirdlib']:
        #     if CITool.need_install_by_type(type, m.type):
        #         self.install_thirdlib(m[0], prefix, build_dir, myrun, myput)
        for m in depends['component']:
            if CITool.need_install_by_type(type, m.type):
                self.install_component(m.name, m.version, './components', myrun)

        # 使用easy_install安装python库.
        for m in depends['easy_install']:
            if CITool.need_install_by_type(type, m.type):
                self.install_easy_install(m.name, m.version, myrun)
        
        for m in depends['pylib']:
            if CITool.need_install_by_type(type, m.type):
                self.install_pylib(m.name, m.build_no, myrun, myput)
        for m in depends['phpext']:
            if CITool.need_install_by_type(type, m.type):
                self.install_phpext(m.name, m.build_no, myrun, myput)

    def install_component(self, path, version, target_dir, runcmd):
        files = self.artifactory.get_program(path, version)
        runcmd(' [ -d %s ] || mkdir -p %s ' % (target_dir, target_dir))
        runcmd(' cp -r %s/* %s' % (files, target_dir))
    def install_easy_install(self, name, version, runcmd):
        ret = runcmd('which easy_install', capture=True)
        if ret.return_code != 0:
            raise Exception('which easy_install return %d' %(ret.return_code))
        cmd = ''
        if ret.stdout.startswith('/usr/'): 
            cmd='sudo easy_install --mls-update '
        else: 
            cmd='easy_install'
        cmd += ' ' + name
        if version:
            cmd += '==' + version
        runcmd(cmd)
    def install_pylib(self, name, build_no, runcmd, myput):
        tarfile = self.artifactory.get_pylib(name, build_no)
        basename = os.path.basename(tarfile)
        target = '~/.octopus/pylib/' + basename
        runcmd('[ -d ~/.octopus/pylib ] || mkdir -p ~/.octopus/pylib')
        myput(tarfile, target)
        self.install_easy_install(target, None, runcmd)
        # runcmd('source ~/.bashrc; easy_install %s' % (target))

    def install_phpext(self, name, build_no, runcmd, myput):
        tarfile = self.artifactory.get_phpext(name, build_no)
        basename = os.path.basename(tarfile)
        build_dir = self.third_source.build_dir
        base, tar, gz = CITool.parse_zip_filename(basename)
        target = build_dir + '/' + basename
        runcmd('[ -d {build_dir} ] || mkdir -p {build_dir}'.format(
            build_dir=build_dir))
        myput(tarfile, target)
        runcmd('cd {build_dir}; tar -zxf {tar_file}; cd {tar_dir}; source ~/.bashrc; phpize; ./configure; make; make install; [ -d {php_ini_d} ] || mkdir {php_ini_d}; cp php.ini {php_ini_d}/{name}.ini' .format(
            build_dir=build_dir, tar_file = basename, tar_dir=base, php_ini_d=self.third_source.prefix+'/etc/php.ini.d', name = name)) 

    def install_third(self, name, prefix, build_dir, runcmd, myput):
        """
        @name 包名，比如curl-7.27.0.tar.gz
        @prefix 安装位置,比如~/third
        @build_dir 源码拷贝到哪里
        @runcmd 运行命令的函数，要么local, 要么run，主要为了统一本地和远程
        """
        base, tar, zip  = CITool.parse_zip_filename(name)
        script_name = base + '.sh'
        local_script = self.artifactory.get_third(script_name)
        runcmd(' [ -d %s ] || mkdir -p %s ' % (prefix, prefix))
        runcmd(' [ -d %s ] || mkdir -p %s ' % (build_dir, build_dir))
        myput(local_script, build_dir)
        print 'start check ' + name 
        ret = runcmd('cd %s && sh %s check' % (build_dir, script_name),
                warn_only=True)
        if ret.return_code == 0:
            print name + ' has installed'
            return 0

        local_pkg = self.artifactory.get_third(name)
        myput(local_pkg, build_dir)
        runcmd('cd %s && sh %s install -p %s -s %s ' % (
            build_dir,  script_name, prefix, name ))


        

    def start(self, run_path):
        # 启动新的服务.
        cmd = 'cd %s; cd program;  sh __start_all.sh'  % (run_path)
        ret = pyshell.remote_shell(cmd, warn_only=True)
        if ret.return_code != 0:
            raise Exception('start failed')

    def stop(self, run_path):
        cmd = 'cd %s; if [ -d program ] ;then cd program;  sh __stop_all.sh; fi'  % (
                run_path)
        ret = pyshell.remote_shell(cmd, warn_only=True)






    

if __name__ == '__main__':
    citool = CITool('/home/rick/.octopus/octopus.conf')
    citool.install_octopus('192.168.56.102', 'work')


