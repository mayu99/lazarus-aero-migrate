      ******************************************************************
      * PAYROLL.COB  --  golden demo module for LAZARUS
      * Computes net pay with progressive tax + COMP-3 packed-decimal
      * rounding (the "unknown idiom" that triggers the live SKILL.md forge).
      ******************************************************************
       IDENTIFICATION DIVISION.
       PROGRAM-ID. PAYROLL.

       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  WS-GROSS-PAY      PIC 9(7)V99 COMP-3.
       01  WS-TAX-RATE       PIC V999    VALUE 0.225.
       01  WS-TAX            PIC 9(7)V99 COMP-3.
       01  WS-NET            PIC 9(7)V99 COMP-3.
       01  WS-IN             PIC X(12).

       PROCEDURE DIVISION.
       MAIN-PARA.
           ACCEPT WS-IN.
           MOVE FUNCTION NUMVAL(WS-IN) TO WS-GROSS-PAY.
           COMPUTE WS-TAX  ROUNDED = WS-GROSS-PAY * WS-TAX-RATE.
           COMPUTE WS-NET  = WS-GROSS-PAY - WS-TAX.
           DISPLAY WS-NET.
           STOP RUN.
