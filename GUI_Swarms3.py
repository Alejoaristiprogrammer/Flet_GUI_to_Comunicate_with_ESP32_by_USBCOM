import base64

import flet as ft
import cv2
#import pandas as pd
import cv2
import matplotlib.pyplot as plt
import serial, time
import serial.tools.list_ports
import numpy as np
import base64
import asyncio
import matplotlib.pyplot as plt
import time
'''
Robot subdivision of images:

For submatrices size, we need the number of
horizontal divisions (WIDTH) and vertical divisions (Height)
'''
#Image to resize: SIZE OF THE IMAGE FOR SYSTEM-> 
################################################CONFIG:::
height_res=4
width_res=8

####################################################
#Dimensiones de la matriz de cada robot:
block_h = 4   # alto del bloque
block_w = 4   # ancho del bloque

# Matriz 4x4 (imagen) -> indices: [y][x]
#
#          x →
#       0     1   |   2     3
#     -------------------------
# y 0 | (0,0) (0,1) | (0,2) (0,3)
#   1 | (1,0) (1,1) | (1,2) (1,3)
#     -------------------------
#   2 | (2,0) (2,1) | (2,2) (2,3)
#   3 | (3,0) (3,1) | (3,2) (3,3)

#el orden de envio del payload para los bots siempre es horizontal y luego vertical

class serialcom:
    def __init__(self):
        self.puertos = serial.tools.list_ports.comports()
        self.comnumber=None
        self.pal_inicio='ESP32 listo'
        self.espcom=None
    def detectar_tarjeta(self):
        #self.espcom=espcom
        for puerto in self.puertos:
            print(f"Dispositivo: {puerto.device}")
            print(f"Descripción: {puerto.description}")
            if 'CH340' in puerto.description or "CP210" in puerto.description or "USB" in puerto.description:
                self.comnumber=puerto.device
            print(f"HWID: {puerto.hwid}")
            print("-" * 40)
        if self.comnumber is None:
            return "Error: ESP32 no encontrado"
        else:
            self.espcom=serial.Serial(self.comnumber,baudrate=115200,timeout=1)
            return 'Conectado a '+ puerto.device

class image_processor:
    def __init__(self):
        self.height_res=0
        self.width_res=0
        self.res_image_rgb=None
    def procesar_imagen(self,image,height_res,width_res):
        self.height_res=height_res
        self.width_res=width_res
        # Redimensionar la imagen a las dimensiones deseadas
        res_image=cv2.resize(image,(self.width_res,self.height_res))
        # Convertir de BGR → RGB
        self.res_image_rgb = cv2.cvtColor(res_image, cv2.COLOR_BGR2RGB)
        return self.res_image_rgb




