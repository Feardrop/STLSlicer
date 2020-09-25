import collections
import json
import numpy as np


class NumpyArrayEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif is_instance_named(obj, "bool_"):
            return bool(str(obj))
        elif is_instance_named(obj, "Path2D"):
            return obj.to_dict()
        else:
            return super(NumpyArrayEncoder, self).default(obj)


def is_instance_named(obj, name):
    """
    Given an object, if it is a member of the class 'name',
    or a subclass of 'name', return True.

    Parameters
    ------------
    obj : instance
      Some object of some class
    name: str
      The name of the class we want to check for

    Returns
    ---------
    is_instance : bool
      Whether the object is a member of the named class
    """
    try:
        type_named(obj, name)
        return True
    except ValueError:
        return False


def type_named(obj, name):
    """
    Similar to the type() builtin, but looks in class bases
    for named instance.

    Parameters
    ------------
    obj: object to look for class of
    name : str, name of class

    Returns
    ----------
    named class, or None
    """
    # if obj is a member of the named class, return True
    name = str(name)
    if obj.__class__.__name__ == name:
        return obj.__class__
    for base in type_bases(obj):
        if base.__name__ == name:
            return base
    raise ValueError("Unable to extract class of name " + name)


def type_bases(obj, depth=4):
    """
    Return the bases of the object passed.
    """
    bases = collections.deque([list(obj.__class__.__bases__)])
    for i in range(depth):
        bases.append([i.__base__ for i in bases[-1] if i is not None])
    try:
        bases = np.hstack(bases)
    except IndexError:
        bases = []
    # we do the hasattr as None/NoneType can be in the list of bases
    bases = [i for i in bases if hasattr(i, "__name__")]
    return np.array(bases)
