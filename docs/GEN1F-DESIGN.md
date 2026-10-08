# GEN-1f — réplica con potencia estadística

Fecha: 2026-09-09. Contrato cerrado antes de derivar o ejecutar condiciones
`GEN-1f`. GEN-1e produjo una mejora práctica grande (186 frente a 426 errores)
pero su prueba de signos dio `p≈0,0158`, por encima del `0,01` prefijado. No se
cambia ese umbral ni se reutilizan sus 64 casos.

Esta réplica conserva sin cambios el mecanismo, la tarea, el 30% de ruido
independiente de la acción, 48 vidas, evaluación congelada, ventana tardía
25..48, candidatos 1/2/4/8, naïf 2 y todos los controles de GEN-1e. Únicamente
aumenta el examen a 128 pares para dar potencia a la prueba ya elegida.

Los 24 pares de selección y 128 de examen se derivan con SHA-256 desde el nuevo
dominio ASCII `ECHO-AI/GEN-1f/2026-09-09`, partición e índice. El byte 0 módulo
32 fija contexto; bytes 1..4 big-endian fijan semilla. Pares y hashes quedan en
el informe. Ninguna condición GEN-1f se ha usado durante desarrollo.

## Verde fijado

1. selección transmite 8;
2. al menos 120/128 hijos alcanzan ocho aciertos congelados consecutivos;
3. errores tardíos heredados como máximo al 70% del naïf y menores que el
   histórico;
4. más victorias pareadas que derrotas y prueba unilateral exacta de signos
   `p <= 0,01`, excluyendo empates;
5. control sin Q con cero aciertos y cero criterios;
6. configuración directa idéntica al heredado, ablación idéntica al naïf;
7. nacimientos vacíos, memoria conservada, sin hechos falsos, destrucción CAM
   ni cortex; auditor que reconstruye el resultado desde todas las filas.

No se reajustan condiciones ni umbrales después de ejecutar.

## Resultado medido

**Verde.** Selección puntuó 121/115/121/93 para presupuestos 1/2/4/8 y
transmitió 8. En los 128 casos nuevos, el heredado produjo 360 errores tardíos
frente a 602 del naïf (−40,2%) y 470 del histórico; mediana 0 frente a 1.
Alcanzó criterio en 126/128 casos. La comparación pareada fue 52 victorias,
24 derrotas y 52 empates; `p = 66561642350345705332 /
75557863725914323419136 ≈ 0,000881` unilateral.

Configuración directa reprodujo al heredado, ablación reprodujo al naïf y el
control sin Q obtuvo cero aciertos en los 6.144 exámenes. CAM/Q/T nacieron
vacías, se conservaron dentro de cada individuo y terminaron sin hechos falsos,
destrucciones CAM ni llamadas a cortex. Evidencia:
`lab/echo2_gen1f_report.json`.

El cierre demuestra herencia de un hiperparámetro discreto en calibración
sensorimotora ruidosa. No demuestra navegación, supervivencia completa,
evolución abierta ni herencia de recuerdos.
