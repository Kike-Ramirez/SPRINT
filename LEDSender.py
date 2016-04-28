# -*- coding: utf-8 -*-

# Module for communication with LED Screen C-Power2200
# Only text. No image mode implemented.
# 
# *******************
# Developer: Kike Ramirez - Espadaysantacruz Studio 
# Date: 21/4/2016
# v1.0

import serial, io, time, binascii, contextlib

portA = '/dev/ttyUSB1'
portB = '/dev/ttyUSB0'

serA = None
serB = None

timerSend = 0.02
baud = 115200


# Función que devuelve el checksum de una cadena hexadecimal
def checksumFFFF(cadena):
    
    decodedCadena = cadena.decode('hex')
    cksum = hex(sum(map(ord, decodedCadena)))[2:]
    n = len(cksum)
    checksum = ''
    for i in range(n,4):
        checksum += '0'
    checksum += str(cksum)
    checksum = checksum[2:4] + checksum[0:2]
    return checksum

# Función que parsea el Command Code del protocolo de comunicación del C-Power2200
def commandParser(effect, alignHor, alignVert, speed, stay, fontsize, fonttype, texto):

    # Define Header - POS 11-12
    commandString = "1200"

    # Define Effect - POS 13
    effect = hex(effect)[2:]
    for i in range(len(effect), 2): 
        commandString += '0'
    commandString += effect

    #Alignment - POS 14
    aligns = {0 : '00', 1 : '01', 2 : '10'}
    alignText = aligns[alignVert] + aligns[alignHor]
    alignment = hex(int(alignText, 2))[2:]
    for i in range(len(alignment), 2): 
        commandString += '0'
    commandString += alignment

    # Speed - POS 15
    speedString = hex(speed)[2:]
    for i in range(len(alignment), 2): 
        commandString += '0'
    commandString += speedString

    # Stay Time - POS 16-17
    stayTime = hex(stay)[2:]
    n = len(stayTime)
    stayString = ''
    for i in range(n,4):
        stayString +='0'
    stayString += stayTime
    commandString += stayString

    # Font Size and Type
    fonts1 = {0:'0000', 1:'0001', 2:'0010', 3:'0011', 4:'0100', 5:'0101', 6:'0110', 7:'0111'}
    fonts2 = {0:'000', 1:'001', 2:'010', 3:'011', 4:'100', 5:'101', 6:'110', 7:'111'}
    fontText =  '0' + fonts2[fonttype] + fonts1[fontsize]
    fontCode = hex(int(fontText, 2))[2:]
    n = len(fontCode)
    fontString = ''
    for i in range(n, 2):
        fontString += '0'
    fontString += fontCode
    commandString += fontString

    # RGB Values
    commandString += 'ff0000'

    # Text 
    commandString += texto.encode('hex')

    # Final Character
    commandString += '00'

    return commandString

# Función que recibe el Command Code y parsea el datagrama completo del protocolo de comunicación del C-Power2200
def packetParser(commandString):

    # Start Command
    packetString = 'a5'

    # Packet Type
    packetString += '68'

    # Card Type - Card Id
    packetString += '3201'

    # Protocol Code - Confirmation Mark
    packetString += '7B01'

    # Packet Data Length
    length = hex(len(commandString)/2)[2:]
    lengthString = ''
    for i in range(len(length), 4):
        lengthString += '0'
    lengthString += length
    packetString += lengthString[2:4] + lengthString[0:2]

    # Packet Number and Last Packet Number
    packetString += '0000'

    # Packet Data
    packetString += commandString

    # Checksum
    checksumString = packetString[2:20] + commandString
    packetString += checksumFFFF(checksumString)
         
    # End character data
    packetString += 'ae'

    return packetString

# Función que envía el datagrama a la pantalla correspondiente
def sendString(led = 0, string = 'test', alignHor = 2, effect = 0):
    global serA, serB

    if led == 0:
        ser = serA
    elif led == 1:
        ser = serB


    ser.flushInput()
    commandString = commandParser(effect, alignHor, 1, 0, 1, 1, 3, string)
    # commandParser(effect, alignHor, alignVert, speed, stay, fontsize, fonttype, texto):
    data = packetParser(commandString)
    datahex = binascii.a2b_hex(data)
    time.sleep(timerSend)
    ser.write(datahex)

# Función que resetea la pantalla correspondiente
def sendReset(led = 0):
    global serA, serB

    if led == 0:
        ser = serA
    elif led == 1:
        ser = serB   

    ser.flushInput()
    commandString = '06'
    data = packetParser(commandString)
    datahex = binascii.a2b_hex(data)
    time.sleep(timerSend)
    ser.write(datahex)

# Función que abre la comunicación serial con las dos pantallas
def open():
    global serA, serB

    serA = serial.Serial(portA, baud, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS, timeout=0)
    serB = serial.Serial(portB, baud, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS, timeout=0)
 
    
# Función que cierra la comunicación serial con ambas pantallas
def close():
    global serA, serB

    serA.close()   
    serB.close()   