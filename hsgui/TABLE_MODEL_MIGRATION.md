# GUI table model migration inventory

This inventory records the behavior of the data tables before the
`QTableWidget` to model/view migration. It is intentionally limited to the
four flat tables in `MainSkel.ui`.

## Tables and data identity

| Object | Columns before user properties | Stable row identity | Editable behavior |
| --- | --- | --- | --- |
| `gxs_TBL` | `gx`, `gname`, `nCxs`, `aif` | image index (`gx`) | `aif` is a checkbox |
| `cxs_TBL` | `cid`, `name`, `gname`, `nGt`, `nKpts`, `theta`, then user properties | chip ID (`cid`) | `name` and user properties; Boolean properties are checkboxes |
| `nxs_TBL` | `nx`, `name`, `nCxs` | name index (`nx`) | `name` |
| `res_TBL` | `rank`, `score`, `name`, `cid` | chip ID (`cid`) | `name` |

The old population loop used temporary visible row numbers while creating
items, then recovered IDs by reading a cell from the same visible row. That is
unsafe once a proxy sorts or filters the rows. The replacement model therefore
stores the stable ID alongside each lightweight row record.

## Population and refresh

`MainWindowBackend._populate_table` constructs plain column lists and tuples
for all four tables and emits `populateSignal`. `MainWindowFrontend.populate_tbl`
then delegates to `_populate_table`, which previously cleared each widget,
created one `QTableWidgetItem` for every cell, and restored the header sort
indicator. All table refresh entry points eventually use this signal.

The tables have dynamic chip-property columns, so their column metadata may
change between refreshes. Model instances should remain attached to their
views while their column definitions and rows are reset.

## Presentation behavior to preserve

- Internal column keys are distinct from display labels such as `cid` / `Chip
  ID`; internal keys are used for editing and filtering.
- Every cell is horizontally centered.
- Editable cells have an RGB `(250, 240, 240)` background.
- Native integer and float values are retained for numeric sorting.
- Boolean values are displayed and edited as checkboxes.
- Vertical headers are hidden.
- Rows, rather than individual cells, are selected. Population currently sets
  every table to single selection, including the result table whose Designer
  file originally requested extended selection.
- The `name` columns in the chip and name tables are twice the default section
  width.
- Image, chip, and result tables explicitly start sorted by column zero in
  ascending order. The name table inherits Qt's original column-zero
  descending sort indicator when population first enables sorting.
- The result view retains `Qt.ElideLeft`.
- Tab captions contain the number of currently visible rows.

There are no table cell icons, cell tooltips, foreground colors, hidden
columns, custom cell widgets, alternating-row styling, or table-specific row
heights in the current implementation.

## Interaction behavior to preserve

- A non-editable cell click selects the image, chip, query result, or name.
  Repeated clicks on the same cell and clicks on editable cells are ignored by
  the selection handler.
- There are no table double-click, Enter-key, selection-change, or body context
  menu handlers in the current code.
- The chip-table horizontal header has a context menu for user-defined
  properties. It can edit/rename or delete a property and must continue to
  resolve the stable internal column key.
- The Filter Table dialog filters the current table with exact, shell-wildcard,
  or `re:` regular-expression conditions, combined with logical AND. Blank and
  `None` conditions are inactive. Clear Filter clears every table.
- Edits are dispatched to backend methods with a stable image, chip, or name
  ID and an internal column key. CSV commas in text edits are represented as
  `;;`, matching the existing workflow.

## UI source and generation note

`hsgui/_frontend/MainSkel.ui` is the Designer source. At the start of the
migration, `setup.py::compile_ui` still pointed to Python 2/PyQt4 `pyuic4` and
the source contained obsolete generated menu actions. The source now contains
the current widget/menu shell, actions remain dynamically owned by `guifront`,
the build command uses PyQt5, and `MainSkel.py` has been regenerated from the
updated source.
