# !/usr/bin/env python2.7  

# $PRINT Installation
# *******************
# Client: OXFAM INTERMON
# Developer: Kike Ramirez - Espadaysantacruz Studio 
# Date: 21/4/2016
# v1.0

# Importamos librerias y modulo de comunicacion con pantalla LED  
import RPi.GPIO as GPIO  
import time
import LEDSender as LED
import math
import yaml


# Declaracion de variables
# ========================

# Cuenta de vueltas totales y parciales (0: BICI A, 1: BICI B, 2: TOTAL)
vueltasTotal = [0, 0, 0]
vueltasParcial = [0, 0, 0]

# velocidad instantanea
velocidad = 0

# Timers => 0: CheckSpeed - 1: CheckStatus - 2: Cuenta Atras - 3: CheckGame - 4: Frozen Results - 5: Record
timerEnd = None
timerCheck = [0, 0, 0, 0, 0, 0]

# Cadenas de texto de la cuenta atras
tituloCuenta = None
textCuenta = None

# Textos de record
textRecordActual = None
textRecordNuevo = None

# Variable usada para ver cuando cambiamos en la cuenta atras (contiene el valor de la cuenta anterior)
cuentaAnt = ''

# Variable que guarda el record actual
record = 0

# Variable que guarda el fraudeFiscal
fraudeFiscal = 0
maxFraudeFiscal = None

# multiplicador que transforma de una vuelta de rueda a una cantidad economica
escalaMoney = None

# Variable que guarda el esfuerzo fiscal
esfuerzoFiscalNumero = 0
esfuerzoFiscal = ''

# Cadenas de texto que se envian en las pantallas
cadenaLEDA = None
cadenaLEDB = None


# ESTADOS DEL JUEGO
# =================
# 0: Standby
# 1: Cuenta Atras
# 2: Jugando
# 3: Resultados
# 4: Record

# Estado actual
status = 0

# Definimos el GPIO
GPIO.setmode(GPIO.BCM)  
  
# GPIO 17 como entrada, pulled up para evitar falsos positivos.   
GPIO.setup(14, GPIO.IN, pull_up_down=GPIO.PUD_UP)  

# GPIO 17 como entrada, pulled up para evitar falsos positivos.   
GPIO.setup(15, GPIO.IN, pull_up_down=GPIO.PUD_UP)
  
def loadYAML():

	global dataMap, maxFraudeFiscal, escalaMoney, timerEnd, textRecordNuevo, textRecordActual, tituloCuenta, textCuenta

	with open('/home/pi/sprint/tree.yaml') as f:

		# Cargamos los parámetros del fichero YAML
		dataMap = yaml.safe_load(f)
		maxFraudeFiscal = dataMap["sprint"]["Economicos"]["FraudeFiscalAnual"]
		escalaMoney = dataMap["sprint"]["Economicos"]["escalaEsfuerzo"]
		timerEnd = [dataMap["sprint"]["Timers"]["Velocidad"], 
					dataMap["sprint"]["Timers"]["Pedaleo"],
					dataMap["sprint"]["Timers"]["CuentaAtras"], 
					dataMap["sprint"]["Timers"]["Juego"], 
					dataMap["sprint"]["Timers"]["Marcador"],
					dataMap["sprint"]["Timers"]["Record"]]
		textRecordNuevo = [dataMap["sprint"]["Textos"]["Record"]["Nuevo"]["Texto"],
							dataMap["sprint"]["Textos"]["Record"]["Nuevo"]["Alineacion"],
							dataMap["sprint"]["Textos"]["Record"]["Nuevo"]["Efecto"]]
		textRecordActual = [dataMap["sprint"]["Textos"]["Record"]["Actual"]["Texto"],
							dataMap["sprint"]["Textos"]["Record"]["Actual"]["Alineacion"],
							dataMap["sprint"]["Textos"]["Record"]["Actual"]["Efecto"]]
		tituloCuenta = 	dataMap["sprint"]["Textos"]["CuentaAtras"]["Titulo"]
		textCuenta = {0: dataMap["sprint"]["Textos"]["CuentaAtras"]["t0"], 
						1: dataMap["sprint"]["Textos"]["CuentaAtras"]["t1"], 
						2: dataMap["sprint"]["Textos"]["CuentaAtras"]["t2"], 
						3: dataMap["sprint"]["Textos"]["CuentaAtras"]["t3"], 
						4: dataMap["sprint"]["Textos"]["CuentaAtras"]["t4"], 
						5: dataMap["sprint"]["Textos"]["CuentaAtras"]["t5"]}


