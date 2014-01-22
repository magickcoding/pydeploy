#encoding: utf-8

import xml
import xml.dom
import xml.dom.minidom
import sys

class CpplintConverter(object):
    """
    将cpplint的分析结果转化成cppcheck, 以方便hudson集成"""
    def __init__(self):
        impl = xml.dom.minidom.getDOMImplementation()
        self.dom = impl.createDocument(None, 'results', None)
        pass
    def parse(self, file):
        for line in open(file):
            parts = line.split(' ')
            if len(parts) < 4:
                continue
            file_and_line = parts[0].split(':')
            if len(file_and_line) != 3:
                continue
            file = file_and_line[0]
            line = file_and_line[1]
            level = parts[-1]
            kind = parts[-2]
            msg = parts[1:len(parts)-2]
            self.add_error(file, line, self.join_msg(msg), kind, level)
    def join_msg(self, parts):
        msg = ""
        for part in parts:
            msg += part + " "
        return msg
    def write(self, out):
        f = file(out, 'w')
        self.dom.writexml(f, '  ', '  ', '\n')

    def add_error(self, file, line, msg, kind, level):
        elem = self.dom.createElement("error")
        elem.setAttribute("file", file)
        elem.setAttribute("line", line)
        elem.setAttribute("id", kind)
        elem.setAttribute("severity", "style")
        elem.setAttribute("msg", msg)
        self.dom.documentElement.appendChild(elem)

if __name__ == "__main__":
    converter = CpplintConverter()
    converter.parse(sys.argv[1])
    converter.write(sys.argv[2])
