import os

def readfile(filename,type=str):
    """read file from

    Args:
        filename (string): read the file if not exists create it.

    Returns:
        list: return a list split with \\n
    """    
    if (os.path.isfile(filename)):
        with open(filename,"r",encoding="utf-8") as f:
            out = f.read().split("\n")
        out = [type(x) for x in out if x != '']
        return out
    else:
        with open(filename,"w",encoding="utf-8") as f:
            pass
        return []


def addtxt(filename,msg):
    """add a new line to the given filename

    Args:
        filename (string): the filename to add
        msg (string): the message to add

    Returns:
        None
    """    """"""
    if (os.path.isfile(filename)):
        with open(filename,"a",encoding="utf-8") as f:
            out = f.write(f"{msg}\n")
        return out
    else:
        with open(filename,"w",encoding="utf-8") as f:
            out = f.write(f"{msg}\n")
        return out
    
def newtxt(filename,arr):
    with open(filename,"w",encoding="utf-8") as f:
        for i in range(len(arr)):
            out = f.write(f"{arr[i]}\n")



if (__name__=="__main__"):
    print(readfile("hi.txt"))