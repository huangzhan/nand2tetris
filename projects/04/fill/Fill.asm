// This file is part of www.nand2tetris.org
// and the book "The Elements of Computing Systems"
// by Nisan and Schocken, MIT Press.
// File name: projects/04/Fill.asm

// Runs an infinite loop that listens to the keyboard input.
// When a key is pressed (any key), the program blackens the screen,
// i.e. writes "black" in every pixel;
// the screen should remain fully black as long as the key is pressed. 
// When no key is pressed, the program clears the screen, i.e. writes
// "white" in every pixel;
// the screen should remain fully clear as long as no key is pressed.

// while (true) {
// 	if (KBD != 0) {
//         black=1
// 	} else {
// 	   black=0
//  	}
// 	fill(black)
// }
(LOOP)
@KBD
D=M
@WHITE
D;JEQ
@black
M=-1
@FILL
0;JMP
(WHITE)
@black
M=0

(FILL)
@8192
D=A
@size
M=D
@i
M=0

@SCREEN
D=A
@ptr
M=D

(FILLOOP)
@size
D=M
@i
D=D-M
@LOOP
D;JEQ

@black
D=M
@ptr
A=M
M=D

@i
M=M+1
@ptr
M=M+1
@FILLOOP
0;JMP

@LOOP
0;JMP
