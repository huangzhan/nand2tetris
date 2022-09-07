#!/usr/bin/env python3
import sys
import os
import re
import struct
from enum import Enum, auto

labelcnt = 0
linecnt = 0

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

def write_code(asm, code):
  global linecnt
  if (code[0] != '('):
    code = '%s // line: %d' % (code, linecnt)
    linecnt += 1
  asm.append(code)

def xlate_neg(cmdline):
  asm = []
  write_code(asm, '@SP')
  write_code(asm, 'A=M-1')
  write_code(asm, 'M=-M')
  return '\n'.join(asm)


def xlate_boolean(cmp, jmp):
  global labelcnt
  asm = []
  true_label = 'TRUE%d' % labelcnt
  end_label = 'END%d' % labelcnt
  labelcnt += 1
  write_code(asm, cmp)
  write_code(asm, '@%s' % true_label)
  write_code(asm, jmp)
  write_code(asm, '@SP')
  write_code(asm, 'A=M-1')
  write_code(asm, 'M=0')
  write_code(asm, '@%s' % end_label)
  write_code(asm, '0;JMP')
  write_code(asm, '(%s)' % true_label)
  write_code(asm, '@SP')
  write_code(asm, 'A=M-1')
  write_code(asm, 'M=-1')
  write_code(asm, '(%s)' % end_label)
  return asm


def xlate_not(cmdline):
  asm = []
  write_code(asm, '@SP')
  write_code(asm, 'A=M-1')
  write_code(asm, 'M=!M')
  #asm.extend(xlate_boolean('D=!M', 'D;JNE'))
  return '\n'.join(asm)

def xlate_arith(cmdline, file, func):
  if (cmdline[0] == 'neg'):
    return xlate_neg(cmdline)
  elif (cmdline[0] == 'not'):
    return xlate_not(cmdline)
  asm = []
  write_code(asm, '@SP')
  write_code(asm, 'AM=M-1')
  write_code(asm, 'D=M')
  write_code(asm, 'A=A-1')
  if (cmdline[0] == 'add'):
    write_code(asm, 'M=D+M')
  elif (cmdline[0] == 'sub'):
    write_code(asm, 'M=M-D')
  elif (cmdline[0] == 'eq'):
    asm.extend(xlate_boolean('D=M-D', 'D;JEQ'))
  elif (cmdline[0] == 'gt'):
    asm.extend(xlate_boolean('D=M-D', 'D;JGT'))
  elif (cmdline[0] == 'lt'):
    asm.extend(xlate_boolean('D=M-D', 'D;JLT'))
  elif (cmdline[0] == 'and'):
    write_code(asm, 'M=M&D')
    #asm.extend(xlate_boolean('D=M&D', 'D;JNE'))
  elif (cmdline[0] == 'or'):
    write_code(asm, 'M=M|D')
    #asm.extend(xlate_boolean('D=M|D', 'D;JNE'))
  else:
    raise ValueError('Invalid vm command')
  
  return '\n'.join(asm)

def xlate_static(cmdline, file):
  index = cmdline[2]
  if (not index.isnumeric()):
    raise ValueError('%s invalid' % ' '.join(cmdline))

  asm = []
  write_code(asm, '@%s.%s' % (file, index))
  return asm

def xlate_temp(cmdline, file):
  index = cmdline[2]
  if (not 0 <= int(index) <= 7):
    raise ValueError('%s invalid' % ' '.join(cmdline))

  asm = []
  write_code(asm, '@%s' % index)
  write_code(asm, 'D=A')
  write_code(asm, '@5')
  write_code(asm, 'A=D+A')
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
  write_code(asm, '@%s' % var)
  return asm

def xlate_xx(cmdline, file):
  segment = cmdline[1]
  index = cmdline[2]
  if (not index.isnumeric()):
    raise ValueError('%s invalid' % ' '.join(cmdline))
  base = VmSegmentTable[segment][1]

  asm = []
  write_code(asm, '@%s' % index)
  write_code(asm, 'D=A')
  write_code(asm, '@%s' % base)
  write_code(asm, 'A=D+M')
  return asm

def xlate_constant(cmdline, file):
  constant = cmdline[2]
  if (not constant.isnumeric()):
    raise ValueError('%s invalid' % ' '.join(cmdline))
  asm = []
  write_code(asm, '@%s' % constant)
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

