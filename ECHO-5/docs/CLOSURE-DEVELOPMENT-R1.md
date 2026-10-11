# Desarrollo de cierre, primera medición

Medición del 10 de octubre de 2026, iniciada a las 20:29 de Madrid y terminada
a las 20:30:51. La auditoría independiente terminó a las 20:34:02 con
`valid: true`. Es desarrollo: no se abrieron las semillas de confirmación.
Fuentes, contratos, logs y resultados originales quedan en
`artifacts/closure-development-20261010-r1/`, con archivo de fuentes y
manifiestos de auditoría. Los cambios posteriores no sustituyen esos recibos.

La suite del código de esta medición completó 212 casos de test; 12 dependían
del perfil opcional y se comprobaron dentro de sus 32 pruebas MiniGrid.
Los recibos están en `artifacts/closure-checks-20261010-r2/`. Pasar la suite
no acredita superioridad científica ni certificación de robótica física.

| Dominio | Resultado de desarrollo | Lectura |
|---|---|---|
| Transferencia estructural | 7/8 casos soportados; abstención en los 4 controles | La muestra es pequeña y queda confirmación |
| Caché de prefijos | 17.190.112 frente a 34.281.796 unidades totales, mismo resultado de búsqueda | Ahorro cercano al 49,86 % en este banco |
| Profundidad y representación | Siete victorias y cero pérdidas frente a cada ablación | La búsqueda profunda consume más trabajo que los controles que no resuelven |
| Memoria adquirida | 18.060.854 unidades frente a 17.190.112 sin biblioteca y 15.579.417 con biblioteca fija | No supera todavía esos controles contando adquisición |
| Contraejemplos | 16/16 en los tres brazos | La tercera consulta llega después de identificar ya la regla |
| MiniGrid/BabyAI | Informativo 8/8; fijo 0/8; pasivo 2/8; sin memoria 5/8; sin planificación 3/8 | Mismos presupuestos y 40 episodios, con replay y auditoría |
| MissionAgent software | Correctitud, seguridad e integridad pasan; 3/12 misiones, empate con convencional | Sin ventaja propia ni evidencia nueva de vuelo simulado |

En contraejemplos, 11 de los 12 brazos identificaron la regla con una consulta;
el restante necesitó dos. Veintitrés de las 36 consultas fueron redundantes.
El selector adaptativo añadió 841 unidades netas, aproximadamente un 0,032 %
del trabajo total, y no mejoró la exactitud final. Esto justifica estudiar
la curva tras cada consulta para medir adquisición, conservando los resultados
finales por separado. La revisión del contrato se hará antes de confirmación,
manteniendo el historial del objetivo inicial que aquí no obtuvo ventaja.

La prueba de navegador descubrió dos problemas distintos. Una espera del
instrumento Playwright usaba evaluación textual bloqueada por CSP; se reemplazó
por comprobaciones de elementos. Después apareció una carrera de interfaz:
un botón de una sesión anterior podía seguir habilitado mientras se creaba la
nueva y su pulsación quedaba ignorada. La corrección deshabilita los controles
durante la solicitud. El Chromium instalado tampoco resolvía los alias genéricos
de fuente: `sans-serif` daba anchura de texto cero, mientras que `Noto Sans`
daba una anchura normal. Se añadió la familia local explícita. Estas
correcciones requieren una nueva comprobación de navegador y su recibo.

No hay cierre verde de ECHO-5 con esta medición. Faltan confirmación reservada,
validación completa de interfaz y campaña nueva Gazebo/PX4 con auditoría.
S6 sigue fuera del alcance.
