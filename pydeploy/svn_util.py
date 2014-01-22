#coding:utf-8
from pyshell import shell
class SVNUtil:
    def info(self):
        pret =  shell('LANG=en_US svn info', timeout=10, capture=True)
        result = {}
        for line in pret.stdout.split('\n'):
            line =  line.rstrip()
            parts = line.split(':', 1)
            if len(parts) == 2:
                if parts[0] == 'Revision':
                    result['revision'] = int(parts[1])
                elif parts[0] == 'URL':
                    result['svn'] = parts[1]

        return  result
if __name__ == '__main__':
    svn = SVNUtil()
    print svn.info()

