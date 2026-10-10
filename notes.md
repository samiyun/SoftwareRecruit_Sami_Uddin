### relations with rover and basestation
- rover and base station act as client and server, rover makes requests
    - for example (in http), rover would make a POST request to transmit whatever data it must deliver
- kind of a flow chart for how rover and base station work:
    - rover: create connection -> send data -> close connection 
    - base station: answer -> process data -> store data

### networking
so in general TCP/UDP, is a way we can transmit data between the computers, 
we either go with TCP or UDP in this task.

TCP establishes a connection by first getting a SYN request from the client (essentially client asking to connect), then server sends a SYN-ACK response (server acknowledges client request), finished off by client sending an ACK request (confirming connection, now client anf server are synced). To end connection, FIN request from the client is sent, ACK response from server for the FIN request, another FIN request is sent to confirm it is ready to close, last ACK response to close connection fully. 

Data that is sent is divided up into segments which are given a sequence (1,2,3,4,5...), the server acknowledges when it recieves a segment. If the server doesnt send a response for a segment, it is resent assuming the data was lost in transmision. 


UDP doesn't establish connections, it's faster, but since there are no acknowledgements between client and server, server will not know about missing data. 

Data that is sent is divided up into datagrams, which is a packet that contains a UDP header and payload (deliverable data), the UDP header is composed of metadata: source port - allows server to identify client to send a response, destination port - identifies servers port number to lead packets there, length - content lenght + header size in bytes, checksum - used to check if anything is corrupted in transmission (it can fail or not)

So in conclusion UDP may not be as viable for our rover since it will be constantly moving away from the server.

So we will use TCP bc:
- TCP (Transmission Control Protocol)
    - conenction flow: SYN (client) --> SYN-ACK (server) --> ACK (client) --> connect
    - disconnection flow: FIN (client) --> ACK (server) --> FIN (client) --> ACK (server) --> disconnects
        - flows are explained in paragraph
    - data is delivered in the same order in which it was sent (tracked by using acknowledgements and counting the sequence of its segments)
    - data transmited is divided into chunks called segments, where each segment is given a sequence
        - the server sends an ACK response for each segment transfered
        - if a segment failed to deliver in time, rover can assume that packet is lost and will resend it

sources:
https://www.geeksforgeeks.org/computer-networks/what-is-transmission-control-protocol-tcp/
https://www.geeksforgeeks.org/computer-networks/user-datagram-protocol-udp/

