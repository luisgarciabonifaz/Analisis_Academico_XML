# Análisis Académico XML

Flujo de datos que parte de las exportaciones XML de ITACA (alumnos, calificaciones,
módulos y cursos) y construye un **Data Warehouse** en estrella que sirve de origen para un
cuadro de mando de análisis académico dirigido al equipo directivo de un instituto de FP.

El diseño completo (análisis de las tablas, reglas, esquema dimensional, decisiones) está en
[`docs/Analisis_y_Diseno_DW.md`](docs/Analisis_y_Diseno_DW.md).

## Flujo de datos

| Paso | Script | Entrada | Salida | Qué hace |
|---|---|---|---|---|
| 1 | `scripts/01_anonimizar_xml.py` | `data/01_raw/<curso>/*.xml` | `data/02_anonimizado/<curso>/*.xml` | **Ofuscación** del XML (que el alumno no se reconozca) + recorte grueso de campos. Reversible. |
| 2 | `scripts/02_xml_a_csv.py` | `data/02_anonimizado/<curso>/*.xml` | `data/03_csv/<curso>/*.csv` | Conversión XML → CSV, añadiendo `anyo` y `fecha_exportacion` del `<centro>`. |
| 3 | `scripts/03_anonimizar_csv.py` | `data/03_csv/<curso>/*.csv` | `data/04_anon/<curso>/*.csv` | **Anonimización real**: seudónimo irreversible del identificador, generalización de fechas. Mismo grano. |
| 4 | `scripts/04_transformar.py` | `data/04_anon/<curso>/*.csv` | `data/05_staging/<curso>/*.csv` | Reglas de negocio + calidad de datos + proyección a la lista blanca de columnas. |
| 5 | `scripts/05_cargar_dw.py` | `data/05_staging/<curso>/*.csv` | `data/06_dw/dim_*.csv`, `data/06_dw/hecho_*.csv` | Carga del DW en estrella con `UNION` de todos los cursos en alcance. |
| 6 | *(pendiente)* | `data/06_dw/*.csv` | Cuadro de mando | KPIs, gráfico y filtros. |

Todos los scripts son Python sin dependencias externas. Cada uno procesa **todos los cursos**
si se ejecuta sin argumentos, o uno concreto con `--curso 2021-22` (`--cursos` en el Paso 5).

```bash
python3 scripts/01_anonimizar_xml.py
python3 scripts/02_xml_a_csv.py
python3 scripts/03_anonimizar_csv.py
python3 scripts/04_transformar.py
python3 scripts/05_cargar_dw.py
```

`data/` está en `.gitignore`: en el repo solo viven los scripts y la documentación.

## Ficheros de origen (XML de ITACA)

- `alumnos.xml`
- `calificaciones.xml`
- `contenidos.xml`
- `cursos.xml`

`grupos.xml` **se descartó**: su único dato necesario para el cuadro de mando (`turno`) ya
está en `alumnos.xml`.

## Reglas de negocio

- Los alumnos con `estado_matricula = "B"` (baja) se eliminan de todas las tablas, **en
  cascada** con sus calificaciones.
- Las únicas evaluaciones válidas son `01`, `02`, `FI` y `EX`.
- `nota_numerica = 0` equivale a **no presentado**.
- En `cursos` hay una relación padre‑hijo (`codigo` ← `padre`) que encadena 4 niveles:
  familia profesional → grado → ciclo formativo → curso (1º / 2º). De ahí salen la familia,
  el grado, el ciclo y el "1º/2º" de cada alumno y de cada módulo.

## Paso 1 — Ofuscación del XML

### Campos que se conservan de cada elemento

**Alumnos**: `NIA`, `nombre`, `apellido1`, `apellido2`, `fecha_nac`, `sexo`, `tipo_doc`,
`documento`, `nacionalidad`, `pais_nac`, `municipio_nac`, `cod_postal`, `provincia`,
`municipio`, `localidad`, `telefono1`, `telefono2`, `telefono3`, `email1`, `email2`, `sip`,
`expediente`, `ensenanza`, `curso`, `grupo`, `turno`, `linea`, `modalidad`, `repite`,
`estado_matricula`, `tipo_matricula`, `matricula_parcial`, `matricula_condic`,
`fecha_matricula`, `fecha_ingreso_centro`

**Calificaciones**: `evaluacion`, `alumno`, `ensenanza`, `curso`, `contenido`,
`bloque_contenido`, `nota_numerica`, `tipo_nota`

