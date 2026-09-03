# Análisis de datos y diseño del Data Warehouse académico

> Curso analizado: **2021‑22** · Ficheros: `Originales/2021-22/Paso1/*.csv`
> Fecha del análisis: 2026‑09‑03

---

## 1. Resumen ejecutivo

Los CSV de `Paso1` provienen de la exportación de ITACA (ya anonimizada en el Paso 1 y
convertida a CSV en el Paso 2). Contienen los datos necesarios para construir un Data
Warehouse dimensional orientado al análisis académico, con:

- **1.341** matrículas de alumno (**1.334** alumnos distintos),
- **18.906** calificaciones,
- **265** módulos (Contenidos), **70** cursos jerárquicos, **46** grupos.

La **integridad referencial del origen es muy buena** (0 huérfanos en todas las
relaciones). Los principales trabajos del flujo son: deduplicar calificaciones,
resolver las matrículas dobles, normalizar nulos, interpretar el "0" como
"no presentado" cuando corresponde, y **aplanar la jerarquía de `Cursos`**
(familia → grado → ciclo → 1º/2º) sobre las dimensiones de curso y de módulo.

---

## 2. Inventario de ficheros

| Fichero | Filas | Grano (1 fila = …) | Clave natural |
|---|---:|---|---|
| `Alumnos.csv` | 1.341 | matrícula de un alumno en un grupo | `NIA` + `grupo` |
| `Calificaciones.csv` | 18.906 | nota de un alumno en un módulo / evaluación / tipo | `alumno` + `curso` + `contenido` + `evaluacion` + `tipo_nota` |
| `Contenidos.csv` (Módulos) | 265 | módulo dentro de un curso (1º/2º de un ciclo) | `curso` + `codigo` |
| `Cursos.csv` | 70 | nodo del árbol académico (familia/grado/ciclo/curso) | `codigo` |
| `Grupos.csv` | 46 | grupo | `codigo` |

Todos los CSV incluyen además `anyo` (= `curso` del `<centro>`) y `fecha_exportacion`
(= `fechaExportacion` del `<centro>`), añadidos en el Paso 2.

---

## 3. Análisis por tabla

### 3.1 Alumnos

- 37 columnas. Campos con valor **constante**: `ensenanza = 5` (FP), `modalidad = COM`.
- **`NIA` no es único**: 1.334 distintos en 1.341 filas → **7 NIA repetidos**.
  Corresponden a alumnos con **doble matrícula** en el curso (típicamente una activa
  `estado_matricula = 'M'` y otra de baja `'B'`, por cambio de grupo o de turno).
- Distribuciones:

  | Campo | Valores |
  |---|---|
  | `sexo` | `M` 792 · `H` 549 |
  | `turno` | `D` (diurno) 949 · `S` (semipresencial) 392 |
  | `estado_matricula` | `M` (matriculado) 1.198 · `B` (baja) 143 |
  | `repite` | `0` → 1.236 · `2` → 105 |
  | `grupo` | 46 distintos, siempre informado |
  | `curso` | 31 distintos (todos nodos hoja del árbol de Cursos) |
  | `nacionalidad` | 42 valores distintos (códigos) |

- `fecha_nac` está siempre informada → permite derivar **edad** y **tramo de edad**.
- Códigos sin descripción: `nacionalidad`, `pais_nac`, `provincia`, `municipio`,
  `localidad`, `municipio_nac` (requieren catálogos).

### 3.2 Calificaciones

- **Grano**: alumno × curso × contenido × evaluación × tipo_nota.
- **237 filas duplicadas exactas** (misma nota repetida, hasta 4×). Se originan por el
  cruce alumno↔grupo en ITACA cuando el alumno tiene doble matrícula. → **`DISTINCT`**.
- `bloque_contenido` **vacío en el 100 %** de las filas → columna eliminable.
- `evaluacion` — 24 códigos. Los relevantes por volumen:

  | Código | Nº | Interpretación probable |
  |---|---:|---|
  | `01` | 6.790 | 1ª evaluación ordinaria |
  | `FI` | 6.173 | Evaluación final ordinaria |
  | `02` | 4.044 | 2ª evaluación ordinaria |
  | `EX` | 1.188 | Evaluación extraordinaria |
  | `FO`, `PO` | 306 / 223 | (por confirmar) |
  | `F1`…`F9`, `FC`, `FE`, `A7`, `A8`, `P1`, `P2`, `11`, `12` | < 70 c/u | faltas / FCT / casos especiales (por confirmar) |

