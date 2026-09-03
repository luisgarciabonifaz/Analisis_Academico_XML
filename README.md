# Analisis_Academico_XML
Proyecto de analisis academico

## Ficheros XML
- alumnos.xml
- calificaciones.xml
- contenidos.xml
- cursos.xml
- grupos.xml

## Campos Respetados del XML

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

Alumnos:
--------
NIA   --> + 2345
nombre  -->  cambio letras
apellido1 --> cambio letras
apellido2 ---> cambio letras
fecha_nac 
sexo
tipo_doc 
documento --> 12345678X
nacionalidad
pais_nac	
municipio_nac
cod_postal 
provincia 
municipio 
localidad
telefono1 --> 666666666 
telefono2 --> 666666666
telefono3 --> 666666666
email1  ---> cambio letras
email2 ---> cambio letras
sip	9813060035 --> 8888888888 
expediente --> + 22222	
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
alumno + 2345
ensenanza
curso
contenido
bloque_contenido
nota_numerica
tipo_nota

