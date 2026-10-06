"""
Módulo de Identificación Unívoca de Dispositivo (Huella Digital de Hardware).
Genera un identificador criptográfico SHA-256 no falsificable combinando:
1. Dirección MAC física del adaptador de red activo.
2. MachineGuid oficial del registro de Windows (HKLM\\SOFTWARE\\Microsoft\\Cryptography).
3. UUID del BIOS / Tarjeta Madre (Win32_ComputerSystemProduct).

Este ID vincula la sesión de examen a un único ordenador físico, impidiendo
que una misma cuenta de estudiante inicie sesión en dos computadores simultáneamente.
"""

import sys
import os
import uuid
import hashlib
import subprocess
import winreg
import psutil
import socket


def obtener_mac() -> str:
    """
    Obtiene la dirección MAC física del adaptador de red principal activo.
    Prioriza adaptadores físicos conectados (Ethernet o Wi-Fi) ignorando túneles/virtuales.
    """
    try:
        # 1. Intentar con psutil buscando interfaz UP no virtual
        interfaces = psutil.net_if_addrs()
        stats = psutil.net_if_stats()
        
        pref_names = ['eth', 'wi-fi', 'ethernet', 'wlan', 'en0', 'red']
        virtual_names = ['vEthernet', 'virtual', 'vmware', 'vbox', 'pseudo', 'loopback', 'teredo', 'isatap']

        candidatos = []
        for iface_name, addrs in interfaces.items():
            name_lower = iface_name.lower()
            if any(vn.lower() in name_lower for vn in virtual_names):
                continue
            is_up = stats[iface_name].isup if iface_name in stats else False
            if not is_up:
                continue

            mac = None
            has_ip = False
            for addr in addrs:
                # psutil.AF_LINK en windows es -1 o socket.AF_LINK
                if addr.family == psutil.AF_LINK or getattr(addr.family, 'name', '') == 'AF_LINK' or addr.family == -1:
                    if addr.address and len(addr.address) in (12, 17):
                        mac = addr.address.replace('-', ':').upper()
                elif addr.family == socket.AF_INET and not addr.address.startswith('127.'):
                    has_ip = True

            if mac and mac != '00:00:00:00:00:00':
                prioridad = 1 if any(p in name_lower for p in pref_names) else 2
                candidatos.append((prioridad, has_ip, mac))

        if candidatos:
            # Ordenar por prioridad de nombre y si tiene IP activa
            candidatos.sort(key=lambda x: (x[0], not x[1]))
            return candidatos[0][2]
    except Exception:
        pass

    # 2. Respaldo mediante uuid.getnode()
    try:
        node = uuid.getnode()
        mac = ':'.join(f'{(node >> i) & 0xff:02X}' for i in range(40, -1, -8))
        if mac and mac != '00:00:00:00:00:00':
            return mac
    except Exception:
        pass

    return "00:00:00:00:00:00"


def obtener_machine_guid() -> str:
    """
    Obtiene el GUID único de instalación del sistema operativo Windows
    almacenado en el Registro del sistema.
    """
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography", 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
            guid, _ = winreg.QueryValueEx(key, "MachineGuid")
            if guid:
                return str(guid).strip().upper()
    except Exception:
        pass

    # Respaldo 32-bit
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography", 0, winreg.KEY_READ) as key:
            guid, _ = winreg.QueryValueEx(key, "MachineGuid")
            if guid:
                return str(guid).strip().upper()
    except Exception:
        pass

    return "WINDOWS-GUID-DESCONOCIDO"


def obtener_bios_uuid() -> str:
    """
    Obtiene el identificador UUID del fabricante del equipo o BIOS.
    """
    try:
        salida = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_ComputerSystemProduct).UUID"],
            creationflags=0x08000000,
            text=True,
            timeout=3
        ).strip()
        if salida and len(salida) > 8:
            return salida.upper()
    except Exception:
        pass

    try:
        salida = subprocess.check_output(
            ["wmic", "csproduct", "get", "uuid"],
            creationflags=0x08000000,
            text=True,
            timeout=3
        )
        lineas = [l.strip() for l in salida.splitlines() if l.strip() and "UUID" not in l.upper()]
        if lineas:
            return lineas[0].upper()
    except Exception:
        pass

    return "BIOS-UUID-DESCONOCIDO"


def obtener_huella_dispositivo() -> dict:
    """
    Retorna un diccionario completo con la dirección MAC, MachineGuid, BIOS UUID
    y el DeviceId criptográfico resultante (SHA-256).
    """
    mac = obtener_mac()
    guid = obtener_machine_guid()
    bios = obtener_bios_uuid()

    semilla = f"{guid}|{mac}|{bios}"
    device_id = hashlib.sha256(semilla.encode('utf-8')).hexdigest()

    return {
        "deviceId": device_id,
        "direccionMac": mac,
        "machineGuid": guid,
        "biosUuid": bios
    }


if __name__ == "__main__":
    huella = obtener_huella_dispositivo()
    print("Huella de Dispositivo:")
    for k, v in huella.items():
        print(f"  {k}: {v}")
