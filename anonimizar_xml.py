import xml.etree.ElementTree as ET

# Carpeta de trabajo y ficheros de entrada
CARPETA = "Originales/2021-22"
ENTRADA_ALUMNOS = f"{CARPETA}/alumnos.xml"
ENTRADA_CALIFICACIONES = f"{CARPETA}/calificaciones.xml"

# Ficheros de salida (nombre distinto para no sobreescribir los originales)
SALIDA_ALUMNOS = f"{CARPETA}/Paso1/alumnos.xml"
SALIDA_CALIFICACIONES = f"{CARPETA}/Paso1/calificaciones.xml"

# Sustitucion de letras solicitada: (a:h, e:j, i:z, o:l, u:s, m:n, d:e, s:a, c:d)
SUSTITUCION = {"a": "h", "e": "j", "i": "z", "o": "l", "u": "s",
               "m": "n", "d": "e", "s": "a", "c": "d"}

# Tabla de traduccion en un solo paso, aplicada a minusculas y mayusculas
_tabla = {}
for origen, destino in SUSTITUCION.items():
    _tabla[ord(origen)] = destino
    _tabla[ord(origen.upper())] = destino.upper()


def cambiar_letras(valor):
    """Aplica la sustitucion de letras conservando el resto de caracteres."""
    if valor is None:
        return None
    return valor.translate(_tabla)


def sumar(valor, cantidad):
    """Suma 'cantidad' a un valor numerico conservando espacios sobrantes."""
    if valor is None:
        return None
    texto = valor.strip()
    if not texto.isdigit():
        return valor
    return str(int(texto) + cantidad)


def anonimizar_alumnos(entrada, salida):
    tree = ET.parse(entrada)
    root = tree.getroot()

    for alumno in root.iter("alumno"):
        alumno.set("NIA", sumar(alumno.get("NIA"), 2345))
        alumno.set("nombre", cambiar_letras(alumno.get("nombre")))
        alumno.set("apellido1", cambiar_letras(alumno.get("apellido1")))
        alumno.set("apellido2", cambiar_letras(alumno.get("apellido2")))
        alumno.set("documento", "12345678X")
        alumno.set("telefono1", "666666666")
        alumno.set("telefono2", "666666666")
        alumno.set("telefono3", "666666666")
        alumno.set("email1", cambiar_letras(alumno.get("email1")))
        alumno.set("email2", cambiar_letras(alumno.get("email2")))
        alumno.set("sip", "8888888888")
        alumno.set("expediente", sumar(alumno.get("expediente"), 234567))

    tree.write(salida, encoding="utf-8", xml_declaration=True)
    print(f"Alumnos anonimizados -> {salida}")


def anonimizar_calificaciones(entrada, salida):
    tree = ET.parse(entrada)
    root = tree.getroot()

    for calificacion in root.iter("calificacion"):
        calificacion.set("alumno", sumar(calificacion.get("alumno"), 2345))

    tree.write(salida, encoding="utf-8", xml_declaration=True)
    print(f"Calificaciones anonimizadas -> {salida}")


if __name__ == "__main__":
    anonimizar_alumnos(ENTRADA_ALUMNOS, SALIDA_ALUMNOS)
    anonimizar_calificaciones(ENTRADA_CALIFICACIONES, SALIDA_CALIFICACIONES)
