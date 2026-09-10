# Análisis de datos y diseño del Data Warehouse académico

> Curso analizado: **2021‑22** · Ficheros: `data/03_csv/2021-22/*.csv`
> Fecha del análisis: 2026‑09‑03 · Actualizado: 2026‑09‑08 — (a) nuevas reglas de trabajo y
> lista blanca de campos de la transformación (`CLAUDE.md` / `README.md`); (b) revisión
> multi‑año tras regenerar los CSV; (c) alta de las calificaciones de 2023‑24;
> (d) **`grupos.xml` eliminado de `data/01_raw/` y retirado de `CLAUDE.md` / `README.md`**:
> la tabla `Grupos` sale del proyecto por completo (ver §3.5 y §7.6);
> (e) **capítulo de transformación ampliado** — diccionario campo a campo
> origen → destino (§5.3), ejemplos aplicados (§5.4) e impacto acumulado en volumen (§5.5);
> (f) **nueva capa de anonimización real sobre los CSV (Paso 3, `scripts/03_anonimizar_csv.py`)**
> entre la conversión a CSV y la transformación → renumeración: transformación = **Paso 4**
> (`data/05_staging/`), carga del DW = **Paso 5** (`data/06_dw/`), cuadro de mando = **Paso 6**.
> El criterio y el diccionario campo a campo de la anonimización están en §5.6;
> (g) **decisión de negocio (2026‑09‑10): `cod_postal`, `nacionalidad`, `pais_nac` y
> `municipio_nac` se dejan tal cual** en el Paso 3 — sin generalizar ni aplicar
> k‑anonimato — porque el cuadro de mando los necesita con su granularidad completa; solo
> se generalizan las fechas (`fecha_nac`→`anyo_nac`, `fecha_matricula`→`aaaa-mm`).
>
> **Alcance del DW**: cursos **2021‑22 … 2024‑25** (4 años completos). **2025‑26 se excluye**
> mientras su exportación esté incompleta (calificaciones vacías); se incorporará sin cambios
> de esquema cuando llegue el export definitivo.
>
> **Tablas de origen: 4** — `Alumnos`, `Calificaciones`, `Contenidos`, `Cursos`. `Grupos` ya
> no se exporta: su único dato imprescindible (`turno`) está duplicado en `Alumnos`.

---

## 1. Resumen ejecutivo

Los CSV de `data/03_csv/<curso>/` provienen de la exportación de ITACA (ofuscada en el
Paso 1 para que el alumno no se reconozca y convertida a CSV en el Paso 2). Contienen los
datos necesarios para construir un Data Warehouse dimensional orientado al análisis académico.

Hay **dos pasos de transformación** encadenados:

- **Paso 3 — anonimización real** (`scripts/03_anonimizar_csv.py`, `data/03_csv/` →
  `data/04_anon/`): rompe de verdad el vínculo con la persona (seudónimo irreversible del
  identificador, generalización de las fechas). No cambia el grano ni el significado
  analítico. Criterio y diccionario campo a campo en §5.6.
- **Paso 4 — reglas de negocio y calidad** (`scripts/04_transformar.py`, `data/04_anon/` →
  `data/05_staging/`): es el único paso que **cambia el significado** de los datos. Aplica
  las reglas de `CLAUDE.md`, corrige los problemas de calidad del origen y recorta cada CSV
  a la lista blanca del `README.md`. Detalle campo a campo en §5.3–§5.5 y §8. Resumen de
  las seis operaciones:

1. **Filtrar filas de baja** — se eliminan los alumnos con `estado_matricula = 'B'` **y en
   cascada todas sus calificaciones** (regla `CLAUDE.md`). El DW solo contiene matrícula viva.
2. **Filtrar evaluaciones no válidas** — solo se conservan `01`, `02`, `FI` y `EX`; el resto
   de códigos (`FO`, `PO`, `F1`‑`F9`, `A7`, `A8`, `P1`, `P2`, `11`, `12`, …) se descartan.
3. **Interpretar `nota_numerica = 0` como "no presentado"** (regla `CLAUDE.md`): se deriva
   `presentado_flag = 0` y `nota = NULL`, conservando `nota_numerica` cruda.
4. **Deduplicar** — `DISTINCT` sobre las calificaciones (el cruce alumno↔grupo de ITACA
   genera filas idénticas) y una fila por `NIA` en alumnos.
5. **Proyectar a la lista blanca de columnas** — se eliminan todos los campos que no
   aparecen en `README.md` (`tipo_nota`, `bloque_contenido`, `ensenanza`, `nombre_val`,
   `linea`, geografía de residencia, teléfonos, fechas de matrícula, …).
6. **Aplanar la jerarquía de `Cursos`** (familia → grado → ciclo → 1º/2º) sobre las
   dimensiones de curso y de módulo (Paso 5).

Cifras del curso 2021‑22 tras el Paso 4 (`scripts/04_transformar.py`, ejecutado): **1.198**
matrículas vivas (todas con `NIA` único), **17.448** calificaciones válidas y deduplicadas,
**265** módulos, **70** cursos jerárquicos. La integridad referencial de `data/05_staging/`
es perfecta: 0 huérfanos en las 4 relaciones (alumno, curso, módulo) en los 4 años en alcance.

Estado de los datos (2026‑09‑10): **4 cursos en alcance** (2021‑22 … 2024‑25), los cuatro con
calificaciones completas tras darse de alta las de 2023‑24, **transformados y verificados**
(§2, §5.5). 2025‑26 queda fuera hasta que su exportación de notas deje de estar vacía. Todos
los años traen el árbol de `Cursos`, así que la jerarquía se resuelve siempre.

---

## 2. Inventario de ficheros

| Fichero | Filas (2021‑22) | Grano (1 fila = …) | Clave natural (tras Paso 4) |
|---|---:|---|---|
| `Alumnos.csv` | 1.341 (→ 1.198 tras quitar `B`) | matrícula de un alumno en un grupo | `NIA` |
| `Calificaciones.csv` | 18.906 (→ 17.448 tras R1+R2+`DISTINCT`) | nota de un alumno en un módulo / evaluación | `alumno` + `curso` + `contenido` + `evaluacion` |
| `Contenidos.csv` (Módulos) | 265 | módulo dentro de un curso (1º/2º de un ciclo) | `curso` + `codigo` |
| `Cursos.csv` | 70 | nodo del árbol académico (familia/grado/ciclo/curso) | `codigo` |
| ~~`Grupos.csv`~~ | — | **fuera del proyecto** — `grupos.xml` ya no se exporta (ver §3.5) | — |

Todos los CSV incluyen `anyo` (= `curso` del `<centro>`) y `fecha_exportacion`
(= `fechaExportacion` del `<centro>`), añadidos en el Paso 2.

> **`grupos.xml` se ha eliminado de `data/01_raw/`** y ya no figura en `CLAUDE.md` /
> `README.md`. Los `Grupos.csv` / `grupos.xml` que aún quedan en `data/02_anonimizado/` y
> `data/03_csv/` son residuos de ejecuciones anteriores y desaparecen al regenerar esas
> capas. Conviene además retirar la entrada `grupos.xml` de `FICHEROS` /
> `CAMPOS_GRUPO` en `scripts/01_anonimizar_xml.py` y de `CONVERSIONES` en
> `scripts/02_xml_a_csv.py` (hoy solo generan un aviso de "no existe"). El código de grupo
> se conserva vía `Alumnos.grupo` como dimensión degenerada; `turno` se toma de
> `Alumnos.turno`.

**Disponibilidad multi‑año** (estado tras regenerar los CSV, 2026‑09‑07):

| Curso | `anyo` interno | Alumnos | Calificaciones | Contenidos | Cursos | En alcance |
|---|:-:|:-:|:-:|:-:|:-:|:-:|
| 2021‑22 | `2021` | 1.341 | 18.906 | 265 | 70 | ✅ |
| 2022‑23 | `2022` | 1.411 | 20.324 | 278 | 71 | ✅ |
| 2023‑24 | `2023` | 1.445 | 19.130 | 260 | 68 | ✅ |
| 2024‑25 | `2024` | 1.465 | 22.510 | 372 | 94 | ✅ |
| 2025‑26 | `2025` | 1.526 | ⚠️ export vacío (`<calificaciones/>`) | 513 | 110 | ❌ diferido |

El `anyo` interno es el **año de inicio** del curso (`2021` ↔ "2021‑22"); `dim_curso_academico`
debe derivar la etiqueta como `f"{anyo}-{(anyo+1) % 100:02d}"`.

**Notas para el Paso 4/5 (`UNION` multi‑año):**

- **2023‑24** ya trae calificaciones (export del **13/01/2026**, ~15 meses posterior al del
  resto de tablas de ese año, del 19/10/2023). Ese desfase provoca **188 calificaciones de
  9 alumnos que no existen en `Alumnos.csv`** (matrículas posteriores al snapshot de
  alumnos) → ver D11. El origen sigue trayendo además `faltas.xml` (16.262 registros de
  asistencia) → posible `hecho_falta` como extensión futura.