def xlate_push(cmdline, file, func):
  segment = cmdline[1]
  asm = []
  func = VmSegmentTable[segment][0]
  asm.extend(func(cmdline, file))
  if (segment == 'constant'):
    write_code(asm, 'D=A')
  else:
    write_code(asm, 'D=M')
  write_code(asm, '@SP')
  write_code(asm, 'A=M')
  write_code(asm, 'M=D')
  write_code(asm, '@SP')
  write_code(asm, 'M=M+1')
  return '\n'.join(asm)

def xlate_pop(cmdline, file, func):
  segment = cmdline[1]
  if (segment == 'constant'):
    raise ValueError('%s invalid' % ' '.join(cmdline))
  asm = []
  write_code(asm, '@SP')
  write_code(asm, 'M=M-1')
  func = VmSegmentTable[segment][0]
  asm.extend(func(cmdline, file))
  write_code(asm, 'D=A')
  write_code(asm, '@R13')
  write_code(asm, 'M=D')
  write_code(asm, '@SP')
  write_code(asm, 'A=M')
  write_code(asm, 'D=M')
  write_code(asm, '@R13')
  write_code(asm, 'A=M')
  write_code(asm, 'M=D')
  return '\n'.join(asm)

def xlate_label(cmdline, file, func):
  asm = []
  label = '%s$%s' % (func, cmdline[1])
  write_code(asm, '(%s)' % label)
  return '\n'.join(asm)

def xlate_goto(cmdline, file, func):
  asm = []
  label = '%s$%s' % (func, cmdline[1])
  write_code(asm, '@%s' % label)
  write_code(asm, '0;JMP')
  return '\n'.join(asm)

def xlate_if(cmdline, file, func):
  asm = []
  label = '%s$%s' % (func, cmdline[1])
  write_code(asm, '@SP')
  write_code(asm, 'AM=M-1')
  write_code(asm, 'D=M')
  write_code(asm, '@%s' % label)
  write_code(asm, 'D;JNE')
  return '\n'.join(asm)

FuncDict = {}

def check_func_name(name):
  pass

def xlate_function(cmdline, file, func):
  asm = []
  check_func_name(func)
  localcnt = cmdline[2]
  if (not localcnt.isnumeric()):
    raise ValueError('%s invalid' % ' '.join(cmdline))

  # func label
  write_code(asm, '(%s)' % func)
  # push 0 localcnt times
  for i in range(int(localcnt)):
    write_code(asm, '@SP')
    write_code(asm, 'A=M')
    write_code(asm, 'M=0')
    write_code(asm, '@SP')
    write_code(asm, 'M=M+1')

  return '\n'.join(asm)

def restore_seg(seg):
  asm = []
  write_code(asm, '@R13')
  write_code(asm, 'AM=M-1')
  write_code(asm, 'D=M')
  write_code(asm, '@%s' % seg)
  write_code(asm, 'M=D')
  return asm

def xlate_return(cmdline, file, func):
  asm = []
  # save LCL to R13
  write_code(asm, '@LCL')
  write_code(asm, 'D=M')
  write_code(asm, '@R13')
  write_code(asm, 'M=D')
  # get RET to R14
  write_code(asm, '@5')
  write_code(asm, 'D=A')
  write_code(asm, '@R13')
  write_code(asm, 'A=M-D')
  write_code(asm, 'D=M')
  write_code(asm, '@R14')
  write_code(asm, 'M=D')
  # put return value (which is on stack top) to ARG, which will be the new stack top
  write_code(asm, '@SP')
  write_code(asm, 'A=M-1')
  write_code(asm, 'D=M')
  write_code(asm, '@ARG')
  write_code(asm, 'A=M')
  write_code(asm, 'M=D')
  # set SP to ARG+1
  write_code(asm, '@ARG')
  write_code(asm, 'D=M')
  write_code(asm, '@SP')
  write_code(asm, 'M=D+1')
  # restore THAT, THIS, ARG, LCL
  asm.extend(restore_seg('THAT'))
  asm.extend(restore_seg('THIS'))
  asm.extend(restore_seg('ARG'))
  asm.extend(restore_seg('LCL'))
  # goto ret
  write_code(asm, '@R14')
  write_code(asm, 'A=M')
  write_code(asm, '0;JMP')

  return '\n'.join(asm)

