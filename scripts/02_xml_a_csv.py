import argparse
import csv
import os
import xml.etree.ElementTree as ET

# Paso 2 del flujo: convierte a CSV los XML ya anonimizados/filtrados del Paso 1.
# Transformacion pura XML -> CSV: no selecciona ni elimina campos, eso ya lo
# hace 01_anonimizar_xml.py.
CARPETA_ENTRADA = "data/02_anonimizado"
CARPETA_SALIDA = "data/03_csv"


def xml_a_csv(xml_file, csv_file, agrupacion):
    """Convierte a CSV los elementos <agrupacion> de un XML ya filtrado.

    Anyade como primeras columnas el curso (anyo) y la fechaExportacion
    leidos del elemento <centro>, y vuelca tal cual el resto de atributos
    que 01_anonimizar_xml.py ha dejado en el XML.
    """
    tree = ET.parse(xml_file)
    root = tree.getroot()

    # Lee el anyo y la fecha de exportacion del elemento centro
    anyo = ""
    fecha_exportacion = ""
    for c in root.iter("centro"):
        anyo = c.get("curso")
        fecha_exportacion = c.get("fechaExportacion")

    with open(csv_file, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        cabecera_escrita = False

        for elemento in root.iter(agrupacion):
            if not cabecera_escrita:
                writer.writerow(["anyo", "fecha_exportacion"] + list(elemento.attrib.keys()))
                cabecera_escrita = True

            valores = [valor.strip() for valor in elemento.attrib.values()]
            writer.writerow([anyo, fecha_exportacion] + valores)

    print(f"{os.path.basename(xml_file)} -> {csv_file}")


# Definicion de cada conversion: (xml, csv, elemento a repetir)
CONVERSIONES = [
    ("alumnos.xml", "Alumnos.csv", "alumno"),
    ("calificaciones.xml", "Calificaciones.csv", "calificacion"),
    ("contenidos.xml", "Contenidos.csv", "contenido"),
    ("cursos.xml", "Cursos.csv", "curso"),
    ("grupos.xml", "Grupos.csv", "grupo"),
]


def procesar_curso(curso):
    carpeta_entrada = os.path.join(CARPETA_ENTRADA, curso)
    carpeta_salida = os.path.join(CARPETA_SALIDA, curso)
    os.makedirs(carpeta_salida, exist_ok=True)

    for xml_name, csv_name, agrupacion in CONVERSIONES:
        xml_file = os.path.join(carpeta_entrada, xml_name)
        if not os.path.isfile(xml_file):
            print(f"[{curso}] aviso: no existe {xml_file}, se omite")
            continue
        xml_a_csv(xml_file, os.path.join(carpeta_salida, csv_name), agrupacion)


def cursos_disponibles():
    return sorted(
        nombre for nombre in os.listdir(CARPETA_ENTRADA)
        if os.path.isdir(os.path.join(CARPETA_ENTRADA, nombre))
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Paso 2: convierte a CSV los XML anonimizados.")
    parser.add_argument("--curso", help="Curso a procesar (ej. 2021-22). Si se omite, se procesan todos los de data/02_anonimizado.")
    args = parser.parse_args()

    cursos = [args.curso] if args.curso else cursos_disponibles()
    for curso in cursos:
        procesar_curso(curso)
    print("Conversion completada.")
