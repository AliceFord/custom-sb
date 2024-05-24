import select
import socket


# sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# sock.setblocking(0)
# sock.bind(("127.0.0.1", "12345"))
# sock.listen(5)

serverIP = "2.tcp.eu.ngrok.io"
serverPort = 11211

# serverIP = input("Enter the server IP: ")
# serverPort = int(input("Enter the server port: "))
print(1)

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.bind(("127.0.0.1", 6809))
print(2)



server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
print(4)
op = server.connect((serverIP, serverPort))
print(5)

client.listen()
print(2.5)
clientConn, clientAddr = client.accept()
print(3)

print(op)

while True:
    socketReady = select.select([clientConn], [], [], 0.5)  # 1 second timeout
    if socketReady[0]:
        messages = clientConn.recv(5246000)
        print(messages)
        server.sendall(messages)

    socketReady = select.select([server], [], [], 0.5)  # 1 second timeout
    if socketReady[0]:
        messages = server.recv(5246000)
        print(messages)
        clientConn.sendall(messages)
