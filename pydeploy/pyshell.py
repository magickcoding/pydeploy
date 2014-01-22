#coding:utf-8
import subprocess
import time
from fabric.api import settings, run, env


def wait_process_end(process, timeout):
    if timeout <= 0:
        process.wait()
        return 0
    start_time = time.time()
    end_time = start_time + timeout
    while 1:
        ret = process.poll()
        if ret == 0:
            return 0
        elif ret is None:
            cur_time = time.time()
            if cur_time >= end_time:
                return 1
            time.sleep(0.1)
        else:
            return 2

class ShellResult:
    def __init__(self, return_code, stdout, stderr):
        self.return_code = return_code
        self.stdout = stdout
        self.stderr = stderr
def shell(command, timeout=0, capture=False, warn_only=False):
    """ 执行一个shell命令
        @return (returncode)
    """
    print '[local] ' + command
    if capture:
        process = subprocess.Popen(command,stdin=subprocess.PIPE, 
                stderr=subprocess.PIPE, stdout=subprocess.PIPE, shell=True)
    else:
        process = subprocess.Popen(command,shell=True)
    ret = wait_process_end(process, timeout)
    if ret == 1:
        process.terminate()
        raise Exception("terminated_for_timout")
    if process.returncode != 0:
        if not warn_only:
            raise Exception('command %s exit with code %d' % (
                command, process.returncode))
    if capture:
        stdout = ''.join(process.stdout.readlines())
        stderr = ''.join(process.stdout.readlines())
        return ShellResult(process.returncode, stdout, stderr)
    else:
        return ShellResult(process.returncode, None, None)

def remote_shell(cmd, capture=False, warn_only=False):
    with settings(warn_only=warn_only):
        ret = run(cmd)
        shell_ret = ShellResult(ret.return_code, ret, ret.stderr)
        return shell_ret
def stop_process(ssh_user, host, pid):
    """ 停止服务，返回停止的进程ID"""
    cmd = "ssh %s@%s \"kill %d\"" % (ssh_user, host, pid)
    returncode, stdout, stderr = exec_command(cmd, 5)
    if returncode != 0:
        err_msg = list_join(stderr)
        raise Exception, "stop_process pid=%d stderr=[%s]" % (pid, err_msg)
    return pid

if __name__ == '__main__':
    ret = shell('echo $HOME', capture=True)
    print ret.stdout
    env.host_string = '192.168.1.157'
    env.user = 'work'
    ret = remote_shell('echo $HOME', capture = True, warn_only = True)
    pass

