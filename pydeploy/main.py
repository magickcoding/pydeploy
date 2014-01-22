#!encoding:utf-8

import sys
import os
import time
import argparse
import getpass
from octopus import CITool
import pyetc
import project_schema
import deploy_schema
from fabric.api import env as fabric_env,  put, run, local, settings
from jinja2 import Template
import pyshell
from programinfo import ProgramInfo
from cpplint2cppcheck import CpplintConverter
import sshutil
import pexpect
def line_is_comment(line):
    if line.startswith('#') or line.startswith('//') or line.startswith(';'):
        return True
    return False
def change_passwd(host, username, passwd):
    cmd = 'ssh -t ' + host +  ' "sudo passwd {username}"'
    cmd = cmd.format(username = username)
    c = pexpect.spawn(cmd)
    c.expect('New UNIX password:')
    print c.before
    c.sendline(passwd)
    c.expect('Retype new UNIX password:')
    print c.before
    c.sendline(passwd)
    c.expect(pexpect.EOF)
    print c.before
    print c.exitstatus

def set_user(host, user):
    """ 添加或者修改用户信息"""
    cmd = 'ssh -t {host} "sudo /usr/sbin/useradd {name}"'.format(
            host=host, name=user['name'])
    pyshell.shell(cmd)
    if user['passwd']:
        change_passwd(host, user['name'], user['passwd'])
    cmd_add_group = 'sudo /usr/sbin/groupadd {group}; sudo /usr/sbin/usermod -a -G {group} {name};'
    cmd = ''
    if user['groups']:
        for group in user['groups']:
            cmd = cmd + cmd_add_group.format(group = group, name=user['name'])
        cmd = 'ssh -t  {host} "' + cmd + '"'
        cmd = cmd.format(host = host)
        pyshell.shell(cmd)

def parse_fileop(line, fileops):
    parts = line.split('=>')
    if len(parts) != 2:
        raise Exception('fileop_format:src=>dst:mask content='+line)
    src = parts[0].strip()
    dst_info = parts[1].split(':')
    if len(dst_info) == 1:
        dst = dst_info[0].strip()
        mode  = 0
    elif len(dst_info) == 2:
        dst = dst_info[0].strip()
        mode = int(dst_info[1].strip(), 8)
    else:
        raise Exception('fileop_format:src=>dst:mask content='+line)
    fileops.append({'src':src, 'dst':dst, 'mode':mode})

def parse_user(line, users):
    (name, passwd, groups) = line.split(':')
    if users.has_key(name):
        raise Exception('duplicated_user name='+name)
    group_list = []
    for g in groups.split(','):
        if g:
            group_list.append(g)
    users[name] = {'name' : name, 'passwd' : passwd, 
            'groups' : group_list}
def read_host(files, hosts):
    if not files is None:
        for file in files:
            fd = open(file, 'r')
            for line in fd:
                line=line.strip()
                if line_is_comment(line):
                    continue
                hosts.append(line)
            fd.close()


def gen_build_metainfo(argv, prog='octopus'):
    argparser = argparse.ArgumentParser(
            description="octopus gen_build_metainfo", prog=prog)
    argparser.add_argument('--build-no', dest='build_no',
        help='build', type=int, default=0)
    args = argparser.parse_args(argv)
    CITool.gen_build_metainfo('./', args.build_no)



def get_program(args):
    """
    获取程序
    """
    build_no = args.build_no
    path = args.program
    citool = CITool()
    path = citool.get_program(program, build_no)
    local('cp -r path ./' + program)

def get_config_file(config_file):
    if not config_file is None:
        return config_file
    conf_path = os.path.abspath(
             os.path.dirname(os.path.abspath(__file__))
             + '/../config/octopus.conf.default')
    lookup_path = ['./octopus.conf', '~/.octopus/octopus.conf',
            '/etc/octopus.conf', conf_path] 
    for path in lookup_path:
        path = os.path.expanduser(path)
        if os.path.exists(path):
            return path
    return None

