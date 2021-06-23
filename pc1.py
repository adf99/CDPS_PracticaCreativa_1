#!/usr/bin/python3
import sys
from subprocess import call
from lxml import etree
import logging
import os.path
import subprocess
import os
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('creativa')

# Los parametros de entrada al menos son 2: creativa.py operacion
if len(sys.argv) > 1:
	# Cogemos el segundo parametro pa ver que operacion es, Python empieza en 0
	operacion = sys.argv[1]
	# Variable global para iniciar valor
	numeroservidores = 0
	# Y aqui if, else if para los distintas opciones
	if operacion == "create":
		numeroservidores = 2
		# Hay tres parametros?
		if len(sys.argv) == 3:
			if (int(sys.argv[2]) > 0 and int(sys.argv[2]) < 6):
				numeroservidores = int(sys.argv[2])
			else:
				raise ValueError("El numero de servidores debe ser entre 1 y 5 o su valor por defecto.")

		# Numero de servidores en pc1.cfg 
		fout = open("pc1.cfg", 'w')
		fout.write("num_serv=" + str(numeroservidores))
		fout.close()

		logger.debug('Archivo con numero de servidores creado correctamente')

		# Crear todo y editar los XML función genérica para todas las máquinas
		def crear(maquina,LANX):
			ruta = "/mnt/tmp/pc1/" #Ruta en la que debe ejecutarse el script
			call(["qemu-img", "create", "-f", "qcow2", "-b", "/lab/cdps/pc1/cdps-vm-base-pc1.qcow2", maquina+".qcow2"]) # Creamos a partir de la imagen base
			tree = etree.parse('plantilla-vm-pc1.xml')
			root = tree.getroot()
			#A partir de aqui cogemos rutas y las cambiamos como se nos indica para cada maquina
			name = root.find("./name") 
			name.text = maquina
			sourcefromdiskanddevice = root.find("./devices/disk/source[@file='/mnt/tmp/XXX/XXX.qcow2']")
			sourcefromdiskanddevice.set("file",ruta+maquina+".qcow2")
			sourcefrominterfanddevice = root.find("./devices/interface/source[@bridge='XXX']")
			sourcefrominterfanddevice.set("bridge", LANX)
			fout = open(maquina+".xml", 'w')
			fout.write(etree.tounicode(tree, pretty_print=True))
			fout.close()
			if maquina == "lb":		
				devices = root.find("devices")
				interfaceLAN2 = etree.SubElement(devices, "interface", type="bridge")
				sourcefrominterfanddeviceLAN2 = etree.SubElement(interfaceLAN2, "source", bridge="LAN2")
				modefrominterfanddeviceLAN2 = etree.SubElement(interfaceLAN2, "model", type="virtio")
				devices.insert(3, interfaceLAN2)
				fout = open("lb.xml", 'w')
				fout.write(etree.tounicode(tree, pretty_print=True))
				fout.close()
			logger.debug('Configuracion de '+ maquina +' finalizada')
			call(["sudo", "virsh", "define", maquina+".xml"]) # Generamos persistencia de las maquinas

		# Llamamos a la función genérica para cada máquina
		crear("c1","LAN1")
		crear("lb","LAN1")		
		def bucleservidores(caso):
			for i in range(1, numeroservidores + 1):
				if caso == 1:
					crear("s" + str(i), "LAN2")
				else:
					configuracion("s" + str(i), i)
		bucleservidores(1)

		# Bridges
		call(["sudo", "brctl", "addbr", "LAN1"]) #Crea LAN1
		call(["sudo", "brctl", "addbr", "LAN2"]) #Crea LAN2
		call(["sudo", "ifconfig", "LAN1", "up"]) #Activa LAN1
		call(["sudo", "ifconfig", "LAN2", "up"]) #Activa LAN2

		# Paquete de configuracion para mostrar una barra de progreso

		#call(["pip3","install", "progress"])		
		#from progress.bar import IncrementalBar
		#Barra de progreso
		#with IncrementalBar('Processing', max=100, suffix='%(percent)d%%') as bar:

		# Ahora toca configurar ficheros redes, función genérica

		def configuracion(maquina, numservidor):
			# Directorio temporal para cada maquina
			call(["mkdir", maquina])
			# Fichero hostname
			hostname = open("./" + maquina + "/hostname", "w")
			hostname.write(maquina)
			hostname.close()
			# Hacemos copy-in, esta en la ruta /etc
			call(["sudo", "virt-copy-in", "-a", maquina + ".qcow2", "./"+ maquina +"/hostname", "/etc"])

			# 2. Fichero hosts: ver practica 1 foto 7 o archivo host dentro de etc
			hosts = open("./" + maquina +"/hosts", "w")
			hosts.write("127.0.1.1 "+ maquina)
			hosts.write("127.0.0.1 localhost\n")
			hosts.write("::1 ip6-localhost ip6-loopback\n")
			hosts.write("fe00::0 ip6-localnet\n")
			hosts.write("ff00::0 ip6-mcastprefix\n")
			hosts.write("ff02::1 ip6-allnodes\n")
			hosts.write("ff02::2 ip6-allrouters\n")
			hosts.write("ff02::3 ip6-allhosts\n")
			hosts.close()
			# Hacemos copy-in, esta en la ruta /etc
			call(["sudo", "virt-copy-in", "-a", maquina +".qcow2", "./"+ maquina +"/hosts", "/etc"])

			# Fichero interfaces

	    # https://www.cyberciti.biz/faq/setting-up-an-network-interfaces-file/
	    # We always want the loopback interface.
	    #
	    # auto lo
	    # iface lo inet loopback

	    # An example ethernet card setup: (broadcast and gateway are optional)
	    #
	    # auto eth0
	    # iface eth0 inet static
	    #     address 192.168.0.42
	    #     network 192.168.0.0
	    #     netmask 255.255.255.0
	    #     broadcast 192.168.0.255
	    #     gateway 192.168.0.1
	    # Ojo en el balanceador no tiene gateway (puerta) pero c1 y servidores si: el propio balanceador

			interfaces = open("./"+ maquina +"/interfaces", "w")
			interfaces.write("auto lo \n")
			interfaces.write("iface lo inet loopback \n")
			interfaces.write("\n")
			interfaces.write("auto eth0 \n")
			interfaces.write("iface eth0 inet static \n")

			if maquina == "c1":
				interfaces.write("address 10.0.1.2 \n")
				interfaces.write("network 10.0.1.0 \n")
				interfaces.write("netmask 255.255.255.0 \n")
				interfaces.write("broadcast 10.0.1.255 \n")
				interfaces.write("gateway 10.0.1.1 \n")
				interfaces.close()

			elif maquina == "lb":
				interfaces.write("address 10.0.1.1 \n")
				interfaces.write("network 10.0.1.0 \n")
				interfaces.write("netmask 255.255.255.0 \n")
				interfaces.write("broadcast 10.0.1.255 \n")
				interfaces.write(" \n")
				interfaces.write("auto eth1 \n")
				interfaces.write("iface eth1 inet static \n")
				interfaces.write("address 10.0.2.1 \n")
				interfaces.write("network 10.0.2.0 \n")
				interfaces.write("netmask 255.255.255.0 \n")
				interfaces.write("broadcast 10.0.2.255 \n") 
				interfaces.close()
				# Fichero sysctl: https://www.ducea.com/2006/08/01/how-to-enable-ip-forwarding-in-linux/ 
				ipforward = open("./"+ maquina +"/sysctl.conf", "w")
				ipforward.write("net.ipv4.ip_forward=1 \n")
				ipforward.close()
				# Hacemos copy-in, esta en la ruta /etc
				call(["sudo", "virt-copy-in", "-a", maquina +".qcow2", "./"+maquina+"/sysctl.conf", "/etc"])

				# Configuracion de HAPROXY
				# Creamos fichero
				haprox = open("haproxyscript.py", "w")			
				haprox.write("#!/usr/bin/python3\n")	
				haprox.write("import sys\n")
				haprox.write("from subprocess import call\n")
				haprox.write('fout= open("/etc/haproxy/haproxy.cfg", '"'w'"')\n')
				haprox.write('fout.write("global\\n")\n')
				haprox.write('fout.write("\\tlog /dev/log	local0\\n")\n')
				haprox.write('fout.write("\\tlog /dev/log	local1 notice\\n")\n')
				haprox.write('fout.write("\\tchroot /var/lib/haproxy\\n")\n')
				haprox.write('fout.write("\\tstats socket /run/haproxy/admin.sock mode 660 level admin expose-fd listeners\\n")\n')
				haprox.write('fout.write("\\tstats timeout 30s\\n")\n')
				haprox.write('fout.write("\\tuser haproxy\\n")\n')
				haprox.write('fout.write("\\tgroup haproxy\\n")\n')
				haprox.write('fout.write("\\tdaemon\\n")\n')
				haprox.write('fout.write("\\n")\n')
				haprox.write('fout.write("\\tca-base /etc/ssl/certs\\n")\n')
				haprox.write('fout.write("\\tcrt-base /etc/ssl/private\\n")\n')
				haprox.write('fout.write("\\n")\n')
				haprox.write('fout.write("\\tssl-default-bind-ciphers ECDH+AESGCM:DH+AESGCM:ECDH+AES256:DH+AES256:ECDH+AES128:DH+AES:RSA+AESGCM:RSA+AES:!aNULL:!MD5:!DSS\\n")\n')
				haprox.write('fout.write("\\tssl-default-bind-options no-sslv3\\n")\n')
				haprox.write('fout.write("\\n")\n')
				haprox.write('fout.write("defaults\\n")\n')
				haprox.write('fout.write("\\tlog	global\\n")\n')
				haprox.write('fout.write("\\tmode	http\\n")\n')
				haprox.write('fout.write("\\toption	httplog\\n")\n')
				haprox.write('fout.write("\\toption	dontlognull\\n")\n')
				haprox.write('fout.write("\\ttimeout connect 5000\\n")\n')
				haprox.write('fout.write("\\ttimeout client  50000\\n")\n')
				haprox.write('fout.write("\\ttimeout server  50000\\n")\n')
				haprox.write('fout.write("\\terrorfile 400 /etc/haproxy/errors/400.http\\n")\n')
				haprox.write('fout.write("\\terrorfile 403 /etc/haproxy/errors/403.http\\n")\n')
				haprox.write('fout.write("\\terrorfile 408 /etc/haproxy/errors/408.http\\n")\n')
				haprox.write('fout.write("\\terrorfile 500 /etc/haproxy/errors/500.http\\n")\n')
				haprox.write('fout.write("\\terrorfile 502 /etc/haproxy/errors/502.http\\n")\n')
				haprox.write('fout.write("\\terrorfile 503 /etc/haproxy/errors/503.http\\n")\n')
				haprox.write('fout.write("\\terrorfile 504 /etc/haproxy/errors/504.http\\n")\n')
				haprox.write('fout.write("\\n")\n')
				haprox.write('fout.write("\\n")\n')
				haprox.write('fout.write("frontend lb \\n")\n')
				haprox.write('fout.write("\\tbind *:80\\n")\n')
				haprox.write('fout.write("\\tmode http\\n")\n')
				haprox.write('fout.write("\\tdefault_backend webservers\\n")\n')
				haprox.write('fout.write("\\n")\n')
				haprox.write('fout.write("backend webservers\\n")\n')
				haprox.write('fout.write("\\tmode http\\n")\n')
				haprox.write('fout.write("\\tbalance roundrobin\\n")\n')
				for i in range(1, numeroservidores + 1):
					haprox.write('fout.write("\\tserver s'+str(i)+ ' 10.0.2.1'+str(i)+ ':80 check\\n")\n')
				haprox.write('fout.write("listen stats\\n")\n')
				haprox.write('fout.write("\\tbind :8001\\n")\n')
				haprox.write('fout.write("\\tstats enable\\n")\n')
				haprox.write('fout.write("\\tstats uri /\\n")\n')
				haprox.write('fout.write("\\tstats hide-version\\n")\n')
				haprox.write('fout.write("\\tstats auth admin:cdps\\n")\n')
				haprox.write("fout.close()\n")
				haprox.close()

				# Hacemos copy in en la maquina virtual del lb
				call(["sudo", "virt-copy-in", "-a", maquina +".qcow2", "./haproxyscript.py", "/home/cdps"])

				# Editamos rclocal para que ejecute lo que queremos cuando se arranque la maquina
				etclocal = open("./" + maquina + "/rc.local", "w")
				etclocal.write("#!/bin/bash\n")
				etclocal.write("sudo service apache2 stop\n")
				etclocal.write("python3 /home/cdps/haproxyscript.py\n")
				etclocal.write("sudo service haproxy restart\n")
				etclocal.write("exit 0\n")
				etclocal.close()
				# Le ponemos permisos de ejecución
				call(["chmod", "+x", "./" + maquina + "/rc.local"])
				# Le hacemos copy in para que sobreescriba el por defecto de la maquina
				call(["sudo", "virt-copy-in", "-a", maquina + ".qcow2", "./"+ maquina +"/rc.local", "/etc"])
			else:
				interfaces.write("address 10.0.2.1"+str(numservidor)+"\n")
				interfaces.write("network 10.0.2.0 \n")
				interfaces.write("netmask 255.255.255.0 \n")
				interfaces.write("broadcast 10.0.2.255 \n")
				interfaces.write("gateway 10.0.2.1 \n")
				interfaces.close()
				# Html para cada servidor
				web = open("./"+maquina+"/index.html", "w")
				web.write("Bienvenido al servidor: "+maquina)
				web.close()
				# Hacemos copy-in, esta en la ruta /var/www/html
				call(["sudo", "virt-copy-in", "-a", maquina+".qcow2", "./"+maquina+"/index.html", "/var/www/html"])

			# Hacemos copy-in, esta en la ruta /etc/network (interfaces)
			call(["sudo", "virt-copy-in", "-a", maquina +".qcow2", "./"+ maquina +"/interfaces", "/etc/network"])
			logger.debug('Configuracion ficheros de ' + maquina + ' finalizada') 

		# Llamamos a la funcion genérica para cada caso
		configuracion("c1", 0)
		#bar.next(33) #La barra de progreso avanza
		configuracion("lb", 0)
		#bar.next(33) #La barra de progreso avanza
		bucleservidores(2)
		#bar.next(34) #La barra de progreso se completa	

		# Configuracion final en el host
		call(["sudo", "ifconfig", "LAN1", "10.0.1.3/24"])
		call(["sudo", "ip", "route", "add", "10.0.0.0/16", "via", "10.0.1.1"])

		logger.debug('Configuracion de ficheros de servidores finalizada') 

		print('El escenario ha sido creado correctamente')

	elif operacion == "start":
		def start(x): #Funcion para automatizar el proceso de arrancar cada maquina junto con su consola
			#Arranca el dominio indicado por parametro
			call(["sudo", "virsh", "start", x]) 
			#Abre una ventana con la consola de la maquina seleccionada por parametro
			os.system("xterm -rv -sb -rightbar -fa monospace -fs 10 -title '"+x+"' -e 'sudo virsh console "+x+"' &") 
		
		#Revisa que el archivo con el numero de servidores exista, lo que indica que el escenario ha sido creado
		if os.path.isfile("pc1.cfg"): 

			#Comprueba si se han introducido más parametros además de start, indicando las maquinas que individualmente se quieren iniciar
			if len(sys.argv) > 2: 
				for i in range(2, len(sys.argv)):

					#Comprueba que las maquinas especificadas han sido creadas consultando si su archivo .xml existe
					if os.path.isfile(sys.argv[i]+".xml"): 
						start(sys.argv[i]) #Arranca las maquinas especificadas
					else: 
						raise ValueError("No existe ninguna máquina virtual con ese nombre\n--help para mas ayuda")

			else: #Si no se indican más parametros que start, se arranca todo el escenario
				start("c1") #Arranca c1
				start("lb") #Arranca lb

				fin= open("pc1.cfg", 'r') # out file
				nservidores = int(fin.readlines()[0][9]) #Toma el valor del numero de servidores para utilizarlo en el bucle posteriormente
				fin.close()

				for i in range(1, nservidores + 1): 			
					start("s"+str(i)) #Arranca todos los servidores	

		else:
			raise ValueError("Debes crear las maquinas virtuales primero\n--help para mas ayuda")


	elif operacion == "stop":
		def stop(x): #Funcion para automatizar el proceso de parar cada maquina junto con su consola
			call(["sudo", "virsh", "shutdown", x]) #Para el dominio indicado por parametro

		#Revisa que el archivo con el numero de servidores exista, lo que indica que el escenario ha sido creado
		if os.path.isfile("pc1.cfg"):

			#Comprueba si se han introducido más parametros además de stop, indicando las maquinas que individualmente se quieren parar 
			if len(sys.argv) > 2: 
				for i in range(2, len(sys.argv)):

					#Comprueba que las maquinas especificadas han sido creadas consultando si su archivo .xml existe
					if os.path.isfile(sys.argv[i]+".xml"): 
						stop(sys.argv[i]) #Para las maquinas especificadas
					else: 
						raise ValueError("No existe ninguna máquina virtual con ese nombre\n--help para mas ayuda")

			else: #Si no se indican más parametros que stop, se para todo el escenario
				fin= open("pc1.cfg", 'r') 
				nservidores = int(fin.readlines()[0][9]) #Toma el valor del numero de servidores para utilizarlo en el bucle posteriormente
				fin.close()
				
				stop("c1") #Para c1
				stop("lb") #Para lb
				for i in range(1, nservidores + 1): 
					stop("s"+str(i)) #Para todos los servidores
		else:
			raise ValueError("Debes crear las maquinas virtuales primero\n--help para mas ayuda")


	elif operacion == "release":
		def release(x): #Funcion para automatizar el proceso de borrar todo el escenario
			#Detiene forzosamente la máquina indicada por parámetro, esté parada o no
			call(["sudo", "virsh", "destroy", x]) 
			#Elimina la definicion de la maquina indicada por parámetro
			call(["sudo", "virsh", "undefine", x]) 
			#Elimina el arhivo .xml de la máquina indicada por parámetro
			call(["rm", x+".xml"]) 
			#Elimina la imagen .qcow2 de la máquina indicada por parámetro
			call(["rm", "-f", x+".qcow2"]) 
			#Elimina el directorio y los archivos que contiene dentro de la máquina indicada por parámetro
			call(["rm", "-r", x]) 

		#Revisa que el archivo con el numero de servidores exista, lo que indica que el escenario ha sido creado
		if os.path.isfile("pc1.cfg"): 
			fin= open("pc1.cfg", 'r') 
			nservidores = int(fin.readlines()[0][9]) #Toma el valor del numero de servidores para utilizarlo en el bucle posteriormente
			fin.close()

			release("c1") #Libera c1
			release("lb") #Libera lb

			for i in range(1, nservidores + 1): 
				release("s"+str(i)) #Libera los servidores
			call(["rm", "pc1.cfg"]) #Borra el archivo que contiene el numero de servidores creados
			call(["rm", "haproxyscript.py"])
			# Bridges
			call(["sudo", "ifconfig", "LAN1", "down"]) #Desactiva LAN1
			call(["sudo", "ifconfig", "LAN2", "down"]) #Desactiva LAN2
			call(["sudo", "brctl", "delbr", "LAN1"]) #Elimina LAN1
			call(["sudo", "brctl", "delbr", "LAN2"]) #Elimina LAN2
			
			print("El escenario se ha liberado adecuadamente")
			
		else:
			raise ValueError("Debes crear las maquinas virtuales primero\n--help para mas ayuda")


	elif operacion == "watch_detail":
		#Revisa que el archivo con el numero de servidores exista, lo que indica que el escenario ha sido creado
		if os.path.isfile("pc1.cfg"): 
			if len(sys.argv) == 3:
				#Revisa que el archivo .xml de la maquina especificada exista
				if os.path.isfile(sys.argv[2]+".xml"): 
					#Estadisticas generales del dominio
					call(["sudo", "virsh", "dominfo", sys.argv[2]]) 
					#Hay conectividad?
					if sys.argv[2][0] == "s":
						#Comprueba si tras realizar un ping el paquete se recibe, teniendo conexion, o no
						subprocess = subprocess.Popen("ping -c 1 10.0.2.1"+ sys.argv[2][1]+" | grep '1 received'", shell=True, stdout=subprocess.PIPE) 
						subprocess_return = subprocess.stdout.read()
						if subprocess_return:
							print("Hay conexión con el servidor")
						else: 
							print("No hay conexion con el servidor")
				else:
					raise ValueError("No existe ninguna máquina virtual con ese nombre\n--help para mas ayuda")
			elif len(sys.argv) == 4:
				#Revisa que el archivo .xml de la maquina especificada exista
				if os.path.isfile(sys.argv[2]+".xml"): 
					#Estado del dominio
					if sys.argv[3] == "estado":
						call(["sudo", "virsh", "domstate", sys.argv[2]])
					#Interfaces del dominio
					elif sys.argv[3] == "interfaz":
						call(["sudo", "virsh", "domiflist", sys.argv[2]])
					#Estadisticas de CPU
					elif sys.argv[3] == "cpu":
						call(["sudo", "virsh", "cpu-stats", sys.argv[2]])
					else: 
						raise ValueError("Parametro incorrecto\n--help para mas ayuda")
				else:
					raise ValueError("No existe ninguna máquina virtual con ese nombre\n--help para mas ayuda")
			else: 
				raise ValueError("Parametros incorrectos\n--help para mas ayuda")
		else: 
			raise ValueError("Debe crear el escenario antes de consultar su estado\n--help para mas ayuda")

	elif operacion == "watch":
		#Revisa que el archivo con el numero de servidores exista, lo que indica que el escenario ha sido creado
		if os.path.isfile("pc1.cfg"): 
			if len(sys.argv) == 3:
				call(["watch", "-n", sys.argv[2], "sudo", "virsh", "list"]) # Monitorizacion de periodo n segundos por parametro
			elif len(sys.argv) == 2:
				call(["watch", "sudo", "virsh", "list"]) # Monitorizacion general periodica de todo el escenario
			else:
				raise ValueError("Parametros incorrectos\n--help para mas ayuda")
		else:
			raise ValueError("Debe crear el escenario antes de consultar su estado\n--help para mas ayuda")		

	elif operacion == "--help": #Informacion de ayuda con la lista de parametros completa
		print("Modo de empleo: pc1 <orden> <otros_parametros>\n")
		print("El parámetro <orden> puede tomar los siguientes valores:\n")
		print("\tcreate: crea el escenario virtual. Se le puede añadir <otros_parametros> indicando el número de servidores a crear (2 por defecto).")
		print("\tstart: arranca las máquinas virtuales.")
		print("\t\tSi queremos arrancar solo unas maquinas en concreto se le pueden añadir <otros_parametros> indicando la máquina o máquinas que queremos arrancar")
		print("\t\tEjemplo, si queremos arrancar lb y s1: pc1 start lb s1")
		print("\tstop: detiene las máquinas virtuales.")
		print("\t\tSi queremos parar solo unas maquinas en concreto se le pueden añadir <otros_parametros> indicando la máquina o máquinas que queremos parar")
		print("\t\tEjemplo, si queremos parar lb y s1: pc1 stop lb s1")
		print("\trelease: libera el escenario virtual,borrando todos los ficheros creados")
		print("\twatch_detail: muestra el estado del escenario de manera mas detallada")
		print("\t\tdominio: muestra estadisticas individuales de la maquina seleccionada")
		print("\t\t\testado: muestra solo el estado de la maquina seleccionada")
		print("\t\t\tcpu: muestra estadisticas de la maquina seleccionada")
		print("\t\t\tinterfaz: muestra las interfaces de la maquina seleccionada")
		print("\twatch: muestra el estado del escenario periodicamente")
		print("\t\tSe le puede configurar el tiempo que comprueba el estado del escenario añadiendo en <otros_parametros> el tiempo especificado")
		print("\t--help: muestra esta ayuda")
	else: 
		raise ValueError("Operacion incorrecta\n--help para mas ayuda")		
else:
	raise ValueError("Debes incluir la operacion a realizar\n--help para mas ayuda")
