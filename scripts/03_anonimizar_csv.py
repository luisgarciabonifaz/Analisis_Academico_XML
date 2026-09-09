import argparse
import csv
import hashlib
import hmac
import os
import secrets
from collections import Counter

# Paso 3 del flujo: anonimizacion REAL sobre los CSV del Paso 2.
#
# El Paso 1 (01_anonimizar_xml.py) solo OFUSCA: cambia letras y suma constantes
# para que un alumno no reconozca sus datos en una simulacion realista, pero el
# resultado es reversible (NIA + 2345, sustitucion fija de letras...).
#
# Este paso rompe de verdad el vinculo con la persona. Criterio (ver README):
#   1. ELIMINAR identificadores directos y datos personales que aun arrastran los
#      CSV (nombre, documento, telefonos, emails, sip, expediente) y la geografia
#      de residencia (provincia, municipio, localidad).
#   2. SEUDONIMIZAR el identificador de alumno (NIA / alumno) con un token HMAC
#      irreversible sin la clave, pero estable: el mismo NIA da el mismo token en
#      todos los ficheros y todos los anyos -> se conserva la integridad
#      referencial y el analisis multi-anyo.
#   3. GENERALIZAR los quasi-identificadores para que no se pueda reidentificar
#      cruzando campos:
#        - fecha_nac -> anyo_nac (solo el anyo)
#        - cod_postal -> cp_distrito (3 primeros digitos)
#        - fecha_matricula -> anyo-mes
#        - nacionalidad / pais_nac / municipio_nac -> supresion por k-anonimato:
#          un valor con menos de K alumnos en su anyo se sustituye por un codigo
#          generico ("otros").
#   4. CONSERVAR sin tocar el resto (sexo, curso, grupo, turno, estado_matricula,
#      notas...). El recorte a la lista blanca lo hace el Paso 4 (transformacion).
#
# Entrada : data/03_csv/<curso>/*.csv      (staging crudo 1:1 con el XML)
# Salida  : data/04_anon/<curso>/*.csv     (mismo grano, ya anonimizado)

CARPETA_ENTRADA = "data/03_csv"
CARPETA_SALIDA = "data/04_anon"

# Clave HMAC para el seudonimo. Vive fuera del control de versiones (data/ esta
# en .gitignore). Se puede fijar tambien con la variable de entorno ANON_KEY.
FICHERO_CLAVE = "data/_claves/anon_hmac.key"

# Un valor de quasi-identificador con menos de K alumnos dentro del mismo anyo
# se considera reidentificable y se suprime.
K_ANONIMATO = 5

# Solo se procesan los 4 CSV canonicos. Grupos.csv esta fuera del proyecto.
TABLAS = ["Alumnos", "Calificaciones", "Contenidos", "Cursos"]

# --- 1. Columnas que se eliminan por completo ---------------------------------
COLUMNAS_FUERA = {
    "Alumnos": [
        "nombre", "apellido1", "apellido2", "tipo_doc", "documento",
        "telefono1", "telefono2", "telefono3", "email1", "email2",
        "sip", "expediente",
        "provincia", "municipio", "localidad",
        "fecha_ingreso_centro",
    ],
    "Calificaciones": [],
    "Contenidos": [],
    "Cursos": [],
}

# --- 2. Columnas con identificador de alumno -> seudonimo HMAC ----------------
COLUMNAS_ID_ALUMNO = {
    "Alumnos": ["NIA"],
    "Calificaciones": ["alumno"],
    "Contenidos": [],
    "Cursos": [],
}

# --- 3a. Generalizacion de campos (renombra y transforma el valor) ------------
def anyo_de_fecha(fecha):
    """'dd/mm/aaaa' -> 'aaaa'."""
    f = (fecha or "").strip()
    if len(f) >= 4 and f[-4:].isdigit():
        return f[-4:]
    return ""


def anyo_mes_de_fecha(fecha):
    """'dd/mm/aaaa' -> 'aaaa-mm'."""
    partes = (fecha or "").strip().split("/")
    if len(partes) == 3 and partes[1].isdigit() and partes[2].isdigit():
        return f"{partes[2]}-{partes[1].zfill(2)}"
    return ""


def distrito_postal(cp):
    """Codigo postal completo -> 3 primeros digitos (distrito)."""
    c = (cp or "").strip()
    return c[:3] if len(c) >= 3 else ""


# columna_origen -> (columna_destino, funcion)
GENERALIZAR = {
    "Alumnos": {
        "fecha_nac":       ("anyo_nac",       anyo_de_fecha),
        "cod_postal":      ("cp_distrito",    distrito_postal),
        "fecha_matricula": ("fecha_matricula", anyo_mes_de_fecha),
    },
    "Calificaciones": {},
    "Contenidos": {},
    "Cursos": {},
}

# --- 3b. Quasi-identificadores por k-anonimato (supresion) --------------------
# campo -> valor de relleno cuando aparece en < K alumnos del anyo
K_ANON_CAMPOS = {
    "Alumnos": {
        "nacionalidad":  "999",
        "pais_nac":      "999",
        "municipio_nac": "9999",
    },
    "Calificaciones": {},
    "Contenidos": {},
    "Cursos": {},
}


