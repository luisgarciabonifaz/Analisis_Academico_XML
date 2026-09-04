import argparse
import os
import xml.etree.ElementTree as ET

# Paso 1 del flujo: anonimiza los XML crudos de ITACA y deja en cada uno solo los
# campos que necesita el Paso 2 (02_xml_a_csv.py).
CARPETA_RAW = "data/01_raw"
CARPETA_SALIDA = "data/02_anonimizado"

# Campos que se conservan de cada elemento: los mismos que usa 02_xml_a_csv.py
# para generar el CSV correspondiente. El resto de atributos se descartan
# aqui para que 02_xml_a_csv.py solo tenga que volcar lo que ya queda en el XML.
CAMPOS_ALUMNO = [
    "NIA", "nombre", "apellido1", "apellido2", "fecha_nac", "sexo",
    "tipo_doc", "documento", "nacionalidad", "pais_nac", "municipio_nac",
    "cod_postal", "provincia", "municipio", "localidad", "telefono1",
    "telefono2", "telefono3", "email1", "email2", "sip", "expediente",
    "ensenanza", "curso", "grupo", "turno", "linea", "modalidad",
    "repite", "estado_matricula", "tipo_matricula", "matricula_parcial",
    "matricula_condic", "fecha_matricula", "fecha_ingreso_centro",
]
CAMPOS_CALIFICACION = [
    "evaluacion", "alumno", "ensenanza", "curso", "contenido",
    "bloque_contenido", "nota_numerica", "tipo_nota",
]
CAMPOS_CONTENIDO = ["codigo", "nombre_cas", "nombre_val", "ensenanza", "curso"]
CAMPOS_CURSO = ["codigo", "nombre_cas", "nombre_val", "abreviatura", "ensenanza", "padre"]
CAMPOS_GRUPO = ["codigo", "nombre", "ensenanza", "linea", "turno", "modalidad",
                "aula", "capacidad"]

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


def filtrar_campos(elemento, campos):
    """Deja en el elemento solo los atributos indicados, en ese orden."""
    atributos = elemento.attrib
    conservados = {campo: atributos.get(campo, "") for campo in campos}
    atributos.clear()
    atributos.update(conservados)


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
        filtrar_campos(alumno, CAMPOS_ALUMNO)

    tree.write(salida, encoding="utf-8", xml_declaration=True)
    print(f"Alumnos anonimizados -> {salida}")


def anonimizar_calificaciones(entrada, salida):
    tree = ET.parse(entrada)
    root = tree.getroot()

    for calificacion in root.iter("calificacion"):
        calificacion.set("alumno", sumar(calificacion.get("alumno"), 2345))
        filtrar_campos(calificacion, CAMPOS_CALIFICACION)

    tree.write(salida, encoding="utf-8", xml_declaration=True)
    print(f"Calificaciones anonimizadas -> {salida}")


def filtrar_xml(entrada, salida, agrupacion, campos):
    """Copia un XML sin datos personales, dejando solo los campos indicados."""
    tree = ET.parse(entrada)
    root = tree.getroot()

    for elemento in root.iter(agrupacion):
        filtrar_campos(elemento, campos)

    tree.write(salida, encoding="utf-8", xml_declaration=True)
    print(f"{agrupacion} filtrado -> {salida}")


# Definicion de cada fichero a procesar: (nombre xml, funcion, args extra)
FICHEROS = [
    ("alumnos.xml", anonimizar_alumnos, ()),
    ("calificaciones.xml", anonimizar_calificaciones, ()),
    ("contenidos.xml", filtrar_xml, ("contenido", CAMPOS_CONTENIDO)),
    ("cursos.xml", filtrar_xml, ("curso", CAMPOS_CURSO)),
    ("grupos.xml", filtrar_xml, ("grupo", CAMPOS_GRUPO)),
]


def procesar_curso(curso):
    carpeta_entrada = os.path.join(CARPETA_RAW, curso)
    carpeta_salida = os.path.join(CARPETA_SALIDA, curso)
    os.makedirs(carpeta_salida, exist_ok=True)

    for nombre_xml, funcion, args_extra in FICHEROS:
        entrada = os.path.join(carpeta_entrada, nombre_xml)
        if not os.path.isfile(entrada):
            print(f"[{curso}] aviso: no existe {entrada}, se omite")
            continue
        salida = os.path.join(carpeta_salida, nombre_xml)
        funcion(entrada, salida, *args_extra)


def cursos_disponibles():
    return sorted(
        nombre for nombre in os.listdir(CARPETA_RAW)
        if os.path.isdir(os.path.join(CARPETA_RAW, nombre))
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Paso 1: anonimiza los XML de ITACA.")
    parser.add_argument("--curso", help="Curso a procesar (ej. 2021-22). Si se omite, se procesan todos los de data/01_raw.")
    args = parser.parse_args()

    cursos = [args.curso] if args.curso else cursos_disponibles()
    for curso in cursos:
        procesar_curso(curso)
    print("Anonimizacion completada.")
