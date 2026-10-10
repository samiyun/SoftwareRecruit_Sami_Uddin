"""
read write in binary because we get a 24-bit bitmap at the end (text is measured in bits) 
use TCP 

can you provide me skeleton code but explain everything? skeleton code should launch localhost connection, youll 

launch 127.0.0.1:5555 
"""

import socket

# AF_INET for ipv4
# SOCK_STREAM to make a TCP socket
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Allow quick reuse of the port (prevents "Address already in use" errors when testing)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

server_socket.bind(('127.0.0.1', 5555))

# Listen for incoming connections (1 means queue up to 1 unaccepted connection)
server_socket.listen(1)
print("Base station listening on 127.0.0.1:5555")

# 5. Accept a connection (This blocks until the rover connects)
# conn is the new socket object used to send/receive data on this specific connection
# addr is the address of the client
conn, addr = server_socket.accept()
print(f"Connected by {addr}")

# 6. Open the output file in Write Binary mode ('wb')
with open('output.bmp', 'wb') as f:
    while True:
        # 7. Receive data in chunks (1024 bytes at a time)
        # TCP recv() will block until it gets data, or returns b'' if the client closes
        data = conn.recv(1024)
        
        # 8. If data is empty (b''), the client has closed the connection. Break the loop.
        if not data:
            break
            
        # 9. Write the received bytes to the file
        f.write(data)

# 10. Clean up: close the connection and the server socket
conn.close()
server_socket.close()
print("Transfer complete. File saved as output.bmp")