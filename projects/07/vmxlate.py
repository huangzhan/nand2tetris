#!/usr/bin/env python3
import sys
import os
import re
import struct
from enum import Enum, auto

labelcnt = 0

class VmCmdType(Enum):
  ARITHMETIC = auto()
  PUSH = auto()
  POP = auto()
  LABEL = auto()
  GOTO = auto()
  IF = auto()
  FUNCTION = auto()
  RETURN = auto()
  CALL = auto()

def xlate_neg(cmdline):
  asm = []
  asm.append('@SP')
  asm.append('A=M-1')
  asm.append('M=-M')
  return '\n'.join(asm)


def xlate_boolean(cmp, jmp):
  global labelcnt
  asm = []
  true_label = 'TRUE%d' % labelcnt
  end_label = 'END%d' % labelcnt
  labelcnt += 1
  asm.append(cmp)
  asm.append('@%s' % true_label)
  asm.append(jmp)
  asm.append('@SP')
  asm.append('A=M-1')
  asm.append('M=0')
  asm.append('@%s' % end_label)
  asm.append('0;JMP')
  asm.append('(%s)' % true_label)
  asm.append('@SP')
  asm.append('A=M-1')
  asm.append('M=-1')
  asm.append('(%s)' % end_label)
  return asm


def xlate_not(cmdline):
  asm = []
  asm.append('@SP')
  asm.append('A=M-1')
  asm.append('M=!M')
  #asm.extend(xlate_boolean('D=!M', 'D;JNE'))
  return '\n'.join(asm)

def xlate_arith(cmdline, file):
  if (cmdline[0] == 'neg'):
    return xlate_neg(cmdline)
  elif (cmdline[0] == 'not'):
    return xlate_not(cmdline)
  asm = []
  asm.append('@SP')
  asm.append('AM=M-1')
  asm.append('D=M')
  asm.append('A=A-1')
  if (cmdline[0] == 'add'):
    asm.append('M=D+M')
  elif (cmdline[0] == 'sub'):
    asm.append('M=M-D')
  elif (cmdline[0] == 'eq'):
    asm.extend(xlate_boolean('D=M-D', 'D;JEQ'))
  elif (cmdline[0] == 'gt'):
    asm.extend(xlate_boolean('D=M-D', 'D;JGT'))
  elif (cmdline[0] == 'lt'):
    asm.extend(xlate_boolean('D=M-D', 'D;JLT'))
  elif (cmdline[0] == 'and'):
    asm.append('M=M&D')
    #asm.extend(xlate_boolean('D=M&D', 'D;JNE'))
  elif (cmdline[0] == 'or'):
    asm.append('M=M|D')
    #asm.extend(xlate_boolean('D=M|D', 'D;JNE'))
  else:
    raise ValueError('Invalid vm command')
  
  return '\n'.join(asm)

def xlate_static(cmdline, file):
  index = cmdline[2]
  if (not index.isnumeric()):
    raise ValueError('%s invalid' % ' '.join(cmdline))

  asm = []
  asm.append('@%s.%s' % (file, index))
  return asm

def xlate_temp(cmdline, file):
  index = cmdline[2]
  # TODO check index 0-7?
  if (not index.isnumeric()):
    raise ValueError('%s invalid' % ' '.join(cmdline))

  asm = []
  asm.append('@%s' % index)
  asm.append('D=A')
  asm.append('@5')
  asm.append('A=D+A')
  return asm

def xlate_pointer(cmdline, file):
  index = cmdline[2]
  if (index == '0'):
    var = 'THIS'
  elif (index == '1'):
    var = 'THAT'
  else:
    raise ValueError('%s invalid' % ' '.join(cmdline))

  asm = []
  asm.append('@%s' % var)
  return asm

def xlate_xx(cmdline, file):
  segment = cmdline[1]
  index = cmdline[2]
  if (not index.isnumeric()):
    raise ValueError('%s invalid' % ' '.join(cmdline))
  base = VmSegmentTable[segment][1]

  asm = []
  asm.append('@%s' % index)
  asm.append('D=A')
  asm.append('@%s' % base)
  asm.append('A=D+M')
  return asm

def xlate_constant(cmdline, file):
  constant = cmdline[2]
  if (not constant.isnumeric()):
    raise ValueError('%s invalid' % ' '.join(cmdline))
  asm = []
  asm.append('@%s' % constant)
  return asm

VmSegmentTable = {
    'constant': [ xlate_constant, None ], 
    'local': [ xlate_xx, 'LCL' ], 
    'argument': [ xlate_xx, 'ARG' ], 
    'this': [ xlate_xx, 'THIS' ], 
    'that': [ xlate_xx, 'THAT' ], 
    'static': [ xlate_static, None ], 
    'temp': [ xlate_temp, None ], 
    'pointer': [ xlate_pointer, None ]
    }

