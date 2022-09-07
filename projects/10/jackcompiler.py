#!/usr/bin/env python3
import sys
import os
import html
from enum import Enum, auto

Symbols = '(){}[].,;+-*/&|<>=-~'
Keywords = ['class', 'field', 'static', 'var', 'int', 'char', 'boolean', 'void', 
    'constructor', 'method', 'function', 'let', 'do', 'if', 'else', 'while', 'return', 
    'true', 'false', 'null', 'this']

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
    print("lexer with path: %s" % path)
    self.tokens = []
    self.state = 0 # 1 if comment
    self.cursor = 0
    file = open(path, 'r')
    lines = file.readlines()
    for line in lines:
      print("lexer with line: %s" % line)
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
    print("parse with: %s" % str)
    if not str:
      return
    s = 0
    si = len(str)
    qi = str.find('"')
    if qi != -1:
      s = 1
      si = qi
      print("quote with s: %d si: %d" % (s, si))
    lci = str.find("//")
    if lci != -1 and lci < si:
      s = 2
      si = lci
      print("line comment with s: %d si: %d" % (s, si))
    lbi = str.find("/*")
    if lbi != -1 and lbi < si:
      s = 3
      si = lbi
      print("block comment with s: %d si: %d" % (s, si))

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
    print("parse_word with: %s" % word)
    for i in range(len(word)):
      print("testing word[%d]: %s" % (i, word[i]))
      if word[i] in Symbols:
        print("testing word[%d]: %s true" % (i, word[i]))
        if i >= 1:
          token = word[0:i]
          self.tokens.append(Token(token, self.token_type(token)))
        self.tokens.append(Token(word[i], TokenType.symbol))
        if i+1 < len(word):
          self.parse_word(word[i+1:])
        return
    print("testing word: %s false" % (word))
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
  indent = 0
  token = ''

  def __init__(self, input, output):
    self.lexer = JackLexer(input)
    self.file = open(output, 'w')
    self.indent = 0
    self.token = self.lexer.next()

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
    if not self.eatIdentifier():
      raise ValueError("Expect identifier")
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
    if not self.eatKeyword('static'):
      if not self.eatKeyword('field'):
        raise ValueError("Expect keyword static or field")
    if not self.eatType():
      raise ValueError("Expect type but got %s" % self.token.str())
    if not self.eatIdentifier():
      raise ValueError("Expect identifier as varName")
    while self.token.str() == ',':
      self.eatSymbol(',')
      if not self.eatIdentifier():
        raise ValueError("Expect identifier as varName")
    if not self.eatSymbol(';'):
      raise ValueError("Expect symbol ;")

    self.indent -= 1
    self.outputNontermEnd('classVarDec')

  def compileSubroutineDec(self):
    self.outputNontermBegin('subroutineDec')
    self.indent += 1
    if not self.eatKeyword('constructor'):
      if not self.eatKeyword('function'):
        if not self.eatKeyword('method'):
          raise ValueError("Expect keyword constructor or function or method")
    if not self.eatKeyword('void'):
      if not self.eatType():
        raise ValueError("Expect type or void but got %s" % self.token.str())
    if not self.eatIdentifier():
      raise ValueError("Expect identifier as subroutineName")
    if not self.eatSymbol('('):
      raise ValueError("Expect symbol (")
    self.compileParameterList()
    if not self.eatSymbol(')'):
      raise ValueError("Expect symbol )")
    self.compileSubroutineBody()

    self.indent -= 1
    self.outputNontermEnd('subroutineDec')

  def compileParameterList(self):
    self.outputNontermBegin('parameterList')
    self.indent += 1
    while True:
      if not self.eatType():
        break
      if not self.eatIdentifier():
        raise ValueError("Expect identifier as varName")
      if not self.eatSymbol(','):
        break
    self.indent -= 1
    self.outputNontermEnd('parameterList')

  def compileSubroutineBody(self):
    self.outputNontermBegin('subroutineBody')
    self.indent += 1

    if not self.eatSymbol('{'):
      raise ValueError("Expect symbol {")

    while self.token.str() == 'var':
      self.compileVarDec()

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
    if not self.eatType():
      raise ValueError("Expect type but got %s" % self.token.str())
    if not self.eatIdentifier():
      raise ValueError("Expect identifier as varName")
    while self.token.str() == ',':
      self.eatSymbol(',')
      if not self.eatIdentifier():
        raise ValueError("Expect identifier as varName")
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

    if not self.eatKeyword('let'):
      raise ValueError("Expect keyword let")
    if not self.eatIdentifier():
      raise ValueError("Expect identifier as varName")
    if self.token.str() == '[':
      if not self.eatSymbol('['):
        raise ValueError("Expect symbol [")
      self.compileExpression()
      if not self.eatSymbol(']'):
        raise ValueError("Expect symbol ]")

    if not self.eatSymbol('='):
      raise ValueError("Expect symbol =")
    self.compileExpression()
    if not self.eatSymbol(';'):
      raise ValueError("Expect symbol =")

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
    self.compileStatements()
    if not self.eatSymbol('}'):
      raise ValueError("Expect symbol }")
    if self.token.str() == 'else':
      if not self.eatKeyword('else'):
        raise ValueError("Expect keyword else")
      if not self.eatSymbol('{'):
        raise ValueError("Expect symbol {")
      self.compileStatements()
      if not self.eatSymbol('}'):
        raise ValueError("Expect symbol }")

    self.indent -= 1
    self.outputNontermEnd('ifStatement')

  def compileWhileStatement(self):
    self.outputNontermBegin('whileStatement')
    self.indent += 1

    if not self.eatKeyword('while'):
      raise ValueError("Expect keyword while")
    if not self.eatSymbol('('):
      raise ValueError("Expect symbol (")
    self.compileExpression()
    if not self.eatSymbol(')'):
      raise ValueError("Expect symbol )")
    if not self.eatSymbol('{'):
      raise ValueError("Expect symbol {")
    self.compileStatements()
    if not self.eatSymbol('}'):
      raise ValueError("Expect symbol }")
    self.indent -= 1
    self.outputNontermEnd('whileStatement')

  def compileDoStatement(self):
    self.outputNontermBegin('doStatement')
    self.indent += 1

    if not self.eatKeyword('do'):
      raise ValueError("Expect keyword do")
    if not self.eatIdentifier():
      raise ValueError("Expect identifier")
    if self.token.str() == '.':
      self.eatSymbol('.')
      if not self.eatIdentifier():
        raise ValueError("Expect identifier as subroutineName")
    if not self.eatSymbol('('):
      raise ValueError("Expect symbol (")
    self.compileExpressionList()
    if not self.eatSymbol(')'):
      raise ValueError("Expect symbol )")
    if not self.eatSymbol(';'):
      raise ValueError("Expect symbol ;")

    self.indent -= 1
    self.outputNontermEnd('doStatement')

  def compileReturnStatement(self):
    self.outputNontermBegin('returnStatement')
    self.indent += 1
    if not self.eatKeyword('return'):
      raise ValueError("Expect keyword return")
    if self.token.str() == ';':
      self.eatSymbol(';')
    else:
      self.compileExpression()
      if not self.eatSymbol(';'):
        raise ValueError("Expect symbol ;")

    self.indent -= 1
    self.outputNontermEnd('returnStatement')

  def compileExpression(self):
    self.outputNontermBegin('expression')
    self.indent += 1

    self.compileTerm()
    while self.token.str() in "+-*/&|<>=":
      self.eatOp()
      self.compileTerm()

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

  def compileTerm(self):
    self.outputNontermBegin('term')
    self.indent += 1

    if not self.eatConstant():
      if self.eatSymbol('('):
        self.compileExpression()
        if not self.eatSymbol(')'):
          raise ValueError("Expect symbol )")
      elif self.eatUnaryOp():
        self.compileTerm()
      else:
        if not self.eatIdentifier():
          raise ValueError("Expect identifier")
        if self.eatSymbol('['):
          self.compileExpression()
          if not self.eatSymbol(']'):
            raise ValueError("Expect symbol ]")
        elif self.eatSymbol('.'):
          if not self.eatIdentifier():
            raise ValueError("Expect identifier as subroutineName")
          if not self.eatSymbol('('):
            raise ValueError("Expect symbol (")
          self.compileExpressionList()
          if not self.eatSymbol(')'):
            raise ValueError("Expect symbol )")
        elif self.eatSymbol('('):
          self.compileExpressionList()
          if not self.eatSymbol(')'):
            raise ValueError("Expect symbol )")
    self.indent -= 1
    self.outputNontermEnd('term')

  def compileExpressionList(self):
    self.outputNontermBegin('expressionList')
    self.indent += 1
    
    if self.token.str() != ')':
      self.compileExpression()
      while self.token.str() == ',':
        self.eatSymbol(',')
        self.compileExpression()

    self.indent -= 1
    self.outputNontermEnd('expressionList')

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

  def output_tree(self, output):
    print("output_tree to %s" % output)
    engine = JackCompileEngine(self.path, output)
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
        path = os.path.join(directory, file)
        x = JackCompiler(os.fsdecode(path))
        x.output_token(os.path.join(sys.argv[1], token_output))
        x.output_tree(os.path.join(sys.argv[1], output))
  elif os.path.isfile(sys.argv[1]):  
    if not sys.argv[1].endswith(".jack"): 
      print("File %s is not jack file")
      return 1

    token_output="%sT.my.xml" % os.path.splitext(sys.argv[1])[0]
    output="%s.my.xml"  % os.path.splitext(sys.argv[1])[0]
    x = JackCompiler(sys.argv[1])
    x.output_token(token_output)
    x.output_tree(output)
  else:
    print("Invalid arg %s" % sys.argv[1])
    return 1

if __name__ == "__main__":
  main()
