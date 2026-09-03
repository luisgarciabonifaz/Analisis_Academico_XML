# Analisis_Academico_XML
Proyecto de analisis academico

## Ficheros XML
- alumnos.xml
- calificaciones.xml
- contenidos.xml
- cursos.xml
- grupos.xml

## Campos Respetados del XML

Puedes crear un script para convertirlos XML de la carpeta Originales/2021-22/Paso1 en CSV añadiendo como campos el curso y la fechaExportacion y cogiendo solo los campos indicados a continuación


Alumnos:
--------
NIA
nombre
apellido1
apellido2
fecha_nac
sexo
tipo_doc 
documento
nacionalidad
pais_nac	
municipio_nac
cod_postal 
provincia 
municipio 
localidad
telefono1 
telefono2 
telefono3
email1 
email2
sip
expediente
ensenanza 
curso 
grupo
turno
linea 
modalidad
repite 
estado_matricula 
tipo_matricula 
matricula_parcial 
matricula_condic
fecha_matricula
fecha_ingreso_centro

Calificaciones:
------------
evaluacion
alumno
ensenanza
curso
contenido
bloque_contenido
nota_numerica
tipo_nota

Contenidos:
------------
codigo
nombre_cas
nombre_val
ensenanza
curso

Cursos:
-----------
codigo
nombre_cas
nombre_val
abreviatura
ensenanza
padre

Grupos:
--------

codigo
nombre
ensenanza
linea
turno
modalidad
aula
capacidad


## Campos Modificados en el XML

Puedes crear un script para realizar los siguientes cambios en los XML de Alumnos y Calificaciones de la carpeta Originales/2021-22 generando un nombre distinto de fichero

Alumnos:
--------
NIA   -->  Sumarle  2345
nombre  -->  cambiar letra
apellido1 --> cambiar letras
apellido2 ---> cambiar letras
documento --> 12345678X
telefono1 --> 666666666 
telefono2 --> 666666666
telefono3 --> 666666666
email1  ---> cambiar letras
email2 ---> cambiar letras
sip	--> 8888888888 
expediente --> Sumar 234567	


Calificaciones:
------------
alumno --> Sumar 2345


Para los cambios de letras usar estos codigos: (a:h, e:j, i:z, o:l, u:s, m:n, d:e, s:a, c:d)


## Analisis

Puedes analizarme los ficheros csv de la carpeta Originales/2021-22/Paso1 y definirme un flujo datos para crear un data warehouse que me permita realizar una analisis  academico teniendo como base estas tablas.

  Alumnos
  Callificaciones
  Modulos(Contenidos)

  Disculpa se me ha olvidado decirte que en la tabla cursos hay una relación padre hijo entre los campos codigo y padre que me devuelve datos interesantes para el analisis, estos datos el grado, la familia, el modulo (contenido) y si es primero o segundo.
  