- **2025‑26**: fuera de alcance mientras las calificaciones estén vacías. Cuando llegue el
  export completo entra sin tocar el esquema. Sus `Contenidos`/`Cursos` ya están.
- **Ficheros residuales a ignorar** en `data/03_csv/2023-24/`: `Horas.csv` y `Modulos.csv`
  (de un análisis manual previo; ningún otro año los tiene). El Paso 4 solo lee los **4 CSV
  canónicos** (`Alumnos`, `Calificaciones`, `Contenidos`, `Cursos`); `Grupos.csv` también
  se ignora.

**Volúmenes reales tras el Paso 4** (`scripts/04_transformar.py`, R1+R2+D1+R3+D2+R4, medidos
sobre `data/05_staging/`):

| Curso | Alumnos vivos (post D1) | Calificaciones válidas y dedup. | No presentados |
|---|---:|---:|---:|
| 2021‑22 | 1.198 | 17.448 | 3.196 |
| 2022‑23 | 1.257 | 18.855 | 3.555 |
| 2023‑24 | 1.384 | 18.136 (− 188 huérfanas D11) | 3.681 |
| 2024‑25 | 1.290 | 18.972 | 4.013 |

> Estas cifras corrigen una estimación anterior de este documento (17.958 / 19.180 / 19.367
> calificaciones), que solo restaba R2 y D2 sobre el crudo y **omitía el efecto de R1**
> (cascada de bajas) sobre `Calificaciones` — real y obligatorio por la regla `CLAUDE.md`
> ("eliminar los alumnos de baja **de todas las tablas**"). El único año que ya coincidía
> exactamente era 2023‑24, donde D11 dominaba la diferencia. Los `Alumnos` vivos también
> bajan un poco frente a la estimación anterior porque esa tabla no aplicaba aún D1 (un
> alumno por `NIA`): 2022‑23 y 2024‑25 tenían 2 y 4 `NIA` duplicados residuales (§5.2 D1).

---

## 3. Análisis por tabla

### 3.1 Alumnos

- 37 columnas en el CSV crudo. Campos con valor **constante**: `ensenanza = 5` (FP),
  `modalidad = COM`.
- **Filtro de bajas (regla `CLAUDE.md`)**: `estado_matricula` — `M` (matriculado) 1.198 ·
  `B` (baja) 143. Las 143 filas `B` **se eliminan en el Paso 4** junto con sus
  calificaciones. `estado_matricula` **no** forma parte de la lista blanca: se usa para
  filtrar y luego se descarta.
- **`NIA` duplicado**: 1.334 distintos en 1.341 filas → 7 `NIA` repetidos. En 2021‑22 los
  7 son parejas `M` + `B`, así que **al quitar las bajas el `NIA` queda único** (1.198
  filas, 1.198 `NIA`). En otros años quedan pocos duplicados `M` + `M` residuales
  (2022‑23: 2, 2023‑24: 0, 2024‑25: 4) → ver D1.
- **Lista blanca (tras Pasos 3 + 4)** — solo se conservan:

  `anyo`, `fecha_exportacion`, `NIA` (seudónimo), `anyo_nac`, `sexo`, `nacionalidad`,
  `pais_nac`, `municipio_nac`, `cod_postal`, `curso`, `grupo`, `turno`.

  El **Paso 3** (§5.6) elimina ya nombre y apellidos, documento, teléfonos, emails, sip,
  expediente, `fecha_ingreso_centro` y la geografía de **residencia**
  (`provincia`, `municipio`, `localidad`); y generaliza `fecha_nac` → `anyo_nac`.
  `cod_postal`, `nacionalidad`, `pais_nac` y `municipio_nac` se dejan **tal cual** (decisión
  de negocio, §5.6). El **Paso 4** (R4) elimina además `ensenanza`, `linea`, `modalidad`,
  `repite`, `estado_matricula`, `tipo_matricula`, `matricula_parcial`, `matricula_condic`,
  `fecha_matricula`.
- Distribuciones útiles que quedan:

  | Campo | Valores (2021‑22, tras quitar `B`) |
  |---|---|
  | `sexo` | `M` · `H` |
  | `turno` | `D` (diurno) · `S` (semipresencial) |
  | `grupo` | 46 distintos, siempre informado |
  | `curso` | nodos hoja (L3) del árbol de Cursos |
  | `nacionalidad`, `pais_nac`, `municipio_nac` | códigos sin descripción → catálogos |

- `fecha_nac` siempre informada; el Paso 3 la reduce a `anyo_nac` → permite derivar **edad**
  (±1 año) y **tramo de edad**.
- `cod_postal` se conserva completo (permite geolocalización precisa del alumno);
  `municipio_nac` es el municipio **de nacimiento**, no el de residencia. Ninguno de los
  dos se generaliza en el Paso 3 (decisión de negocio, §5.6).

### 3.2 Calificaciones

- **Grano de origen**: alumno × curso × contenido × evaluación × tipo_nota.
  **Grano tras el Paso 4**: alumno × curso × contenido × evaluación (se elimina `tipo_nota`).
- **Filtro de evaluaciones (regla `CLAUDE.md`)** — solo son válidas `01`, `02`, `FI`, `EX`:

  | Código | Nº (2021‑22) | Interpretación | Se conserva |
  |---|---:|---|:-:|
  | `01` | 6.790 | 1ª evaluación ordinaria | ✅ |
  | `FI` | 6.173 | Evaluación final ordinaria | ✅ |
  | `02` | 4.044 | 2ª evaluación ordinaria | ✅ |
  | `EX` | 1.188 | Evaluación extraordinaria | ✅ |
  | `FO`, `PO`, `F1`‑`F9`, `FC`, `FE`, `A7`, `A8`, `P1`, `P2`, `11`, `12`, … | ~711 en total | faltas / FCT / casos especiales | ❌ se descartan |

  El filtro de evaluaciones elimina entre el **3,8 % y el 4,3 %** de las filas según el año
  (711 en 2021‑22, 751 en 2022‑23, 806 en 2023‑24, 962 en 2024‑25). El reparto de códigos
  no válidos es estable entre años (`FO` y `PO` a la cabeza).
- **`tipo_nota` se elimina** (no está en la lista blanca). Comprobado en los 4 años: al
  proyectar a la clave `(alumno, curso, contenido, evaluacion)` y quitar `tipo_nota`,
  **todas las filas que colapsan tienen la misma `nota_numerica`** (0 conflictos) → un
  `DISTINCT` sobre las columnas de la lista blanca lo resuelve sin pérdida de información.
- **`bloque_contenido` vacío en el 100 %** de las filas → se elimina (además ya no está en
  la lista blanca).
- `nota_numerica` — rango 0–10. Distribución 2021‑22:

  | Nota | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
  |---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
  | Nº | 4.038 | 246 | 248 | 429 | 1.210 | 972 | 2.160 | 3.101 | 3.217 | 2.426 | 858 |

  **Regla firme (`CLAUDE.md`)**: `nota_numerica = 0` ⇒ **no presentado**. En las
  evaluaciones válidas de alumnos vivos (2021‑22) hay 3.581 ceros + 1 vacío antes de D2, que
  pasan a `presentado_flag = 0` y `nota = NULL`; tras D2 (`DISTINCT`) quedan **3.196** filas
  no presentadas en `data/05_staging/` (§5.5). Se acepta el efecto colateral de que un 0
  "real" (suspenso con nota 0) es indistinguible y se cuenta como no presentado;
  `nota_numerica` cruda se conserva en
  el hecho por si dirección quiere revisarlo.
- La lista blanca de Calificaciones es: `anyo`, `fecha_exportacion`, `evaluacion`,
  `alumno`, `curso`, `contenido`, `nota_numerica`.

### 3.3 Contenidos (Módulos)

- **`codigo` NO es único**: 184 códigos distintos en 265 filas. La clave real es
  **`(curso, codigo)`** — un mismo módulo (p. ej. `0156` "Inglés") se imparte en varios
  ciclos.
- El campo `curso` apunta **siempre a un nodo hoja (L3)** del árbol de Cursos → cada módulo
  se clasifica por familia / grado / ciclo / 1º‑2º.
- **Lista blanca (Paso 4)**: `anyo`, `fecha_exportacion`, `codigo`, `nombre_cas`, `curso`.
  Se eliminan `nombre_val` y `ensenanza`.
- `tipo_modulo` sigue siendo derivable del `codigo`: tutoría (`TU*`), inglés técnico /
  horario en inglés (`CV*`), módulos ordinarios (código numérico).

### 3.4 Cursos — árbol jerárquico

`Cursos.csv` es un **árbol de 4 niveles** encadenado por `codigo ← padre`:

