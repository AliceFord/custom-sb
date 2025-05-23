import socket
import threading
import sys
from Constants import ACTIVE_CONTROLLERS

PORT = 6809  # 6810 for internet connection

SERVER = "127.0.0.1"
ADDR = (SERVER, PORT)

controllers = []
pilots = []


def esConvert(*args):
    return (":".join(args) + "\r\n").encode("UTF-8")


class ControllerHandler:
    def __init__(self, sock: socket.socket) -> None:
        self.sock = sock

        self.callsign = ""
        self.server = ""
        self.cid = ""
        self.name = ""
        self.password = ""
        # other stuff I don't care about
        self.lat = ""
        self.lon = ""
        self.range = ""

        self.freq = ""

    def handle(self, message: str):
        message = message.split(":")
        if message[0].startswith("#AA"):
            self.callsign = message[0][3:]
            self.server = message[1]
            self.name = message[2]
            self.cid = message[3]
            self.password = message[4]
            self.lat = message[9]
            self.lon = message[10]
            self.range = message[11]

            self.sock.sendall(esConvert("#TMserver", self.callsign, "Vatsim UK FSD Server"))

            return 0

        elif message[0].startswith("%" + self.callsign):
            self.freq = message[1]
            self.lat = message[5]
            self.lon = message[6]

            return 1  # forward message to other controllers

        elif message[0].startswith("$CQ" + self.callsign):
            #print(message)
            if message[2] == "IP":
                self.sock.sendall(esConvert("$CR" + self.server, self.callsign, "ATC", "Y", self.callsign))
                return 0
            if message[2] == "FP":
                planeInQuestion = message[3]
                for pilot in pilots:
                    if pilot.callsign == planeInQuestion:
                        self.sock.sendall(esConvert(*pilot.fpMessage))  # flightplan
                        self.sock.sendall(esConvert("$CQ" + self.server, self.callsign, "BC", planeInQuestion, pilot.squawk))  # squawk
                        break
                return 0

            return 1

        else:
            pass

        return 1


class PilotHandler:
    def __init__(self, sock: socket.socket) -> None:
        self.sock = sock

        self.callsign = ""
        self.server = ""
        self.cid = ""
        self.name = ""
        self.password = ""
        # other stuff I don't care about
        self.lat = ""
        self.lon = ""
        self.range = ""

        self.freq = ""

        self.squawk = "0000"

        self.fpMessage = ""

    def handle(self, message: str):
        message = message.split(":")
        if message[0].startswith("#AP"):
            self.callsign = message[0][3:]
            self.server = message[1]
            self.cid = message[2]
            self.password = message[3]
            self.name = message[7]

            return 0

        elif message[0].startswith("@N"):
            self.squawk = message[2]
            return 2

        elif message[0].startswith("$FP"):
            self.fpMessage = message
            return 2

        return 2


server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(ADDR)


def handle_client(conn: socket.socket, addr):
    global controllers, pilots
    print(f"[NEW CONNECTION] {addr} connected.")
    connected = True
    firstMessage = True
    messageHandler = None
    controllerPilotType = None
    while connected:
        try:
            messages = conn.recv(262144).decode("UTF-8")
            for message in messages.split("\r\n"):
                if message == "":
                    continue
                if firstMessage:
                    firstMessage = False
                    if "AA" in message:  # Login controller
                        messageHandler = ControllerHandler(conn)
                        controllers.append(messageHandler)
                        controllerPilotType = "controller"
                    elif "AP" in message:
                        messageHandler = PilotHandler(conn)
                        pilots.append(messageHandler)
                        controllerPilotType = "pilot"

                status = messageHandler.handle(message)
                if status == 1:
                    for controller in controllers:
                        if controller.callsign != messageHandler.callsign:  # not us, but is an actual human that cares about packets  #  and controller.callsign in ACTIVE_CONTROLLERS
                            controller.sock.sendall(esConvert(message))
                elif status == 2:
                    for controller in controllers:
                        controller.sock.sendall(esConvert(message))

        except ConnectionResetError:
            print(f"[DISCONNECTED] {addr} disconnected.")
            connected = False
        except UnicodeDecodeError:
            print("POTATO")
        except Exception as e:
            print("HUGE POTATO")
            print(e)

    conn.shutdown(socket.SHUT_RDWR)
    conn.close()
    if controllerPilotType == "controller":
        controllers.remove(messageHandler)
    else:
        pilots.remove(messageHandler)


def start():
    server.settimeout(5)
    server.listen()
    print(f"[LISTENING] Server is listening on {SERVER}")
    while True:
        try:
            conn, addr = server.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
        except socket.timeout:
            pass
        except Exception:
            break
    
    sys.exit()


print("[STARTING] server is starting...")
start()