def push_D():
  asm = []
  write_code(asm, '@SP')
  write_code(asm, 'A=M')
  write_code(asm, 'M=D')
  write_code(asm, '@SP')
  write_code(asm, 'M=M+1')
  return asm

def push_seg(seg):
  asm = []
  write_code(asm, '@%s' % seg)
  write_code(asm, 'D=M')
  asm.extend(push_D())
  return asm

def push_label(label):
  asm = []
  write_code(asm, '@%s' % label)
  write_code(asm, 'D=A')
  asm.extend(push_D())
  return asm

def xlate_call(cmdline, file, func):
  asm = []
  callee = cmdline[1]
  argcnt = cmdline[2]
  if (not argcnt.isnumeric()):
    raise ValueError('%s invalid' % ' '.join(cmdline))
  retlabel = "%s$ret.%d" % (func, FuncDict[func]['retcnt'])
  FuncDict[func]['retcnt'] += 1

  # push frame
  asm.extend(push_label(retlabel))
  asm.extend(push_seg('LCL'))
  asm.extend(push_seg('ARG'))
  asm.extend(push_seg('THIS'))
  asm.extend(push_seg('THAT'))

  # setup new segments
  # ARG: SP-5-argcnt
  write_code(asm, '@SP')
  write_code(asm, 'D=M')
  write_code(asm, '@5')
  write_code(asm, 'D=D-A')
  write_code(asm, '@%s' % argcnt)
  write_code(asm, 'D=D-A')
  write_code(asm, '@ARG')
  write_code(asm, 'M=D')
  # LCL: SP
  write_code(asm, '@SP')
  write_code(asm, 'D=M')
  write_code(asm, '@LCL')
  write_code(asm, 'M=D')

  # goto func
  write_code(asm, '@%s' % callee)
  write_code(asm, '0;JMP')

  # return label
  write_code(asm, '(%s)' % retlabel)
  return '\n'.join(asm)

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
  func = ''
  def __init__(self, cmdline, file, func):
    print("VmCmd init file: %s func: %s" % (file, func))
    print(cmdline)
    self.cmdline = cmdline
    self.file = file
    self.func = func
  def str(self):
    return " ".join(self.cmdline)
  def type(self):
    return VmCmdTable[self.cmdline[0]]
  def xlate(self):
    return VmCmdXlateTable[self.type()](self.cmdline, self.file, self.func)

class VmFile:
  file = ""
  cmds = []
  cursor=0
  global FuncDict
  def __init__(self, path):
    f = open(path,"r")
    self.file = os.path.basename(path)
    lines = f.readlines()
    func = 'null'
    self.cmds = []
    for line in lines:
      line = re.sub("//.*", "", line)
      line_cmds = line.split()
      if (line_cmds):
        print(line_cmds)
        if (line_cmds[0] == 'function'):
          func = line_cmds[1]
          if func in FuncDict:
            raise ValueError("Function %s already defined" % func)
          FuncDict[func] = {
              'retcnt': 0,
              'file': self.file
              }
        cmd = {'func': func, 'cmd': line_cmds}
        self.cmds.append(cmd)
    cursor=0
    print(self.cmds)
  def nextcmd(self):
    if (self.cursor >= len(self.cmds)):
      return None
    cmd = VmCmd(self.cmds[self.cursor]['cmd'], self.file, self.cmds[self.cursor]['func'])
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
    # bootstrap code
    asm = []
    # SP=256
    write_code(asm, '@261')
    write_code(asm, 'D=A')
    write_code(asm, '@SP')
    write_code(asm, 'M=D')
    # call Sys.init
    # setup new segments
    # ARG: no need?
    # LCL: SP
    write_code(asm, '@SP')
    write_code(asm, 'D=M')
    write_code(asm, '@LCL')
    write_code(asm, 'M=D')
    
    # goto func
    write_code(asm, '@%s' % 'Sys.init')
    write_code(asm, '0;JMP')
    f.write("%s\n" % '\n'.join(asm))
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
    output="%s/%s.asm" % (sys.argv[1], os.path.basename(sys.argv[1]))
    directory = os.fsencode(sys.argv[1])
    for file in os.listdir(directory):
      filename = os.fsdecode(file)
      print('testing %s' % filename)
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