- `tipo_nota` — ~16 códigos numéricos largos (p. ej. `146988218`, `360492991`).
  Dominio desconocido; se comporta como atributo de la nota (¿nota de módulo vs RA/UF,
  convocatoria, tipo cualitativo…?). Requiere catálogo.
- `nota_numerica` — rango 0–10, 1 valor vacío. Distribución:

  | Nota | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
  |---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
  | Nº | 4.038 | 246 | 248 | 429 | 1.210 | 972 | 2.160 | 3.101 | 3.217 | 2.426 | 858 |

  Los **4.038 ceros** son sospechosos: muchos se concentran en `tipo_nota = 146988218`
  y en evaluaciones `01/EX/FI`. Es muy probable que un buen número signifique
  **"no presentado / sin calificar"** y no un 0 real. → derivar `presentado_flag`
  y dejar `nota = NULL` en esos casos, conservando `nota_numerica` cruda aparte.

### 3.3 Contenidos (Módulos)

- **`codigo` NO es único**: 184 códigos distintos en 265 filas. La clave real es
  **`(curso, codigo)`** — un mismo módulo (p. ej. `0156` "Inglés") se imparte en
  varios ciclos.
- El campo `curso` apunta **siempre a un nodo hoja (nivel 3)** del árbol de Cursos
  → cada módulo se puede clasificar por familia / grado / ciclo / 1º‑2º.
- `nombre_cas` y `nombre_val` (castellano y valenciano).
- Tipos de módulo derivables del `codigo`: tutoría (`TU*`), inglés técnico /
  horario en inglés (`CV*`), y módulos ordinarios (código numérico).

### 3.4 Cursos — árbol jerárquico

`Cursos.csv` es un **árbol de 4 niveles** encadenado por `codigo ← padre`:

| Nivel | Concepto | `nombre_cas` | `abreviatura` | Nº nodos |
|---|---|---|---|---:|
| **L0** | Familia profesional | nombre de la familia | código de familia (`190`, `020`…) | 7 |
| **L1** | Grado / enseñanza | GRADO MEDIO / SUPERIOR / CURSO ESPECIALIZACIÓN | `GM` / `GS` / `CE` | 12 |
| **L2** | Ciclo formativo | nombre del ciclo | código del ciclo (`845104`…) | 18 |
| **L3** | Curso (1º / 2º) | `Primero` / `Segundo` / `Primero CE` | `1CFS` `2CFS` `1CFM` `2CFM` `1CES` | 33 |

- `Alumnos`, `Calificaciones` y `Contenidos` referencian **siempre nodos L3**.
- **Datos que aporta la jerarquía** (subiendo por `padre` desde el `curso`):
  - **si es primero o segundo** (`curso_nivel` = 1ª cifra de la abreviatura L3, coincide con la 1ª cifra del `grupo`),
  - **ciclo formativo** (L2),
  - **grado** GM/GS/CE (L1),
  - **familia profesional** (L0),
  - y por extensión, la clasificación de cada **módulo/contenido**.
- **Casos borde**:
  - La familia `039` (HOSTELERÍA Y TURISMO) aparece en **dos** nodos raíz distintos
    (`2712307648` y `2712338777`). Exponer `familia_codigo` como atributo; agrupar
    por ese código si se quiere unificar.
  - Rama `2712338777 → 2712338886` (`X27`, "OPERACIONES BÁSICAS DE PISOS"): solo
    2 niveles (programa formativo básico, sin L2/L3), sin referencias. Resolver con
    `grado = 'PFB'` y `ciclo` / `curso_nivel` = NULL sin que falle el proceso.

### 3.5 Grupos

- 46 grupos, clave `codigo`. `aula` frecuentemente vacía.
- `turno` (D/S), `modalidad` (COM), `linea`, `capacidad`.
- El nivel 1º/2º también está en el `codigo`/`nombre` del grupo (redundante con `dim_curso`).
- Métrica derivable: **ocupación** = nº de alumnos matriculados / `capacidad`.

