import sys;
import os;
import re;
import struct;

class HackAsm:
  symtable = {
      "SP": 0,
      "LCL": 1, 
      "ARG": 2, 
      "THIS": 3, 
      "THAT": 4, 
      "SCREEN": 16384, 
      "KBD": 24576
      }
  var_base = 16
  cmds = []
  def __init__(self, path):
    for i in range(16):
      name = "R%d" % i
      self.symtable[name] = i
    f = open(path,"r")
    lines = f.readlines()
    offset = 0
    for line in lines:
      nline = re.sub("//.*", "", line)
      nline = re.sub("\s+", "", nline)
      print("line: %s nline: %s" % (line, nline))
      if (nline):
        print("adding nline at offset: %d" % offset)
        m = re.match("\((.+)\)", nline)
        if m:
          sym = m.group(1)
          print("label command: %s" % sym)
          self.symtable[sym] = offset
        else:
          self.cmds.append(nline)
          offset += 1
    print(self.symtable)

  def __Acode(self, value):
    if (value.isdigit()):
      v = int(value)
    elif value in self.symtable:
      v = self.symtable[value]
    else:
      self.symtable[value] = self.var_base
      v = self.var_base
      self.var_base += 1
    if v >= 2**15:
      raise ValueError("Invalid value: %s" % value)
    str = "{:016b}".format(v)
    return str
    #return struct.pack('H', v)

  def __jump(self, jmp):
    if not jmp:
      return "000"
    if (jmp == "JGT"):
      j = 1
    elif (jmp == "JEQ"):
      j = 2
    elif (jmp == "JGE"):
      j = 3
    elif (jmp == "JLT"):
      j = 4
    elif (jmp == "JNE"):
      j = 5
    elif (jmp == "JLE"):
      j = 6
    elif (jmp == "JMP"):
      j = 7
    else:
      raise ValueError("Invalid jump value: %s" % jmp)
    str = "{:03b}".format(j)
    return str
    #return j

  def __dest(self, dest):
    d = 0
    if not dest:
      return "000"
    m = re.match("(A)?(M)?(D)?", dest)
    if m:
      if m.group(1):
        d += 4
      if m.group(2):
        d += 1
      if m.group(3):
        d += 2
      str = "{:03b}".format(d)
      print("d=%d, str=%s" % (d, str))
      return str
      #return d
    raise ValueError("Invalid dest value: %s" % dest)

  def __comp(self, comp):
    if (comp == '0'):
      return "0101010"
    elif (comp == '1'):
      return "0111111"
    elif (comp == '-1'):
      return "0111010"
    elif (comp == 'D'):
      return "0001100"
    elif (comp == "A"):
      return "0110000"
    elif (comp == "M"):
      return "1110000"
    elif (comp == "!D"):
      return "0001101"
    elif (comp == "!A"):
      return "0110001"
    elif (comp == "!M"):
      return "1110001"
    elif (comp == "-D"):
      return "0001111"
    elif (comp == "-A"):
      return "0110011"
    elif (comp == "-M"):
      return "1110011"
    elif (comp == "D+1"):
      return "0011111"
    elif (comp == "A+1"):
      return "0110111"
    elif (comp == "M+1"):
      return "1110111"
    elif (comp == "D-1"):
      return "0001110"
    elif (comp == "A-1"):
      return "0110010"
    elif (comp == "M-1"):
      return "1110010"
    elif (comp == "D+A"):
      return "0000010"
    elif (comp == "D+M"):
      return "1000010"
    elif (comp == "D-A"):
      return "0010011"
    elif (comp == "D-M"):
      return "1010011"
    elif (comp == "A-D"):
      return "0000111"
    elif (comp == "M-D"):
      return "1000111"
    elif (comp == "D&A"):
      return "0000000"
    elif (comp == "D&M"):
      return "1000000"
    elif (comp == "D|A"):
      return "0010101"
    elif (comp == "D|M"):
      return "1010101"
    raise ValueError("Invalid comp %s" % comp)

  def __Ccode(self, dest, comp, jmp):
    j = self.__jump(jmp)
    c = self.__comp(comp)
    d = self.__dest(dest)

    print ("comp=%s dest=%s jmp=%s" % (comp, dest, jmp))
    print ("c=%s d=%s j=%s" % (c, d, j))
    str = "111" + c + d + j
    return str
    #return struct.pack('H', v)

  def assemble(self, path):
    bincode = []
    for cmd in self.cmds:
      print("cmd: %s" % cmd)
      m = re.match("@(.+)", cmd)
      if m:
        bincode.append(self.__Acode(m.group(1)))
        continue
      dest = ""
      jmp = ""
      comp = ""
      if '=' in cmd:
        arr = cmd.split('=')
        dest = arr[0]
        cmd = arr[1]
      comp = cmd
      if ';' in cmd:
        arr = cmd.split(';')
        comp = arr[0]
        jmp = arr[1]
      bincode.append(self.__Ccode(dest, comp, jmp))
    f = open(path, "wb")
    for code in bincode:
      f.write(code)
      f.write("\n")

def main():
  if (len(sys.argv) != 3):
    print("Usage: xx");
    return 1
  h = HackAsm(sys.argv[1])
  h.assemble(sys.argv[2])

if __name__ == "__main__":
  main()
