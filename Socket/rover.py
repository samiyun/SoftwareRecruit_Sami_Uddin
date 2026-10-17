import socket

# 1. Create a TCP socket
rover_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# 2. Connect to the base station
rover_socket.connect(('127.0.0.1', 5555))
print("Connected to base station.")

# 3. Open the BMP file in Read Binary mode ('rb')
with open('Utah.bmp', 'rb') as f:
    while True:
        # 4. Read a chunk of the file (1024 bytes at a time)
        chunk = f.read(1024)

        # 5. If chunk is empty (b''), we've reached the end of the file. Break.
        if not chunk:
            break

        # 6. Send the chunk over the socket
        # sendall() ensures all bytes in the chunk are sent, unlike send()
        rover_socket.sendall(chunk)

# 7. Clean up: close the socket. This sends a FIN packet to the server,
# causing the server's recv() to return b'' and break its loop.
rover_socket.close()
print("Image transmitted successfully.")