---

## 4. Integridad referencial (resultado de las comprobaciones)

| Relación | Resultado |
|---|---|
| `Calificaciones.alumno` → `Alumnos.NIA` | ✅ 0 huérfanos |
| `Calificaciones.(curso, contenido)` → `Contenidos.(curso, codigo)` | ✅ 0 huérfanos |
| `Calificaciones.curso` → `Cursos.codigo` | ✅ 0 huérfanos |
| `Alumnos.curso` → `Cursos.codigo` | ✅ 0 huérfanos |
| `Alumnos.grupo` → `Grupos.codigo` | ✅ 0 huérfanos |
| `Contenidos.curso` → `Cursos.codigo` | ✅ 0 huérfanos |
| Alumnos sin ninguna calificación | 73 (en su mayoría bajas) |

---

## 5. Problemas de calidad y tratamiento

| # | Problema | Detalle | Tratamiento |
|---|---|---|---|
| D1 | NIA duplicado en Alumnos | 7 NIA con 2 matrículas (activa + baja) | Marcar `es_matricula_principal` (la `M`, o la más reciente). `dim_alumno` = 1 fila por NIA |
| D2 | Filas duplicadas en Calificaciones | 237 filas idénticas por el cruce alumno↔grupo | `DISTINCT` en staging |
| D3 | `bloque_contenido` siempre vacío | 18.906 / 18.906 | Eliminar columna |
| D4 | `nota_numerica = 0` ambiguo | 4.038 ceros; muchos = "no presentado" | `presentado_flag`; `nota = NULL` si no presentado; conservar `nota_numerica` cruda |
| D5 | Nulos como `" "` | ITACA rellena vacíos con espacio | Normalizar `""` → NULL al tipar (el `strip()` ya se hace en el Paso 2) |
| D6 | Códigos sin descripción | `evaluacion`, `tipo_nota`, `nacionalidad`, `pais_nac`, `provincia`, `municipio` | Tablas de catálogo rellenadas manualmente una vez |
| D7 | Columnas constantes | `ensenanza = 5`, `modalidad = COM` en todo Alumnos | Mantener, no usar como filtro |
| D8 | Familia `039` en 2 nodos raíz | jerarquía de Cursos | Clave por `familia_codigo`, no por `codigo` del nodo |
| D9 | Rama sin L2/L3 (`X27`) | programa formativo básico | Resolver niveles faltantes a NULL / `PFB` |

---

## 6. Flujo de datos (capas)

```
Originales/<curso>/*.xml              ITACA en bruto
   │  Paso 1 · anonimizar_xml.py      (anonimización)
   ▼
Originales/<curso>/Paso1/*.xml        XML anonimizado
   │  Paso 2 · XML_a_CSV.py           (extracción a CSV + anyo, fecha_exportacion)
   ▼
Originales/<curso>/Paso1/*.csv        STAGING CRUDO (1:1 con el XML)
   │  Paso 3 · transformar.py         dedup · tipado · nulos · flags · D1/D2/D4
   ▼
<curso>/Staging/*.csv                 STAGING LIMPIO
   │  Paso 4 · cargar_dw.py           claves subrogadas · jerarquía de Cursos ·
   │                                  catálogos · UNION multi-año
   ▼
DW/  dim_*.csv  +  hecho_*.csv        DATA WAREHOUSE (esquema en estrella)
   │  Paso 5
   ▼
Cuadro de mando (Power BI / Looker Studio / …)
```

**Multi‑año**: los pasos 1–3 se ejecutan por cada carpeta de `Originales/*`; el paso 4
hace `UNION` incremental usando `anyo` como parte de la clave de negocio.

---

## 7. Modelo dimensional (esquema en estrella)

### 7.1 Hecho principal — `hecho_calificacion`

**Grano**: una calificación de un alumno en un módulo, evaluación y tipo de nota.

