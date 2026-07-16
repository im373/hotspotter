"""Reusable model/view support for HotSpotter's flat GUI data tables."""

import fnmatch
import numbers
import re

from PyQt5 import QtCore
from PyQt5 import QtGui


RECORD_ID_ROLE = QtCore.Qt.UserRole
RAW_VALUE_ROLE = QtCore.Qt.UserRole + 1
COLUMN_KEY_ROLE = QtCore.Qt.UserRole + 2


def _qt_scalar(value):
    """Convert scalar subclasses to values Qt can store in a QVariant."""
    if isinstance(value, str):
        return str(value)
    if isinstance(value, bool):
        return bool(value)
    if isinstance(value, numbers.Integral):
        return int(value)
    if isinstance(value, numbers.Real):
        return float(value)
    scalar_item = getattr(value, 'item', None)
    if callable(scalar_item):
        scalar = scalar_item()
        if scalar is not value:
            return _qt_scalar(scalar)
    return value


def normalize_filter_condition(condition):
    """Return ``None`` for an inactive condition and stripped text otherwise."""
    if condition is None:
        return None
    condition = str(condition).strip()
    if not condition or condition.lower() == 'none':
        return None
    return condition


def compile_filter_condition(column_key, condition):
    """Build a value predicate for an exact, wildcard, or raw-regex filter."""
    condition = normalize_filter_condition(condition)
    if condition is None:
        return None
    if condition.startswith('re:'):
        try:
            regex = re.compile(condition[3:])
        except re.error as ex:
            raise ValueError(
                'Invalid regular expression for %s: %s' % (column_key, ex)
            )
        return lambda value: regex.fullmatch(str(value)) is not None
    if any(char in condition for char in '*?['):
        return lambda value: fnmatch.fnmatchcase(str(value), condition)
    return lambda value: str(value) == condition


class DataTableModel(QtCore.QAbstractTableModel):
    """Expose lightweight ``(record_id, values)`` rows to a ``QTableView``."""

    cell_edited = QtCore.pyqtSignal(object, str, object)

    def __init__(self, columns=None, rows=None, parent=None):
        super(DataTableModel, self).__init__(parent)
        self._columns = list(columns or [])
        self._rows = []
        self._set_row_storage(rows or [])

    def _set_row_storage(self, rows):
        self._rows = [
            {'id': record_id, 'values': list(values)}
            for record_id, values in rows
        ]

    def rowCount(self, parent=QtCore.QModelIndex()):
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 0 if parent.isValid() else len(self._columns)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None
        row = index.row()
        column = index.column()
        if row >= len(self._rows) or column >= len(self._columns):
            return None
        column_definition = self._columns[column]
        value = self._rows[row]['values'][column]

        if role == QtCore.Qt.DisplayRole:
            if column_definition.get('checkable', False):
                return None
            formatter = column_definition.get('formatter')
            displayed = formatter(value) if formatter is not None else value
            return _qt_scalar(displayed)
        if role in (QtCore.Qt.EditRole, RAW_VALUE_ROLE):
            return _qt_scalar(value)
        if role == RECORD_ID_ROLE:
            return _qt_scalar(self._rows[row]['id'])
        if role == QtCore.Qt.CheckStateRole:
            if column_definition.get('checkable', False):
                if (
                    column_definition.get('nullable', False)
                    and (value is None or value == '')
                ):
                    return QtCore.Qt.PartiallyChecked
                return QtCore.Qt.Checked if bool(value) else QtCore.Qt.Unchecked
            return None
        if role == QtCore.Qt.TextAlignmentRole:
            return column_definition.get(
                'alignment',
                int(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter),
            )
        if role == QtCore.Qt.BackgroundRole:
            if column_definition.get('editable', False):
                return QtGui.QColor(250, 240, 240)
            return None
        if role == QtCore.Qt.ToolTipRole:
            tooltip = column_definition.get('tooltip')
            return tooltip(value) if callable(tooltip) else tooltip
        return None

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if orientation != QtCore.Qt.Horizontal:
            return None
        if section < 0 or section >= len(self._columns):
            return None
        column_definition = self._columns[section]
        if role == QtCore.Qt.DisplayRole:
            return column_definition.get('header', column_definition['key'])
        if role == COLUMN_KEY_ROLE:
            return column_definition['key']
        return None

    def flags(self, index):
        if not index.isValid():
            return QtCore.Qt.NoItemFlags
        flags = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
        column_definition = self._columns[index.column()]
        if column_definition.get('editable', False):
            flags |= QtCore.Qt.ItemIsEditable
        if column_definition.get('checkable', False):
            flags |= QtCore.Qt.ItemIsUserCheckable
            if column_definition.get('nullable', False):
                flags |= QtCore.Qt.ItemIsUserTristate
        return flags

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        if not index.isValid():
            return False
        column = index.column()
        column_definition = self._columns[column]
        if role == QtCore.Qt.CheckStateRole:
            if not column_definition.get('checkable', False):
                return False
            if (
                column_definition.get('nullable', False)
                and int(value) == int(QtCore.Qt.PartiallyChecked)
            ):
                new_value = ''
            else:
                new_value = int(value) == int(QtCore.Qt.Checked)
        elif role == QtCore.Qt.EditRole:
            if not column_definition.get('editable', False):
                return False
            parser = column_definition.get('parser')
            try:
                new_value = parser(value) if parser is not None else value
            except (TypeError, ValueError):
                return False
        else:
            return False

        row = index.row()
        old_value = self._rows[row]['values'][column]
        if old_value == new_value and type(old_value) is type(new_value):
            return False
        self._rows[row]['values'][column] = new_value
        roles = [QtCore.Qt.DisplayRole, QtCore.Qt.EditRole, RAW_VALUE_ROLE]
        if column_definition.get('checkable', False):
            roles.append(QtCore.Qt.CheckStateRole)
        self.dataChanged.emit(index, index, roles)
        self.cell_edited.emit(
            self._rows[row]['id'],
            str(column_definition['key']),
            new_value,
        )
        return True

    def set_rows(self, rows):
        self.beginResetModel()
        self._set_row_storage(rows)
        self.endResetModel()

    def set_table(self, columns, rows):
        """Reset changing column metadata and row data without replacing the model."""
        self.beginResetModel()
        self._columns = list(columns)
        self._set_row_storage(rows)
        self.endResetModel()

    def update_value(self, record_id, column_key, value):
        """Replace one source value without emitting the user-edit signal."""
        source_row = self.source_row_for_id(record_id)
        if source_row is None:
            return False
        try:
            source_column = self.column_index(column_key)
        except KeyError:
            return False
        self._rows[source_row]['values'][source_column] = value
        index = self.index(source_row, source_column)
        roles = [QtCore.Qt.DisplayRole, QtCore.Qt.EditRole, RAW_VALUE_ROLE]
        if self._columns[source_column].get('checkable', False):
            roles.append(QtCore.Qt.CheckStateRole)
        self.dataChanged.emit(index, index, roles)
        return True

    def record_at(self, source_row):
        record = self._rows[source_row]
        return {'id': record['id'], 'values': tuple(record['values'])}

    def record_id_at(self, source_row):
        return self._rows[source_row]['id']

    def column_key(self, source_column):
        return str(self._columns[source_column]['key'])

    def column_keys(self):
        return [self.column_key(column) for column in range(len(self._columns))]

    def column_definitions(self):
        return list(self._columns)

    def column_index(self, column_key):
        for column, definition in enumerate(self._columns):
            if definition['key'] == column_key:
                return column
        raise KeyError('Table has no column %r' % (column_key,))

    def value_at(self, source_row, column_key):
        return self._rows[source_row]['values'][self.column_index(column_key)]

    def source_row_for_id(self, record_id):
        for row, record in enumerate(self._rows):
            if record['id'] == record_id:
                return row
        return None


