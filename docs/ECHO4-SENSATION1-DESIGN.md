# E4-SENSATION-1 — contrato del primer entregable

2026-09-21. Implementación autorizada por el usuario, siguiendo el
[roadmap oficial publicado](https://www.rxlabs.org/docs/echoai/echo4).

## Alcance y orden

Primero **SENSATION**, después BOUNDARY y SELF. Este entregable es una
auditoría temporal exhaustiva y una ventana de observaciones reutilizable;
no cierra por sí solo SENSATION-1 ni incorpora un predictor aprendido a Q.
No se avanza a atribución causal suponiendo que un error significa causa
externa. El mundo WORLD-1 y el agente histórico permanecen intactos.

## Entrada y memoria

La ventana recibe exclusivamente WSP de 16 bytes y la acción **ejecutada**
0..2. No recibe H, temperatura exacta, semillas, etiquetas causales,
viabilidad, recompensa ni acciones propuestas. No infiere una acción a
partir de la intención. Un veto sin transición no añade un paso; una
acción wait efectivamente ejecutada sí lo añade.

Comparación fijada antes de ejecutar: 0, 2 y 4 transiciones pasadas. Una
historia de k pasos contiene k+1 observaciones y k acciones. Payload fijo:
16, 50 y 84 bytes respectivamente, más el contador acotado de ocupación.
No se toca ningún campo WSP. Es memoria de trabajo local de paquetes ya
recibidos, no un formato de comunicación nuevo ni una segunda CAM.
Python tiene sobrecoste de objetos; esos bytes no son una medida del heap
real ni una promesa de implementación C Heap-0.

La ventana rechaza tipos inválidos, booleanos, acciones fuera de rango y
paquetes de longitud incorrecta antes de mutar. Reiniciar es explícito.
El delta de U/B, si se consulta, es del código sensorial cuantizado, no
una medición exacta de energía/temperatura ni una velocidad física.

## Auditoría externa, no controlador

Se parte de **todos** los 16.002 estados vivos y se enumeran todas las
secuencias de cuatro acciones cuyo prefijo completo permanece vivo.
Los prefijos que terminan antes se cuentan aparte. No hay selección por
recompensa, política testigo ni búsqueda de un resultado positivo.

Sobre la **misma población** de prefijos supervivientes se comparan las
proyecciones de 0, 2 y 4 pasos. Un prefijo vivo de cuatro pasos no garantiza
que su estado final sea viable indefinidamente. Se conservan esos casos.
El informe también reproduce las 32 clases de la observación instantánea
del dominio vivo completo, separado de la población comparada.

Cada historia agrupa los estados exactos finales compatibles. Solo el
evaluador conoce esos estados y las tres consecuencias posibles siguientes.
Informa:

- Historias distintas y número de prefijos que representan.
- Ambigüedad de la siguiente observación y de terminalidad, separadas.
- Prefijos en grupos ambiguos: mismo denominador en los tres brazos.
- Diferentes conjuntos de acciones viables; esto **no** implica conflicto.
- Conflicto real: todos los estados del grupo son viables individualmente,
  pero no comparten ninguna acción viable. Grupos mixtos/condenados aparte.
- Casos testigo deterministas de ambigüedad residual.
- Coste máximo de la ventana, digest del contenido y fuentes.

Las fracciones se publican como numerador/denominador enteros. Un menor
porcentaje ambiguo solo demuestra información adicional en ese dominio.
Los conteos no son una distribución natural de experiencias del agente.
No se presentan como precisión predictiva aprendida o supervivencia.

## Aceptación de este entregable

1. Ventana acotada, sin mutación de los paquetes originales y sin acceso
   a mundo, auditor, CAM, Q, T o córtex.
2. Enumeración reproducible, truncamiento terminal explícito y misma
   población de comparación. Más historia refina, nunca amplía, el conjunto
   compatible de un prefijo. La ambigüedad ponderada no puede aumentar.
3. Caso independiente de referencia en un dominio pequeño y comprobación
   de testigos contra la física; rechazo de configuraciones inválidas.
4. CLI JSON reproducible en proceso nuevo, sin escrituras implícitas.
5. Regresiones WORLD-1/NEXUS-0/HEAT seleccionadas intactas. Ningún cambio a
   las fuentes históricas de nexus0 ni a certificados sellados.

Una auditoría correcta puede devolver un resultado negativo. No se exige
que cuatro pasos eliminen la ambigüedad ni se cambia el contrato después.

## Lo que falta para cerrar SENSATION-1

Elegir e integrar un predictor usando T y memoria existente con presupuesto
explícito, comparar contra T instantánea con igual acceso a sensores,
registrar predicción antes del resultado, distinguir error de incertidumbre
y evaluar en trayectorias reservadas con umbrales fijados previamente.
La auditoría exhaustiva es desarrollo público, **no** un examen reservado.
No se usarán sus estados compatibles o testigos como entradas del agente.
La etiqueta de cuatro estados sigue pendiente de ese contrato predictivo.
BOUNDARY-1 requerirá además intervenciones comparables y perturbaciones;
el WORLD-1 nominal no permite atribuir por sí solo causas cuerpo/entorno.
