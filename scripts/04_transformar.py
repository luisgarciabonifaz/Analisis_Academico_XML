import argparse
import csv
import os
from collections import Counter

# Paso 4 del flujo: aplica las reglas de negocio de CLAUDE.md y los arreglos de
# calidad de datos sobre los CSV ya anonimizados del Paso 3, y proyecta cada
# tabla a su lista blanca de columnas (ver README.md).
#
# Orden de operaciones (docs/Analisis_y_Diseno_DW.md §6.2), por cada curso:
#   1. Cargar y tipar los 4 CSV canonicos; normalizar " " / "" -> "" (D4).
#   2. R1 - bajas: quitar los alumnos con estado_matricula = 'B' y, en el mismo
#      INNER JOIN, las calificaciones de alumnos que no tengan matricula viva
#      (cascada de bajas + huerfanas D11, ver docs §8.1 y D11).
#   3. R2 - evaluaciones: solo se conservan 01, 02, FI, EX.
#   4. D1 - un alumno por NIA: si tras R1 quedan NIA repetidos (matriculas
#      M+M residuales), quedarse con una fila (ver criterio de desempate).
#   5. R3 - presentado / nota / aprobado, derivadas de nota_numerica.
#   6. D2 - deduplicar: DISTINCT en Calificaciones y en el resto de tablas.
#   7. R4 - proyectar cada tabla a su lista blanca. Escribir a data/05_staging/.
#
# Entrada : data/04_anon/<curso>/*.csv     (ya anonimizado, Paso 3)
# Salida  : data/05_staging/<curso>/*.csv  (lista blanca + flags derivados)

CARPETA_ENTRADA = "data/04_anon"
CARPETA_SALIDA = "data/05_staging"

# Solo se procesan los 4 CSV canonicos (Alumnos, Calificaciones, Contenidos,
# Cursos). Grupos esta fuera del proyecto (no llega a data/04_anon/).
EVALUACIONES_VALIDAS = {"01", "02", "FI", "EX"}

# R4 - lista blanca de columnas (README.md, seccion "Transformacion de los CSV").
# 'presentado_flag', 'nota' y 'aprobado_flag' son derivadas de R3 (no existen
# en el origen, se anaden aqui). 'NIA' / 'alumno' ya son un seudonimo (Paso 3).
LISTA_BLANCA = {
    "Alumnos": [
        "anyo", "fecha_exportacion", "NIA", "anyo_nac", "sexo",
        "nacionalidad", "pais_nac", "municipio_nac", "cod_postal",
        "curso", "grupo", "turno",
    ],
    "Calificaciones": [
        "anyo", "fecha_exportacion", "evaluacion", "alumno", "curso",
        "contenido", "nota_numerica",
        "presentado_flag", "nota", "aprobado_flag",
    ],
    "Contenidos": ["anyo", "fecha_exportacion", "codigo", "nombre_cas", "curso"],
    "Cursos": ["anyo", "fecha_exportacion", "codigo", "nombre_cas", "abreviatura", "padre"],
    # "Grupos": fuera del proyecto -> no se lee ni se proyecta.
}


# --- Utilidades de carga -----------------------------------------------------
def leer_csv(ruta):
    """Lee un CSV a lista de dict, normalizando 'espacio en blanco' -> '' (D4)."""
    if not os.path.isfile(ruta):
        return None
    with open(ruta, newline="", encoding="utf-8") as fh:
        filas = []
        for fila in csv.DictReader(fh):
            filas.append({campo: (valor or "").strip() for campo, valor in fila.items()})
    return filas


def escribir_csv(ruta, filas, columnas):
    with open(ruta, "w", newline="", encoding="utf-8") as fh:
        escritor = csv.DictWriter(fh, fieldnames=columnas)
        escritor.writeheader()
        for fila in filas:
            escritor.writerow({c: fila.get(c, "") for c in columnas})


# --- R1 -- bajas (+ D11, huerfanas de calificacion) --------------------------
def aplicar_r1(alumnos, calificaciones):
    """Elimina alumnos de baja; INNER JOIN de Calificaciones con la matricula
    viva -- descarta a la vez las de alumnos dados de baja (cascada) y las
    huerfanas sin alumno en absoluto (D11, ver docs/Analisis_y_Diseno_DW.md)."""
    alumnos_vivos = [a for a in alumnos if a.get("estado_matricula", "") != "B"]
    nia_vivos = {a["NIA"] for a in alumnos_vivos}
    calif_vivas = [c for c in calificaciones if c["alumno"] in nia_vivos]
    return alumnos_vivos, calif_vivas


# --- R2 -- evaluaciones validas ----------------------------------------------
def aplicar_r2(calificaciones):
    return [c for c in calificaciones if c["evaluacion"] in EVALUACIONES_VALIDAS]


# --- D1 -- un alumno por NIA --------------------------------------------------
def aplicar_d1(alumnos, calificaciones):
    """Si tras R1 quedan NIA repetidos (matriculas M+M residuales), se queda
    una fila por NIA. Desempate: 1) fecha_matricula (aaaa-mm) mas reciente;
    2) el 'curso' de la fila con mas calificaciones asociadas (aproxima el
    'grupo con mas calificaciones' del diseno: Calificaciones no lleva grupo,
    pero si 'curso', que es el nodo de matricula real)."""
    por_nia = {}
    for a in alumnos:
        por_nia.setdefault(a["NIA"], []).append(a)

    conteo_curso = Counter((c["alumno"], c["curso"]) for c in calificaciones)

    resultado = []
    for nia, filas in por_nia.items():
        if len(filas) == 1:
            resultado.append(filas[0])
            continue
        elegida = max(filas, key=lambda f: (
            f.get("fecha_matricula", ""),
            conteo_curso.get((f["NIA"], f["curso"]), 0),
        ))
        resultado.append(elegida)
    return resultado


