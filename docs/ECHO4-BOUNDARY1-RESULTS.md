# E4-BOUNDARY-1 — cierre en influencia causal observable

2026-09-21. **Verde en el protocolo virtual de intervenciones emparejadas.**
No cierra ECHO-4 completo, SELF, mantenimiento, pertenencia corporal ni
conciencia. [Contrato prospectivo v1](ECHO4-BOUNDARY1-DESIGN.md).

## Qué está implementado

- `echo4/boundary.py`: mapa entero acotado que compara cambios de U/B
  frente a una referencia de espera. Ocho pares por contexto/acción;
  replicación de signo, desconocido ante contradicción o evidencia insuficiente.
- `echo4/boundary_agent.py`: conexión opt-in al Agent/SENSATION original,
  compartiendo CAM/T y conservando Q/gate. `observe_intervention(pair)` ingiere
  evidencia experimental; `influence_estimate(packet, action)` consulta el mapa.
  Los turnos ordinarios no se convierten automáticamente en pruebas causales
  y la política todavía no consume la estimación para recuperarse.
- `echo4/boundary_world.py`: ejecutor y juez privados. Reutiliza la transición
  original de WORLD-1; añade desacoplamiento experimental de canales, calor
  común y retardo. No cambia la física histórica ni entrega estado exacto al consumidor.
- `echo4/boundary_bench.py`: identificación, examen congelado, ablación,
  trazas completas, hashes y reproducción desde cero. CLI propio para no
  invalidar el certificado SENSATION.

Salida: tres máscaras de 16 bits, influencia / sin efecto observable /
desconocido, más signos y primer tick con efecto replicado. Solo U y B
son elegibles; los otros 14 bytes permanecen desconocidos. No es un mapa
de «qué parte del universo soy yo». El error de SENSATION se registra,
pero no se usa como prueba de una causa externa.

## Resultados

Los aciertos siguientes exigen las tres máscaras completas correctas;
signos y retardos también coinciden en todas las evaluaciones.

| Medida | Desarrollo | B | C |
|---|---:|---:|---:|
| Bloques por familia | 2 | 16 | 16 |
| Pares de identificación | 352 | 2.816 | 2.816 |
| Evaluaciones correctas | 176/176 | 1.408/1.408 | 1.408/1.408 |
| Coincidencia temporal, aciertos | 70/176 | 778/1.408 | 765/1.408 |
| Ventaja en puntos porcentuales | 60,23 | 44,74 | 45,67 |
| Influencias falsas | 0 | 0 | 0 |
| Abstenciones correctas en inválidos | 64/64 | 512/512 | 512/512 |
| Retardo nominal/retrasado correcto | 32/32 | 256/256 | 256/256 |
| Bloques con congelación exacta | 22/22 | 176/176 | 176/176 |
| Ablación sin restauración: desconocido | 176/176 | 1.408/1.408 | 1.408/1.408 |

Cada una de las once familias obtiene **128/128** en B y en C: completo,
solo H, solo temperatura, solo externo, propio más externo, retrasado,
veto, ejecución sin recibo, no emparejado, captura caducada y subbanda.
En cada etapa hay 640 evaluaciones con influencia en al menos un canal,
256 sin efecto observable y 512 desconocidos esperados. Ningún desconocido
se elimina del denominador.

La ventaja sobre coincidencia incluye la abstención correcta. Restringiendo
el diagnóstico a los 896 ensayos válidos de cada etapa, el mapa obtiene
896/896 frente a 778/896 en B y 765/896 en C. No se compara contra el mejor
estimador causal convencional ni se afirma novedad científica por ganarle
a este control deliberadamente simple.

## Invariantes, memoria y comprobación

WSP permanece en 16 bytes, cómputo rápido entero, sin LLM, hardware ni
segundo bus. Cero hechos escritos por el estimador y cero slots destruidos.
La prueba nativa confirma CAM/T compartidas, SENSATION conectado y cero
hechos falsos/llamadas corticales. Sus pulsos son experimentales, no una
política de mantenimiento aprendida. Usa instancias restauradas nuevas:
no fuerza `respawn()` sobre un cuerpo vivo.

