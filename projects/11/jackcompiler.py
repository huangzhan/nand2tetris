#!/usr/bin/env python3
import sys
import os
import html
import json
from enum import Enum, auto

Symbols = '(){}[].,;+-*/&|<>=-~'
Keywords = ['class', 'field', 'static', 'var', 'int', 'char', 'boolean', 'void', 
    'constructor', 'method', 'function', 'let', 'do', 'if', 'else', 'while', 'return', 
    'true', 'false', 'null', 'this']
BinaryOpTable = {
      '+': 'add',
      '-': 'sub',
      '*': 'call Math.multiply 2',
      '/': 'call Math.divide 2',
      '&': 'and',
      '|': 'or',
      '<': 'lt',
      '>': 'gt',
      '=': 'eq',
      }

UnaryOpTable = {
      '-': 'neg',
      '~': 'not',
      }


class TokenType(Enum):
  keyword = auto()
  symbol = auto()
  identifier = auto() # letter, digits, _, not starting with digit
  integerConstant = auto() # 0..32767
  stringConstant = auto() # no double quote or newline

class Token():
  value = ''
  kind = ''
  def __init__(self, value, kind):
    self.value = value
    self.kind = kind

  def typestr(self):
    return self.kind.name

  def str(self):
    return self.value

  def htmlstr(self):
    return html.escape(self.value)

class JackLexer():
  tokens = []
  state = 0
  cursor = 0
  def __init__(self, path):
    #print("lexer with path: %s" % path)
    self.tokens = []
    self.state = 0 # 1 if comment
    self.cursor = 0
    file = open(path, 'r')
    lines = file.readlines()
    for line in lines:
      #print("lexer with line: %s" % line)
      if (self.state == 0):
        self.parse(line)
      else: # find ending comment block
        si = line.find("*/")
        if si != -1:
          self.state = 0
          self.parse(line[si+2:])
    if self.state != 0:
      raise ValueError("No ending block comment")

  def parse(self, str):
    #print("parse with: %s" % str)
    if not str:
      return
    s = 0
    si = len(str)
    qi = str.find('"')
    if qi != -1:
      s = 1
      si = qi
      #print("quote with s: %d si: %d" % (s, si))
    lci = str.find("//")
    if lci != -1 and lci < si:
      s = 2
      si = lci
      #print("line comment with s: %d si: %d" % (s, si))
    lbi = str.find("/*")
    if lbi != -1 and lbi < si:
      s = 3
      si = lbi
      #print("block comment with s: %d si: %d" % (s, si))

    if s == 0:
      for w in str.split():
        self.parse_word(w)
      return 0
    if s == 1:
      qi = str.find('"', si+1)
      if qi == -1:
        raise ValueError("No matching \"")
      if si > 0:
        self.parse(str[0:si])
      self.tokens.append(Token(str[si+1:qi], TokenType.stringConstant))
      self.parse(str[qi+1:])
      return 0
    if s == 2:
      self.parse(str[0:si])
      return 0
    if s == 3:
      self.state = 1
      self.parse(str[0:si])
      str = str[si+2:]
      si = str.find("*/")
      if si != -1:
        self.state = 0
        self.parse(str[si+2:])
      return 0

  def token_type(self, token):
    if token in Keywords:
      return TokenType.keyword
    if token.isnumeric():
      return TokenType.integerConstant
    if token.isidentifier():
      return TokenType.identifier
    raise ValueError("Invalid token %s" % token)

  def parse_word(self, word):
    #print("parse_word with: %s" % word)
    for i in range(len(word)):
      #print("testing word[%d]: %s" % (i, word[i]))
      if word[i] in Symbols:
        #print("testing word[%d]: %s true" % (i, word[i]))
        if i >= 1:
          token = word[0:i]
          self.tokens.append(Token(token, self.token_type(token)))
        self.tokens.append(Token(word[i], TokenType.symbol))
        if i+1 < len(word):
          self.parse_word(word[i+1:])
        return
    #print("testing word: %s false" % (word))
    self.tokens.append(Token(word, self.token_type(word)))

  def next(self):
    if (self.cursor >= len(self.tokens)):
      return None
    token = self.tokens[self.cursor]
    self.cursor += 1
    return token

