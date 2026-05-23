      ******************************************************************
      * INTEREST.COB  --  second golden demo module for LAZARUS.
      * Daily simple-interest accrual: interest = principal * rate.
      *
      * THE IDIOM (DIFFERENT from payroll.cob): a COBOL `COMPUTE` WITHOUT
      * `ROUNDED` *TRUNCATES* the extra fraction digits — it drops them,
      * never rounds. Legacy financial systems do this deliberately (the
      * institution keeps the sub-cent). A naive Python translation that
      * uses round() rounds the half-up/half-even way and diverges on any
      * input whose raw interest has a non-zero 3rd decimal >= the rounding
      * threshold (e.g. 13.33 -> COBOL 0.49 vs round() 0.50). This is the
      * OPPOSITE trap from payroll.cob (which needed ROUND-HALF-UP); the
      * differential oracle catches both.
      ******************************************************************
       IDENTIFICATION DIVISION.
       PROGRAM-ID. INTEREST.

       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  WS-PRINCIPAL   PIC 9(7)V99 COMP-3.
       01  WS-RATE        PIC V9999   VALUE 0.0375.
       01  WS-INTEREST    PIC 9(7)V99 COMP-3.
       01  WS-IN          PIC X(12).

       PROCEDURE DIVISION.
       MAIN-PARA.
           ACCEPT WS-IN.
           MOVE FUNCTION NUMVAL(WS-IN) TO WS-PRINCIPAL.
      *    No ROUNDED: COBOL truncates the product to the field's 2 decimals.
           COMPUTE WS-INTEREST = WS-PRINCIPAL * WS-RATE.
           DISPLAY WS-INTEREST.
           STOP RUN.
