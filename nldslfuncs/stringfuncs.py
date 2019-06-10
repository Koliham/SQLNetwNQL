def isnum(wert: str):
    try:
        a = float(wert)
        return True
    except:
        pass
    try:
        b = int(wert)
        return True
    except:
        pass
    return False







if __name__ == "__main__":
    a = []
    # a.append(0)
    # a.append(0.0)
    a.append("0")
    a.append("0.0")
    a.append("4")
    a.append("4.0")
    a.append("3.8")
    a.append("asdasf")
    a.append("")

    for w in a:
        print(w,"\t",type(w),"\t",isnum(w))