| Campo | Tipo | Origen / cálculo |
|---|---|---|
| `alumno_sk` → `dim_alumno` | FK | `Calificaciones.alumno` |
| `modulo_sk` → `dim_modulo` | FK | `(curso, contenido)` |
| `curso_sk` → `dim_curso` | FK | `Calificaciones.curso` |
| `grupo_sk` → `dim_grupo` | FK | vía `Alumnos` (matrícula principal) |
| `curso_academico_sk` → `dim_curso_academico` | FK | `anyo` |
| `evaluacion_cod` → `dim_evaluacion` | FK | `Calificaciones.evaluacion` |
| `tipo_nota_cod` → `dim_tipo_nota` | FK | `Calificaciones.tipo_nota` |
| `nota_numerica` | decimal | valor crudo |
| `nota` | decimal / NULL | NULL si `presentado_flag = 0` |
| `presentado_flag` | 0/1 | derivado (D4) |
| `aprobado_flag` | 0/1 | `nota >= 5` |
| `n_calificaciones` | int = 1 | contador |

### 7.2 Hecho secundario — `hecho_matricula`

**Grano**: alumno × grupo × curso académico. Evita inflar los conteos de matrícula por
el fan‑out de las notas.

Métricas: `matriculado_flag`, `baja_flag` (`estado_matricula = 'B'`), `repite_flag`,
`matricula_parcial_flag`, `matricula_condic_flag`, `dias_hasta_baja`.

### 7.3 Dimensiones

| Dimensión | Clave natural | Atributos principales / derivados |
|---|---|---|
| `dim_alumno` | `NIA` | `sexo`, `fecha_nac`, **`edad`**, **`tramo_edad`** (<20 / 20‑24 / 25‑29 / 30+), `nacionalidad` (desc.), `pais_nac`, **`es_extranjero`**, `provincia`, `municipio`, `cod_postal`. SCD1 (SCD2 opcional para histórico de domicilio) |
| `dim_modulo` | `(curso, codigo)` | `codigo`, `nombre_cas`, `nombre_val`, `ensenanza`, **`tipo_modulo`** (tutoría / inglés / ordinario), **+ jerarquía académica heredada del `curso`** (familia, grado, ciclo, 1º/2º) |
| `dim_curso` | `codigo` (L3) | `curso_nivel` (1/2), `curso_nombre`, `ciclo_cod`, `ciclo_nombre_cas`/`_val`, `grado_cod` (GM/GS/CE), `grado_nombre`, `familia_cod`, `familia_nombre`, `ensenanza` |
| `dim_grupo` | `codigo` | `nombre`, `turno` (D/S), `modalidad`, `linea`, `aula`, `capacidad`, **`ocupacion`** = nº alumnos / `capacidad` |
| `dim_evaluacion` | `cod` | `descripcion`, **`tipo`** (parcial / final ordinaria / extraordinaria / falta‑FCT) — *rellenar manualmente* |
| `dim_tipo_nota` | `cod` | `descripcion` — *rellenar manualmente* |
| `dim_nacionalidad` / `dim_pais` / `dim_territorio` | `cod` | descripción — *catálogos oficiales* |
| `dim_curso_academico` | `anyo` | etiqueta ("2021‑22"), `fecha_exportacion` |

### 7.4 Jerarquía de navegación del cuadro de mando

```
Familia profesional  →  Grado (GM/GS/CE)  →  Ciclo formativo  →  Curso (1º / 2º)  →  Grupo
```

`dim_curso` y `dim_modulo` la llevan desnormalizada, de modo que el cuadro de mando no
necesita joins recursivos.

### 7.5 Diagrama del modelo

```
                 dim_curso_academico
                          │
   dim_alumno ── hecho_calificacion ── dim_modulo
        │        │   │   │   │   │
        │        │   │   │   │   └── dim_tipo_nota
        │        │   │   │   └────── dim_evaluacion
        │        │   │   └────────── dim_grupo
        │        │   └────────────── dim_curso  (familia→grado→ciclo→1º/2º)
        │        └────────────────── dim_curso_academico
        │
   hecho_matricula ── dim_grupo / dim_curso / dim_curso_academico
```

---

## 8. Lógica clave de transformación

### 8.1 Resolución de la jerarquía de Cursos (Paso 4)

