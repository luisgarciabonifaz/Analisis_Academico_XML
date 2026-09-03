import xml.etree.ElementTree as ET
import csv
import os

# Carpeta con los XML de entrada y carpeta donde se generan los CSV
CARPETA_ENTRADA = "Originales/2021-22/Paso1"
CARPETA_SALIDA = "Originales/2021-22/Paso1"


def xml_a_csv(xml_file, csv_file, campos, agrupacion):
    """Convierte un XML de ITACA en CSV.

    Anyade como primeras columnas el curso (anyo) y la fechaExportacion
    leidos del elemento <centro>, y toma solo los campos indicados.
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

        # Encabezados: anyo, fecha_exportacion y los campos solicitados
        writer.writerow(["anyo", "fecha_exportacion"] + campos)

        for elemento in root.iter(agrupacion):
            fila = [anyo, fecha_exportacion]
            for campo in campos:
                valor = elemento.get(campo)
                fila.append(valor.strip() if valor is not None else "")
            writer.writerow(fila)

    print(f"{os.path.basename(xml_file)} -> {csv_file}")


# Definicion de cada conversion: (xml, csv, campos, elemento a repetir)
CONVERSIONES = [
    (
        "alumnos.xml",
        "Alumnos.csv",
        ["NIA", "nombre", "apellido1", "apellido2", "fecha_nac", "sexo",
         "tipo_doc", "documento", "nacionalidad", "pais_nac", "municipio_nac",
         "cod_postal", "provincia", "municipio", "localidad", "telefono1",
         "telefono2", "telefono3", "email1", "email2", "sip", "expediente",
         "ensenanza", "curso", "grupo", "turno", "linea", "modalidad",
         "repite", "estado_matricula", "tipo_matricula", "matricula_parcial",
         "matricula_condic", "fecha_matricula", "fecha_ingreso_centro"],
        "alumno",
    ),
    (
        "calificaciones.xml",
        "Calificaciones.csv",
        ["evaluacion", "alumno", "ensenanza", "curso", "contenido",
         "bloque_contenido", "nota_numerica", "tipo_nota"],
        "calificacion",
    ),
    (
        "contenidos.xml",
        "Contenidos.csv",
        ["codigo", "nombre_cas", "nombre_val", "ensenanza", "curso"],
        "contenido",
    ),
    (
        "cursos.xml",
        "Cursos.csv",
        ["codigo", "nombre_cas", "nombre_val", "abreviatura", "ensenanza", "padre"],
        "curso",
    ),
    (
        "grupos.xml",
        "Grupos.csv",
        ["codigo", "nombre", "ensenanza", "linea", "turno", "modalidad",
         "aula", "capacidad"],
        "grupo",
    ),
]


if __name__ == "__main__":
    os.makedirs(CARPETA_SALIDA, exist_ok=True)
    for xml_name, csv_name, campos, agrupacion in CONVERSIONES:
        xml_a_csv(
            os.path.join(CARPETA_ENTRADA, xml_name),
            os.path.join(CARPETA_SALIDA, csv_name),
            campos,
            agrupacion,
        )
    print("Conversion completada.")
