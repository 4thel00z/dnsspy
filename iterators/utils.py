import re

def split_iter(string):
    return (x.group(0) for x in re.finditer(r"[A-Za-z\-0-9']+", string))