# Funciones callback para cuando recibimos pulsos desde las bicis A y B  
def pulseA(channel):  
 	global vueltasTotal, vueltasParcial
 	vueltasTotal[0] += 1
 	vueltasParcial[0] += 1
 	vueltasTotal[2] += 1
 	vueltasParcial[2] += 1

def pulseB(channel):  
 	global vueltasTotal, vueltasParcial
 	vueltasTotal[1] += 1
 	vueltasParcial[1] += 1
 	vueltasTotal[2] += 1
 	vueltasParcial[2] += 1

# Cuando se detecte un flanco de bajada en los pines 14 o 15 del GPIO   
# se lanza una excepcion y se llama a las funciones pulseA y pulseB  
GPIO.add_event_detect(14, GPIO.FALLING, callback=pulseA, bouncetime=10)  
GPIO.add_event_detect(15, GPIO.FALLING, callback=pulseB, bouncetime=10)  

# Funcion que reinicia el sistema y vuelve al estado inicial
def reStart():
	global vueltasParcial, vueltasTotal, status
	vueltasTotal = [0, 0, 0]
	vueltasParcial = [0, 0, 0]
	status = 0
	LED.sendReset(0)
	LED.sendReset(1)

# Funcion que se llama periodicamente (segun el valor de timerEnd[0]) para
# actualizar los valores de vueltas y velocidad. Si estamos en el estado 0 y 
# se contabilizan 5 pulsos (para evitar electricidad estatica), se lanza el juego.
def checkSpeed():
  global velocidad, vueltasTotal, vueltasParcial, timerCheck, status, cuentaAnt

  # Actualizamos la velocidad
  velocidad = vueltasParcial[2]
  cuentaAnt = 1000

  # Si hay alguien pedaleando 
  if (velocidad > 0):
  	# Actualizamos el timer de pedaleo (no han parado)
  	timerCheck[1] = time.time()
  	# Si estabamos parados, comenzamos el juego
  	if (status == 0) & (vueltasTotal[2] > 5):
  		status = 1
  		cuentaAnt = 1000
  		LED.sendString(0, tituloCuenta, 1, 13)
  		LED.sendString(1, "")
  		timerCheck[2] = time.time()
  vueltasParcial = [0, 0, 0]


# ===================
# INICIO DEL PROGRAMA
# ===================

loadYAML()

# Abrimos el puerto serie
LED.open()

# Tomamos referencia del tiempo
timerCheck[0] = time.time()

# Reiniciamos estados
reStart()

