# NOT FOR USE IN PRODUCTION

k = 30
while True:
    lines = [input() for i in range(3)]
    out = [f"{k}:A(2)_J"]
    for line in lines:
        out.append(line.replace("COORD:", "").replace(":", "#"))

    print(":".join(out))
    k += 1
