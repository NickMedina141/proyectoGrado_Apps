from PyQt6.QtWidgets import QWidget, QMessageBox, QLineEdit
from PyQt6.QtGui import QIcon
from PyQt6.uic import loadUi
from api.cliente_respuesta import cliente_api
import os

class VentanaLogin(QWidget):
    def __init__(self, app_principal=None):
        super().__init__()
        self.app_principal = app_principal
        
        # Cargar UI
        ruta_ui = os.path.join(os.path.dirname(__file__), "ventana_login.xml")
        loadUi(ruta_ui, self)
        
        logo_path = os.path.join(os.path.dirname(__file__), "recursos", "logo_upc.png").replace("\\", "/")
        if os.path.exists(logo_path):
            self.etiqueta_logo.setText("")
            self.etiqueta_logo.setStyleSheet(f"border-image: url('{logo_path}'); border-radius: 30px;")
        
        # Conectar botones
        self.boton_ingresar.clicked.connect(self.procesar_login)
        self.boton_ojo.clicked.connect(self.alternar_visibilidad_clave)
        
        # Rutas de los íconos (Nivel de carpeta anterior + recursos)
        self.ruta_ojo_abierto = os.path.join(os.path.dirname(os.path.dirname(__file__)), "recursos", "ojo_abierto.svg")
        self.ruta_ojo_cerrado = os.path.join(os.path.dirname(os.path.dirname(__file__)), "recursos", "ojo_cerrado.svg")
        
        # Restaurar a tamaño cuadrado de ícono original
        # boton_ojo sizing defined in ventana_login.xml
        self.boton_ojo.setText("") # Quitar cualquier texto residual
        self.boton_ojo.setIcon(QIcon(self.ruta_ojo_cerrado))
        
    def alternar_visibilidad_clave(self):
        if self.entrada_clave.echoMode() == QLineEdit.EchoMode.Password:
            self.entrada_clave.setEchoMode(QLineEdit.EchoMode.Normal)
            self.boton_ojo.setIcon(QIcon(self.ruta_ojo_abierto))
        else:
            self.entrada_clave.setEchoMode(QLineEdit.EchoMode.Password)
            self.boton_ojo.setIcon(QIcon(self.ruta_ojo_cerrado))

    def procesar_login(self):
        correo = self.entrada_correo.text().strip()
        clave = self.entrada_clave.text().strip()
        
        if not correo or not clave:
            QMessageBox.warning(self, "Campos Incompletos", "Por favor ingresa tu correo y contraseña.")
            return
            
        self.boton_ingresar.setEnabled(False)
        self.boton_ingresar.setText("Validando...")
        
        # Llama a la API (bloqueante en este paso simple)
        exito, mensaje = cliente_api.login_estudiante(correo, clave)
        
        if exito:
            # --- INSIGHTFACE ENROLLMENT ---
            from motor_ia.biometria_facial import biometria_motor
            import cv2
            import json
            
            import sys
            if getattr(sys, 'frozen', False):
                base_dir = os.path.dirname(sys.executable)
            else:
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ruta_datos = os.path.join(base_dir, "datos_biometricos")
            os.makedirs(ruta_datos, exist_ok=True)
            # Limpiamos el correo para usarlo de nombre de archivo
            correo_limpio = correo.replace("@", "_").replace(".", "_")
            ruta_emb = os.path.join(ruta_datos, f"emb_{correo_limpio}.json")
            
            if not os.path.exists(ruta_emb):
                QMessageBox.information(self, "Biometria Facial", "Es tu primera vez. Por favor, mira fijamente a la camara en un lugar iluminado para registrar tu Rostro Base.")
                cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
                import time
                start_time = time.time()
                emb = None
                frame_final = None
                
                # Intentar detectar el rostro continuamente hasta por 10 segundos
                while time.time() - start_time < 10.0:
                    exito_cap, frame = cap.read()
                    if exito_cap:
                        emb = biometria_motor.obtener_embedding(frame, exigir_frontal=True)
                        if emb is not None:
                            frame_final = frame
                            break
                    
                    # Pequeña pausa para que la cámara ajuste el brillo y el usuario se posicione
                    time.sleep(0.1)
                
                cap.release()
                
                if emb is not None and frame_final is not None:
                    with open(ruta_emb, 'w') as f:
                        json.dump(emb.tolist(), f)
                    cv2.imwrite(os.path.join(ruta_datos, f"rostro_{correo_limpio}.jpg"), frame_final)
                    QMessageBox.information(self, "Biometria", "Rostro registrado con exito. Ahora ingresaras al panel.")
                else:
                    QMessageBox.warning(self, "Error Biometrico", "No se detecto tu rostro claramente. Intenta iniciar sesion nuevamente asegurando buena iluminacion.")
                    self.boton_ingresar.setEnabled(True)
                    self.boton_ingresar.setText("Iniciar Sesion")
                    return

            # Guardar la ruta globalmente para que hilo_camara la lea
            biometria_motor.ruta_emb_actual = ruta_emb

            if self.app_principal:
                self.app_principal.mostrar_ventana_principal()
        else:
            QMessageBox.critical(self, "Error de Inicio", mensaje)
            
        self.boton_ingresar.setEnabled(True)
        self.boton_ingresar.setText("Iniciar Sesión")