class JackCompileEngine:
  lexer = ''
  file = ''
  vmfile = ''
  indent = 0
  token = ''
  symbolTable = None
  className = ''
  labelIndex = 0

  def __init__(self, input, output, vmoutput):
    self.lexer = JackLexer(input)
    self.file = open(output, 'w')
    self.vmfile = open(vmoutput, 'w')
    self.indent = 0
    self.token = self.lexer.next()
    self.symbolTable = SymbolTable()

  def outputNontermBegin(self, kind):
    self.file.write("%s<%s>\n" % ('  ' * self.indent, kind))

  def outputNontermEnd(self, kind):
    self.file.write("%s</%s>\n" % ('  ' * self.indent, kind))
  
  def eatKeyword(self, str):
    t = self.token
    if (t.kind != TokenType.keyword):
      return None
    if (t.str() != str):
      return None
    self.file.write("%s<%s> %s </%s>\n" % ('  ' * self.indent, t.typestr(), t.htmlstr(), t.typestr()))
    self.token = self.lexer.next()
    return t 

  def eatIdentifier(self):
    t = self.token
    if (t.kind != TokenType.identifier):
      return None
    self.file.write("%s<%s> %s </%s>\n" % ('  ' * self.indent, t.typestr(), t.htmlstr(), t.typestr()))
    self.token = self.lexer.next()
    return t 
  
  def eatSymbol(self, str):
    t = self.token
    if (t.kind != TokenType.symbol):
      return None
    if (t.str() != str):
      return None
    self.file.write("%s<%s> %s </%s>\n" % ('  ' * self.indent, t.typestr(), t.htmlstr(), t.typestr()))
    self.token = self.lexer.next()
    return t 

  def eatIntegerConstant(self):
    t = self.token
    if (t.kind != TokenType.integerConstant):
      return None
    self.file.write("%s<%s> %s </%s>\n" % ('  ' * self.indent, t.typestr(), t.htmlstr(), t.typestr()))
    self.token = self.lexer.next()
    return t 
  
  def eatStringConstant(self):
    t = self.token
    if (t.kind != TokenType.stringConstant):
      return None
    self.file.write("%s<%s> %s </%s>\n" % ('  ' * self.indent, t.typestr(), t.htmlstr(), t.typestr()))
    self.token = self.lexer.next()
    return t 

  def compileClass(self):
    self.outputNontermBegin('class')
    self.indent += 1
    if not self.eatKeyword('class'):
      raise ValueError("Expect keyword class")
    if not (t := self.eatIdentifier()):
      raise ValueError("Expect identifier")
    self.className = t.value
    if not self.eatSymbol('{'):
      raise ValueError("Expect symbol {")
    while self.token.str() == 'static' or self.token.str() == 'field':
      self.compileClassVarDec()
    while self.token.str() == 'constructor' or self.token.str() == 'function' or self.token.str() == 'method':
      self.compileSubroutineDec()
    if not self.eatSymbol('}'):
      raise ValueError("Expect symbol }")

    self.indent = 0
    self.outputNontermEnd('class')
    print("class %s dumping symbol table" % self.className)
    self.symbolTable.debug()

  def eatType(self):
    if t := self.eatKeyword('int'):
      return t
    if t := self.eatKeyword('char'):
      return t
    if t := self.eatKeyword('boolean'):
      return t
    if t := self.eatIdentifier():
      return t
    return None

  def eatOp(self):
    if t := self.eatSymbol('+'):
      return t
    if t := self.eatSymbol('-'):
      return t
    if t := self.eatSymbol('*'):
      return t
    if t := self.eatSymbol('/'):
      return t
    if t := self.eatSymbol('&'):
      return t
    if t := self.eatSymbol('|'):
      return t
    if t := self.eatSymbol('<'):
      return t
    if t := self.eatSymbol('>'):
      return t
    if t := self.eatSymbol('='):
      return t
    return None

  def compileClassVarDec(self):
    self.outputNontermBegin('classVarDec')
    self.indent += 1
    kind = self.token.str()
    if not self.eatKeyword('static'):
      if not self.eatKeyword('field'):
        raise ValueError("Expect keyword static or field")
    if not (t := self.eatType()):
      raise ValueError("Expect type but got %s" % self.token.str())
    datatype = t.str()
    if not (t := self.eatIdentifier()):
      raise ValueError("Expect identifier as varName")
    self.symbolTable.addClassSymbol(t.str(), kind, datatype)
    while self.token.str() == ',':
      self.eatSymbol(',')
      if not (t := self.eatIdentifier()):
        raise ValueError("Expect identifier as varName")
      self.symbolTable.addClassSymbol(t.str(), kind, datatype)
    if not self.eatSymbol(';'):
      raise ValueError("Expect symbol ;")

    self.indent -= 1
    self.outputNontermEnd('classVarDec')

  def compileSubroutineDec(self):
    self.outputNontermBegin('subroutineDec')
    self.indent += 1

    if t := self.eatKeyword('constructor'):
      type = 'constructor'
    elif t := self.eatKeyword('function'):
      type = 'function'
    elif t := self.eatKeyword('method'):
      type = 'method'
    else:
      raise ValueError("Expect keyword constructor or function or method")

    if not self.eatKeyword('void'):
      if not self.eatType():
        raise ValueError("Expect type or void but got %s" % self.token.str())
    if not (t := self.eatIdentifier()):
      raise ValueError("Expect identifier as subroutineName")
    self.symbolTable.newSub(t.str())
    if not self.eatSymbol('('):
      raise ValueError("Expect symbol (")
    if type == 'method':
      self.symbolTable.addSubSymbol('this', 'argument', self.className)
    self.compileParameterList()
    if not self.eatSymbol(')'):
      raise ValueError("Expect symbol )")
    self.compileSubroutineBody(type)

    self.indent -= 1
    self.outputNontermEnd('subroutineDec')

  def compileParameterList(self):
    self.outputNontermBegin('parameterList')
    self.indent += 1
    while True:
      if not (t := self.eatType()):
        break
      datatype = t.str()
      if not (t := self.eatIdentifier()):
        raise ValueError("Expect identifier as varName")
      self.symbolTable.addSubSymbol(t.str(), 'argument', datatype)
      if not self.eatSymbol(','):
        break
    self.indent -= 1
    self.outputNontermEnd('parameterList')

  def compileSubroutineBody(self, type):
    self.outputNontermBegin('subroutineBody')
    self.indent += 1

    if not self.eatSymbol('{'):
      raise ValueError("Expect symbol {")

    if type == 'constructor':
      self.symbolTable.addSubSymbol('this', 'local', self.className)
    while self.token.str() == 'var':
      self.compileVarDec()

    self.writeCode('function %s.%s %d' % (self.className, self.symbolTable.subName, self.symbolTable.varCount('local')))
    if type == 'constructor':
      self.writeCode('push constant %d' % self.symbolTable.varCount('field'))
      self.writeCode('call Memory.alloc 1')
      self.writeCode("pop pointer 0")
      self.writeCode("push pointer 0")
      self.writeCode("pop %s" % self.symbolTable.get('this'))
    elif type == 'method':
      self.writeCode("push %s" % self.symbolTable.get('this'))
      self.writeCode('pop pointer 0')

    self.compileStatements()

    if not self.eatSymbol('}'):
      raise ValueError("Expect symbol }")

    self.indent -= 1
    self.outputNontermEnd('subroutineBody')

  def compileVarDec(self):
    self.outputNontermBegin('varDec')
    self.indent += 1

    if not self.eatKeyword('var'):
      raise ValueError("Expect keyword var")
    if not (t := self.eatType()):
      raise ValueError("Expect type but got %s" % self.token.str())
    datatype = t.str()
    if not (t := self.eatIdentifier()):
      raise ValueError("Expect identifier as varName")
    self.symbolTable.addSubSymbol(t.str(), 'local', datatype)
    while self.token.str() == ',':
      self.eatSymbol(',')
      if not (t := self.eatIdentifier()):
        raise ValueError("Expect identifier as varName")
      self.symbolTable.addSubSymbol(t.str(), 'local', datatype)
    if not self.eatSymbol(';'):
      raise ValueError("Expect symbol ;")

    self.indent -= 1
    self.outputNontermEnd('varDec')

  def compileStatements(self):
    self.outputNontermBegin('statements')
    self.indent += 1

    while True:
      if self.token.str() == 'let':
        self.compileLetStatement()
      elif self.token.str() == 'if':
        self.compileIfStatement()
      elif self.token.str() == 'while':
        self.compileWhileStatement()
      elif self.token.str() == 'do':
        self.compileDoStatement()
      elif self.token.str() == 'return':
        self.compileReturnStatement()
      else:
        break

    self.indent -= 1
    self.outputNontermEnd('statements')

  def compileLetStatement(self):
    self.outputNontermBegin('letStatement')
    self.indent += 1
    arrVar = False
 
    if not self.eatKeyword('let'):
      raise ValueError("Expect keyword let")
    if not (t := self.eatIdentifier()):
      raise ValueError("Expect identifier as varName")
    varName = t.value
    if self.token.str() == '[':
      arrVar = True
      self.writeCode("push %s" % self.symbolTable.get(varName))
      if not self.eatSymbol('['):
        raise ValueError("Expect symbol [")
      self.compileExpression()
      if not self.eatSymbol(']'):
        raise ValueError("Expect symbol ]")
      self.writeCode("add")

    if not self.eatSymbol('='):
      raise ValueError("Expect symbol =")
    self.compileExpression()
    if not self.eatSymbol(';'):
      raise ValueError("Expect symbol ;")
    
    if arrVar:
      self.writeCode("pop temp 0")
      self.writeCode("pop pointer 1")
      self.writeCode("push temp 0")
      self.writeCode("pop that 0")
    else:
      self.writeCode("pop %s" % self.symbolTable.get(varName))

    self.indent -= 1
    self.outputNontermEnd('letStatement')

  def compileIfStatement(self):
    self.outputNontermBegin('ifStatement')
    self.indent += 1

    if not self.eatKeyword('if'):
      raise ValueError("Expect keyword if")
    if not self.eatSymbol('('):
      raise ValueError("Expect symbol (")
    self.compileExpression()
    if not self.eatSymbol(')'):
      raise ValueError("Expect symbol )")
    if not self.eatSymbol('{'):
      raise ValueError("Expect symbol {")
    label1 = self.getLabel()
    label2 = self.getLabel()
    self.writeCode('not')
    self.writeCode('if-goto %s' % label1)
    self.compileStatements()
    self.writeCode('goto %s' % label2)
    if not self.eatSymbol('}'):
      raise ValueError("Expect symbol }")
    self.writeCode('label %s' % label1)
    if self.token.str() == 'else':
      if not self.eatKeyword('else'):
        raise ValueError("Expect keyword else")
      if not self.eatSymbol('{'):
        raise ValueError("Expect symbol {")
      self.compileStatements()
      if not self.eatSymbol('}'):
        raise ValueError("Expect symbol }")
    self.writeCode('label %s' % label2)

    self.indent -= 1
    self.outputNontermEnd('ifStatement')

  def compileWhileStatement(self):
    self.outputNontermBegin('whileStatement')
    self.indent += 1

    label1 = self.getLabel()
    label2 = self.getLabel()
    if not self.eatKeyword('while'):
      raise ValueError("Expect keyword while")
    if not self.eatSymbol('('):
      raise ValueError("Expect symbol (")
    self.writeCode('label %s' % label1)
    self.compileExpression()
    self.writeCode('not')
    self.writeCode('if-goto %s' % label2)
    if not self.eatSymbol(')'):
      raise ValueError("Expect symbol )")
    if not self.eatSymbol('{'):
      raise ValueError("Expect symbol {")
    self.compileStatements()
    if not self.eatSymbol('}'):
      raise ValueError("Expect symbol }")
    self.writeCode('goto %s' % label1)
    self.writeCode('label %s' % label2)

    self.indent -= 1
    self.outputNontermEnd('whileStatement')

  def compileDoStatement(self):
    self.outputNontermBegin('doStatement')
    self.indent += 1
    funcName = ''
    argCnt = 0

    if not self.eatKeyword('do'):
      raise ValueError("Expect keyword do")
    if not (t := self.eatIdentifier()):
      raise ValueError("Expect identifier")
    name = t.value
    if self.token.str() == '.':
      self.eatSymbol('.')
      if not (t := self.eatIdentifier()):
        raise ValueError("Expect identifier as subroutineName")
      if type:= self.symbolTable.getType(name):
        funcName = "%s.%s" % (type, t.value)
        #print("XXXXXXXXX %s" % funcName)
        self.writeCode("push %s" % self.symbolTable.get(name))
        argCnt += 1
      else:
        funcName = "%s.%s" % (name, t.value)
        #print("YYYYYYYYY %s" % funcName)
    else:
      funcName = "%s.%s" % (self.className, name)
      #print("ZZZZZZZZ %s" % funcName)
      self.writeCode("push %s" % self.symbolTable.get('this'))
      argCnt += 1
    if not self.eatSymbol('('):
      raise ValueError("Expect symbol (")
    argCnt += self.compileExpressionList()
    if not self.eatSymbol(')'):
      raise ValueError("Expect symbol )")
    if not self.eatSymbol(';'):
      raise ValueError("Expect symbol ;")
    self.writeCode("call %s %d" % (funcName, argCnt))
    self.writeCode("pop temp 0")

    self.indent -= 1
    self.outputNontermEnd('doStatement')

  def compileReturnStatement(self):
    self.outputNontermBegin('returnStatement')
    self.indent += 1
    if not self.eatKeyword('return'):
      raise ValueError("Expect keyword return")
    if self.token.str() == ';':
      self.eatSymbol(';')
      self.writeCode("push constant 0")
    else:
      self.compileExpression()
      if not self.eatSymbol(';'):
        raise ValueError("Expect symbol ;")

    self.writeCode("return")
    self.indent -= 1
    self.outputNontermEnd('returnStatement')

  def compileExpression(self):
    self.outputNontermBegin('expression')
    self.indent += 1

    self.compileTerm()
    while self.token.str() in "+-*/&|<>=":
      t = self.eatOp()
      self.compileTerm()
      self.writeCode(BinaryOpTable[t.str()])

    self.indent -= 1
    self.outputNontermEnd('expression')

  def eatConstant(self):
    if t := self.eatIntegerConstant():
      return t
    if t := self.eatStringConstant():
      return t
    if t := self.eatKeyword('true'):
      return t
    if t := self.eatKeyword('false'):
      return t
    if t := self.eatKeyword('null'):
      return t
    if t := self.eatKeyword('this'):
      return t
    return None

  def eatUnaryOp(self):
    if t := self.eatSymbol('-'):
      return t
    if t := self.eatSymbol('~'):
      return t
    return None

  def writeConstant(self, t):
    if t.kind == TokenType.integerConstant:
      self.writeCode("push constant %s" % t.value)
    elif t.kind == TokenType.stringConstant:
      self.writeCode('push constant %d' % (len(t.value)+1))
      self.writeCode('call String.new 1')
      for i in t.value:
        self.writeCode('push constant %d' % ord(i))
        self.writeCode('call String.appendChar 2')
    elif t.value == 'true':
      self.writeCode('push constant 1')
      self.writeCode('neg')
    elif t.value == 'false':
      self.writeCode('push constant 0') 
    elif t.value == 'null':
      self.writeCode('push constant 0') 
    elif t.value == 'this':
      self.writeCode("push %s" % self.symbolTable.get('this'))

  def compileTerm(self):
    self.outputNontermBegin('term')
    self.indent += 1
    funcName = ''
    argCnt = 0

    if t := self.eatConstant():
      self.writeConstant(t)
    else:
      if self.eatSymbol('('):
        self.compileExpression()
        if not self.eatSymbol(')'):
          raise ValueError("Expect symbol )")
      elif t := self.eatUnaryOp():
        self.compileTerm()
        self.writeCode(UnaryOpTable[t.str()])
      else:
        if not (t := self.eatIdentifier()):
          raise ValueError("Expect identifier")
        name = t.value
        if self.eatSymbol('['): # array
          self.writeCode("push %s" % self.symbolTable.get(name))
          self.compileExpression()
          if not self.eatSymbol(']'):
            raise ValueError("Expect symbol ]")
          self.writeCode("add")
          self.writeCode("pop pointer 1")
          self.writeCode("push that 0")
        elif self.eatSymbol('.'): # method call on object NAME
          if not (t := self.eatIdentifier()):
            raise ValueError("Expect identifier as subroutineName")
          if not self.eatSymbol('('):
            raise ValueError("Expect symbol (")
          if type:= self.symbolTable.getType(name):
            funcName = "%s.%s" % (type, t.value)
            self.writeCode("push %s" % self.symbolTable.get(name))
            argCnt += 1
          else:
            funcName = "%s.%s" % (name, t.value)
          argCnt += self.compileExpressionList()
          self.compileExpressionList()
          if not self.eatSymbol(')'):
            raise ValueError("Expect symbol )")
          self.writeCode("call %s %d" % (funcName, argCnt))
        elif self.eatSymbol('('): # method call on this object
          funcName = "%s.%s" % (self.className, name)
          self.writeCode("push argument 0")
          argCnt = self.compileExpressionList() + 1
          if not self.eatSymbol(')'):
            raise ValueError("Expect symbol )")
          self.writeCode("call %s %d" % (funcName, argCnt))
        else: # plain variable
          self.writeCode("push %s" % self.symbolTable.get(name))

    self.indent -= 1
    self.outputNontermEnd('term')

  def compileExpressionList(self):
    self.outputNontermBegin('expressionList')
    self.indent += 1
    argCnt = 0
    
    if self.token.str() != ')':
      self.compileExpression()
      argCnt += 1
      while self.token.str() == ',':
        self.eatSymbol(',')
        self.compileExpression()
        argCnt += 1

    self.indent -= 1
    self.outputNontermEnd('expressionList')
    return argCnt

  def getLabel(self):
    l = "L%d" % (self.labelIndex)
    self.labelIndex += 1
    return l

  def writeCode(self, code):
    self.vmfile.write('%s\n' % code)