```python
def resolver_jerarquia(cod, by_cod):
    """Sube por 'padre' recogiendo los ancestros L3 → L0."""
    cadena, actual = [], cod
    while actual and actual in by_cod and len(cadena) < 5:
        cadena.append(by_cod[actual])
        actual = by_cod[actual]["padre"].strip()
    # cadena[0]=L3 curso · [1]=L2 ciclo · [2]=L1 grado · [3]=L0 familia
    return cadena

def fila_dim_curso(cod, by_cod):
    c = resolver_jerarquia(cod, by_cod)
    L3 = c[0] if len(c) > 0 else {}
    L2 = c[1] if len(c) > 1 else {}
    L1 = c[2] if len(c) > 2 else {}
    L0 = c[3] if len(c) > 3 else {}
    abrev = L3.get("abreviatura", "").strip()
    return {
        "curso_cod":        cod,
        "curso_nivel":      int(abrev[0]) if abrev[:1].isdigit() else None,
        "curso_nombre":     L3.get("nombre_cas"),
        "ciclo_cod":        L2.get("abreviatura"),
        "ciclo_nombre_cas": L2.get("nombre_cas"),
        "ciclo_nombre_val": L2.get("nombre_val"),
        "grado_cod":        L1.get("abreviatura"),
        "grado_nombre":     L1.get("nombre_cas"),
        "familia_cod":      L0.get("abreviatura"),
        "familia_nombre":   L0.get("nombre_cas"),
        "ensenanza":        L3.get("ensenanza"),
    }
```

### 8.2 Deduplicación y matrícula principal (Paso 3)

- `Calificaciones`: `DISTINCT` sobre todas las columnas.
- `Alumnos`: agrupar por `NIA`; si hay > 1 fila, marcar `es_matricula_principal = 1`
  en la de `estado_matricula = 'M'` (si varias o ninguna, la de `fecha_matricula`
  más reciente). El resto de matrículas van a `hecho_matricula` pero no a `dim_alumno`.

### 8.3 Presentado / nota (Paso 3)

```python
presentado_flag = 0 if (nota_numerica in ("", None)) else 1
# refinamiento con el catálogo de tipo_nota una vez identificados
# los códigos de "no presentado":
if tipo_nota in TIPOS_NO_PRESENTADO:
    presentado_flag = 0
nota = None if presentado_flag == 0 else float(nota_numerica)
aprobado_flag = 1 if (nota is not None and nota >= 5) else 0
```

---

## 9. Análisis académico habilitado

- **Tasa de aprobados / suspensos** por módulo, ciclo, grado, familia, grupo,
  evaluación, turno, sexo, tramo de edad, nacionalidad.
- **Evolución de notas** 1ª → 2ª → final por alumno / grupo / módulo.
- **Módulos "cuello de botella"**: mayor % de suspensos o de no presentados.
- **Tasa de abandono**: bajas / matrículas y tiempo medio hasta la baja.
- **Rendimiento diurno (D) vs semipresencial (S)**.
- **Ocupación de grupos** frente a capacidad.
- **Comparativa entre familias y grados** (GM vs GS vs CE).
- **Comparativa entre cursos académicos** (2021‑22 … 2025‑26) al cargar todos los años.

---

## 10. Artefactos a construir

| Paso | Script | Entrada | Salida |
|---|---|---|---|
| 3 | `transformar.py` | `Originales/<curso>/Paso1/*.csv` | `<curso>/Staging/*.csv` |
| 4 | `cargar_dw.py` | `<curso>/Staging/*.csv` + catálogos | `DW/dim_*.csv`, `DW/hecho_*.csv` |
| — | Plantillas de catálogo | — | `DW/catalogos/dim_evaluacion.csv`, `dim_tipo_nota.csv`, `dim_nacionalidad.csv` (a completar) |

### Pendientes de negocio (requieren tu conocimiento)

1. Descripción de los códigos de `evaluacion` (¿qué son `FO`, `PO`, `F1`‑`F9`, `A7`, `A8`, `P1`, `P2`, `11`, `12`?).
2. Descripción de los códigos de `tipo_nota` y cuáles significan "no presentado".
3. Confirmar la regla de "matrícula principal" para los 7 NIA duplicados.
4. Catálogos oficiales de `nacionalidad`, `pais_nac`, `provincia`, `municipio`.
