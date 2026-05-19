def is_empty(value):
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == '':
        return True
    return False
