"""Validation and type handling for user-defined chip properties."""


PROPERTY_DATATYPES = ('str', 'int', 'bool')
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
    datatype = normalize_property_definition(datatype)['datatype']
    return {'str': '', 'int': 0, 'bool': False}[datatype]


def coerce_property_value(value, datatype):
    """Convert a CSV or GUI value to the declared property datatype."""
    datatype = normalize_property_definition(datatype)['datatype']
    if datatype == 'str':
        return '' if value is None else str(value)
    if datatype == 'int':
        if value is None or (isinstance(value, str) and not value.strip()):
            return 0
        if isinstance(value, bool):
            return int(value)
        return int(value)
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    text = '' if value is None else str(value).strip().lower()
    if text in ('', '0', 'false', 'no', 'off'):
        return False
    if text in ('1', 'true', 'yes', 'on'):
        return True
    raise ValueError('%r is not a valid boolean value' % value)


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
