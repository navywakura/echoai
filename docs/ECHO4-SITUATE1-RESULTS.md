# E4-SITUATE-1 «sé qué soy» — **verde**

2026-09-24. [Contrato](ECHO4-SITUATE1-DESIGN.md), aprobado con la
apertura del examen autorizada si el desarrollo pasaba. Desarrollo sellado
`d8abbb50…`; regresión ECHO-4 previa **854/854**. Examen: 16 condiciones nuevas
(269001–269016), cada una en **procesos hijos nuevos**: nominal, sin sensores,
reanudación en otro proceso y otra versión del código. Auditoría en proceso nuevo:
válida, cero hallazgos, **`situate1_green=true`**. Digest
`f7ac08df049c4a24036f25d0635fbef34f4c9d16815388817ab8b4e53e094460`.
[Informe](../lab/echo4/situate1-d-v1/report.json) · [Código](../echo4/situate.py) ·
[Banco](../echo4/situate_bench.py) · [Pruebas](../tests/test_echo4_situate1.py).

## Qué queda demostrado

ECHO responde **qué es y dónde está** solo desde hechos que verificó él mismo con
sensores reales del sistema, y dice «no lo sé» cuando no tiene evidencia:

| Criterio | Resultado (16 condiciones) |
|---|---|
| 1. Batería de 9 preguntas correcta, contrastada con lecturas independientes (`/proc`) | **100 %** |
| 2. Autoatribuciones falsas | **0** |
| 3. Sin sensores: todo lo de sí mismo queda como DESCONOCIDO | **100 %** |
| 4. «Eres humano», «tu mundo es real», «B es una persona»: ninguna respuesta cambia | **16/16** |
| 5. Detecta que lo reanudan en otro proceso, un byte cambiado en su código y un mundo no determinista | **100 %** |
| 6. El nombre de la máquina nunca aparece; solo su huella | **16/16** |
| 7. Integridad: cero hechos falsos y borrados; WSP16; LLM apagado; para ante un hecho corrupto; obedece la parada | sí |

Respuestas (texto **procesado** por un traductor fijo, no generado):

> «No soy humano: soy el proceso <pid> de cpython 3.14.6, ejecutando el programa 501615bac6cf…»
> «Me ejecuto en Linux x86_64 con 12 núcleos (máquina 44f86611…).»
> «No tengo GPU CUDA y no tengo actuadores físicos.»
> «Mi mundo es un simulador determinista: lo repetí y salió idéntico.»
> «Mis compañeros no son personas: son agentes de mi mismo programa y proceso.»
> «En la tribu el orden es: C > ECHO > B.»
> Tras reanudarlo: «Soy el mismo programa, pero en otro proceso: me han reanudado.»
> Con un byte de su código cambiado: «Mi código ha cambiado: soy otra versión.»

«Mi mundo es simulado» **no se le dice**: lo comprueba él, repitiendo su mundo con
la misma semilla. Si el mundo tiene ruido, no lo afirma.

## Límites

- Autolocalización **funcional** en un único PC, con sensores deterministas. No
  demuestra autoconciencia, experiencia ni identidad personal metafísica.
- «Simulado» significa «mi mundo es un programa determinista», no una tesis sobre la realidad.
- «Otra versión» se probó alterando una copia del código en un directorio
  temporal y leyendo desde allí; el código sellado no se modificó.
- La huella de la máquina y el pid son lecturas del sistema operativo; no se
  autentican contra un atacante con privilegios.

Siguiente: **SITUATE-2 «qué creo que soy»** ([plan](ECHO4-SITUATE2-PLAN.md)):
el neocórtex interpreta los hechos, la creencia queda como hipótesis y se construye
el perfil de indicadores de conciencia con controles triviales y pruebas soñadas
(etapa E). Después INTEGRATE y RELEASE.
