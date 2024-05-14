import re

def parseFile(path):
    with open(path, 'r') as file:
        data = file.read()

    matches = re.findall(r".*\n@N:(.*?):(.*?):1:(.*?):(.*?):.*?:.*?:(.*?):0\n\$FP.*?:\*A:(.*?):(.*?):.*?:(.*?):.*?:.*?:(.*?):(.*?):.*?:00:0:0::/v/:(.*?)\n", data)
    return matches



if __name__ == "__main__":
    parseFile("sessions/OBS_SS_PT2_Lesson2.txt")