class DataTableProxyModel(QtCore.QSortFilterProxyModel):
    """Sort native values and apply per-column HotSpotter filter conditions."""

    def __init__(self, parent=None):
        super(DataTableProxyModel, self).__init__(parent)
        self._conditions = {}
        self._predicates = {}
        self.setDynamicSortFilter(True)
        self.setSortRole(RAW_VALUE_ROLE)

    def set_filters(self, conditions):
        normalized = {}
        predicates = {}
        source = self.sourceModel()
        column_keys = set(source.column_keys()) if source is not None else set()
        for column_key, condition in conditions.items():
            condition = normalize_filter_condition(condition)
            if condition is None or column_key not in column_keys:
                continue
            predicates[column_key] = compile_filter_condition(
                column_key,
                condition,
            )
            normalized[column_key] = condition
        self._conditions = normalized
        self._predicates = predicates
        self.invalidateFilter()

    def filters(self):
        return dict(self._conditions)

    def clear_filters(self):
        self.set_filters({})

    def rename_filter_key(self, old_key, new_key):
        conditions = self.filters()
        if old_key in conditions:
            conditions[new_key] = conditions.pop(old_key)
        self.set_filters(conditions)

    def remove_filter_key(self, column_key):
        conditions = self.filters()
        conditions.pop(column_key, None)
        self.set_filters(conditions)

    def filterAcceptsRow(self, source_row, source_parent):
        source = self.sourceModel()
        column_keys = set(source.column_keys())
        return all(
            predicate(source.value_at(source_row, column_key))
            for column_key, predicate in self._predicates.items()
            if column_key in column_keys
        )

    def lessThan(self, left, right):
        left_value = left.data(RAW_VALUE_ROLE)
        right_value = right.data(RAW_VALUE_ROLE)
        if left_value is None or right_value is None:
            return left_value is None and right_value is not None
        numeric_types = (int, float)
        left_numeric = isinstance(left_value, numeric_types) and not isinstance(
            left_value, bool
        )
        right_numeric = isinstance(right_value, numeric_types) and not isinstance(
            right_value, bool
        )
        if left_numeric and right_numeric:
            return left_value < right_value
        if type(left_value) is type(right_value):
            try:
                return left_value < right_value
            except TypeError:
                pass
        return str(left_value) < str(right_value)