def install_depends(argv, prog):
    """
    安装程序需要的依赖(假定是在当前目录下获取octopus.prj,用处是帮助在本地搭建环境)
    """
    argparser = argparse.ArgumentParser(description="octopus install_depends", prog=prog)
    argparser.add_argument('-c', '--conf', dest='config_file',
        help='octopus配置文件路径, 寻找优先级为./octopus.conf > ~/.octopus/octopus.conf')
    argparser.add_argument('-t', '--type', dest='type',default='all',
        help='要安装的依赖类型，取值为compile, runtime, all')
    args = argparser.parse_args(argv)
    config_file = get_config_file(args.config_file)
    print 'use config ' + config_file
    if config_file is None:
        print "please specift config file"
        return 1
    if args.type != 'compile' and args.type != 'runtime' and args.type != 'all':
        print 'wrong type, must be [compile, runtime, all]'
        return 1
    citool = CITool(config_file)
    program_path = '.'
    program_info  = ProgramInfo(program_path)
    citool.install_depends(program_info.get_depends(), args.type)


def deploy(argv, prog='octopus'):
    argparser = argparse.ArgumentParser(description="octopus deploy", prog=prog)
    argparser.add_argument('-c', '--conf', dest='config_file',
        help='octopus配置文件路径, 寻找优先级为./octopus.conf > ~/.octopus/octopus.conf')
    argparser.add_argument('--build-no', dest='build_no',
        help='build', type=int, default=0)
    argparser.add_argument(
            '--program', dest='program', help='要部署的程序')
    argparser.add_argument(
            '--env', dest='env', help='部署环境',  default='test')
    args = argparser.parse_args(argv)
    config_file = get_config_file(args.config_file)
    if config_file is None:
        print "please specift config file"
        return 1
    citool = CITool(config_file)
    # 如果指定了program ,先下载program.
    program_path = '.'
    if args.program:
        program_path = citool.get_program(args.program, args.build_no)
    program_path = os.path.abspath(program_path)
    print 'start deploy ' + program_path + ', env=' + args.env
    citool.deploy(program_path, args.env)

def show_usage(argv, prog):
    for (name, cmd) in COMMANDS.items():
        print name, cmd[1]
    

def gen_conf(argv, prog):
    argparser = argparse.ArgumentParser(description="octopus ", prog=prog)
    argparser.add_argument('-t', '--tpl', dest='tpl',
        help='输入的模版文件', required=True)
    argparser.add_argument('-o', '--output',  dest='output',
        help='输出文件路径', required=True)
    argparser.add_argument(
            'params', metavar='N', nargs='*',
            help='模版参数')
    args = argparser.parse_args(argv)
    if not os.path.exists(args.tpl):
        print args.tpl + ' not exist'
        sys.exit(1)
    s = open(args.tpl, 'r').read()
    params = {}
    for p in args.params:
        (k,v) = p.split('=')
        params[k] = v
    out = Template(s.decode('utf-8')).render(params)
    open(args.output, 'w').write(out.encode('utf-8'))

def cpplint2cppcheck(argv, prog):
    argparser = argparse.ArgumentParser(description="octopus ", prog=prog)
    argparser.add_argument('-i', '--input',  dest='input',
        help='输入cpplint结果文件', required=True)
    argparser.add_argument('-o', '--output',  dest='output',
        help='输出cppcheck文件', required=True)
    args = argparser.parse_args(argv)
    converter = CpplintConverter()
    converter.parse(args.input)
    converter.write(args.output)
def check_cpp(argv, prog):
    CMD_TPL1='for d in {{dirs}};do find $d -name "*.cc" -o -name "*.cpp" -o -name "*.h" -o -name "*.hpp" -o -name "*.c" | xargs -I {} cpplint {}; done' 
    CMD_TPL2='for d in {{dirs}};do find $d -name "*.cc" -o -name "*.cpp" -o -name "*.h" -o -name "*.hpp" -o -name "*.c" | xargs -I {} cpplint {} >> {{out}}/cpplint.txt 2>&1;done'

    argparser = argparse.ArgumentParser(description="octopus ", prog=prog)
    argparser.add_argument('-o',  dest='output_dir',
        help='文件输出目录', default='')
    argparser.add_argument(
            'dirs', metavar='N', nargs='*',
            help='要检查的目录')

    args = argparser.parse_args(argv)
    if args.output_dir:
        local('[ -d {out} ] || mkdir -p {out}'.format(out=args.output_dir))
        local('if [ -f {out}/cpplint.txt ];then rm -f {out}/cpplint.txt; fi'.format(
            out=args.output_dir))
        cmd = Template(CMD_TPL2.decode('utf-8'));
        cmd = cmd.render(out=args.output_dir, dirs=' '.join(args.dirs))
        cmd = cmd.encode('utf-8')
        pyshell.shell(cmd, warn_only=True)
        converter = CpplintConverter()
        converter.parse(args.output_dir+'/cpplint.txt')
        converter.write(args.output_dir+'/cpplint.xml')
    else:
        cmd = Template(CMD_TPL1.decode('utf-8'));
        cmd = cmd.render(out=args.output_dir, dirs=' '.join(args.dirs))
        cmd = cmd.encode('utf-8')
        pyshell.shell(cmd, warn_only=True)

