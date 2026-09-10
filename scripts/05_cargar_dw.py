import argparse
import csv
import os
from collections import defaultdict

# Paso 5 del flujo: carga el Data Warehouse en estrella (docs/Analisis_y_Diseno_DW.md §7)
# a partir del staging limpio del Paso 4, con UNION de todos los cursos EN ALCANCE.
#
# Entrada : data/05_staging/<curso>/*.csv  (uno por curso academico)
# Salida  : data/06_dw/dim_*.csv, data/06_dw/hecho_*.csv
#
# Claves subrogadas (todas deterministas, sin contador global -- el CSV se puede
# regenerar sin que cambien las claves):
#   alumno_sk           = NIA (ya es un seudonimo estable entre anyos, Paso 3)
#   curso_academico_sk  = anyo
#   curso_sk            = "<anyo>_<codigo>"       (el codigo de Cursos NO es estable
#                                                   entre anyos, comprobado: 0 codigos
#                                                   L3 comunes entre 2021-22 y 2022-23)
#   modulo_sk            = "<anyo>_<curso>_<codigo>" (codigo tampoco es unico dentro
#                                                   de un mismo anyo, ver docs §3.3)
#   evaluacion_cod / turno = el propio codigo (dominio fijo, sin subrogada)

CARPETA_ENTRADA = "data/05_staging"
CARPETA_SALIDA = "data/06_dw"
CARPETA_CATALOGOS = "data/catalogos"

# D9: 2025-26 se excluye del DW mientras su exportacion de calificaciones este
# vacia (ver docs/Analisis_y_Diseno_DW.md §2). Quitar de aqui cuando llegue el
# export definitivo -- el resto del script no necesita ningun otro cambio.
ANYOS_EXCLUIDOS = {"2025-26"}

# Codigo de nacionalidad "Espanola" en el catalogo de origen (comprobado: 724 es
# el valor dominante, 1.065 de 1.198 alumnos en 2021-22) -> para es_extranjero.
NACIONALIDAD_ESPANOLA = "724"

TRAMOS_EDAD = [(20, "<20"), (25, "20-24"), (30, "25-29"), (None, "30+")]


