######################### CLIENT CODE ############################
import socket

# HOST = '142.250.66.110'
# PORT = 80

HOST = '127.0.0.1'
PORT = 21001

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))
    print("Connected to server")

    # receive assigned ID from server
    try:
        data = s.recv(1024)
        if data:
            intro = data.decode()
            if intro.startswith("ID:"):
                client_id = intro.split(":", 1)[1]
                print(f"Assigned client ID: {client_id}")
            else:
                print("Server message:", intro)
    except Exception as e:
        print(f"Error receiving initial data: {e}")

    while True:
        message = input("Enter message: ")
        # message = "exit"
        s.send((message).encode())

        message_received = ""
        data = s.recv(32768)
        if not data:
            print("Server disconnected")
            break

        message_received += data.decode()

        print("Server answer: ", message_received)

    s.close()

print("Client finished")