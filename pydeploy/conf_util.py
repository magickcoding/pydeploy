#encoding:utf-8
import sys

def instance():
    pass


class ConfUtil(object) :
    def __init__(self, conf_path, conf_mod, conf_fromlist = []) :
        self.conf_path = conf_path
        self.conf_mod = conf_mod
        self.conf_fromlist = conf_fromlist

    def AddConf(self) :
        if len(self.conf_mod) == 0 :
            return False
        if len(self.conf_path) != 0 :
            sys.path.append(self.conf_path)
        print "add conf:" + self.conf_path + "/" + self.conf_mod
        self.conf = __import__(self.conf_mod, globals(), locals(), 
                                self.conf_fromlist)
        print "add conf:" + self.conf_mod + " OK"
        return True

    def RemoveConf(self) :
        if len(self.conf_mod) == 0 :
            return False
        sys.path.remove(self.conf_path)
        return True

if __name__ == '__main__':
    import define
    tmp_conf = ConfUtil("./build", "conf")
    tmp_conf.AddConf()
    print define.g_lib_dependency.keys()
    tmp_conf.RemoveConf()
        

