#!/usr/bin/env python

import socket
import threading
import struct
import hashlib
import base64
import getopt

HTTP_METHOD = "GET"
HTTP_VERSION = "HTTP/1.1"
HTTP_BAD_REQUEST = "400 Bad Request\r\n"
HTTP_METHOD_NOT_ALLOWED = "405 Method Not Allowed\r\n"
WEBSOCKET_VERSION = "13"

WEBSOCKET_MAGIC_HANDSHAKE_STRING = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
PORT = 9876


def handshake(request):
    final_line = ""
    close = False
    response = HTTP_VERSION + " "
    lines = request.splitlines()
    #ignore Heading first
    headers = {}
    for line in lines:
        header = line.split(":")
        if len(header) is 1:
            continue
        headers[header[0].strip()] = header[1].strip()
    
    if close:
        return response, close
    print headers 
    response = "HTTP/1.1 101 Switching Protocols\r\n"
    response += "Upgrade: WebSocket\r\n"
    response += "Connection: Upgrade\r\n"
    #to = base64.encodestring("ws://localhost:9876/\r")
    response += "Sec-WebSocket-Accept: " + base64.encodestring(hashlib.sha1(headers['Sec-WebSocket-Key'] + WEBSOCKET_MAGIC_HANDSHAKE_STRING).digest()) + "\r\n"
        
    return response, close
# decode the message from clients
def DecodedCharArrayFromByteStreamIn(stringStreamIn):
    #turn string values into opererable numeric byte values
    byteArray = [ord(character) for character in stringStreamIn]
    datalength = byteArray[1] & 127
    indexFirstMask = 2 
    if datalength == 126:
        indexFirstMask = 4
    elif datalength == 127:
        indexFirstMask = 10
    masks = [m for m in byteArray[indexFirstMask : indexFirstMask+4]]
    indexFirstDataByte = indexFirstMask + 4
    decodedChars = []
    i = indexFirstDataByte
    j = 0
    while i < len(byteArray):
        decodedChars.append( chr(byteArray[i] ^ masks[j % 4]) )
        i += 1
        j += 1
    return decodedChars

#encode the messages to clients
def StringToFrame(data):
    """Turns a string into a WebSocket data frame. Returns a bytes(). 'data' is a string"""
    # copy from chatroom code

    #determine the size of the data we were told to send
    rawData = data#bytearray(data, 'ascii')
    dataLength = len(rawData)
    outputBytes = bytearray()
    outputBytes.append(0x81) #0x81 = text data type
    if dataLength < 0x7D:
        #a nice short length
        outputBytes.append(len(rawData))
    elif dataLength >= 0x7E and len(rawData) < 0xFFFF:
        #two additional bytes of length needed
        outputBytes.append(0x7E)
        outputBytes.append(dataLength >> 8 & 0xFF)
        outputBytes.append(dataLength & 0xFF)
    else:
        #eight additional bytes of length needed
        outputBytes.append(0x7F)
        outputBytes.append(dataLength >> 56 & 0xFF)
        outputBytes.append(dataLength >> 48 & 0xFF)
        outputBytes.append(dataLength >> 40 & 0xFF)
        outputBytes.append(dataLength >> 32 & 0xFF)
        outputBytes.append(dataLength >> 24 & 0xFF)
        outputBytes.append(dataLength >> 16 & 0xFF)
        outputBytes.append(dataLength >> 8 & 0xFF)
        outputBytes.append(dataLength & 0xFF)
        #tack on the raw data now
    for byte in rawData:
        outputBytes.append(ord(byte))
    return bytes(outputBytes)


def handle(conn, addr):
    request = conn.recv(4096)
    response,close = handshake(request)
    conn.send(response)
    # data = conn.recv(1024)
    lock = threading.Lock()

    while 1:
        print "Waiting for data from", conn, addr
        data = conn.recv(1024)

        # original will now like ['H', 'e', 'l', 'l', 'o', ' ', 'W', 'o', 'r', 'l', 'd', '!']
        original = DecodedCharArrayFromByteStreamIn(data)
        if not original:
            print "No data"
            break
        # make it flat
        origin = ''.join(original)

        print "Done"


        print 'Data from', addr, ':', origin

        # Broadcast received data to all clients
        # first frame the data
        ori = StringToFrame(origin)
        lock.acquire()
        [conn.send(ori) for conn in clients]
        lock.release()

    print 'Client closed:', addr
    lock.acquire()
    clients.remove(conn)
    lock.release()
    conn.close()

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('', PORT))
    server.listen(1)
    while 1:
        conn, addr = server.accept()
        print 'Connected by', addr
        clients.append(conn)
        threading.Thread(target = handle, args = (conn, addr)).start()

clients = []
start_server()
