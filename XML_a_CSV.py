import xml.etree.ElementTree as ET
import csv

def xml_to_csv(xml_file, csv_file,campos,agrupacion):

    tree = ET.parse(xml_file)
    root = tree.getroot()

    # Lee el anyo y la fecha de exportación
    for c in root.iter("centro"):
        anyo=c.get("curso")
        fecha_exportacion=c.get("fechaExportacion")


    # Abre el archivo CSV en modo escritura
    with open(csv_file, 'w', newline='') as file:
        writer = csv.writer(file)

        # Escribe los encabezados en el archivo CSV
        cabecera=["anyo","fecha_exportacion"]
        cabecera+=campos

        writer.writerow(cabecera)

        # Escribe los datos de cada curso_grupo en el archivo CSV
        for grupo in root.iter(agrupacion):
            fila = []
            # Los dos primeros campos: anyo, fecha_exportacion
            fila.append(anyo)
            fila.append(fecha_exportacion)
            for campo in campos:
                valor = grupo.get(campo)
                fila.append(valor)
            writer.writerow(fila)
    
# Llama a la función y proporciona la ruta del archivo XML de entrada y la ruta del archivo CSV de salida


campos = ["evaluacion","alumno","ensenanza","curso","contenido","bloque_contenido","nota_numerica","tipo_nota","observacion","capacidades_inf","medidas_inf","borrar","sobreescribir"]
agrupacion = 'calificacion' 
xml_to_csv('calificaciones.xml', 'Calificaciones.csv', campos, agrupacion)
print("Calificaciones Convertido.")




