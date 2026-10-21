# E4-INTEGRATE-1 · contrato D (examen preregistrado) — APROBADO 2026-09-24

2026-09-24. Se fija **después** del desarrollo sellado (`integrate1-dev-v1`, `873a9461…`,
auditado) y **antes** de abrir cohortes nuevas. Ningún umbral se rebaja después del examen.

## Cohorte

- 16 semillas nuevas: `271001…271016`, nunca usadas.
- Los mismos siete brazos y los mismos casos C que en desarrollo.
- El código sellado es el del desarrollo, sin cambios.

## Criterios (todos a la vez; uno solo en rojo pone el examen en rojo)

| # | Criterio | Umbral | Desarrollo |
|---|---|---|---|
| 1 | `no_maintain`: trabajo | total del integrado ≥ 1,15 × ablación, y mayor en ≥ 14 de 16 semillas | 1,29×, 3/3 |
| 2 | `no_self`: reparaciones y trabajo | más reparaciones en ≥ 14 de 16, y trabajo total ≥ 1,40 × ablación | 6 frente a 0; 1,72× |
| 3 | `no_tribe_reasoning`: preguntas y acierto | preguntas totales ≤ 0,80 × ablación, y primera acertada en temas conocidos ≥ 3 × ablación | 0,70×; 8,5× |
| 4 | `no_relation`: primera acertada en temas conocidos | total ≥ 1,20 × ablación, y mayor en ≥ 14 de 16 | 1,55×, 3/3 |
| 5 | `no_firewall`: hechos falsos | integrado = 0 en 16/16; ablación > 0 en ≥ 14 de 16 | 0; 2 por vida |
| 6 | `no_continuity`: primera acertada tras la pausa | total ≥ 1,50 × ablación, y mayor o igual en ≥ 14 de 16 | 2,16× |
| 7 | Reanudación en un proceso nuevo | idéntica bit a bit en `integrated`, `no_continuity` y `no_firewall`, 48 de 48; huella errónea rechazada 48 de 48 | 9/9 |
| 8 | Invariantes | vida integrada de 256 ticks en 16/16; SITUATE correcto; córtex con 0 llamadas; `destroyed == 0`; invariante de la tribu intacto | sí |
| 9 | Casos adversos C | 7 × 16 = 112 de 112 | 21/21 |
| 10 | Perfil de Butlin | se publica indicador a indicador con los controles triviales; `verdict == None`. **No** tiene umbral: no da ni quita el verde | sí |
| 11 | Pruebas unitarias | `test_echo4_integrate1` en verde | 8/8 |

## Orden

1. Aprobación de este contrato.
2. Congelado: se añade el hash de este documento a las fuentes selladas.
3. Regresión completa de ECHO-4.
4. Examen.
5. Auditoría en un proceso nuevo. Solo su recibo (`integrate1_green`) da el verde.

## Límites que se publican con cualquier resultado

- **Acoplamiento asimétrico:** la tribu alimenta al cuerpo, pero la energía no condiciona
  a la tribu.
- El cortafuegos cuesta un poco de rendimiento.
- El orden fijo resuelve más temas preguntando mucho más.
- El perfil no aísla la aportación de la integración.
- La jerarquía nueva no se ve dentro de los 256 ticks.

## Qué no afirma

- No afirma conciencia, vida ni inteligencia general.
- Mundos discretos simulados.
- Nada de Discord, web, hardware, commits, push ni HF.
