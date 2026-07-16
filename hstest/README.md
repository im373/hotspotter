# HotSpotter tests

This directory contains the tests and smoke scripts that still exercise the
current Python 3 application. Historical diagnostics and obsolete experiments
are retained in [`legacy/`](legacy/README.md).

## Automated tests

Run the non-interactive unit tests with:

```powershell
python -m unittest discover -s hstest -p "test_*.py" -v
```

These tests do not require a HotSpotter database or a visible GUI.

## Smoke and integration scripts

Run smoke scripts as modules from the repository root so Python includes the
repository packages on its import path. Pass a disposable test database when
applicable:

```powershell
python -m hstest.small_test --dbdir "F:\path\to\test-database" --strict
python -m hstest.query_test --dbdir "F:\path\to\test-database" --strict
```

Do not launch these files by pathname (`python hstest/small_test.py`). In that
form Python places `hstest/`, rather than the repository root, on `sys.path`
and imports such as `hsdev` will not resolve.

The current scripts cover:

- application and database startup (`small_test.py`);
- query and GUI startup (`query_test.py`);
- new database and image import (`newdb_test.py`);
- multi-query, vsone, chip, feature, and spatial-verification workflows;
- a destructive end-to-end workflow (`big_test.py`).

`big_test.py` and `newdb_test.py` modify database contents. Only run them
against disposable data or a verified clone. Add `--interactive` to scripts
that support it when the Qt event loop should remain open for inspection.

Legacy files are excluded from normal unittest and pytest collection. They are
retained as implementation references and are not expected to import or
execute cleanly.