# --- Clave / seudonimo -------------------------------------------------------
def cargar_o_crear_clave(ruta):
    env = os.environ.get("ANON_KEY")
    if env:
        return env.encode("utf-8")
    if os.path.isfile(ruta):
        with open(ruta, encoding="utf-8") as fh:
            return fh.read().strip().encode("utf-8")
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    clave = secrets.token_hex(32)
    with open(ruta, "w", encoding="utf-8") as fh:
        fh.write(clave + "\n")
    print(f"[clave] generada una clave HMAC nueva en {ruta}")
    print("[clave] guarda una copia segura: sin ella no se puede reproducir el seudonimo")
    print("[clave] borrala si quieres cortar definitivamente el enlace con el NIA real")
    return clave.encode("utf-8")


def seudonimo(valor, clave):
    v = (valor or "").strip()
    if not v:
        return ""
    mac = hmac.new(clave, v.encode("utf-8"), hashlib.sha256).hexdigest()
    return "AL" + mac[:16]


# --- Procesado de una tabla -------------------------------------------------
def cabecera_salida(campos_entrada, tabla):
    fuera = set(COLUMNAS_FUERA[tabla])
    generalizar = GENERALIZAR[tabla]
    salida = []
    for campo in campos_entrada:
        if campo in fuera:
            continue
        salida.append(generalizar.get(campo, (campo, None))[0])
    return salida


def conjuntos_a_suprimir(filas, tabla):
    """Por cada campo con k-anonimato, el conjunto de valores con < K apariciones."""
    resultado = {}
    for campo in K_ANON_CAMPOS[tabla]:
        conteo = Counter(f[campo].strip() for f in filas if f.get(campo, "").strip())
        resultado[campo] = {v for v, n in conteo.items() if n < K_ANONIMATO}
    return resultado


def anonimizar_tabla(entrada, salida, tabla, clave):
    with open(entrada, newline="", encoding="utf-8") as fh:
        lector = csv.DictReader(fh)
        campos_entrada = lector.fieldnames or []
        filas = list(lector)

    fuera = set(COLUMNAS_FUERA[tabla])
    ids = set(COLUMNAS_ID_ALUMNO[tabla])
    generalizar = GENERALIZAR[tabla]
    k_campos = K_ANON_CAMPOS[tabla]
    suprimir = conjuntos_a_suprimir(filas, tabla)

    campos_salida = cabecera_salida(campos_entrada, tabla)
    n_suprimidos = Counter()

    with open(salida, "w", newline="", encoding="utf-8") as fh:
        escritor = csv.DictWriter(fh, fieldnames=campos_salida)
        escritor.writeheader()
        for fila in filas:
            out = {}
            for campo in campos_entrada:
                if campo in fuera:
                    continue
                valor = fila.get(campo, "")
                if campo in k_campos and valor.strip() and valor.strip() in suprimir.get(campo, ()):
                    valor = k_campos[campo]
                    n_suprimidos[campo] += 1
                if campo in ids:
                    valor = seudonimo(valor, clave)
                destino, funcion = generalizar.get(campo, (campo, None))
                if funcion is not None:
                    valor = funcion(valor)
                out[destino] = valor
            escritor.writerow(out)

    extra = ""
    if n_suprimidos:
        extra = " · k-anon: " + ", ".join(f"{c}={n}" for c, n in n_suprimidos.items())
    print(f"{tabla}: {len(filas)} filas -> {salida}{extra}")


def copiar_tabla(entrada, salida, tabla):
    """Tablas sin datos personales: se copian tal cual para que 04_anon/ quede completa."""
    with open(entrada, newline="", encoding="utf-8") as fh:
        filas = list(csv.reader(fh))
    with open(salida, "w", newline="", encoding="utf-8") as fh:
        csv.writer(fh).writerows(filas)
    n = max(len(filas) - 1, 0)
    print(f"{tabla}: {n} filas copiadas sin cambios -> {salida}")


def procesar_curso(curso, clave):
    carpeta_entrada = os.path.join(CARPETA_ENTRADA, curso)
    carpeta_salida = os.path.join(CARPETA_SALIDA, curso)
    os.makedirs(carpeta_salida, exist_ok=True)

    for tabla in TABLAS:
        entrada = os.path.join(carpeta_entrada, f"{tabla}.csv")
        if not os.path.isfile(entrada):
            print(f"[{curso}] aviso: no existe {entrada}, se omite")
            continue
        salida = os.path.join(carpeta_salida, f"{tabla}.csv")
        if COLUMNAS_ID_ALUMNO[tabla] or COLUMNAS_FUERA[tabla] or GENERALIZAR[tabla] or K_ANON_CAMPOS[tabla]:
            anonimizar_tabla(entrada, salida, tabla, clave)
        else:
            copiar_tabla(entrada, salida, tabla)


def cursos_disponibles():
    return sorted(
        nombre for nombre in os.listdir(CARPETA_ENTRADA)
        if os.path.isdir(os.path.join(CARPETA_ENTRADA, nombre))
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Paso 3: anonimizacion real de los CSV.")
    parser.add_argument("--curso", help="Curso a procesar (ej. 2021-22). Si se omite, se procesan todos los de data/03_csv.")
    parser.add_argument("--clave", default=FICHERO_CLAVE, help=f"Fichero con la clave HMAC (por defecto {FICHERO_CLAVE}). Tambien se puede usar la variable de entorno ANON_KEY.")
    args = parser.parse_args()

    clave = cargar_o_crear_clave(args.clave)
    cursos = [args.curso] if args.curso else cursos_disponibles()
    for curso in cursos:
        procesar_curso(curso, clave)
    print("Anonimizacion de CSV completada.")
