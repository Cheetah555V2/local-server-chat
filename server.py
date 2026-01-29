import socket
from threading import Thread, Lock

HOST = '0.0.0.0'
PORT = 21001
s = None

connected_clients_number = 0
next_client_id = 1
clients = {}  # client_id -> conn
messages = []  # each message: {'from': id, 'text': str, 'need_to_send': [ids]}
clients_lock = Lock()
messages_lock = Lock()


def client_processor(conn, client_id):
    global connected_clients_number

    try:
        while True:
            data = conn.recv(4096)
            if not data:
                print(f"Client {client_id} disconnected")
                with clients_lock:
                    if client_id in clients:
                        del clients[client_id]
                connected_clients_number -= 1
                break

            message_text = data.decode()
            print(f"Received message from client {client_id}: {message_text}")

            # Build message with recipients = all current clients except sender
            with clients_lock:
                recipients = [cid for cid in clients.keys() if cid != client_id]

            msg = {"from": client_id, "text": message_text, "need_to_send": recipients}

            # Append to global messages and prepare per-client payloads
            with messages_lock:
                messages.append(msg)

                # Prepare payloads: collect any undelivered messages for each client
                payloads = {}
                current_client_ids = []
                with clients_lock:
                    current_client_ids = list(clients.keys())

                for cid in current_client_ids:
                    payloads[cid] = []

                for m in messages:
                    # iterate over a copy of need_to_send to allow modification
                    for cid in list(m['need_to_send']):
                        if cid in payloads:
                            payloads[cid].append(f"From {m['from']}: {m['text']}")
                        # mark as delivered to this cid
                        if cid in m['need_to_send']:
                            try:
                                m['need_to_send'].remove(cid)
                            except ValueError:
                                pass

                # Remove messages that have been delivered to everyone
                messages[:] = [m for m in messages if m['need_to_send']]

            # Send payloads (do not hold messages_lock while sending network IO)
            with clients_lock:
                for cid, payload_list in payloads.items():
                    conn_to_send = clients.get(cid)
                    if not conn_to_send:
                        continue
                    try:
                        if payload_list:
                            payload = "\n".join(payload_list)
                        else:
                            payload = "No new messages for you for now!"
                        conn_to_send.send(payload.encode())
                    except Exception as e:
                        print(f"Error sending to client {cid}: {e}")
                        # remove client on send failure
                        try:
                            del clients[cid]
                        except KeyError:
                            pass
                        connected_clients_number -= 1

    except Exception as e:
        print(f"Exception in client processor {client_id}: {e}")
    finally:
        try:
            conn.close()
        except Exception:
            pass


try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print("Socket created")
except OSError as msg:
    s = None
    print(f"Error creating socket: {msg}")
    exit(1)

try:
    s.bind((HOST, PORT))
    s.listen()
    print("Socket bound and listening")
except OSError as msg:
    print("Error binding/listening!")
    s.close()
    exit(1)

while True:
    conn, addr = s.accept()
    print("Client connected from address: ", addr)

    # assign unique ID
    with clients_lock:
        client_id = next_client_id
        next_client_id += 1
        clients[client_id] = conn

    connected_clients_number += 1

    # send assigned ID to client immediately
    try:
        conn.send(f"ID:{client_id}".encode())
    except Exception as e:
        print(f"Failed to send ID to client {client_id}: {e}")

    client_thread = Thread(target=client_processor, args=(conn, client_id))
    client_thread.start()

s.close()
print("Server finished")