| Nivel | Concepto | `nombre_cas` | `abreviatura` | Nº nodos |
|---|---|---|---|---:|
| **L0** | Familia profesional | nombre de la familia | código de familia (`190`, `020`…) | 7 |
| **L1** | Grado / enseñanza | GRADO MEDIO / SUPERIOR / CURSO ESPECIALIZACIÓN | `GM` / `GS` / `CE` | 12 |
| **L2** | Ciclo formativo | nombre del ciclo | código del ciclo (`845104`…) | 18 |
| **L3** | Curso (1º / 2º) | `Primero` / `Segundo` / `Primero CE` | `1CFS` `2CFS` `1CFM` `2CFM` `1CES` | 33 |

- `Alumnos`, `Calificaciones` y `Contenidos` referencian **siempre nodos L3**.
- **Lista blanca (Paso 4)**: `anyo`, `fecha_exportacion`, `codigo`, `nombre_cas`,
  `abreviatura`, `padre`. Se eliminan `nombre_val` y `ensenanza`.
- **Datos que aporta la jerarquía** (subiendo por `padre` desde el `curso`):
  - **1º o 2º** (`curso_nivel` = 1ª cifra de la abreviatura L3, coincide con la 1ª cifra del `grupo`),
  - **ciclo formativo** (L2),
  - **grado** GM/GS/CE (L1),
  - **familia profesional** (L0),
  - y por extensión, la clasificación de cada **módulo/contenido**.
- **Casos borde**:
  - La familia `039` (HOSTELERÍA Y TURISMO) aparece en **dos** nodos raíz distintos
    (`2712307648` y `2712338777`). Exponer `familia_codigo` como atributo y agrupar por él.
  - Rama `2712338777 → 2712338886` (`X27`, "OPERACIONES BÁSICAS DE PISOS"): solo 2 niveles
    (programa formativo básico, sin L2/L3), sin referencias. Resolver con `grado = 'PFB'` y
    `ciclo` / `curso_nivel` = NULL sin que falle el proceso.
  - **Crecimiento de la oferta**: los nodos de `Cursos` pasan de 70 (2021‑22) a 94
    (2024‑25) y los `Contenidos` de 265 a 372, manteniéndose siempre 7 familias raíz.
    `dim_curso` y `dim_modulo` deben cargarse **por año** (`UNION` en el Paso 5), no
    reutilizar un único árbol.

### 3.5 Grupos — **tabla fuera del proyecto**

`grupos.xml` se ha eliminado de `data/01_raw/` y de `CLAUDE.md` / `README.md`: la tabla no
se extrae, ni se transforma, ni se carga. Motivos y consecuencias:

- **`turno` (D/S)** —único campo de `Grupos` necesario para el cuadro de mando (filtro
  "Turno")— está **también en `Alumnos.turno`**. Comprobado en los 4 años: `Alumnos.turno`
  está **siempre informado** (0 vacíos) y **coincide con `Grupos.turno`** (0 discrepancias
  en 3 años; 1 sola fila discrepante de 1.259 en 2022‑23). → El filtro Turno se sirve desde
  la matrícula.
- **`codigo` de grupo** — está en `Alumnos.grupo` (siempre informado, 0 huérfanos). Se
  conserva como **dimensión degenerada** (`grupo_cod`) en los hechos: permite agrupar por
  grupo, aunque sin nombre "bonito" (se ve `1CFSF`, no "1º Desarrollo de Aplicaciones Web").
- **`capacidad`** — solo existía en `Grupos`. Se **pierde** la métrica de **ocupación**
  (alumnos / capacidad). No es un requisito del cuadro de mando (§11).
- **`aula`** — se pierde (uso marginal, ~40 % vacía). Sin análisis por espacio físico.
- **`modalidad`** — constante `COM`, sin valor analítico.
- **1º/2º** — ya viene de `dim_curso.curso_nivel` (abreviatura L3 del árbol de Cursos); el
  código de grupo solo servía de comprobación cruzada.

**Resumen**: quitar `Grupos` no afecta a ningún requisito del cuadro de mando; solo se
renuncia a ocupación/capacidad, al nombre descriptivo del grupo y al aula.

---

## 4. Integridad referencial (comprobaciones sobre el origen 2021‑22)

| Relación | Resultado |
|---|---|
| `Calificaciones.alumno` → `Alumnos.NIA` | ✅ 0 huérfanos |
| `Calificaciones.(curso, contenido)` → `Contenidos.(curso, codigo)` | ✅ 0 huérfanos |
| `Calificaciones.curso` → `Cursos.codigo` | ✅ 0 huérfanos |
| `Alumnos.curso` → `Cursos.codigo` | ✅ 0 huérfanos |
| `Contenidos.curso` → `Cursos.codigo` | ✅ 0 huérfanos |
| Alumnos sin ninguna calificación | 73 (en su mayoría bajas; casi todos desaparecen al filtrar `B`) |

Revalidado sobre los 4 años en alcance:

| Relación | 2021‑22 | 2022‑23 | 2023‑24 | 2024‑25 |
|---|:-:|:-:|:-:|:-:|
| `Calificaciones.alumno` → `Alumnos.NIA` | 0 | 0 | **188 filas / 9 alumnos** (D11) | 0 |
| `Calificaciones.(curso, contenido)` → `Contenidos` | 0 | 0 | 0 | 0 |
| `Calificaciones.curso` → `Cursos.codigo` | 0 | 0 | 0 | 0 |
| Notas en conflicto tras quitar `tipo_nota` | 0 | 0 | 0 | 0 |

> Tras el Paso 4 hay que **revalidar** que al borrar las bajas no queden calificaciones
> huérfanas y que ningún `Alumnos.curso` quede sin nodo en el árbol del año.

---

## 5. Transformación de los datos (Pasos 3 y 4)

§5.1–§5.5 describen el **Paso 4** (reglas de negocio `CLAUDE.md` + calidad + lista blanca,
`data/04_anon/` → `data/05_staging/`). §5.6 describe el **Paso 3** (anonimización real,
`data/03_csv/` → `data/04_anon/`), que se ejecuta **antes** que todo lo anterior.

### 5.1 Reglas de negocio del Paso 4 (obligatorias, de `CLAUDE.md`)

| # | Regla | Detalle | Tratamiento |
|---|---|---|---|
| R1 | Eliminar bajas | `estado_matricula = 'B'` en Alumnos | Borrar esas filas **y en cascada sus calificaciones** (join por `alumno = NIA`). Aplicar **antes** de deduplicar. |
| R2 | Evaluaciones válidas | solo `01`, `02`, `FI`, `EX` | `WHERE evaluacion IN ('01','02','FI','EX')` sobre Calificaciones. El resto se descarta. |
| R3 | `nota_numerica = 0` = no presentado | ceros en evaluaciones válidas | `presentado_flag = 0`, `nota = NULL`; conservar `nota_numerica` cruda. |
| R4 | Lista blanca de columnas | campos de `README.md` §"Transformación de los CSV" | Proyectar cada CSV a sus columnas permitidas; eliminar el resto. Último sub‑paso del Paso 4. |

### 5.2 Problemas de calidad detectados

| # | Problema | Detalle | Tratamiento |
|---|---|---|---|
| D1 | `NIA` duplicado residual | tras R1 quedan 0 (2021‑22), 2 (2022‑23), 0 (2023‑24), 4 (2024‑25) parejas `M` + `M` (cambio de grupo/turno dentro del curso) | 1 fila por `NIA` en `dim_alumno`: quedarse con la de `fecha_matricula` más reciente (ya generalizada a `aaaa-mm` en el Paso 3; si empatan, `grupo` con más calificaciones). Documentar la elección. |
| D2 | Filas duplicadas en Calificaciones | el cruce alumno↔grupo de ITACA repite notas idénticas (hasta 4×); al quitar `tipo_nota` colapsan más filas, todas con la misma nota. Afecta a 2021‑22 (‑237), 2022‑23 (‑393), 2024‑25 (‑2.181); 2023‑24 no trae duplicados (export distinto) | `DISTINCT` sobre las columnas de la lista blanca, **después** de R1/R2. |
| D3 | `bloque_contenido` siempre vacío | 100 % de las filas en todos los años | Eliminado por R4 (y de todas formas 100 % nulo). |
| D4 | Nulos como `" "` | ITACA rellena vacíos con espacio | Normalizar `""` → NULL al tipar (el `strip()` ya se hace en el Paso 2). |
| D5 | Códigos sin descripción | `nacionalidad`, `pais_nac`, `municipio_nac` (el Paso 3 los deja tal cual, sin generalizar) | Tablas de catálogo rellenadas manualmente una vez. `evaluacion` ya no necesita catálogo (dominio fijo de 4). |
| D6 | Columnas constantes | `ensenanza = 5` (Alumnos/Calificaciones/Contenidos/Cursos), `modalidad = COM` (Alumnos) | Todas se eliminan por R4 (no están en la lista blanca). |
| D7 | Familia `039` en 2 nodos raíz | jerarquía de Cursos | Clave por `familia_codigo`, no por `codigo` del nodo. |
| D8 | Rama sin L2/L3 (`X27`) | programa formativo básico | Resolver niveles faltantes a NULL / `PFB`. |
| D9 | 2025‑26 sin calificaciones | export de notas vacío (curso en marcha) | **Fuera de alcance** hasta que llegue el export completo; entra sin cambios de esquema. |
| D10 | Ficheros residuales en `data/03_csv/2023-24/` | `Horas.csv` y `Modulos.csv` (análisis manual previo; ningún otro año los tiene) | El Paso 4 solo lee los 4 CSV canónicos; conviene borrarlos (junto con los `Grupos.csv` residuales de todos los años). |
| D11 | Huérfanos de calificación en 2023‑24 | `Calificaciones` exportado 15 meses después que `Alumnos` → 188 filas de 9 alumnos sin `NIA` en `Alumnos.csv` | `INNER JOIN` con la matrícula viva (la cascada de R1 ya descarta lo que no casa). Ideal: reexportar `Alumnos` 2023‑24 a fecha coherente. |
| D12 | `Grupos` retirada | el DW ya no tiene `dim_grupo` | `turno` ← `Alumnos.turno`; `grupo_cod` como dimensión degenerada en los hechos; sin ocupación/capacidad ni aula (ver §3.5, §7.6). |