**Contenidos**: `codigo`, `nombre_cas`, `nombre_val`, `ensenanza`, `curso`

**Cursos**: `codigo`, `nombre_cas`, `nombre_val`, `abreviatura`, `ensenanza`, `padre`

### Cambios aplicados (solo Alumnos y Calificaciones)

| Campo | Cambio |
|---|---|
| `NIA` (Alumnos) / `alumno` (Calificaciones) | sumar `2345` |
| `nombre`, `apellido1`, `apellido2`, `email1`, `email2` | sustitución de letras |
| `documento` | `12345678X` |
| `telefono1`, `telefono2`, `telefono3` | `666666666` |
| `sip` | `8888888888` |
| `expediente` | sumar `234567` |

Sustitución de letras: `a→h, e→j, i→z, o→l, u→s, m→n, d→e, s→a, c→d`.

> Es una ofuscación **reversible**: sirve para que un alumno no reconozca sus datos en una
> simulación realista, no para anonimizar de verdad. Eso lo hace el Paso 3.

## Paso 3 — Anonimización real de los CSV

- **Elimina** los datos personales que aún arrastra el CSV (`nombre`, apellidos,
  `documento`, teléfonos, emails, `sip`, `expediente`), la geografía de **residencia**
  (`provincia`, `municipio`, `localidad`) y `fecha_ingreso_centro`.
- **Seudonimiza** `NIA` / `alumno` con un token HMAC‑SHA256 irreversible sin la clave, pero
  estable entre ficheros y años (mantiene la integridad referencial y el análisis
  multi‑año). La clave vive en `data/_claves/anon_hmac.key` (fuera del repo).
- **Generaliza** las fechas: `fecha_nac` → `anyo_nac` (año), `fecha_matricula` → `aaaa-mm`.
- **Deja tal cual** `cod_postal`, `nacionalidad`, `pais_nac` y `municipio_nac` (decisión de
  negocio: el cuadro de mando los necesita con su granularidad completa).

## Paso 4 — Transformación (reglas de negocio + lista blanca)

Aplica, en este orden: R1 (bajas + huérfanas) · R2 (evaluaciones válidas) · D1 (un alumno
por `NIA`) · R3 (deriva `presentado_flag` / `nota` / `aprobado_flag`) · D2 (deduplicación) ·
R4 (proyección a la lista blanca).

### Campos que se quedan (lista blanca R4)

**Alumnos**: `anyo`, `fecha_exportacion`, `NIA`, `anyo_nac`, `sexo`, `nacionalidad`,
`pais_nac`, `municipio_nac`, `cod_postal`, `curso`, `grupo`, `turno`

**Calificaciones**: `anyo`, `fecha_exportacion`, `evaluacion`, `alumno`, `curso`,
`contenido`, `nota_numerica` · **+ derivadas (R3)**: `presentado_flag`, `nota`,
`aprobado_flag`

**Contenidos**: `anyo`, `fecha_exportacion`, `codigo`, `nombre_cas`, `curso`

**Cursos**: `anyo`, `fecha_exportacion`, `codigo`, `nombre_cas`, `abreviatura`, `padre`

## Paso 5 — Data Warehouse

Esquema en estrella en `data/06_dw/`, con `UNION` de los cursos **2021‑22 … 2024‑25**
(2025‑26 se excluye mientras su exportación de calificaciones esté vacía).

- **Dimensiones**: `dim_alumno`, `dim_curso`, `dim_modulo`, `dim_curso_academico`,
  `dim_evaluacion`, `dim_turno` (y `dim_nacionalidad` / `dim_pais` / `dim_municipio` si se
  aportan los catálogos en `data/catalogos/`).
- **Hechos**: `hecho_calificacion` (grano: una calificación) y `hecho_matricula` (grano:
  un alumno por curso académico, con `todo_aprobado_flag` y desglose de módulos).

## Cuadro de mando (Paso 6, pendiente)

Requisitos: % de alumnos con todo aprobado (KPI principal), gráfico individual y KPIs con
totales, y filtros por **Familia, Grado, Curso (1º/2º), Ciclo, Turno y Año**.

## Pendientes

- Catálogos oficiales de `nacionalidad`, `pais_nac` y `municipio_nac` en `data/catalogos/`.
- Construir el cuadro de mando (Paso 6).
