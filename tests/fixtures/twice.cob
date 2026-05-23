      ******************************************************************
      * TWICE.COB -- tiny test fixture for the oracle harness.
      * Reads an integer on stdin, prints it doubled (zero-padded 9(5)).
      * Deterministic, no network, compiles in well under a second.
      * (Named TWICE not DOUBLE: GnuCOBOL transpiles to C and rejects
      *  a program base name that collides with the C keyword 'double'.)
      ******************************************************************
       IDENTIFICATION DIVISION.
       PROGRAM-ID. TWICE.

       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  WS-IN    PIC X(10).
       01  WS-NUM   PIC 9(5).
       01  WS-OUT   PIC 9(5).

       PROCEDURE DIVISION.
       MAIN-PARA.
           ACCEPT WS-IN.
           MOVE FUNCTION NUMVAL(WS-IN) TO WS-NUM.
           COMPUTE WS-OUT = WS-NUM * 2.
           DISPLAY WS-OUT.
           STOP RUN.
