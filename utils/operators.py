def Bool(x):
    if x == None:
        return None
    if isinstance(x, str):
        if x == 'True' or x == 'true':
            return True
        elif x == 'False' or x == 'false':
            return False
        else:
            return None
    return bool(x)


def Int(x):
    try:
        return int(x)
    except:
        return None
def Float(x):
    try:
        x = float(x)
        return x
    except:
        return None