> **Ya no aplican**: el problema de `tipo_nota` sin catálogo (columna eliminada), la
> ambigüedad del "0" (ahora es regla R3), y la resolución de matrículas dobles `M` + `B`
> (R1 las elimina).

### 5.3 Diccionario de transformación por tabla (Paso 4)

Para cada CSV de `data/04_anon/<curso>/` (ya anonimizado en el Paso 3: sin datos personales,
`NIA`/`alumno` seudonimizados, `fecha_nac`→`anyo_nac`) se indica qué le pasa a **cada campo**
al escribir `data/05_staging/<curso>/`. Leyenda de la columna *Acción*:

- **CLAVE** — se conserva; forma parte de la clave natural del *staging*.
- **CONSERVA** — se conserva tal cual (solo se normaliza `" "` / `""` → NULL, D4).
- **CONSERVA (cruda)** — se conserva sin tocar aunque tenga un flag derivado al lado.
- **FILTRA→ELIMINA** — se usa para filtrar filas (R1/R2) y después **no** se escribe.
- **DERIVA** — no viaja al *staging*, pero de él salen columnas nuevas.
- **ELIMINA (R4)** — se descarta por no estar en la lista blanca del `README.md`.
- **NUEVA** — columna que no existe en el origen y se añade en este paso.

#### Alumnos — 21 columnas de entrada (`data/04_anon/`) → 12 de lista blanca + 0 derivadas

(Recuérdese: los datos personales, la geografía de residencia y `fecha_ingreso_centro` ya
**no existen** a la entrada del Paso 4 — los eliminó el Paso 3, ver §5.6.)

| Campo entrada | Acción | Destino / motivo |
|---|---|---|
| `anyo`, `fecha_exportacion` | CONSERVA | añadidos en Paso 2; `anyo` entra en la clave de negocio multi‑año |
| `NIA` | CLAVE | seudónimo del alumno (Paso 3); único tras R1 + D1 |
| `estado_matricula` | FILTRA→ELIMINA | R1: las filas `B` (y sus calificaciones) se borran; el campo **no** se escribe |
| `fecha_matricula` (`aaaa-mm`) | DERIVA→ELIMINA | solo se usa como criterio de desempate en D1; no se escribe |
| `anyo_nac`, `sexo`, `nacionalidad`, `pais_nac`, `municipio_nac`, `cod_postal` | CONSERVA | atributos de `dim_alumno` (`anyo_nac` alimenta `edad` / `tramo_edad` en Paso 5; `nacionalidad`/`pais_nac`/`municipio_nac`/`cod_postal` llegan sin generalizar, §5.6) |
| `curso` | CONSERVA | FK a `dim_curso` (nodo hoja L3); enlaza toda la jerarquía académica |
| `grupo` | CONSERVA | dimensión **degenerada** `grupo_cod` en los hechos |
| `turno` | CONSERVA | `D`/`S`; viaja **degenerado** a los dos hechos (sustituye a `Grupos.turno`) |
| `ensenanza` (=5), `modalidad` (=COM), `linea` | ELIMINA (R4) | columnas constantes, sin valor analítico (D6) |
| `repite`, `tipo_matricula`, `matricula_parcial`, `matricula_condic` | ELIMINA (R4) | fuera de alcance del cuadro de mando |

#### Calificaciones — 10 columnas crudas → 7 de lista blanca + 3 derivadas

| Campo origen | Acción | Destino / motivo |
|---|---|---|
| `anyo`, `fecha_exportacion` | CONSERVA | `anyo` entra en la clave de negocio |
| `alumno` | CLAVE | FK a `dim_alumno` (= seudónimo del `NIA`, ya aplicado en el Paso 3); R1 borra en cascada las de alumnos de baja; D11 descarta las huérfanas de 2023‑24 |
| `curso` | CLAVE | FK a `dim_curso` |
| `contenido` | CLAVE | con `curso` forma la FK a `dim_modulo` (`codigo` no es único, §3.3) |
| `evaluacion` | CLAVE + FILTRA | R2: solo `01`, `02`, `FI`, `EX`; el resto de filas se descarta. El código válido **sí** se escribe |
| `nota_numerica` | CLAVE + CONSERVA (cruda) | rango 0–10; se conserva el valor bruto (incluidos los 0) en el hecho |
| `presentado_flag` | NUEVA (R3) | `0` si `nota_numerica` es NULL o `= 0`; si no `1` |
| `nota` | NUEVA (R3) | `= nota_numerica` salvo que `presentado_flag = 0` → **NULL** |
| `aprobado_flag` | NUEVA (R3) | `1` si `nota >= 5`; si no (incluye no presentado y NULL) `0` |
| `ensenanza` | ELIMINA (R4) | constante `5` (D6) |
| `bloque_contenido` | ELIMINA (R4) | vacío en el 100 % de las filas, todos los años (D3) |
| `tipo_nota` | ELIMINA (R4) | baja el grano de alumno×curso×contenido×evaluación×`tipo_nota` a sin `tipo_nota`; comprobado 0 conflictos de nota al colapsar (§3.2) → lo resuelve el `DISTINCT` de D2 |

#### Contenidos (Módulos) — 7 columnas crudas → 5 de lista blanca

| Campo origen | Acción | Destino / motivo |
|---|---|---|
| `anyo`, `fecha_exportacion` | CONSERVA | `dim_modulo` se carga **por año** (la oferta crece, §3.4) |
| `codigo` | CLAVE | parte de la clave `(curso, codigo)`; no es único por sí solo |
| `curso` | CLAVE | nodo hoja L3 → hereda familia/grado/ciclo/1º‑2º en Paso 5 |
| `nombre_cas` | CONSERVA | descripción del módulo; de `codigo` se deriva `tipo_modulo` en Paso 5 |
| `nombre_val` | ELIMINA (R4) | nombre en valenciano, redundante |
| `ensenanza` | ELIMINA (R4) | constante `5` (D6) |

#### Cursos — 8 columnas crudas → 6 de lista blanca

| Campo origen | Acción | Destino / motivo |
|---|---|---|
| `anyo`, `fecha_exportacion` | CONSERVA | el árbol se resuelve **por año** |
| `codigo` | CLAVE | nodo del árbol |
| `padre` | CONSERVA | enlace `codigo ← padre`; el Paso 5 sube por él para aplanar L3→L0 (§8.7) |
| `nombre_cas` | CONSERVA | nombre del nodo (familia / grado / ciclo / curso según nivel) |
| `abreviatura` | CONSERVA | de la abreviatura L3 (`1CFS`, `2CFM`…) sale `curso_nivel` (1/2); de L1 el `grado_cod` (GM/GS/CE) |
| `nombre_val` | ELIMINA (R4) | nombre en valenciano |
| `ensenanza` | ELIMINA (R4) | constante `5` (D6) |

> `Grupos` no aparece: `grupos.xml` ya no se exporta (§3.5).

### 5.4 Ejemplos aplicados (2021‑22)

**R1 — baja en cascada.** Alumno con `NIA = 11111` y `estado_matricula = 'B'`:

```
Alumnos      : fila NIA=11111 …                         -> ELIMINADA
Calificaciones: 14 filas con alumno=11111 …             -> ELIMINADAS (cascada)
```

**R2 + R3 — evaluación no válida y no presentado.** Mismo alumno y módulo, 4 filas crudas:

| evaluacion | nota_numerica | tipo_nota | Resultado Paso 4 |
|---|---|---|---|
| `01` | `7` | `RA` | fila válida → `presentado_flag=1`, `nota=7`, `aprobado_flag=1` |
| `01` | `7` | `UF` | **duplicado** al quitar `tipo_nota` → colapsa con la anterior (D2) |
| `FI` | `0` | `RA` | válida → `presentado_flag=0`, `nota=NULL`, `aprobado_flag=0` (R3) |
| `FO` | `` | `` | evaluación no válida → **descartada** (R2) |

