"""Text and numeric formatting helpers for HotSpotter."""

import decimal

import numpy as np

from . import tools


def horiz_string(str_list):
    """Join possibly multiline values side by side."""
    all_lines = []
    hpos = 0
    for value in str_list:
        lines = str(value).split('\n')
        line_diff = len(lines) - len(all_lines)
        if line_diff > 0:
            all_lines += [' ' * hpos] * line_diff
        for line_index, line in enumerate(lines):
            all_lines[line_index] += line
            hpos = max(hpos, len(all_lines[line_index]))
        for line_index in range(len(all_lines)):
            hpos_diff = hpos - len(all_lines[line_index])
            if hpos_diff > 0:
                all_lines[line_index] += ' ' * hpos_diff
    return '\n'.join(all_lines)


def remove_chars(instr, illegals_chars):
    outstr = instr
    for ill_char in illegals_chars:
        outstr = outstr.replace(ill_char, '')
    return outstr


def indent(string, indent='    '):
    return indent + string.replace('\n', '\n' + indent)


def truncate_str(str, maxlen=110):
    if len(str) < maxlen:
        return str
    truncmsg = ' ~~~TRUNCATED~~~ '
    maxlen_ = maxlen - len(truncmsg)
    lowerb = int(maxlen_ * .8)
    upperb = maxlen_ - lowerb
    return str[:lowerb] + truncmsg + str[-upperb:]


def pack_into(instr, textwidth=160, breakchars=' ', break_words=True):
    newlines = ['']
    word_list = instr.split(breakchars)
    for word in word_list:
        if len(newlines[-1]) + len(word) > textwidth:
            newlines.append('')
        while break_words and len(word) > textwidth:
            newlines[-1] += word[:textwidth]
            newlines.append('')
            word = word[textwidth:]
        newlines[-1] += word + ' '
    return '\n'.join(newlines)


def str2(obj):
    if isinstance(obj, dict):
        return str(obj).replace(', ', '\n')[1:-1]
    if isinstance(obj, type):
        return str(obj).replace('<type \'', '').replace('\'>', '')
    return str(obj)


def num_fmt(num, max_digits=1):
    if tools.is_float(num):
        return ('%.' + str(max_digits) + 'f') % num
    if tools.is_int(num):
        return int_comma_str(num)
    return repr(num)


def int_comma_str(num):
    return '{:,}'.format(int(num))


def fewest_digits_float_str(num, n=8):
    int_part = int(num)
    dec_part = num - int_part
    x = decimal.Decimal(dec_part, decimal.Context(prec=8))
    decimal_list = x.as_tuple()[1]
    nonzero_pos = 0
    for index in range(0, min(len(decimal_list), n)):
        if decimal_list[index] != 0:
            nonzero_pos = index
    sig_dec = int(dec_part * 10 ** (nonzero_pos + 1))
    return int_comma_str(int_part) + '.' + str(sig_dec)


def commas(num, n=8):
    if tools.is_float(num):
        return '%.3f' % num
    return '%d' % num


def format(num, n=8):
    """Format a number compactly for legacy reports."""
    if num is None:
        return 'None'
    if tools.is_float(num):
        ret = ('%.' + str(n) + 'E') % num
        exp_pos = ret.find('E')
        exp_part = ret[(exp_pos + 1):].replace('+', '')
        if exp_part.find('-') == 0:
            exp_part = '-' + exp_part[1:].strip('0')
        exp_part = exp_part.strip('0')
        if exp_part:
            exp_part = 'E' + exp_part
        flt_part = ret[:exp_pos].strip('0').strip('.')
        return flt_part + exp_part
    return '%d' % num


def float_to_decimal(f):
    """Convert a floating-point number to an exact Decimal."""
    numerator_value, denominator_value = f.as_integer_ratio()
    numerator = decimal.Decimal(numerator_value)
    denominator = decimal.Decimal(denominator_value)
    ctx = decimal.Context(prec=60)
    result = ctx.divide(numerator, denominator)
    while ctx.flags[decimal.Inexact]:
        ctx.flags[decimal.Inexact] = False
        ctx.prec *= 2
        result = ctx.divide(numerator, denominator)
    return result


def sigfig_str(number, sigfig):
    assert sigfig > 0
    try:
        value = decimal.Decimal(number)
    except TypeError:
        value = float_to_decimal(float(number))
    sign, digits, exponent = value.as_tuple()
    if len(digits) < sigfig:
        digits = list(digits)
        digits.extend([0] * (sigfig - len(digits)))
    shift = value.adjusted()
    result = int(''.join(map(str, digits[:sigfig])))
    if len(digits) > sigfig and digits[sigfig] >= 5:
        result += 1
    result = list(str(result))
    shift += len(result) - sigfig
    result = result[:sigfig]
    if shift >= sigfig - 1:
        result += ['0'] * (shift - sigfig + 1)
    elif 0 <= shift:
        result.insert(shift + 1, '.')
    else:
        result = ['0.'] + ['0'] * (-shift - 1) + result
    if sign:
        result.insert(0, '-')
    return ''.join(result)


def joins(string, list_, with_head=True, with_tail=False, tostrip='\n'):
    head = string if with_head else ''
    tail = string if with_tail else ''
    return (head + string.join(map(str, list_)) + tail).strip(tostrip)


def indent_list(indent, list_):
    return [indent + str(item) for item in list_]