# --- R3 -- presentado / nota / aprobado --------------------------------------
def derivar_nota(nota_numerica):
    """nota_numerica = '' / 0 -> no presentado (regla CLAUDE.md)."""
    txt = (nota_numerica or "").strip()
    if txt == "":
        return {"presentado_flag": "0", "nota": ""}
    valor = float(txt.replace(",", "."))
    if valor == 0:
        return {"presentado_flag": "0", "nota": ""}
    return {"presentado_flag": "1", "nota": f"{valor:g}"}


def aplicar_r3(calificaciones):
    resultado = []
    for c in calificaciones:
        derivadas = derivar_nota(c.get("nota_numerica"))
        nota = derivadas["nota"]
        aprobado = "1" if (nota != "" and float(nota) >= 5) else "0"
        fila = dict(c)
        fila["presentado_flag"] = derivadas["presentado_flag"]
        fila["nota"] = nota
        fila["aprobado_flag"] = aprobado
        resultado.append(fila)
    return resultado


# --- D2 -- deduplicacion ------------------------------------------------------
def clave_calificacion(c):
    """Clave de negocio tras R1-R3: el DISTINCT que resuelve el cruce
    alumno<->grupo de ITACA (mismas notas repetidas) y el colapso al quitar
    tipo_nota / bloque_contenido (comprobado: 0 conflictos de nota, ver
    docs/Analisis_y_Diseno_DW.md §3.2)."""
    return (c["anyo"], c["alumno"], c["curso"], c["contenido"], c["evaluacion"], c["nota_numerica"])


def deduplicar(filas, clave):
    vistas = set()
    resultado = []
    for fila in filas:
        k = clave(fila)
        if k in vistas:
            continue
        vistas.add(k)
        resultado.append(fila)
    return resultado


# --- R4 -- proyeccion a la lista blanca --------------------------------------
def proyectar(filas, tabla):
    columnas = LISTA_BLANCA[tabla]
    return [{c: fila.get(c, "") for c in columnas} for fila in filas], columnas


# --- Orquestacion por curso ---------------------------------------------------
def procesar_curso(curso):
    carpeta_entrada = os.path.join(CARPETA_ENTRADA, curso)
    carpeta_salida = os.path.join(CARPETA_SALIDA, curso)
    os.makedirs(carpeta_salida, exist_ok=True)

    alumnos = leer_csv(os.path.join(carpeta_entrada, "Alumnos.csv"))
    if alumnos is None:
        print(f"[{curso}] aviso: no existe Alumnos.csv, se omite el curso")
        return
    calificaciones = leer_csv(os.path.join(carpeta_entrada, "Calificaciones.csv")) or []
    contenidos = leer_csv(os.path.join(carpeta_entrada, "Contenidos.csv")) or []
    cursos = leer_csv(os.path.join(carpeta_entrada, "Cursos.csv")) or []

    n_alumnos_crudos = len(alumnos)
    n_calif_crudas = len(calificaciones)

    # 2. R1 -- bajas + D11
    alumnos, calificaciones = aplicar_r1(alumnos, calificaciones)
    # 3. R2 -- evaluaciones validas
    calificaciones = aplicar_r2(calificaciones)
    # 4. D1 -- un alumno por NIA
    alumnos = aplicar_d1(alumnos, calificaciones)
    # 5. R3 -- presentado / nota / aprobado
    calificaciones = aplicar_r3(calificaciones)
    # 6. D2 -- deduplicar
    calificaciones = deduplicar(calificaciones, clave_calificacion)
    alumnos = deduplicar(alumnos, lambda a: a["NIA"])
    contenidos = deduplicar(contenidos, lambda m: (m["curso"], m["codigo"]))
    cursos = deduplicar(cursos, lambda c: c["codigo"])

    # 7. R4 -- proyectar a la lista blanca y escribir
    alumnos_out, cols_alumnos = proyectar(alumnos, "Alumnos")
    calif_out, cols_calif = proyectar(calificaciones, "Calificaciones")
    contenidos_out, cols_contenidos = proyectar(contenidos, "Contenidos")
    cursos_out, cols_cursos = proyectar(cursos, "Cursos")

    escribir_csv(os.path.join(carpeta_salida, "Alumnos.csv"), alumnos_out, cols_alumnos)
    escribir_csv(os.path.join(carpeta_salida, "Calificaciones.csv"), calif_out, cols_calif)
    escribir_csv(os.path.join(carpeta_salida, "Contenidos.csv"), contenidos_out, cols_contenidos)
    escribir_csv(os.path.join(carpeta_salida, "Cursos.csv"), cursos_out, cols_cursos)

    no_presentados = sum(1 for c in calif_out if c["presentado_flag"] == "0")
    print(
        f"{curso}: Alumnos {n_alumnos_crudos} -> {len(alumnos_out)} · "
        f"Calificaciones {n_calif_crudas} -> {len(calif_out)} "
        f"({no_presentados} no presentados) · Contenidos {len(contenidos_out)} · "
        f"Cursos {len(cursos_out)}"
    )


def cursos_disponibles():
    return sorted(
        nombre for nombre in os.listdir(CARPETA_ENTRADA)
        if os.path.isdir(os.path.join(CARPETA_ENTRADA, nombre))
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Paso 4: reglas de negocio, calidad y lista blanca.")
    parser.add_argument("--curso", help="Curso a procesar (ej. 2021-22). Si se omite, se procesan todos los de data/04_anon.")
    args = parser.parse_args()

    cursos = [args.curso] if args.curso else cursos_disponibles()
    for curso in cursos:
        procesar_curso(curso)
    print("Transformacion completada.")