Salida (2 filas): `(…,01,7,7,1,1)` y `(…,FI,0,,0,0)` — se conserva `nota_numerica=0` crudo,
`nota` va vacía.

**R4 — proyección.** La fila de `Alumnos` entra al Paso 4 con 21 columnas (el Paso 3 ya quitó
las personales) y sale con 12; `estado_matricula`, `repite`, `fecha_matricula`, … no llegan
a `data/05_staging/`.

### 5.5 Impacto acumulado en volumen

Filas de `Calificaciones` que sobreviven a cada operación (orden de §6.2), medidas
ejecutando `scripts/04_transformar.py` sobre los 4 años en alcance:

| Curso | Crudas | tras R1 (cascada bajas + D11) | tras R2 (eval. válidas) | tras D2 (`DISTINCT`) = **Staging** | de las cuales D11 | No presentados |
|---|---:|---:|---:|---:|---:|---:|
| 2021‑22 | 18.906 | 18.396 (−510) | 17.685 (−711) | **17.448** (−237) | 0 | 3.196 |
| 2022‑23 | 20.324 | 19.999 (−325) | 19.248 (−751) | **18.855** (−393) | 0 | 3.555 |
| 2023‑24 | 19.130 | 18.942 (−188) | 18.136 (−806) | **18.136** (−0) | 188 | 3.681 |
| 2024‑25 | 22.510 | 22.091 (−419) | 21.129 (−962) | **18.972** (−2.157) | 0 | 4.013 |

El `DISTINCT` de D2 colapsa, tras quitar `tipo_nota`, filas que ya eran idénticas en la
lista blanca (comprobado: 0 conflictos de nota). En 2023‑24 las 188 bajas de R1 **son**
las huérfanas D11 (`Calificaciones` exportado 15 meses después que `Alumnos`, §2); por eso
D2 no encuentra duplicados adicionales ese año (export distinto al resto). El filtro R2
elimina el **3,7 %–4,3 %** de las filas según el año.

`Alumnos`: 1.341 → **1.198** (R1 quita 143 bajas; D1 no quita ninguna en 2021‑22; en
2022‑23 y 2024‑25 D1 sí colapsa 2 y 4 `NIA` duplicados residuales, §5.2 D1).
`Contenidos` y `Cursos`: sin cambio de volumen (solo `DISTINCT` de seguridad y R4).

### 5.6 Anonimización real de los CSV (Paso 3)

Script: `scripts/03_anonimizar_csv.py` · `data/03_csv/<curso>/` → `data/04_anon/<curso>/`
(mismo grano, sin cambio de significado analítico). Se ejecuta por año (`--curso`) o sobre
todos. Solo procesa los 4 CSV canónicos; `Contenidos` y `Cursos` (sin datos personales) se
copian tal cual.

**Objetivo.** El Paso 1 solo *ofusca* (reversible: `NIA + 2345`, sustitución fija de letras)
para que el alumno no se reconozca en la simulación. El Paso 3 **rompe el vínculo con la
persona**: ninguna fila debe poder atribuirse a alguien concreto ni siquiera cruzando
campos, conservando la utilidad analítica (rendimiento por ciclo, edad, turno, sexo, origen).

**Criterio, campo a campo (tabla `Alumnos`):**

| Técnica | Campos | Qué hace |
|---|---|---|
| **Eliminar** | `nombre`, `apellido1/2`, `tipo_doc`, `documento`, `telefono1‑3`, `email1/2`, `sip`, `expediente`, `provincia`, `municipio`, `localidad`, `fecha_ingreso_centro` | identificadores directos + datos personales que aún arrastra el CSV + geografía de **residencia** (muy identificativa en municipios pequeños) |
| **Seudonimizar** (HMAC‑SHA256, prefijo `AL`) | `NIA` (en `Alumnos`) y `alumno` (en `Calificaciones`) | token irreversible sin la clave, **determinista y estable** entre ficheros y años → se mantiene la integridad referencial (0 huérfanos) y el análisis multi‑año (p. ej. 635 alumnos enlazan 2021‑22 ↔ 2022‑23) |
| **Generalizar** | `fecha_nac` → `anyo_nac` (año); `fecha_matricula` → `aaaa-mm` | elimina la parte única de cada fecha; `anyo_nac` basta para `edad` / `tramo_edad` (§7.3) |
| **Conservar sin tocar** | `cod_postal`, `nacionalidad`, `pais_nac`, `municipio_nac`, `sexo`, `curso`, `grupo`, `turno`, `estado_matricula`, y en `Calificaciones` todo lo demás | **decisión de negocio (2026‑09‑10)**: el cuadro de mando necesita estos cuatro campos con su granularidad completa, no generalizada. El recorte a la lista blanca sigue siendo cosa del Paso 4 (R4) |

> **Nota de riesgo, no bloqueante.** `cod_postal` + `nacionalidad` combinados pueden acotar
> mucho a un alumno con una nacionalidad poco común en su código postal, incluso con el `NIA`
> seudonimizado (reidentificación por quasi‑identificadores). Se acepta porque el cuadro de
> mando es de uso interno para el equipo directivo, no un dataset que vaya a publicarse. Si
> en el futuro `data/04_anon/` sale del centro, retomar la generalización (`cp_distrito`,
> agrupar nacionalidades raras) descartada aquí.

**Gestión de la clave HMAC:**

- Se genera sola en `data/_claves/anon_hmac.key` (todo `data/` está en `.gitignore`) o se
  fija con la variable de entorno `ANON_KEY` / `--clave <fichero>`.
- **Guardar una copia segura** si se quiere reproducir los mismos tokens en ejecuciones
  futuras (altas de nuevos años). **Borrarla** corta de forma definitiva el enlace token ↔
  `NIA` real (útil si el `data/04_anon/` se va a compartir).
- Alternativa equivalente: tabla de correspondencia `NIA → token` aleatoria persistida fuera
  del repo. Se ha elegido HMAC por no necesitar estado y funcionar de forma incremental.

**Efecto en el resto del diseño:** el Paso 4 (§5.1–§5.5) y el modelo (§7) trabajan ya sobre
estos nombres — `anyo_nac`, `NIA`/`alumno` seudónimos; `cod_postal`, `nacionalidad`,
`pais_nac` y `municipio_nac` conservan su nombre y granularidad originales. La derivación de
`edad` en `dim_alumno` pasa a ser `anyo_del_curso − anyo_nac` (aproximada, ±1 año).

---

## 6. Flujo de datos (capas)

```
data/01_raw/<curso>/*.xml             ITACA en bruto
   │  Paso 1 · scripts/01_anonimizar_xml.py   OFUSCACIÓN (que el alumno no se reconozca) +
   │                                          filtrado grueso de campos · reversible
   ▼
data/02_anonimizado/<curso>/*.xml     XML ofuscado
   │  Paso 2 · scripts/02_xml_a_csv.py        extracción a CSV + anyo, fecha_exportacion
   ▼
data/03_csv/<curso>/*.csv             STAGING CRUDO (1:1 con el XML)
   │  Paso 3 · scripts/03_anonimizar_csv.py   ANONIMIZACIÓN REAL: seudónimo irreversible del
   │                                          NIA · generalización de fechas de nacimiento
   ▼
data/04_anon/<curso>/*.csv            STAGING CRUDO ANONIMIZADO (mismo grano)
   │  Paso 4 · scripts/04_transformar.py      ← REGLAS DE NEGOCIO (R1‑R4) + calidad (D1‑D4)
   ▼
data/05_staging/<curso>/*.csv         STAGING LIMPIO (solo lista blanca + flags derivados)
   │  Paso 5 · scripts/05_cargar_dw.py        claves subrogadas · jerarquía de Cursos ·
   │                                          catálogos · UNION multi‑año · hechos
   ▼
data/06_dw/  dim_*.csv  +  hecho_*.csv        DATA WAREHOUSE (esquema en estrella)
   │  Paso 6
   ▼
Cuadro de mando (Power BI / Looker Studio / …)
```

> **Paso 1 vs Paso 3 — dos "anonimizaciones" con objetivos distintos.** El Paso 1 *ofusca*
> (cambio fijo de letras, `NIA + 2345`): es reversible y su fin es que un alumno no reconozca
> sus datos al recibir una simulación realista. El Paso 3 *anonimiza de verdad*: sustituye el
> identificador por un token irreversible sin la clave y generaliza las fechas que casi por
> sí solas identifican a una persona. `cod_postal`, `nacionalidad`, `pais_nac` y
> `municipio_nac` se dejan tal cual por decisión de negocio (§5.6).

### 6.1 Reparto de responsabilidades entre Paso 1, Paso 3 y Paso 4