# --- Utilidades ---------------------------------------------------------------
def leer_csv(ruta):
    if not os.path.isfile(ruta):
        return []
    with open(ruta, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def escribir_csv(ruta, filas, columnas):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", newline="", encoding="utf-8") as fh:
        escritor = csv.DictWriter(fh, fieldnames=columnas)
        escritor.writeheader()
        for fila in filas:
            escritor.writerow({c: fila.get(c, "") for c in columnas})


def cargar_catalogo(nombre):
    """Catalogo manual opcional data/catalogos/<nombre>.csv (columnas cod,descripcion).
    Si no existe, se sirve sin descripcion (queda el codigo crudo, ver docs §10)."""
    ruta = os.path.join(CARPETA_CATALOGOS, f"{nombre}.csv")
    filas = leer_csv(ruta)
    return {f["cod"]: f.get("descripcion", "") for f in filas}


def cursos_en_alcance():
    return sorted(
        nombre for nombre in os.listdir(CARPETA_ENTRADA)
        if os.path.isdir(os.path.join(CARPETA_ENTRADA, nombre)) and nombre not in ANYOS_EXCLUIDOS
    )


def tramo_edad(edad):
    if edad is None:
        return ""
    for limite, etiqueta in TRAMOS_EDAD:
        if limite is None or edad < limite:
            return etiqueta
    return ""


# --- Jerarquia de Cursos (docs §8.7), adaptada con clave por anyo -------------
def resolver_jerarquia(cod, by_cod):
    cadena, actual = [], cod
    vistos = set()
    while actual and actual in by_cod and actual not in vistos and len(cadena) < 5:
        vistos.add(actual)
        cadena.append(by_cod[actual])
        actual = by_cod[actual].get("padre", "").strip()
    return cadena  # [0]=L3 curso · [1]=L2 ciclo · [2]=L1 grado · [3]=L0 familia


def fila_dim_curso(anyo, cod, by_cod):
    cadena = resolver_jerarquia(cod, by_cod)
    L3 = cadena[0] if len(cadena) > 0 else {}
    L2 = cadena[1] if len(cadena) > 1 else {}
    L1 = cadena[2] if len(cadena) > 2 else {}
    L0 = cadena[3] if len(cadena) > 3 else {}
    abrev = L3.get("abreviatura", "").strip()
    return {
        "curso_sk": f"{anyo}_{cod}",
        "anyo": anyo,
        "curso_cod": cod,
        "curso_nivel": abrev[0] if abrev[:1].isdigit() else "",
        "curso_nombre": L3.get("nombre_cas", ""),
        "ciclo_cod": L2.get("abreviatura", ""),
        "ciclo_nombre": L2.get("nombre_cas", ""),
        "grado_cod": L1.get("abreviatura", ""),
        "grado_nombre": L1.get("nombre_cas", ""),
        "familia_cod": L0.get("abreviatura", ""),
        "familia_nombre": L0.get("nombre_cas", ""),
    }


def tipo_modulo(codigo):
    if codigo.startswith("TU"):
        return "tutoria"
    if codigo.startswith("CV"):
        return "ingles"
    return "ordinario"


# --- Dimensiones de dominio fijo ----------------------------------------------
def dim_evaluacion():
    return [
        {"cod": "01", "nombre": "1a evaluacion", "tipo": "parcial"},
        {"cod": "02", "nombre": "2a evaluacion", "tipo": "parcial"},
        {"cod": "FI", "nombre": "Final ordinaria", "tipo": "final"},
        {"cod": "EX", "nombre": "Extraordinaria", "tipo": "extraordinaria"},
    ]


def dim_turno():
    return [
        {"cod": "D", "nombre": "Diurno"},
        {"cod": "S", "nombre": "Semipresencial"},
    ]


# --- Carga por curso -----------------------------------------------------------
def procesar_curso(anyo_carpeta, estado):
    """Vuelca un curso academico sobre el 'estado' acumulado (dims + hechos)."""
    carpeta = os.path.join(CARPETA_ENTRADA, anyo_carpeta)
    alumnos = leer_csv(os.path.join(carpeta, "Alumnos.csv"))
    calificaciones = leer_csv(os.path.join(carpeta, "Calificaciones.csv"))
    contenidos = leer_csv(os.path.join(carpeta, "Contenidos.csv"))
    cursos = leer_csv(os.path.join(carpeta, "Cursos.csv"))
    if not alumnos:
        print(f"[{anyo_carpeta}] aviso: sin Alumnos.csv, se omite")
        return

    anyo = alumnos[0]["anyo"]
    fecha_exportacion = alumnos[0].get("fecha_exportacion", "")
    by_cod = {c["codigo"]: c for c in cursos}

    # dim_curso_academico
    estado["curso_academico"].append({
        "curso_academico_sk": anyo,
        "anyo": anyo,
        "etiqueta": f"{anyo}-{(int(anyo) + 1) % 100:02d}",
        "fecha_exportacion": fecha_exportacion,
    })

    # dim_curso -- solo los nodos L3 realmente usados por Alumnos/Calificaciones/Contenidos
    hojas = ({a["curso"] for a in alumnos}
             | {c["curso"] for c in calificaciones}
             | {m["curso"] for m in contenidos})
    dim_curso_anyo = {}
    for cod in hojas:
        if not cod:
            continue
        fila = fila_dim_curso(anyo, cod, by_cod)
        dim_curso_anyo[cod] = fila
        estado["curso"].append(fila)

    # dim_modulo -- (anyo, curso, codigo), hereda la jerarquia del curso
    dim_modulo_anyo = {}
    for m in contenidos:
        curso_cod = m["curso"]
        jerarquia = dim_curso_anyo.get(curso_cod, {})
        fila = {
            "modulo_sk": f"{anyo}_{curso_cod}_{m['codigo']}",
            "anyo": anyo,
            "curso_sk": f"{anyo}_{curso_cod}",
            "codigo": m["codigo"],
            "nombre_cas": m["nombre_cas"],
            "tipo_modulo": tipo_modulo(m["codigo"]),
            "familia_nombre": jerarquia.get("familia_nombre", ""),
            "grado_nombre": jerarquia.get("grado_nombre", ""),
            "ciclo_nombre": jerarquia.get("ciclo_nombre", ""),
            "curso_nivel": jerarquia.get("curso_nivel", ""),
        }
        dim_modulo_anyo[(curso_cod, m["codigo"])] = fila
        estado["modulo"].append(fila)

    # dim_alumno (SCD1: la ultima aparicion cronologica gana) + catalogos
    for a in alumnos:
        edad = int(anyo) - int(a["anyo_nac"]) if a.get("anyo_nac", "").isdigit() else None
        nacionalidad = a.get("nacionalidad", "")
        estado["alumno"][a["NIA"]] = {
            "alumno_sk": a["NIA"],
            "sexo": a.get("sexo", ""),
            "anyo_nac": a.get("anyo_nac", ""),
            "edad": edad if edad is not None else "",
            "tramo_edad": tramo_edad(edad),
            "nacionalidad_cod": nacionalidad,
            "nacionalidad_desc": estado["cat_nacionalidad"].get(nacionalidad, ""),
            "es_extranjero": "" if not nacionalidad else ("0" if nacionalidad == NACIONALIDAD_ESPANOLA else "1"),
            "pais_nac_cod": a.get("pais_nac", ""),
            "pais_nac_desc": estado["cat_pais"].get(a.get("pais_nac", ""), ""),
            "municipio_nac_cod": a.get("municipio_nac", ""),
            "municipio_nac_desc": estado["cat_municipio"].get(a.get("municipio_nac", ""), ""),
            "cod_postal": a.get("cod_postal", ""),
        }

    # hecho_calificacion -- una fila por calificacion valida (grano del Paso 4)
    matricula_por_nia = {a["NIA"]: a for a in alumnos}
    for c in calificaciones:
        matricula = matricula_por_nia.get(c["alumno"], {})
        estado["hecho_calificacion"].append({
            "alumno_sk": c["alumno"],
            "modulo_sk": f"{anyo}_{c['curso']}_{c['contenido']}",
            "curso_sk": f"{anyo}_{c['curso']}",
            "curso_academico_sk": anyo,
            "evaluacion_cod": c["evaluacion"],
            "grupo_cod": matricula.get("grupo", ""),
            "turno": matricula.get("turno", ""),
            "nota_numerica": c["nota_numerica"],
            "nota": c["nota"],
            "presentado_flag": c["presentado_flag"],
            "aprobado_flag": c["aprobado_flag"],
            "n_calificaciones": "1",
        })

    # hecho_matricula -- una fila por alumno matriculado ese curso academico
    notas_por_alumno_modulo = defaultdict(lambda: defaultdict(list))
    for c in calificaciones:
        notas_por_alumno_modulo[c["alumno"]][(c["curso"], c["contenido"])].append(c)

    for a in alumnos:
        modulos = notas_por_alumno_modulo.get(a["NIA"], {})
        n_matriculados = len(modulos)
        n_aprobados = n_suspensos = n_no_presentados = 0
        finales = []
        for notas_modulo in modulos.values():
            por_eval = {n["evaluacion"]: n for n in notas_modulo}
            final = por_eval.get("EX") or por_eval.get("FI")
            finales.append(final)
            if final is None:
                # matriculado con notas parciales pero sin EX/FI todavia
                # (ver docs §10 "Pendientes de negocio" #3): se cuenta como no
                # presentado, igual que si la nota final fuese 0.
                n_no_presentados += 1
            elif final["presentado_flag"] == "0":
                n_no_presentados += 1
            elif final["aprobado_flag"] == "1":
                n_aprobados += 1
            else:
                n_suspensos += 1

        if n_matriculados == 0:
            todo_aprobado = ""  # sin ninguna calificacion ese anyo (§8.8)
        else:
            todo_aprobado = "1" if all(
                f is not None and f["aprobado_flag"] == "1" for f in finales
            ) else "0"

        estado["hecho_matricula"].append({
            "alumno_sk": a["NIA"],
            "curso_sk": f"{anyo}_{a['curso']}",
            "curso_academico_sk": anyo,
            "grupo_cod": a.get("grupo", ""),
            "turno": a.get("turno", ""),
            "matriculado_flag": "1",
            "todo_aprobado_flag": todo_aprobado,
            "n_modulos_matriculados": str(n_matriculados),
            "n_modulos_aprobados": str(n_aprobados),
            "n_modulos_suspensos": str(n_suspensos),
            "n_modulos_no_presentados": str(n_no_presentados),
        })

    print(
        f"{anyo_carpeta}: dim_curso +{len(dim_curso_anyo)} · dim_modulo +{len(dim_modulo_anyo)} · "
        f"hecho_calificacion +{len(calificaciones)} · hecho_matricula +{len(alumnos)}"
    )


def main():
    parser = argparse.ArgumentParser(description="Paso 5: carga el Data Warehouse en estrella.")
    parser.add_argument(
        "--cursos", nargs="*",
        help="Cursos a cargar (ej. 2021-22 2022-23). Si se omite, todos los de "
             f"data/05_staging salvo {sorted(ANYOS_EXCLUIDOS)}.",
    )
    args = parser.parse_args()
    cursos = args.cursos if args.cursos else cursos_en_alcance()

    estado = {
        "curso_academico": [],
        "curso": [],
        "modulo": [],
        "alumno": {},  # NIA -> fila (SCD1, se sobreescribe)
        "hecho_calificacion": [],
        "hecho_matricula": [],
        "cat_nacionalidad": cargar_catalogo("dim_nacionalidad"),
        "cat_pais": cargar_catalogo("dim_pais"),
        "cat_municipio": cargar_catalogo("dim_municipio"),
    }

    print(f"Cursos en alcance: {cursos} (excluidos: {sorted(ANYOS_EXCLUIDOS)})")
    for curso in cursos:
        procesar_curso(curso, estado)

    escribir_csv(
        os.path.join(CARPETA_SALIDA, "dim_curso_academico.csv"), estado["curso_academico"],
        ["curso_academico_sk", "anyo", "etiqueta", "fecha_exportacion"],
    )
    escribir_csv(
        os.path.join(CARPETA_SALIDA, "dim_curso.csv"), estado["curso"],
        ["curso_sk", "anyo", "curso_cod", "curso_nivel", "curso_nombre", "ciclo_cod",
         "ciclo_nombre", "grado_cod", "grado_nombre", "familia_cod", "familia_nombre"],
    )
    escribir_csv(
        os.path.join(CARPETA_SALIDA, "dim_modulo.csv"), estado["modulo"],
        ["modulo_sk", "anyo", "curso_sk", "codigo", "nombre_cas", "tipo_modulo",
         "familia_nombre", "grado_nombre", "ciclo_nombre", "curso_nivel"],
    )
    escribir_csv(
        os.path.join(CARPETA_SALIDA, "dim_alumno.csv"), list(estado["alumno"].values()),
        ["alumno_sk", "sexo", "anyo_nac", "edad", "tramo_edad", "nacionalidad_cod",
         "nacionalidad_desc", "es_extranjero", "pais_nac_cod", "pais_nac_desc",
         "municipio_nac_cod", "municipio_nac_desc", "cod_postal"],
    )
    escribir_csv(os.path.join(CARPETA_SALIDA, "dim_evaluacion.csv"), dim_evaluacion(), ["cod", "nombre", "tipo"])
    escribir_csv(os.path.join(CARPETA_SALIDA, "dim_turno.csv"), dim_turno(), ["cod", "nombre"])
    escribir_csv(
        os.path.join(CARPETA_SALIDA, "hecho_calificacion.csv"), estado["hecho_calificacion"],
        ["alumno_sk", "modulo_sk", "curso_sk", "curso_academico_sk", "evaluacion_cod",
         "grupo_cod", "turno", "nota_numerica", "nota", "presentado_flag", "aprobado_flag",
         "n_calificaciones"],
    )
    escribir_csv(
        os.path.join(CARPETA_SALIDA, "hecho_matricula.csv"), estado["hecho_matricula"],
        ["alumno_sk", "curso_sk", "curso_academico_sk", "grupo_cod", "turno",
         "matriculado_flag", "todo_aprobado_flag", "n_modulos_matriculados",
         "n_modulos_aprobados", "n_modulos_suspensos", "n_modulos_no_presentados"],
    )

    n_alumnos = len(estado["alumno"])
    n_todo_aprobado = sum(1 for m in estado["hecho_matricula"] if m["todo_aprobado_flag"] == "1")
    n_con_flag = sum(1 for m in estado["hecho_matricula"] if m["todo_aprobado_flag"] != "")
    pct = (100 * n_todo_aprobado / n_con_flag) if n_con_flag else 0
    print(
        f"DW cargado en {CARPETA_SALIDA}/: {n_alumnos} alumnos distintos (todos los anyos) · "
        f"{len(estado['hecho_matricula'])} filas de hecho_matricula · "
        f"{len(estado['hecho_calificacion'])} filas de hecho_calificacion · "
        f"% todo aprobado (global) = {pct:.1f}%"
    )


if __name__ == "__main__":
    main()
