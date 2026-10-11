# ECHO-5: segundo desarrollo del cierre, 10 de octubre de 2026

El ensayo `artifacts/closure-development-20261010-r2/` terminó y su auditoría
independiente es válida. Los cuatro dominios se reconstruyeron desde recibos
y replays en procesos nuevos. Este resultado no cierra la versión: es
desarrollo, con pocas réplicas, y conserva resultados negativos.

Las fuentes propias medidas tienen SHA-256
`4924b61e1b6524fbe210fa21d7d7a571999e3c64ac0d806b77493e1beb59292d`.
Los contratos, fuentes, configuraciones y auditorías están archivados en la
carpeta del ensayo. Las revisiones V2 de transferencia y contraejemplos se
declararon después del primer desarrollo y antes de abrir confirmación. El
primer resultado permanece en su directorio original.

| Comparación | Resultado observado | Alcance |
|---|---|---|
| Representación nueva frente a ablación | 7/8 frente a 0/8 casos con solución dentro del lenguaje | Cuatro familias estructurales, dos semillas por familia |
| Profundidad ampliada frente a búsqueda corta | 7/8 frente a 0/8 | Misma gramática, límites declarados; no prueba de minimalidad universal |
| Caché de prefijos | 17.241.748 frente a 34.333.432 unidades lógicas | Mismos programas, estados y aciertos; aproximadamente 49,8 % menos trabajo total |
| Memoria aprendida frente a vacía | 18.112.490 frente a 17.241.748 | Menos trabajo de evaluación, pero la adquisición aún encarece este lote pequeño |
| Memoria aprendida frente a biblioteca fija | 7/8 en ambas; 18.112.490 frente a 15.631.053 unidades | La fija contiene las seis mismas macros como referencia manual; no hay superioridad del aprendizaje |
| Memoria aprendida frente a irrelevante | 18.112.490 frente a 21.934.672 unidades | Igual número de recuerdos y pasos expandidos; coste de adquisición incluido |
| Abstención | Ninguna predicción en los cuatro controles | Ambigüedad de ejemplos y transformación fuera del lenguaje |
| Contraejemplos, precisión final | 16/16 en cada condición | Cuatro adquisiciones independientes; final saturado |
| Contraejemplos, utilidad durante adquisición | Adaptativo 1,00; aleatorio 0,9167; secuencial 1,00 | Una victoria independiente, tres empates; evidencia insuficiente para cierre |
| MiniGrid/BabyAI | Informativo 8/8; fijo 0/8; pasivo 2/8; sin memoria 5/8; sin planificación 3/8 | Observación parcial nativa, 40 filas y replay; semillas de desarrollo |
| MissionAgent software | ECHO 3/12; convencional 3/12; horizonte uno 4/12 | Cero colisiones/reservas infringidas; las paradas seguras siguen contando como misiones no completadas |

La memoria reduce trabajo semántico frente a vacía aun contando adquisición,
pero no reduce el coste total en estas doce tareas. La diferencia minúscula
frente a la biblioteca fija durante evaluación procede de metadatos, no de
una búsqueda mejor. La confirmación ampliada debe medir la amortización;
suponerla no equivale a observarla.

El selector adaptativo necesitó menos consultas en una de cuatro réplicas.
La media de precisión en los tres prefijos mejora 0,0833 frente a aleatorio,
por debajo del umbral 0,10 previsto, y el intervalo incluye cero. El coste
adicional medio fue aproximadamente 0,1055 %. No se deben contar los casos ni
los prefijos como réplicas independientes de la adquisición.

La revisión del puente robótico detectó además una conexión incompleta:
aceptar una hipótesis opcional no acredita que el razonador nuevo la produzca
en ejecución normal. Las filas de este ensayo usan `plan_source=compose`.
Debe conectarse ese camino antes de confirmar la integración solicitada. El
ensayo Gazebo/PX4 inicial se conserva como referencia del puente heredado.

El panel se comprobó de principio a fin con un navegador real. Una misión
nativa de puerta y llave terminó con éxito en 20 acciones y un juez externo.
Paso, reproducción, pausa, registro, disposición móvil y diagnóstico neuronal
pasaron sus comprobaciones. Recibo: `artifacts/browser-20261010-r3/result.json`.
La actividad LIF procede de una red real de 256 unidades estimulada desde una
observación pública; es diagnóstico independiente, no evidencia de que esa
red haya elegido las acciones de MiniGrid.

Las pruebas en `artifacts/closure-checks-20261010-r3/` pasaron: 229 casos en el
entorno base, con 12 omitidos allí por dependencia opcional; 32 en el entorno
MiniGrid/BabyAI, incluidos esos 12. No se ha publicado una release ni se ha
declarado ECHO-5 en verde. S6 continúa fuera de este trabajo.