| Campo | Paso 1 — ofuscación (XML) | Paso 3 — anonimización (CSV) | Paso 4 — transformación (CSV) |
|---|---|---|---|
| Identificador de alumno (`NIA` / `alumno`) | `NIA + 2345` (reversible) | **seudónimo HMAC irreversible** y estable entre ficheros y años | se usa como FK a `dim_alumno` |
| Datos personales (nombre, apellidos, doc, teléfono, email, sip, expediente) | letras cambiadas o valor fijo | **eliminados** | ya no están |
| Geografía de residencia (`provincia`, `municipio`, `localidad`) | salen del Paso 1 | **eliminados** | ya no están |
| `fecha_nac` | sale del Paso 1 | → `anyo_nac` (solo el año) | alimenta `edad` / `tramo_edad` |
| `cod_postal`, `nacionalidad`, `pais_nac`, `municipio_nac` | salen del Paso 1 | **se conservan tal cual** (decisión de negocio, §5.6) | atributo de `dim_alumno` (+ catálogo) |
| `fecha_matricula` | sale del Paso 1 | → `aaaa-mm` | desempate de D1, luego se elimina (R4) |
| `estado_matricula`, `evaluacion` | **se conservan** | se conservan sin tocar | R1/R2 los usan; `evaluacion` queda, `estado_matricula` se descarta |
| `tipo_nota`, `bloque_contenido`, `nombre_val`, `linea`, `ensenanza` | pueden seguir saliendo | se conservan sin tocar | **eliminados por R4** |

> El Paso 3 **no recorta a la lista blanca** (eso es R4, en el Paso 4): solo toca lo que
> hace falta para anonimizar. Columnas como `repite` o `tipo_matricula` siguen presentes en
> `data/04_anon/` y las elimina el Paso 4.

> Optimización opcional: recortar ya en el Paso 1 (`CAMPOS_*` de
> `scripts/01_anonimizar_xml.py`) los campos que ni el Paso 3 ni el Paso 4 usan (`tipo_nota`,
> `bloque_contenido`, `nombre_val`, `linea`, geografía de residencia). Hay que **mantener**
> `estado_matricula` y `evaluacion`. `grupos.xml` ya **no está** en `data/01_raw/`: falta
> solo limpiar el código muerto que lo referencia (`CAMPOS_GRUPO` + entrada de `FICHEROS` en
> el Paso 1; entrada de `CONVERSIONES` en el Paso 2).

### 6.2 Orden de operaciones dentro del Paso 4 (importante)

Por cada carpeta `data/04_anon/<curso>/`:

1. **Cargar y tipar** los 4 CSV canónicos del año (`Alumnos`, `Calificaciones`,
   `Contenidos`, `Cursos`; ignorar `Grupos.csv` y cualquier otro fichero — ver D10/D12).
   Si `Calificaciones.csv` no existe o está vacío (p. ej. exports parciales como 2025‑26),
   continuar solo con matrícula + dimensiones. Normalizar `" "` / `""` → NULL (D4).
2. **R1 — bajas**: calcular el conjunto de `NIA` con `estado_matricula = 'B'`;
   eliminar esas filas de `Alumnos` y todas las filas de `Calificaciones` cuyo
   `alumno` esté en ese conjunto.
3. **R2 — evaluaciones**: filtrar `Calificaciones` a `evaluacion IN ('01','02','FI','EX')`.
4. **D1 — un alumno por `NIA`**: si tras R1 quedan `NIA` repetidos, quedarse con una fila
   (regla de desempate, ver D1) y reasignar sus calificaciones a esa matrícula.
5. **R3 — presentado / nota**: derivar `presentado_flag`, `nota`, `aprobado_flag` (§8.3).
6. **D2 — deduplicar**: `DISTINCT` en `Calificaciones` (ya proyectadas conceptualmente a la
   clave de negocio) y en el resto de tablas.
7. **R4 — lista blanca**: proyectar cada tabla a sus columnas permitidas + las columnas
   derivadas del punto 5. Escribir a `data/05_staging/<curso>/`.

Los pasos 1–4 se ejecutan por cada carpeta de `data/01_raw/*` (los scripts aceptan
`--curso <año>`, o procesan todos los años). El Paso 5 hace `UNION` incremental de los
**4 años en alcance** (2021‑22 … 2024‑25) usando `anyo` como parte de la clave de negocio;
2025‑26 se sumará cuando su exportación de calificaciones deje de estar vacía.

---

## 7. Modelo dimensional (esquema en estrella)

### 7.1 Hecho principal — `hecho_calificacion`

**Grano**: una calificación de un alumno en un módulo y una evaluación (`01`/`02`/`FI`/`EX`).

| Campo | Tipo | Origen / cálculo |
|---|---|---|
| `alumno_sk` → `dim_alumno` | FK | `Calificaciones.alumno` |
| `modulo_sk` → `dim_modulo` | FK | `(curso, contenido)` |
| `curso_sk` → `dim_curso` | FK | `Calificaciones.curso` |
| `grupo_cod` (degenerada) | texto | vía `Alumnos.grupo` (matrícula única tras D1) — sin `dim_grupo` |
| `turno` | `D` / `S` | vía `Alumnos.turno` (denormalizado para poder filtrar el hecho de notas por turno) |
| `curso_academico_sk` → `dim_curso_academico` | FK | `anyo` |
| `evaluacion_cod` → `dim_evaluacion` | FK | `Calificaciones.evaluacion` |
| `nota_numerica` | decimal | valor crudo (incluye los 0) |
| `nota` | decimal / NULL | NULL si `presentado_flag = 0` |
| `presentado_flag` | 0/1 | 0 si `nota_numerica` es NULL o `= 0` (R3) |
| `aprobado_flag` | 0/1 | `1` si `nota >= 5` |
| `n_calificaciones` | int = 1 | contador |

> Sin `tipo_nota_cod` (columna eliminada en R4) ni `grupo_sk` (sin `dim_grupo`, ver §7.6).

### 7.2 Hecho secundario — `hecho_matricula`

**Grano**: alumno × curso académico (una fila por alumno con matrícula viva).
Evita inflar los conteos de matrícula por el fan‑out de las notas.

Atributos degenerados: `grupo_cod` (de `Alumnos.grupo`), `turno` (`D`/`S`, de
`Alumnos.turno`), `curso_cod` (para enlazar con `dim_curso`).

Métricas: `matriculado_flag` (siempre 1 — solo hay matrícula viva),
**`todo_aprobado_flag`** (1 / 0; **NULL** solo si el año no tiene calificaciones — no ocurre
en los 4 años en alcance, sí ocurriría con 2025‑26; ver §8.8 — alimenta el KPI principal del
cuadro de mando, §11.1), `n_modulos_matriculados`, `n_modulos_aprobados`,
`n_modulos_suspensos`, `n_modulos_no_presentados`.

> `baja_flag`, `dias_hasta_baja` y la tasa de abandono **ya no son calculables**: R1 elimina
> las bajas del DW. Si dirección quiere análisis de abandono, habrá que revisar la regla R1
> (p. ej. conservar las bajas en `hecho_matricula` con `baja_flag = 1` pero fuera de
> `dim_alumno` y de `hecho_calificacion`).

### 7.3 Dimensiones

| Dimensión | Clave natural | Atributos principales / derivados |
|---|---|---|
| `dim_alumno` | `NIA` (seudónimo, §5.6) | `sexo`, `anyo_nac`, **`edad`** (= año del curso − `anyo_nac`, ±1), **`tramo_edad`** (<20 / 20‑24 / 25‑29 / 30+), `nacionalidad` (desc.), `pais_nac` (desc.), **`es_extranjero`**, `municipio_nac` (desc.), `cod_postal`. SCD1 |
| `dim_modulo` | `(anyo, curso, codigo)` | `codigo`, `nombre_cas`, **`tipo_modulo`** (tutoría / inglés / ordinario), **+ jerarquía académica heredada del `curso`** (familia, grado, ciclo, 1º/2º) |
| `dim_curso` | `(anyo, codigo)` (L3) | `curso_nivel` (1/2), `curso_nombre`, `ciclo_cod`, `ciclo_nombre`, `grado_cod` (GM/GS/CE/PFB), `grado_nombre`, `familia_cod`, `familia_nombre` |
| `dim_evaluacion` | `cod` | dominio **fijo** de 4 filas (no requiere catálogo manual): `01` = 1ª evaluación (parcial), `02` = 2ª evaluación (parcial), `FI` = Final ordinaria (final), `EX` = Extraordinaria (extraordinaria) |
| `dim_turno` *(opcional)* | `cod` | 2 filas: `D` = Diurno, `S` = Semipresencial. Solo para poner etiqueta legible al filtro; si no, `turno` se usa como texto degenerado |
| `dim_nacionalidad` / `dim_pais` / `dim_municipio` | `cod` | descripción — *catálogos oficiales, a completar manualmente* (códigos originales, sin agrupar: el Paso 3 no los toca, §5.6) |
| `dim_curso_academico` | `anyo` | etiqueta ("2021‑22"), `fecha_exportacion` |

No hay `dim_grupo`: el grupo queda como **atributo degenerado** `grupo_cod` en los hechos
(ver §7.6). `turno` viaja también degenerado en `hecho_calificacion` y `hecho_matricula`.

