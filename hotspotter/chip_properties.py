"""Validation, comparison, and type handling for chip properties."""


import hashlib
import json
import math


PROPERTY_DATATYPES = ('str', 'int', 'float', 'bool')
INTEGER_MIN = -(2 ** 63)
INTEGER_MAX = (2 ** 63) - 1
PROPERTY_IMPORTANCE = {
    0: 'Not significant',
    1: 'Important feature',
    2: 'Permanent feature',
}

RESERVED_PROPERTY_NAMES = {
    '#chips', '#gt', '#kpts', 'aif', 'all detected', 'chip id', 'cid',
    'confidence', 'gx', 'gname', 'image index', 'image name', 'match_name',
    'matching name', 'matching_name', 'name', 'name index', 'ncxs', 'ngt',
    'nkpts', 'nx', 'rank', 'roi', 'roi (x, y, w, h)', 'score', 'theta',
}


def normalize_property_definition(datatype='str', importance=0):
    """Validate and normalize a property definition."""
    datatype = str(datatype).strip().lower()
    if datatype not in PROPERTY_DATATYPES:
        raise ValueError(
            'Property datatype must be one of %r, not %r' % (
                PROPERTY_DATATYPES,
                datatype,
            )
        )
    try:
        importance = int(importance)
    except (TypeError, ValueError):
        raise ValueError('Property importance must be 0, 1, or 2')
    if importance not in PROPERTY_IMPORTANCE:
        raise ValueError('Property importance must be 0, 1, or 2')
    return {
        'datatype': datatype,
        'importance': importance,
    }


def validate_property_name(name, existing_names=(), original_name=None):
    """Return a safe property name or raise ``ValueError``."""
    name = str(name).strip()
    if not name:
        raise ValueError('Property name cannot be empty')
    if any(char in name for char in ',\r\n'):
        raise ValueError('Property names cannot contain commas or newlines')
    lowered = name.lower()
    if lowered in RESERVED_PROPERTY_NAMES:
        raise ValueError('%r is reserved for a built-in column' % name)
    original_lower = (
        None if original_name is None else str(original_name).lower()
    )
    existing_lower = {str(key).lower() for key in existing_names}
    if lowered in existing_lower and lowered != original_lower:
        raise ValueError('A chip property named %r already exists' % name)
    return name


def default_property_value(datatype):
    """Return the default cell value for a datatype."""
    normalize_property_definition(datatype)
    return ''


def is_empty_property_value(value):
    """Return whether a property value represents an unset metadata cell."""
    return value is None or (isinstance(value, str) and not value.strip())


def coerce_property_value(value, datatype):
    """Convert a CSV or GUI value to the declared property datatype."""
    datatype = normalize_property_definition(datatype)['datatype']
    if is_empty_property_value(value):
        return ''
    if datatype == 'str':
        return str(value)
    if datatype == 'int':
        try:
            converted = int(value)
        except (OverflowError, TypeError, ValueError) as ex:
            raise ValueError('%r is not a valid integer value' % value) from ex
        if converted < INTEGER_MIN or converted > INTEGER_MAX:
            raise ValueError(
                'Integer metadata must be between %d and %d; got %r' % (
                    INTEGER_MIN,
                    INTEGER_MAX,
                    value,
                )
            )
        return converted
    if datatype == 'float':
        try:
            converted = float(value)
        except (OverflowError, TypeError, ValueError) as ex:
            raise ValueError('%r is not a valid float value' % value) from ex
        if not math.isfinite(converted):
            raise ValueError(
                'Float metadata must be finite; got %r' % value
            )
        return converted
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    text = str(value).strip().lower()
    if text in ('0', 'false', 'no', 'off'):
        return False
    if text in ('1', 'true', 'yes', 'on'):
        return True
    raise ValueError('%r is not a valid boolean value' % value)


def permanent_metadata_constraints(prop_dict, prop_metadata, cx):
    """Return the nonempty permanent metadata values for one chip."""
    constraints = {}
    prop_metadata = prop_metadata or {}
    for key, values in prop_dict.items():
        definition = prop_metadata.get(key, {})
        if int(definition.get('importance', 0)) < 2:
            continue
        value = values[cx]
        if not is_empty_property_value(value):
            constraints[key] = value
    return constraints


def metadata_matches_constraints(prop_dict, cx, constraints):
    """Return whether a chip satisfies constraints, treating empty as wildcard."""
    for key, expected in constraints.items():
        value = prop_dict[key][cx]
        if not is_empty_property_value(value) and value != expected:
            return False
    return True


def _json_property_value(value):
    if is_empty_property_value(value):
        return None
    scalar_item = getattr(value, 'item', None)
    if callable(scalar_item):
        value = scalar_item()
    if isinstance(value, (bool, int, float, str)):
        return value
    return str(value)


def permanent_metadata_uid(prop_dict, prop_metadata):
    """Return a stable cache suffix for all permanent metadata state."""
    prop_metadata = prop_metadata or {}
    payload = []
    for key in sorted(prop_dict):
        definition = prop_metadata.get(key, {})
        if int(definition.get('importance', 0)) < 2:
            continue
        payload.append({
            'key': key,
            'datatype': definition.get('datatype', 'str'),
            'values': [_json_property_value(value)
                       for value in prop_dict[key]],
        })
    serialized = json.dumps(
        payload,
        sort_keys=True,
        separators=(',', ':'),
    ).encode('utf-8')
    return '_PMETA' + hashlib.sha1(serialized).hexdigest()[:16]


def definitions_for_properties(property_keys, saved_definitions=None):
    """Return normalized definitions for the current chip properties."""
    saved_definitions = saved_definitions or {}
    definitions = {}
    for key in property_keys:
        definition = saved_definitions.get(key, {})
        if not isinstance(definition, dict):
            raise ValueError(
                'Definition for property %r must be an object' % key
            )
        definitions[key] = normalize_property_definition(
            definition.get('datatype', 'str'),
            definition.get('importance', 0),
        )
    return definitions