class SymbolTable:
  classTable = {}
  fieldIndex = 0
  staticIndex = 0
  subDict = {}
  subName = ''

  def __init__(self):
    self.classTable = {}
    self.fieldIndex = 0
    self.staticIndex = 0
    self.subDict = {}
    self.subName = ''

  def addClassSymbol(self, name, kind, datatype):
    if name in self.classTable:
      raise ValueError("Duplicate class var %s" % name)
    if kind == 'field':
        self.classTable[name] = (kind, datatype, self.fieldIndex)
        self.fieldIndex += 1
    else:
        self.classTable[name] = (kind, datatype, self.staticIndex)
        self.staticIndex += 1

  def addSubSymbol(self, name, kind, datatype):
    s = self.subDict[self.subName]
    t = s["symtable"]
    if name in t:
      raise ValueError("Duplicate symbol %s in subroutine %s" % (name, self.subName))
    if kind == 'local':
        t[name] = (kind, datatype, s["localIndex"])
        s["localIndex"] += 1
    else:
        t[name] = (kind, datatype, s["argIndex"])
        s["argIndex"] += 1

  def newSub(self, name):
    self.subDict[name] = {}
    self.subDict[name]["localIndex"] = 0
    self.subDict[name]["argIndex"] = 0
    self.subDict[name]["symtable"] = {}
    self.subName = name

  def varCount(self, kind):
    if kind == "field":
        return self.fieldIndex
    elif kind == "static":
        return self.staticIndex
    elif kind == "local":
        return self.subDict[self.subName]["localIndex"]
    elif kind == "arg":
        return self.subDict[self.subName]["argIndex"]
    return -1

  def get(self, varName):
    s = self.subDict[self.subName]
    t = s["symtable"]
    if varName in t:
      return "%s %s" % (t[varName][0], t[varName][2])
    if varName in self.classTable:
      kind = self.classTable[varName][0]
      if kind == 'field':
        segment = 'this'
      else:
        segment = 'static'
      return "%s %s" % (segment, self.classTable[varName][2])
    raise ValueError("Undefined var name %s in %s" % (varName, self.subName))

  def getType(self, varName):
    s = self.subDict[self.subName]
    t = s["symtable"]
    if varName in t:
      return t[varName][1]
    if varName in self.classTable:
      return self.classTable[varName][1]
    return None

  def debug(self):
    print("\ndumping classTable\n")
    print(json.dumps(self.classTable))
    print("\ndumping subDict\n")
    print(json.dumps(self.subDict))