def main(page: ft.Page):
    
    #espcom=None
    enviado="Enviar imagen"
    im_pro=image_processor()
    
    page.title = "Wireless Image Transmission"
    page.padding = 30
    page.bgcolor = "#34844D"

    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.CENTER

    
    async def escuchar_serial(consola: ft.ListView):
        loop = asyncio.get_event_loop() # Obtener el bucle de eventos actual
        while True:
            if mySerial.espcom and mySerial.espcom.in_waiting > 0: # Verifica que el puerto esté abierto y tenga datos disponibles
                datos = await loop.run_in_executor(None, mySerial.espcom.readline)# Lee la línea SERIAL de forma asíncrona sin bloquear la UI
                #run in executor permite ejecutar la función de lectura en un hilo separado, evitando que la interfaz se congele mientras espera datos del puerto serial
                linea = datos.decode('utf-8', errors='ignore').strip()
                consola.controls.append(
                ft.Text(f">> {linea}", color=ft.Colors.BLUE, size=14)
                )
                consola.update()
            await asyncio.sleep(0.01)  # da chance a otras tareas (no bloquea la UI)
    
    

    async def handle_pick_files(e):
        
        #nonlocal res_image_rgb
        file = await ft.FilePicker().pick_files(
            allow_multiple=False
        )

        if not file:
            selected_files.value = "Ningún archivo seleccionado"
            selected_files.color = ft.Colors.RED
            selected_files.update()
            return

        selected_files.value = file[0].path
        selected_files.color = ft.Colors.GREEN
        selected_files.update()
        filename = selected_files.value

        image = cv2.imread(filename)

        img_button.content = ft.Text(
            file[0].name,
            color=ft.Colors.WHITE,
            weight=ft.FontWeight.BOLD
        )

        img_button.update()
        height_res = int(textfieldheight.value)
        width_res = int(textfieldwidth.value)
        print(f"Dimensiones ingresadas: {width_res}x{height_res}")
        
        res_image_rgb = im_pro.procesar_imagen(image,height_res,width_res,)
        _, buffer = cv2.imencode(".jpg",image)

        image_view.src_base64 = base64.b64encode(buffer).decode("utf-8")
        image_view.src=image_view.src_base64
        image_view.update()

        filename_preview = f"resized_{time.time()}.png"
        plt.imshow(
            res_image_rgb,
            interpolation='nearest'
        )

        plt.axis("off")

        plt.savefig(
            filename_preview,
            bbox_inches="tight",
            pad_inches=0
        )
        plt.close()
        image_view2.src=filename_preview
        image_view2.update()


    def connect_esp32(e):
        
        #mySerial=serialcom()
        estado_esp32 = mySerial.detectar_tarjeta()
        textotar.value=estado_esp32
        textotar.color=ft.Colors.RED if "Error" in estado_esp32 else ft.Colors.GREEN
        textotar.update()
        if "Conectado" in estado_esp32:
            page.run_task(escuchar_serial, consola)
            
    def send_frame(e):
        global enviado
        if  im_pro.res_image_rgb is None:
            selected_files.value = "Seleccione una imagen primero"
            selected_files.color = ft.Colors.RED
            selected_files.update()
            return
        # Aquí iría la lógica para enviar el frame al ESP32

        bloquesC=0
        bloques=[]
        for y in range(0, height_res, block_h):
            for x in range(0, width_res, block_w):
                bloque = im_pro.res_image_rgb[y:y+block_h, x:x+block_w]
                bloquesC+=1
                #bloques.append(bloquesC)
                bloques.append(bloque.flatten())
                #Order of robots: width: 1, 2, 3, 4 
                #           then height: 5, 6, 7, 8
        print(bloquesC)

        print(len(bloques))
        print(bloques)
        payload = np.concatenate(bloques).astype(np.uint8) #convert list of arrays into a single numpy array

        print("payload plano: ")
        print(payload)
        databyte = payload.tobytes()

        packet = bytearray()
        packet.append(0xAA)  # HEADER

        size = len(databyte)
        packet.append((size >> 8) & 0xFF)  # tamaño alto
        packet.append(size & 0xFF)         # tamaño bajo

        packet.extend(databyte)            # agrega como varios elementos, no una sola lista

        packet.append(0x55)  # END

        mySerial.espcom.write(packet)   
        enviado='Frame enviado al ESP32'
        textoe.value=enviado
        textoe.update()
        #mostrar_mensaje_temporal()
        print(enviado)
        


    selected_files = ft.Text(
        value="",
        size=12,
        color=ft.Colors.GREY_700
    )

    mySerial=serialcom()
    estado_esp32=mySerial.detectar_tarjeta()
    
    consola = ft.ListView(
    height=150,
    spacing=2,
    auto_scroll=True  # se desplaza solo al último mensaje
)
    
    if "Conectado" in estado_esp32:
        page.run_task(escuchar_serial, consola)

    textotar = ft.Text(
        value=estado_esp32,
        color=ft.Colors.RED if "Error" in estado_esp32 else ft.Colors.GREEN,
        size=18,
        weight=ft.FontWeight.BOLD
    )

    img_button = ft.Button(
        content=ft.Text(
            "Seleccionar imagen JPG",
            weight=ft.FontWeight.BOLD
        ),
        icon=ft.Icons.UPLOAD_ROUNDED,
        bgcolor="#2563EB",
        color=ft.Colors.WHITE,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=12),
            padding=20,
        ),
        on_click=handle_pick_files,
    )

    conectarEsp_button = ft.Button(
        content=ft.Text(
            "Conectar ESP32",
            weight=ft.FontWeight.BOLD
        ),
        icon=ft.Icons.CONNECTED_TV,
        bgcolor="#2563EB",
        color=ft.Colors.WHITE,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=12),
            padding=20
        ),
        on_click=connect_esp32,
        visible="Error" in estado_esp32
    )

    send_button = ft.Button(
        content=ft.Text(
            "Send Frame!",
            weight=ft.FontWeight.BOLD
        ),
        icon=ft.Icons.SEND,
        bgcolor="#25EB32",
        color=ft.Colors.WHITE,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=12),
            padding=20
        ),
        on_click=send_frame,
        visible=True
    )

    textoe = ft.Text(
        value="Enviado!" if 'enviado' in enviado else "Enviar imagen",
        #color=ft.Colors.RED if "Error" in estado_esp32 else ft.Colors.GREEN,
        size=18,
        weight=ft.FontWeight.BOLD
    )
    
    image_view = ft.Image(
    src="F:\Dropbox\MCUProjects\PlatformIO\WirelessImage\BLANK_ICON.png",
    width=300,
    height=300,
    border_radius=10,
    fit=ft.BoxFit.CONTAIN
    )

    ##Resized Image to send:
    image_view2 = ft.Image(
    src="F:\Dropbox\MCUProjects\PlatformIO\WirelessImage\BLANK_ICON.png",
    width=300,
    height=300,
    border_radius=10,
    fit=ft.BoxFit.CONTAIN
    )

    textowidth = ft.Text(
        value="Width: ",
        color=ft.Colors.BLUE,
        size=18,
        weight=ft.FontWeight.BOLD
    )

    textoheight=ft.Text(
        value="Height: ",
        color=ft.Colors.BLUE,
        size=18,
        weight=ft.FontWeight.BOLD
    )

    textfieldwidth=ft.TextField(
        label="",   
        width=50,)

    textfieldheight=ft.TextField(
        label="",   
        width=50,)

    card = ft.Container(
        width=900,
        padding=30,
        border_radius=20,
        bgcolor=ft.Colors.WHITE,
        shadow=ft.BoxShadow(
            spread_radius=1,
            blur_radius=20,
            color=ft.Colors.BLACK12,
            offset=ft.Offset(0, 4),
        ),
        content=ft.Column(
            spacing=25,
            scroll=ft.ScrollMode.AUTO,
            controls=[

                ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    controls=[
                        ft.Icon(
                            ft.Icons.WIFI,
                            color="#2563EB",
                            size=40
                        ),

                        ft.Text(
                            "Wireless Image Transmission",
                            size=28,
                            weight=ft.FontWeight.BOLD,
                            color="#1E3A8A"
                        )
                    ]
                ),

                ft.Divider(height=1, color=ft.Colors.BLUE_100),

                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                    controls=[

                        ft.Column(
                            spacing=20,
                            horizontal_alignment=ft.CrossAxisAlignment.START,
                            controls=[

                                ft.Text(
                                    "Select an image:",
                                    size=22,
                                    weight=ft.FontWeight.BOLD,
                                    color="#1E293B"
                                ),

                                img_button,

                                selected_files,
                            ]
                        ),

                        ft.VerticalDivider(width=20),

                        ft.Column(
                            spacing=20,horizontal_alignment=ft.CrossAxisAlignment.START,
                            controls=[ft.Text(
                                    "Matrix Dimensions:",
                                    size=22,
                                    weight=ft.FontWeight.BOLD,
                                    color="#1E293B"
                                ),
                                ft.Row(controls=[textowidth, textfieldwidth]),
                                ft.Row(controls=[textoheight, textfieldheight])],
                                
                            ),
                        ft.VerticalDivider(width=20),
                        ft.Column(
                            spacing=20,
                            horizontal_alignment=ft.CrossAxisAlignment.START,
                            controls=[

                                ft.Text(
                                    "ESP32 Status:",
                                    size=22,
                                    weight=ft.FontWeight.BOLD,
                                    color="#1E293B"
                                ),

                                ft.Container(
                                    padding=15,
                                    border_radius=12,
                                    bgcolor="#F1F5F9",
                                    content=textotar
                                ),
                                conectarEsp_button,
                            ]
                        )
                    ]
                ),
                ft.Divider(height=1, color=ft.Colors.BLUE_100),
                ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        image_view, image_view2
                    ]
                ),
                ft.Divider(height=1, color=ft.Colors.BLUE_100),
                ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        send_button
                    ]
                ),ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        textoe
                    ]
                ),ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        consola
                    ])
            ]
        )
    )

    page.add(
        ft.SafeArea(
            expand=True,
            content=card
        )
    )
    


ft.run(main)