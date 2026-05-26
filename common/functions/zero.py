def zero_str(count):
    if 10 < count < 100:
        return f"0{count}"
    elif count < 10:
        return f"00{count}"
    else:
        return str(count)