def xlate_push(cmdline, file):
  segment = cmdline[1]
  asm = []
  func = VmSegmentTable[segment][0]
  asm.extend(func(cmdline, file))
  if (segment == 'constant'):
    asm.append('D=A')
  else:
    asm.append('D=M')
  asm.append('@SP')
  asm.append('A=M')
  asm.append('M=D')
  asm.append('@SP')
  asm.append('M=M+1')
  return '\n'.join(asm)

def xlate_pop(cmdline, file):
  segment = cmdline[1]
  if (segment == 'constant'):
    raise ValueError('%s invalid' % ' '.join(cmdline))
  asm = []
  asm.append('@SP')
  asm.append('M=M-1')
  func = VmSegmentTable[segment][0]
  asm.extend(func(cmdline, file))
  asm.append('D=A')
  asm.append('@R13')
  asm.append('M=D')
  asm.append('@SP')
  asm.append('A=M')
  asm.append('D=M')
  asm.append('@R13')
  asm.append('A=M')
  asm.append('M=D')
  return '\n'.join(asm)

def xlate_label(cmdline, file):
  return ''

def xlate_goto(cmdline, file):
  return ''

def xlate_if(cmdline, file):
  return ''

def xlate_function(cmdline, file):
  return ''

def xlate_return(cmdline, file):
  return ''

def xlate_call(cmdline, file):
  return ''

VmCmdXlateTable = {
    VmCmdType.ARITHMETIC: xlate_arith,
    VmCmdType.PUSH: xlate_push,
    VmCmdType.POP: xlate_pop,
    VmCmdType.LABEL: xlate_label,
    VmCmdType.GOTO: xlate_goto,
    VmCmdType.IF: xlate_if,
    VmCmdType.FUNCTION: xlate_function,
    VmCmdType.CALL: xlate_call,
    VmCmdType.RETURN: xlate_return,
    }

VmCmdTable = {
    'add': VmCmdType.ARITHMETIC,
    'sub': VmCmdType.ARITHMETIC,
    'neg': VmCmdType.ARITHMETIC,
    'eq': VmCmdType.ARITHMETIC,
    'gt': VmCmdType.ARITHMETIC,
    'lt': VmCmdType.ARITHMETIC,
    'and': VmCmdType.ARITHMETIC,
    'or': VmCmdType.ARITHMETIC,
    'not': VmCmdType.ARITHMETIC,
    'pop': VmCmdType.POP,
    'push': VmCmdType.PUSH,
    'label': VmCmdType.LABEL,
    'goto': VmCmdType.GOTO,
    'if-goto': VmCmdType.IF,
    'function': VmCmdType.FUNCTION,
    'return': VmCmdType.RETURN,
    'call': VmCmdType.CALL
    }

class VmCmd:
  cmdline = []
  file = ''
  def __init__(self, cmdline, vmfile):
    self.cmdline = cmdline
    self.vmfile = vmfile
  def str(self):
    return " ".join(self.cmdline)
  def type(self):
    return VmCmdTable[self.cmdline[0]]
  def xlate(self):
    return VmCmdXlateTable[self.type()](self.cmdline, self.file)

class VmFile:
  file = ""
  cmds = []
  cursor=0
  def __init__(self, path):
    f = open(path,"r")
    file = os.path.basename(path)
    lines = f.readlines()
    for line in lines:
      line = re.sub("//.*", "", line)
      line_cmds = line.split()
      if (line_cmds):
        print(line_cmds)
        self.cmds.append(line_cmds)
    cursor=0
  def nextcmd(self):
    if (self.cursor >= len(self.cmds)):
      return None
    cmd = VmCmd(self.cmds[self.cursor], self.file)
    self.cursor += 1
    return cmd

class VmXlator:
  vms = []

  def __init__(self):
    pass

  def addvm(self, path):
    print("addvm %s" % path)
    vm = VmFile(path)
    self.vms.append(vm)

  def xlate(self, output):
    print("xlate to %s" % output)
    f = open(output, "w")
    for vm in self.vms:
      cmd = vm.nextcmd()
      while (cmd):
        print("cmd is %s" % cmd.str())
        f.write("// %s\n" % cmd.str())
        f.write("%s\n" % cmd.xlate())
        cmd = vm.nextcmd()

def main():
  if (len(sys.argv) != 2):
    print("Usage: xx");
    return 1

  x = VmXlator()
  if os.path.isdir(sys.argv[1]):  
    output="%s.asm" % sys.argv[1]
    directory = os.fsencode(sys.argv[1])
    for file in os.listdir(directory):
      filename = os.fsdecode(file)
      if filename.endswith(".vm"): 
        path = os.path.join(directory, file)
        x.addvm(os.fsdecode(path))
        continue
  elif os.path.isfile(sys.argv[1]):  
    output="%s.asm" % os.path.splitext(sys.argv[1])[0]
    x.addvm(sys.argv[1])
  else:
    return 1
  x.xlate(output)

if __name__ == "__main__":
  main()