try:
	# Entramos en bucle infinito
	while True:

		# Si el estado es 0 - IDLE -
		if (status == 0):
			# Comprobamos el pedaleo cada segundo por si hay que arrancar
			if (time.time() - timerCheck[0] >= timerEnd[0]):
				checkSpeed()
				timerCheck[0] = time.time()
		
		# Si estamos en el estado 1 - CUENTA ATRAS - mandamos a pantalla los textos		
		if (status == 1):
			cuentaAtras = int(time.time() - timerCheck[2])
			if (cuentaAtras != cuentaAnt):
				if (timerEnd[2] - cuentaAtras-1) >= 0:
					LED.sendString(1, textCuenta[timerEnd[2] - cuentaAtras-1], 1, 6)
					cuentaAnt = cuentaAtras

		# Si estamos en la cuenta atras y se nos ha acabado el tiempo
		if (status == 1) & (time.time() - timerCheck[2] >= timerEnd[2]):
			# Pasamos a estado 2 - JUGANDO - 
			status = 2
			# Inicializamos los valores de timers y vueltas para empezar a jugar
			timerCheck[1] = time.time()
			timerCheck[3] = time.time()
			vueltasTotal = [0, 0, 0]
			vueltasParcial = [0, 0, 0]
			# Reseteamos las pantallas
			LED.sendReset(0)

		# Si estamos en el estado 2 - JUGANDO - 
		if (status == 2):

			print str(time.time() - timerCheck[3])

			# Enviamos texto a la pantalla superior
			cadenaLEDA = ''
			fraudeFiscal = str(int(math.exp((time.time() - timerCheck[3])*0.75 - 30*0.75) * maxFraudeFiscal))
			
			for i in range(len(fraudeFiscal), 13):
				cadenaLEDA += '0'

			cadenaLEDA += fraudeFiscal

			LED.sendString(0, cadenaLEDA)

			# Enviamos cadena a la pantalla inferior
			cadenaLEDB = ''

			ratioA = str(50)
			ratioB = str(50)

			if vueltasTotal[2] != 0:				
				ratioA = str(int(vueltasTotal[0] * 100 / vueltasTotal[2]))
				ratioB = str(100 - int(vueltasTotal[0] * 100 / vueltasTotal[2]))

			cadenaLEDB += ratioA + '% '

			esfuerzoFiscalNumero = int((vueltasTotal[2] * escalaMoney))
			esfuerzoFiscal = str(esfuerzoFiscalNumero)

			for i in range(len(esfuerzoFiscal), 5):
				cadenaLEDB += '0'

			cadenaLEDB += esfuerzoFiscal + ' ' + ratioB + '%'


			LED.sendString(1, cadenaLEDB)			# Comprobamos la velocidad cada segundo


			# Comprobamos la velocidad segun timerEnd[0]
			if (time.time() - timerCheck[0] >= timerEnd[0]):
				checkSpeed()
				timerCheck[0] = time.time()

			# Comprobamos que se mantiene el pedaleo segun timerEnd[1]
			if (time.time() - timerCheck[1] >= timerEnd[1]):
				reStart()

			# Comprobamos que no hemos terminado el timerEnd[3] - Timer del juego
			if (time.time() - timerCheck[3] >= timerEnd[3]):

				# Pasamos a estado 3 - MARCADOR CONGELADO - 
				status = 3
				timerCheck[4] = time.time()

				# Enviamos la cifra total del fraude fiscal a la pantalla superior
				cadenaLEDA = ''
				for i in range(len(fraudeFiscal), 13):
					cadenaLEDA += '0'

				cadenaLEDA += str(int(maxFraudeFiscal))
				LED.sendString(0, cadenaLEDA, 1, 13)

		# Si estamos en modo 3 - CONGELADO - comprobamos el timerEnd[4]
		if (status == 3) & (time.time() - timerCheck[4] >= timerEnd[4]):

			# Si hemos pasado el tiempo, pasamos a estado 4 - Mostrar Records - 
			status = 4
			timerCheck[5] = time.time()

			# Si hay nuevo record, lo mostramos por pantalla
			if record <= esfuerzoFiscalNumero:
				record = esfuerzoFiscalNumero
				LED.sendString(0, textRecordNuevo[0] + '\n' + esfuerzoFiscal + " euros", textRecordNuevo[1], textRecordNuevo[2])			# Comprobamos la velocidad cada segundo
				LED.sendString(1, cadenaLEDB, 1, 13)

			# Si no hay nuevo record, mostramos el antiguo por pantalla
			else:
				LED.sendString(0, textRecordActual[0] + '\n' + str(record) + " euros", textRecordActual[1], textRecordActual[2])			# Comprobamos la velocidad cada segundo
				LED.sendString(1, cadenaLEDB, 1, 0)

		# Si estamos en el modo 4 - MOSTRANDO RECORD - Comprobamos si hemos pasado el timerEnd[5]
		if (status == 4) & (time.time() - timerCheck[5] >= timerEnd[5]):

			# Si es asi, reiniciamos
			reStart()


# En caso de salir, cerrar el GPIO y el puerto serial
except KeyboardInterrupt:  
    GPIO.cleanup()       # clean up GPIO on CTRL+C exit  
    LED.close()