class JackCompiler:
  path = ''

  def __init__(self, path):
    print("Compiler init with %s" % path)
    self.path = path

  def output_token(self, output):
    print("output_token to %s" % output)
    file = open(output, 'w')
    file.write("<tokens>\n")
    lexer = JackLexer(self.path)
    t=lexer.next()
    while t:
      file.write("<%s> %s </%s>\n" % (t.typestr(), t.htmlstr(), t.typestr()))
      t=lexer.next()
    file.write("</tokens>\n")

  def output_tree(self, output, vmoutput):
    print("output_tree to %s" % output)
    engine = JackCompileEngine(self.path, output, vmoutput)
    engine.compileClass()

def main():
  if (len(sys.argv) != 2):
    print("Usage: xx");
    return 1

  if os.path.isdir(sys.argv[1]):  
    directory = os.fsencode(sys.argv[1])
    for file in os.listdir(directory):
      filename = os.fsdecode(file)
      if filename.endswith(".jack"): 
        token_output="%sT.my.xml" % os.path.splitext(filename)[0]
        output="%s.my.xml" % os.path.splitext(filename)[0]
        vmoutput="%s.vm" % os.path.splitext(filename)[0]
        path = os.path.join(directory, file)
        x = JackCompiler(os.fsdecode(path))
        x.output_token(os.path.join(sys.argv[1], token_output))
        x.output_tree(os.path.join(sys.argv[1], output), os.path.join(sys.argv[1], vmoutput))
  elif os.path.isfile(sys.argv[1]):  
    if not sys.argv[1].endswith(".jack"): 
      print("File %s is not jack file")
      return 1

    token_output="%sT.my.xml" % os.path.splitext(sys.argv[1])[0]
    output="%s.my.xml"  % os.path.splitext(sys.argv[1])[0]
    vmoutput="%s.vm"  % os.path.splitext(sys.argv[1])[0]
    x = JackCompiler(sys.argv[1])
    x.output_token(token_output)
    x.output_tree(output, vmoutput)
  else:
    print("Invalid arg %s" % sys.argv[1])
    return 1

if __name__ == "__main__":
  main()
