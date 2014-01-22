#encoding:utf-8

import time
class MetainfoError(Exception):
    def __init__(self, msg):
        self.msg = msg
        pass
    def __str__(self):
        return self.msg

class Metainfo(object):
    """ 读取metainfo的类"""
    def __init__(self):
        self.build_number = 0
        self.svn = ''
        self.build_time = ''
        self.files = {}
        self.depends = {}
        pass

    def load(self, file_path):
        file = open(file_path, 'r')
        config = {}
        line_number = -1 
        for line in file:
            ++line_number
            line = line.strip()
            if not line:
                continue
            if line.find('#')  ==  0 or line.find('//') == 0:
                continue
            parts = line.split(':', 1)
            if len(parts) != 2:
                continue
            key = parts[0].strip().upper()
            v = config.get(parts[0], [])
            v.append(parts[1].strip())
            config[key] = v
        file.close()
        build_val = config.get('BUILD', [])
        if len(build_val) != 1:
            raise MetainfoError("BUILD need 1, but got %d" % (len(build_val)))
        self.build_number = int(build_val[0])
        svn_val = config.get('SVN', [])
        if len(svn_val) != 1:
            raise MetainfoError("SVN need 1, but got %d" % (len(build_val)))
        self.svn = svn_val[0]
        build_time_val = config.get('BUILD_TIME', [])
        if len(build_time_val) != 1:
            raise MetainfoError("BUILD_TIME need 1, but got %d"
                    % (len(build_time_val)))
        self.build_time = build_time_val[0]

        files_val = config.get('FILE_MD5', [])
        for file_md5 in files_val:
            file_md5 = file_md5.strip()
            file_info_part = file_md5.split(',')
            self.files[file_info_part[0]] = file_info_part[1]
        depends_val = config.get('DEPENDS', [])
        for one_depend in depends_val:
            one_depend = one_depend.strip()
            depend_info = one_depend.split(',')
            if len(depend_info) != 3:
                raise MetainfoError("DEPENDS %s "
                    % (one_depend))
            self.depends[depend_info[0]] = {'build' : int(depend_info[1]), 
                    'svn' : depend_info[2]}
    def save(self, path):
        file = open(path, 'w')
        file.write('SVN: %s\n' % (self.svn))
        file.write('BUILD: %d\n' % (self.build_number))
        file.write('BUILD_TIME: %s' % (time.strftime('%Y-%m-%d %H:%M', time.localtime(time.time()))))
        file.close()

    
    def __str__(self):
        s = object.__repr__(self) 
        s += '<build_number:' + str(self.build_number)
        s += ', svn:' + self.svn
        s += ', build_time:' + self.build_time
        s += ', files: '
        s += repr(self.files)
        s += ', depends: '
        s += repr(self.depends)
        return s