> **`anyo` entra en la clave natural de `dim_curso`/`dim_modulo`** (verificado al implementar
> `scripts/05_cargar_dw.py`, no solo intuido en §3.4): **0 códigos L3 coinciden** entre
> 2021‑22 y 2022‑23 — ITACA regenera el `codigo` de `Cursos` cada exportación. Las claves
> subrogadas son por tanto `curso_sk = "<anyo>_<codigo>"` y
> `modulo_sk = "<anyo>_<curso>_<codigo>"`; `alumno_sk` sí puede ser el `NIA` seudónimo a
> secas porque ese seudónimo **es** estable entre años (§5.6).

> Respecto a la versión anterior: **desaparecen `dim_tipo_nota` y `dim_grupo`**;
> `dim_evaluacion` pasa de "rellenar manualmente 24 códigos" a un dominio fijo de 4;
> `dim_alumno` pierde la geografía de residencia (`provincia`, `municipio`, `localidad`) y
> `dim_curso`/`dim_modulo` pierden los nombres en valenciano y `ensenanza`.
> Además, por la anonimización del Paso 3 (§5.6): la clave `NIA` es un **seudónimo**
> irreversible y `fecha_nac` se reduce a `anyo_nac`; `cod_postal`, `nacionalidad`,
> `pais_nac` y `municipio_nac` viajan **sin generalizar** (decisión de negocio).

### 7.4 Jerarquía de navegación del cuadro de mando

```
Familia profesional  →  Grado (GM/GS/CE)  →  Ciclo formativo  →  Curso (1º / 2º)  →  Grupo (código)
```

`dim_curso` y `dim_modulo` la llevan desnormalizada, de modo que el cuadro de mando no
necesita joins recursivos. El último nivel (Grupo) usa el `grupo_cod` degenerado del hecho.

### 7.5 Diagrama del modelo

```
                 dim_curso_academico
                          │
   dim_alumno ── hecho_calificacion ── dim_modulo
        │        │   │   │
        │        │   │   └────────────── dim_evaluacion
        │        │   └────────────────── dim_curso  (familia→grado→ciclo→1º/2º)
        │        └────────────────────── dim_curso_academico
        │        (degeneradas: grupo_cod, turno)
        │
   hecho_matricula ── dim_curso / dim_curso_academico
                      (degeneradas: grupo_cod, turno)
```

### 7.6 Baja de `dim_grupo` (decisión de diseño)

`Grupos` se retira del proyecto (§3.5, D12). Efecto en el modelo:

| Antes (`dim_grupo`) | Ahora |
|---|---|
| `grupo_sk` FK en los dos hechos | `grupo_cod` **texto degenerado** (de `Alumnos.grupo`) |
| filtro Turno ← `dim_grupo.turno` | filtro Turno ← `turno` degenerado (de `Alumnos.turno`) o `dim_turno` opcional |
| `nombre` de grupo, `aula` | **se pierden** (solo queda el código) |
| `capacidad` → métrica `ocupacion` | **se pierde** (no es requisito del cuadro de mando) |

Sin impacto en el KPI principal ni en los filtros obligatorios (§11).

---

## 8. Lógica clave de transformación

### 8.1 R1 — Eliminación de bajas y cascada (Paso 4)

```python
def aplicar_r1(alumnos, calificaciones):
    """Elimina las FILAS de baja (no el NIA entero: 7 NIA de 2021-22 tienen a
    la vez una fila M y una B, y la fila M debe sobrevivir, ver D1) y hace un
    INNER JOIN de Calificaciones con la matricula viva -- lo que de paso
    tambien descarta las huerfanas D11 (alumno que no existe en absoluto)."""
    alumnos_vivos = [a for a in alumnos if a.get("estado_matricula", "").strip() != "B"]
    nia_vivos = {a["NIA"] for a in alumnos_vivos}
    calif_vivas = [c for c in calificaciones if c["alumno"] in nia_vivos]
    return alumnos_vivos, calif_vivas
```

> Ojo: filtrar por `nia_baja = {NIA con alguna fila B}` y descartar `NIA in nia_baja` (en vez
> de filtrar fila a fila por `estado_matricula`) es una trampa: para los 7 NIA de 2021‑22
> con pareja `M`+`B` tumbaría también la fila `M` viva. La versión de arriba, verificada con
> `scripts/04_transformar.py`, da los **1.198** alumnos y los **17.448** registros de
> `Calificaciones` de §2/§5.5.

### 8.2 R2 — Filtro de evaluaciones válidas (Paso 4)

```python
EVALUACIONES_VALIDAS = {"01", "02", "FI", "EX"}

def aplicar_r2(calificaciones):
    return [c for c in calificaciones
            if c["evaluacion"].strip() in EVALUACIONES_VALIDAS]
```

### 8.3 R3 — Presentado / nota (Paso 4)

```python
def derivar_nota(nota_numerica):
    """nota_numerica = '' / NULL / 0  ->  no presentado (regla CLAUDE.md)."""
    txt = (nota_numerica or "").strip()
    if txt == "":
        return {"presentado_flag": 0, "nota": None}
    valor = float(txt.replace(",", "."))
    if valor == 0:
        return {"presentado_flag": 0, "nota": None}
    return {"presentado_flag": 1, "nota": valor}

# aprobado_flag: se calcula sobre 'nota' (NULL -> no aprobado)
aprobado_flag = 1 if (nota is not None and nota >= 5) else 0
# 'nota_numerica' cruda se conserva en hecho_calificacion aparte.
```

### 8.4 D1 — Un alumno por `NIA` (Paso 4)

```python
def matricula_unica(filas_nia, conteo_curso):
    """De las (pocas) matrículas M+M de un mismo NIA tras R1, elige una.
    conteo_curso: Counter((NIA, curso)) -> nº de calificaciones, tras R1+R2."""
    if len(filas_nia) == 1:
        return filas_nia[0]
    # 1º criterio: fecha_matricula ('aaaa-mm', ya generalizada en el Paso 3) mas
    # reciente; 2º: el 'curso' de matricula con mas calificaciones asociadas
    # (Calificaciones no lleva 'grupo', asi que se usa 'curso' como aproximacion)
    return max(filas_nia, key=lambda f: (
        f.get("fecha_matricula", ""),
        conteo_curso.get((f["NIA"], f["curso"]), 0),
    ))
```

### 8.5 D2 — Deduplicación (Paso 4)

- `Calificaciones`: `DISTINCT` sobre `(anyo, alumno, curso, contenido, evaluacion,
  nota_numerica)` — **después** de R1 y R2. Comprobado: no genera conflictos de nota.
- `Alumnos`, `Contenidos`, `Cursos`: `DISTINCT` de seguridad.

### 8.6 R4 — Proyección a la lista blanca (Paso 4, último sub‑paso)

```python
LISTA_BLANCA = {
    "Alumnos":       ["anyo", "fecha_exportacion", "NIA", "anyo_nac", "sexo",
                      "nacionalidad", "pais_nac", "municipio_nac", "cod_postal",
                      "curso", "grupo", "turno"],   # NIA seudonimo; 'grupo'/'turno' -> degeneradas
    "Calificaciones":["anyo", "fecha_exportacion", "evaluacion", "alumno", "curso",
                      "contenido", "nota_numerica",
                      # + derivadas en R3:
                      "presentado_flag", "nota", "aprobado_flag"],
    "Contenidos":    ["anyo", "fecha_exportacion", "codigo", "nombre_cas", "curso"],
    "Cursos":        ["anyo", "fecha_exportacion", "codigo", "nombre_cas",
                      "abreviatura", "padre"],
    # "Grupos": fuera del proyecto (§3.5) -> grupos.xml ya no se exporta.
}
```

En el Paso 5, `grupo_cod` y `turno` se copian de la matrícula principal de cada alumno
(`Alumnos.grupo` / `Alumnos.turno`) a `hecho_matricula` y `hecho_calificacion`.

### 8.7 Resolución de la jerarquía de Cursos (Paso 5)

```python
def resolver_jerarquia(cod, by_cod):
    """Sube por 'padre' recogiendo los ancestros L3 -> L0."""
    cadena, actual = [], cod
    while actual and actual in by_cod and len(cadena) < 5:
        cadena.append(by_cod[actual])
        actual = by_cod[actual]["padre"].strip()
    return cadena  # [0]=L3 curso · [1]=L2 ciclo · [2]=L1 grado · [3]=L0 familia

def fila_dim_curso(cod, by_cod):
    c = resolver_jerarquia(cod, by_cod)
    L3 = c[0] if len(c) > 0 else {}
    L2 = c[1] if len(c) > 1 else {}
    L1 = c[2] if len(c) > 2 else {}
    L0 = c[3] if len(c) > 3 else {}
    abrev = L3.get("abreviatura", "").strip()
    return {
        "curso_cod":      cod,
        "curso_nivel":    int(abrev[0]) if abrev[:1].isdigit() else None,
        "curso_nombre":   L3.get("nombre_cas"),
        "ciclo_cod":      L2.get("abreviatura"),
        "ciclo_nombre":   L2.get("nombre_cas"),
        "grado_cod":      L1.get("abreviatura"),
        "grado_nombre":   L1.get("nombre_cas"),
        "familia_cod":    L0.get("abreviatura"),
        "familia_nombre": L0.get("nombre_cas"),
    }
```

