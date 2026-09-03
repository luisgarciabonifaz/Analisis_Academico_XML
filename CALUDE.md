# Analisis Academico XML

## Sobre este proyecto
Soy un profesor de un instituto de formación profesional y el objetivo del proyecto es crear un cuadro de mando de analisis academico para el equipo directivo del instituto.
Hay que crear de un flujo de datos para extraer información de ficheros XML con datos de alumnos, calificaciones, modulos y cursos y crear el Data Warehouse que sirva como origen de datos para el cuadro de mando.

## Reglas de trabajo
- Lenguaje Scripts: Python
- Datos origen en formato XML
- Datos salida en formato CSV

## Stack Tecnológico
Scripts en python

## Modelo de datos
- **Alumnos**: Tabla con los datos de los alumnos: Alumno, Fecha_Nac, Sexo, Cod_Postal, Provincia, Municipio, Nacionalidad, Pais_Nac
- **Calificaciones**: Tabla con las calificaciones de los alumonos por modulo y evaluación: Alumno, Modulo, Curso, Evaluacion, Nota
- **Modulos**: Tabla con información de los modulos: Codigo, Nombre, Curso
- **Horas**: Tabla de horas por mudulo.

## Funcionalidades principales del Flujo
- Modificar los XML originales para que los datos no sean reconocibles
- Convertir los XML en CSV incluyendo, Año y Fecha de exportacion como campos
- Eliminar campos del los CSV que no son necesarios
- Diseñar el esquema del Data Warehouse.
- Modificar y/o crear los csv que conformam el Data Warehouse
- Diseñar el Cuadro de mando
- Crear el cuadro de mando