def sshkey_copy(argv, prog):
    argparser = argparse.ArgumentParser(description="ssh 信任关系建立", prog=prog)
    argparser.add_argument('-d', '--direction' , dest='direction',
            choices=[1, 2, 3], type=int, default=1, 
            help='1:本机到nodes的信任关系 2:nodes之间的双向关系, 3:都建立' )
    argparser.add_argument(
            '-n', '--nodes', metavar="(user@)host", nargs='+',
            help='要建立信任关系的节点')
    argparser.add_argument( '-f', '--file', help='节点文件', nargs='+')
    argparser.add_argument(
            '-u', '--user', help='默认用户', nargs='?')
    argparser.add_argument(
            '-p', '--passwd',  action='store_true', 
            help='是否输入默认密码')
    args = argparser.parse_args(argv)
    default_user = args.user
    if not default_user:
        default_user = getpass.getuser()
    default_passwd = ''
    if args.passwd:
        print 'please input passwd as default'
        default_passwd = getpass.getpass()
    nodes = []
    if args.nodes is None:
        args.nodes = []
    for node in args.nodes:
        parts = node.split('@')
        if len(parts) == 1:
            nodes.append({ 'user': default_user, 'host' : parts[0],
                'passwd': default_passwd})
        else:
            nodes.append({ 'user': parts[0], 'host' : parts[1],
                'passwd': default_passwd})
    if args.file is None:
        args.file = []
    for file in args.file:
        fd = open(file, 'r')
        for line in fd:
            line = line.strip()
            if not line:
                continue
            parts = line.split('@')
            if len(parts) == 1:
                nodes.append({ 'user': default_user, 'host' : parts[0],
                    'passwd': default_passwd})
            else:
                nodes.append({ 'user': parts[0], 'host' : parts[1],
                    'passwd': default_passwd})
    # 建立本机到node之间的信任关系
    if args.direction == 1 or args.direction == 3:
        for node in nodes:
            print '====start local=>{user}@{host}====='.format(
                    user=node['user'], host=node['host'])
            sshutil.build_ssh1(node)
    if args.direction == 2 or args.direction == 3:
        for i in range(len(nodes)):
            for j in range(i+1, len(nodes)):
                print '====start {src_user}@{src_host}=>{dst_user}@{dst_host}====='.format(
                     src_user=nodes[i]['user'], src_host=nodes[i]['host'],
                     dst_user=nodes[j]['user'], dst_host=nodes[j]['host'],)
                sshutil.build_ssh2(nodes[i], nodes[j])
                print '====start {src_user}@{src_host}=>{dst_user}@{dst_host}====='.format(
                     src_user=nodes[j]['user'], src_host=nodes[j]['host'],
                     dst_user=nodes[i]['user'], dst_host=nodes[i]['host'],)
                sshutil.build_ssh2(nodes[j], nodes[i])

def userset(argv, prog):
    """更新用户密码和组的命令，目前只适用于root"""
    argparser = argparse.ArgumentParser(description="更新用户信息, 用户不存在则创建用户", prog=prog)
    argparser.add_argument(
            '-n', '--hosts', metavar="host", nargs='+',
            help='要建立信任关系的节点')
    argparser.add_argument('-f', '--hostfile', help='节点文件', nargs='+')
    argparser.add_argument('-s', '--userfile', help='用户文件', nargs='+')
    argparser.add_argument(
            '-u', '--user', help='要修改或者建立的用户', nargs='+',
            metavar='user:passwd:g1,g2,...gn')
    args = argparser.parse_args(argv)
    hosts = []
    if not args.hosts is None:
        hosts.extend(args.hosts)
    read_host(args.hostfile, hosts)
    print 'hosts = ', ','.join(hosts)
    users = {} # 'name':{'passwd':, groups:[]}
    if not args.user is None:
        for u in args.user:
            parse_user(u, users)
    if not args.userfile is None:
        for file in args.userfile:
            fd = open(file, 'r')
            for line in fd:
                line = line.strip()
                if line_is_comment(line):
                    continue
                parse_user(line, users)
            fd.close()
    user_list = []
    for user_name, user_info in users.iteritems():
        if not user_info['passwd']:
            print "please specify passwd for " + user_name
            user_info['passwd'] = getpass.getpass()
        user_list.append(user_info)
    print user_list
    for host in hosts:
        for user in user_list:
            set_user(host, user)
