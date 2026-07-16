# Legacy test archive

Files in this directory are retained for historical reference. They are not
part of the supported test suite and may contain Python 2-era APIs, hard-coded
paths, missing imports, commented-out implementations, unsafe import-time
execution, or dependencies on old databases and visualization behavior.

The archive includes:

- algorithm and visualization experiments;
- old database conversion and environment diagnostics;
- incomplete GUI and preferences checks;
- machine-specific crash reports;
- scratch multiprocessing and nearest-neighbor investigations.

This directory is excluded from normal unittest and pytest collection. Do not
run its files directly unless you have reviewed their side effects and
requirements. When restoring a legacy test, move it back to `hstest/`, remove
import-time execution, replace printed output with assertions, and make all
database or GUI requirements explicit.