`by_cod` se construye **por año** (todos los cursos ya traen `Cursos.csv`). Si algún
`Alumnos.curso` no apareciera en el árbol de su año, dejar la jerarquía a NULL sin bloquear
la carga.

### 8.8 `todo_aprobado_flag` (Paso 5 — KPI del cuadro de mando)

Se calcula por alumno y curso académico, a partir de la **nota final** de cada módulo
matriculado (no de cada evaluación parcial), para no contar dos veces el mismo módulo:

```python
def nota_final_modulo(notas_modulo):
    """De las calificaciones de un alumno en un modulo, la definitiva:
    la extraordinaria (EX) si existe; si no, la final ordinaria (FI)."""
    por_evaluacion = {n["evaluacion"]: n for n in notas_modulo}
    return por_evaluacion.get("EX") or por_evaluacion.get("FI")

def todo_aprobado(alumno_notas):
    """alumno_notas: notas del alumno agrupadas por modulo (curso, contenido)."""
    if not alumno_notas:
        return None  # el alumno no tiene NINGUNA calificacion (año sin notas) -> se excluye
    finales = [nota_final_modulo(ns) for ns in alumno_notas.values()]
    if any(f is None for f in finales):
        return 0  # falta la nota final de algun modulo con calificaciones parciales
    return 1 if all(f["aprobado_flag"] == 1 for f in finales) else 0
```

- Un módulo cuya nota final es "no presentado" (R3 → `aprobado_flag = 0`) cuenta como **no
  aprobado**.
- Un año entero sin calificaciones (2025‑26, fuera de alcance) dejaría `todo_aprobado_flag`
  **NULL** en todo su `hecho_matricula` → el KPI de §11.1 filtra los NULL, no los cuenta
  como 0. Los 4 años en alcance sí tienen calificaciones.

> Pendiente de confirmar con dirección (§10): si un módulo matriculado **sin** nota final
> registrada (`EX`/`FI`) debe contar como "no aprobado" (criterio de arriba) o excluirse.

---

## 9. Análisis académico habilitado

- **% de alumnos con todo aprobado** (`todo_aprobado_flag`, §8.8) — KPI principal del cuadro
  de mando, filtrable por familia, grado, curso (1º/2º), ciclo, turno y año (§11).
- **Tasa de aprobados / suspensos / no presentados** por módulo, ciclo, grado, familia,
  grupo, evaluación (`01`/`02`/`FI`/`EX`), turno, sexo, tramo de edad, nacionalidad.
- **Evolución de notas** 1ª (`01`) → 2ª (`02`) → final (`FI`) → extraordinaria (`EX`) por
  alumno / grupo / módulo.
- **Módulos "cuello de botella"**: mayor % de suspensos o de no presentados.
- **Recuperación en extraordinaria**: alumnos que pasan de suspenso en `FI` a aprobado en `EX`.
- **Rendimiento diurno (D) vs semipresencial (S)** (`turno`, desde la matrícula).
- **Comparativa entre familias y grados** (GM vs GS vs CE).
- **Comparativa entre cursos académicos** — **4 años completos** (2021‑22 … 2024‑25) con
  calificaciones, matrícula y jerarquía. 2025‑26 se añadirá cuando su export esté completo.

> **Ya no habilitado**: análisis de abandono / bajas y desglose por `tipo_nota`
> (RA/UF/convocatoria), por eliminarse esos datos en el Paso 4; **ocupación de grupos frente
> a capacidad** y nombre/aula del grupo, por retirarse `Grupos` (§3.5).

---

## 10. Artefactos a construir

| Paso | Script | Entrada | Salida |
|---|---|---|---|
| 3 | `scripts/03_anonimizar_csv.py` ✅ | `data/03_csv/<curso>/*.csv` | `data/04_anon/<curso>/*.csv` (anonimizado, mismo grano) |
| 4 | `scripts/04_transformar.py` ✅ | `data/04_anon/<curso>/*.csv` | `data/05_staging/<curso>/*.csv` (lista blanca + flags) |
| 5 | `scripts/05_cargar_dw.py` ✅ | `data/05_staging/<curso>/*.csv` (2021‑22…2024‑25) + catálogos opcionales | `data/06_dw/dim_*.csv`, `data/06_dw/hecho_*.csv` |
| — | Plantillas de catálogo | — | `data/catalogos/dim_nacionalidad.csv`, `dim_pais.csv`, `dim_municipio.csv` (a completar con los códigos originales, sin agrupar) |
| — | `dim_evaluacion` | — | dominio fijo de 4 filas, se genera en código (no es catálogo manual) |
| 6 | Herramienta de BI | `data/06_dw/dim_*.csv`, `data/06_dw/hecho_*.csv` | Cuadro de mando — KPI, gráfico y filtros de §11 |

### Pendientes de negocio (requieren tu conocimiento)

1. **D1** — Implementado en `scripts/04_transformar.py` con: 1º `fecha_matricula`
   (`aaaa-mm`) más reciente, 2º el `curso` con más calificaciones asociadas (adaptación de
   "grupo con más calificaciones": `Calificaciones` no lleva `grupo`, sí `curso`). Confirmar
   si este criterio vale o si hace falta otro.
2. **Catálogos** oficiales de `nacionalidad`, `pais_nac`, `municipio_nac`.
3. **§8.8** — Si un módulo matriculado sin nota final registrada cuenta como "no aprobado"
   o se excluye del `todo_aprobado_flag`.
4. **Abandono** — ¿Se necesita analizar bajas? Si sí, revisar R1 para conservarlas en
   `hecho_matricula` sin meterlas en `dim_alumno` ni en `hecho_calificacion`.
5. **D11** — Las 188 calificaciones de 2023‑24 sin alumno: ¿se descartan (propuesta) o hay
   que pedir una reexportación de `Alumnos` 2023‑24 con fecha coherente?
6. **`faltas.xml` de 2023‑24** — ¿interesa un `hecho_falta` (asistencia) en una fase
   posterior? Hay 16.262 registros disponibles solo para ese año.

---

## 11. Especificación funcional del cuadro de mando

Requisitos de `CLAUDE.md`.

### 11.1 KPI principal

**% de alumnos con todo aprobado** = alumnos con `todo_aprobado_flag = 1` (§8.8) / alumnos
con `todo_aprobado_flag` **no nulo**, sobre el conjunto filtrado. Con los 4 años en alcance
todos los alumnos tienen valor; el filtro de NULL solo actúa si más adelante se carga un año
sin calificaciones (2025‑26).

KPI's de apoyo con totales (tarjetas), recalculados según los filtros:

- Nº de alumnos matriculados (matrícula viva)
- Nº de alumnos con todo aprobado
- Nº de calificaciones registradas (evaluaciones `01`/`02`/`FI`/`EX`)
- % de no presentados sobre el total de calificaciones

> Se retira el KPI "Nº de bajas": R1 elimina las bajas del DW.

### 11.2 Gráfico individual

Gráfico principal que desglosa el % de todo aprobado por la dimensión elegida en el eje
(p. ej. por ciclo, por `grupo_cod`, o por alumno cuando el filtro deja un único grupo). Se
construye sobre `hecho_matricula` agregado por `alumno_sk` / `grupo_cod` y el
`todo_aprobado_flag`, cruzado con `dim_curso` para el desglose jerárquico. El eje "Grupo"
muestra el código (`1CFSF`), no un nombre descriptivo (ya no hay `dim_grupo`).

### 11.3 Filtros

| Filtro | Dimensión / campo de origen |
|---|---|
| Familia | `dim_curso.familia_nombre` |
| Grado | `dim_curso.grado_nombre` (GM / GS / CE) |
| Curso (1º / 2º) | `dim_curso.curso_nivel` |
| Ciclo | `dim_curso.ciclo_nombre` |
| Turno | `turno` degenerado del hecho (de `Alumnos.turno`); etiqueta vía `dim_turno` opcional |
| Año | `dim_curso_academico.anyo` |

Todos los filtros están cubiertos por el modelo de §7.3 **sin `dim_grupo`**: Familia / Grado /
Curso / Ciclo salen de `dim_curso`, Año de `dim_curso_academico`, y **Turno de la propia
matrícula**. Solo hace falta que el Paso 5 haga el `UNION` multi‑año para que `Año` tenga
más de un valor.

### 11.4 Grano del KPI

El KPI y el gráfico se calculan sobre `hecho_matricula` (una fila por alumno con matrícula
viva), **no** sobre `hecho_calificacion`, para que el fan‑out de notas por módulo/evaluación
no distorsione el porcentaje.
