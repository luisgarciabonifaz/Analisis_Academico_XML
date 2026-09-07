# Analisis Academico XML

## Sobre este proyecto
Soy un profesor de un instituto de formación profesional y el objetivo del proyecto es crear un cuadro de mando de analisis academico para el equipo directivo del instituto.
Hay que crear de un flujo de datos para extraer información de ficheros XML con datos de alumnos, calificaciones, modulos y cursos y crear el Data Warehouse que sirva como origen de datos para el cuadro de mando.

## Reglas de trabajo
- Lenguaje Scripts: Python
- Datos origen en formato XML
- Datos salida en formato CSV

- En la tabla cursos hay una relación padre hijo entre los campos codigo y padre que me devuelve datos interesantes para el analisis, estos datos el grado, la familia, el modulo (contenido) y si es primero o segundo.
- Los alumnos con estado_maticula="B" hay que eliminarlos de todas las tablas
- Las únicas evaluaciones validas son 01, 02, FI y EX
- La nota_numerica=0 es equivalente a no presentado

## Stack Tecnológico
Scripts en python

## Modelo de datos
- **Alumnos**: Tabla con los datos de los alumnos: Alumno, Fecha_Nac, Sexo, Cod_Postal, Provincia, Municipio, Nacionalidad, Pais_Nac
- **Calificaciones**: Tabla con las calificaciones de los alumonos por modulo y evaluación: Alumno, Modulo, Curso, Evaluacion, Nota
- **Modulos**: Tabla con información de los modulos: Codigo, Nombre, Curso
- **Horas**: Tabla de horas por mudulo.

Datos realmente interesantes de los ficheros:

Alumnos
-------
anyo
fecha_exporataciion
NIA
fecha_nac
sexo
nacionalidad
pais_nac
municipio_nac
cod_postal
curso
grupo
turno

Calificaciones
--------------
anyo
fecha_exportacion
evaluacion
alumno
curso
contenido
nota_numerica

Contenidos
----------
anyo
fecha_exportacion
codigo
nombre_cas
curso

Cursos
------
anyo
fecha_exportacion
codigo
nombre_cas
abreviatura
padre


Grupos
------
anyo
fecha_exportacion
codigo
nombre
turno
modalidad
aula
capacidad


## Funcionalidades principales del Flujo
- Modificar los XML originales para que los datos no sean reconocibles
- Convertir los XML en CSV incluyendo, Año y Fecha de exportacion como campos
- Eliminar campos del los CSV que no son necesarios
- Diseñar el esquema del Data Warehouse.
- Modificar y/o crear los csv que conformam el Data Warehouse
- Diseñar el Cuadro de mando
- Crear el cuadro de mando

## Caracteriticas del cuadro de mando

- Deben aparecer valores de porcentaje de alumnos con todo aprobado
- Grafico individual y KPI's con totales
- Debe tener los siguientes filtros
  - Familia
  - Grado
  - Curso (Primero/Segundo) 
  - Ciclo
  - Turno 
  - Año