Mapa: máximo 128 filas y 4.096 pares ingeridos, 1.536 contadores de signo
como máximo; no retiene una lista creciente de ensayos. En campaña: máximo
dos filas y 16 pares aceptados por instancia, CAM de hasta nueve slots
en desarrollo y ocho en B/C. Son límites estructurales del modelo host,
no una medida de RSS ni una afirmación de empaquetado C/Heap-0.

**34 pruebas nuevas; 179 con las regresiones seleccionadas, todas pasan.**
Cubren contraste calculado independientemente, signo, umbral, conflicto,
retardo, cuantización, veto real, 26 entradas inválidas sin mutación,
repetición de IDs, capacidad, congelación y orden predicción→física.
El auditor rechaza informe, recibo/traza y manifiesto de fuentes alterados,
datos finales añadidos y archivos ausentes. Una B fallida no abre C.

La auditoría completa en un **proceso nuevo** devuelve `valid=true`,
`closure_eligible=true`, sin hallazgos, y reproduce:

```text
48789bd52dd733f4f278c09160894d5869530ad0ecfeebe21735ab06e43641f6
```

Se conserva y vuelve a verificar el certificado SENSATION:
`96f2deaeefdc40a38d45710dc732106f68295d7a81553bef4b6e554a8f8d1b88`.
No se han modificado sus fuentes selladas ni las del núcleo histórico.

## Qué demuestra y qué no

Demuestra identificación de **influencia observable** después de recibir
ensayos comparables. El calor externo puede ser perfectamente predecible
y no ser efecto de la acción; un veto no es un actuador sin efecto.
La variante subbanda contiene cambios físicos que no cruzan bandas:
«sin efecto observable» no significa ausencia física de control.

La restauración exacta y la igualdad de perturbaciones son garantías del
ejecutor, comprobadas mediante replay del simulador. El recibo público es
procedencia confiada, no autenticación criptográfica. WSP idénticos solos
no justifican el contraste. Fuera de esa garantía no se aplica este cierre.

El retardo publicado es el primer efecto **visible y replicado** desde la
orden, no el tiempo exacto del actuador. Por ejemplo, en desarrollo la carga
afecta físicamente a la temperatura en t=1, pero el contraste de su banda
puede aparecer en t=2. La ventana no distingue efectos posteriores a dos ticks.

Cada bloque identifica de nuevo una condición estacionaria; no hay
generalización entre acoplamientos desconocidos. Los puntos iniciales están
elegidos cerca de límites perceptivos, no representan todos los cuerpos.
Las semillas son públicas y el smoke de tests reproduce un bloque por etapa;
**no es un examen ciego bajo custodia ni una prueba estadística independiente**.
El 100% corresponde al banco explícito, no a causalidad universal.

Faltan atribución cuerpo/entorno, experimentación autónoma y recuperación
conductual: corresponden a **E4-SELF-1**, siguiente fase. BOUNDARY no demuestra
experiencia subjetiva, alma, identidad personal ni control de una contraparte.

## Evidencia y reproducción

8.976 pares con traza en desarrollo/B/C, incluidos los inválidos; 2.992
son evaluaciones congeladas. Evidencia local, aproximadamente 14,2 MB:

- [Informe](../lab/echo4/boundary1-v1/report.json).
- [Recibo de auditoría](../lab/echo4/boundary1-v1/audit-receipt.json).
- [Desarrollo](../lab/echo4/boundary1-v1/development.jsonl),
  [B](../lab/echo4/boundary1-v1/B.jsonl), [C](../lab/echo4/boundary1-v1/C.jsonl).

Desde `echoai/`, sin dependencias nuevas:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.. python3 -m unittest echoai.tests.test_echo4_boundary1 -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.. python3 -m echoai.echo4.boundary_bench verify lab/echo4/boundary1-v1
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.. python3 -m echoai.echo4 sensation-verify lab/echo4/sensation1-predictor-v1
```

Para una nueva copia reproducida, elegir un directorio que no exista:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.. python3 -m echoai.echo4.boundary_bench campaign /tmp/echo4-boundary1-reproduction
```

No sobrescribe evidencia. `--quick` es smoke y nunca autoriza cierre.
Documentación y resultados actualizados localmente; no publicados ni enviados
a Git/Vercel en esta fase.
