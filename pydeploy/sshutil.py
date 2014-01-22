#coding: utf-8
from fabric.api import run, local, env, put, get
import pexpect

def build_ssh1(dest):
    """从本机建立到目标机的信任关系 """
    env.host_string = dest['host']
    env.user = dest['user']
    env.password = dest['passwd']
    cmd="[ -d ~/.ssh ] || mkdir ~/.ssh; "
    local(cmd)
    cmd='if [ ! -f ~/.ssh/id_rsa.pub ]; then ssh-keygen -N "" -f ~/.ssh/id_rsa ; fi'
    local(cmd)

    run('[ -d ~/.ssh ] || mkdir ~/.ssh')
    id_rsa_pub_file = '~/.ssh/tmp.pub'
    run('if [ -f {pubkey} ]; then rm {pubkey}; fi'.format(
        pubkey=id_rsa_pub_file))
    put('~/.ssh/id_rsa.pub', id_rsa_pub_file)
    cmd = 'existed=0;content=`cat {pubkey}`; if [ -f ~/.ssh/authorized_keys ];then grep "$content" ~/.ssh/authorized_keys >/dev/null 2>&1; if [ $? -eq 0 ];then existed=1;fi;fi; '
    cmd = cmd + ' if [ $existed -eq 0 ]; then cat {pubkey} >> ~/.ssh/authorized_keys ; fi && rm {pubkey} && chmod 600 ~/.ssh/authorized_keys &&  chmod og-w ~; chmod og-w ~/.ssh'
    cmd = cmd.format(pubkey = id_rsa_pub_file)
    run(cmd)
    cmd='ssh {user}@{host} "id"'.format(user=env.user, host=dest['host'])
    # local(cmd)
    print "spawn" , cmd
    child = pexpect.spawn(cmd)
    i = child.expect(['\(yes/no\)\?', pexpect.EOF])
    if i==0:
        child.sendline('yes')
    print child.before
    child.close()
   
def build_ssh2(src, dest):
    """建立从src到dest的信任关系"""
    env.host_string = src['host']
    env.user = src['user']
    env.password = src['passwd']
    cmd="[ -d ~/.ssh ] || mkdir ~/.ssh; "
    run(cmd)
    cmd='if [ ! -f ~/.ssh/id_rsa.pub ]; then ssh-keygen -N "" -f ~/.ssh/id_rsa ; fi'
    run(cmd)
    id_rsa_pub_file = '~/.ssh/{user}@{host}_id_rsa.pub'.format(
            user=src['user'], host=src['host'])
    get('~/.ssh/id_rsa.pub', id_rsa_pub_file)
    env.host_string = dest['host']
    env.user = dest['user']
    env.password = dest['passwd']
    run('[ -d ~/.ssh ] || mkdir ~/.ssh')
    put(id_rsa_pub_file, id_rsa_pub_file)
    cmd = 'existed=0;content=`cat {pubkey}`; if [ -f ~/.ssh/authorized_keys ];then grep "$content" ~/.ssh/authorized_keys >/dev/null 2>&1; if [ $? -eq 0 ];then existed=1;fi;fi; '
    cmd = cmd + ' if [ $existed -eq 0 ]; then cat {pubkey} >> ~/.ssh/authorized_keys ; fi && rm {pubkey} && chmod 600 ~/.ssh/authorized_keys &&  chmod og-w ~; chmod og-w ~/.ssh'
    cmd = cmd.format(pubkey=id_rsa_pub_file)
    run(cmd)

    #进行测试，并且消除第一次连接要敲回车的问题
    env.host_string = src['host']
    env.user = src['user']
    env.password = src['passwd']
    cmd='ssh {user}@{host} "ls"'.format(user=dest['user'], host=dest['host'])
    run(cmd)