def pushfile(argv, prog):
    """push文件"""
    argparser = argparse.ArgumentParser(description="push文件到目标机器", prog=prog)
    argparser.add_argument(
            '-n', '--hosts', metavar="host", nargs='+',
            help='目标机器')
    argparser.add_argument('-f', '--hostfile', help='机器列表文件', nargs='+')
    argparser.add_argument('-l', '--opfile', help='文件拷贝操作文件', nargs='+')
    argparser.add_argument('-u', '--user', help='用户名', nargs='?')
    argparser.add_argument(
            '-a', '--fop', help='要拷贝文件', nargs='+',
            metavar='src_path=>dst_path:mask')
    args = argparser.parse_args(argv)
    hosts = []
    if not args.hosts is None:
        hosts.extend(args.hosts)
    read_host(args.hostfile, hosts)
    print 'hosts = ', ','.join(hosts)
    fileops = [] 
    print args.opfile
    if not args.fop is None:
        for u in args.fop:
            parse_fileop(u, fileops)
    if not args.opfile is None:
        for file in args.opfile:
            fd = open(file, 'r')
            for line in fd:
                line = line.strip()
                if line_is_comment(line):
                    continue
                parse_fileop(line, fileops)
            fd.close()
    # 先确认本地文件都存在
    for fileop in fileops:
        if not os.path.exists(fileop['src']):
            raise Exception('src_not_exist src=' + fileop['src'])
        if os.path.isdir(fileop['src']):
            raise Exception('src_is_dir src=' + fileop['src'])
    if not args.user is None:
        fabric_env.user = args.user
    for host in hosts:
        fabric_env.host_string = host
        for fileop in fileops:
            print '[{host}] copy {src} to {dst}'.format(
                    host = host, src = fileop['src'], dst = fileop['dst'])

            if fileop['mode']:
                put(fileop['src'], fileop['dst'], mode=fileop['mode'])
            else:
                put(fileop['src'], fileop['dst'], mirror_local_mode=True)
def runcmd(argv, prog):
    """运行命令"""
    argparser = argparse.ArgumentParser(description="远程机器上运行命令", prog=prog)
    argparser.add_argument(
            '-n', '--hosts', metavar="host", nargs='+',
            help='目标机器')
    argparser.add_argument('-f', '--hostfile', help='机器列表文件', nargs='+')
    argparser.add_argument('-c', '--cmd', help='运行的脚本', 
            required=True)
    argparser.add_argument('-u', '--user', help='用户', nargs='?')
    args = argparser.parse_args(argv)
    hosts = []
    if not args.hosts is None:
        hosts.extend(args.hosts)
    read_host(args.hostfile, hosts)
    for host in hosts:
        if not args.user:
            command = 'ssh -t {host} "{cmd}"'.format(host=host,
                    cmd=args.cmd)
        else:
            command = 'ssh -t {user}@{host} "{cmd}"'.format(host=host,
                cmd=args.cmd, user=args.user)
        local(command)

COMMANDS = {
        'deploy' : (deploy, '部署到目标环境'), 
        'gen_buildmeta' : (gen_build_metainfo, '在本地生成METAINFO/build.inf'),
        'install_depends' : (install_depends, '安装依赖'),
        'gen_conf' : (gen_conf, '辅助生成配置文件'),
        'cpplint2cppcheck' : (cpplint2cppcheck,
            '将cpplint的输出转化成cppcheck，方便集成到jenkins'),
        'check_cpp' : (check_cpp,
            '检查cpp代码'),
        'sshkey_copy' : (sshkey_copy,
            '拷贝ssh公钥，建立信任关系'),
        'userset' : (userset,
            '用户修改'),
        'pushfile' : (pushfile,
            '拷贝文件'),
        'run' : (runcmd, '运行脚本'),
        'help' : (show_usage, '打印支持的命令和功能，详细帮助请使用command -h')
        }

def main():
    command_name = sys.argv[1]
    if not COMMANDS.has_key(command_name):
        print "not supported command:" + command_name
        return 1
    command = COMMANDS[command_name][0](sys.argv[2:], sys.argv[0])

if __name__ == '__main__':
    ret = main()
    sys.exit(ret)
