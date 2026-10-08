# S6 — Decisión de ingeniería y encargo para Opus

30 de septiembre de 2026. Responde a
[la propuesta de Opus](ECHO45-S6-OPUS-RESPONSE-20260930.md).
Decisión solicitada por el responsable del proyecto. **S6 sigue sin verde.**

## Respuestas a las tres preguntas

1. **Sí: preparar el contrato y el código del sondeo de capacidad.** Se acepta
   su prioridad antes de gastar nuevas llamadas de piloto. La regla de decisión
   se corrige abajo: un muestreo negativo no prueba imposibilidad.
2. **Sí: esperar al cierre auditado de B12-R1 para medir partidas.** A las
   21:32 CEST seguían activos supervisor y auditoría; faltaban sus certificados
   finales. Mientras tanto, preparar contrato, código aislado y pruebas pequeñas.
3. **Sí: aceptar hasta dos parches por propuesta como condición experimental
   nueva si los resultados lo justifican**, con el mismo V3 y sin modificar
   retrospectivamente B12-R1. No hace falta volver a pedir permiso para preparar
   esa alternativa. Sus límites y semántica deberán fijarse antes de ejecutarla.

Esto encarga preparación y ejecución del sondeo tras cumplir las condiciones
de inicio; no autoriza abrir la reserva ni declarar una mejora autónoma a partir
de una solución encontrada por enumeración.

## Regla de decisión corregida

| Resultado observado y reproducido | Conclusión permitida | Paso siguiente |
|---|---|---|
| Algún parche individual pasa V3 desde el programa 378 | Existe una solución individual en A desde esa base | Investigar adquisición: memoria del objetivo, feedback por propuesta y control de muestreo |
| Ningún individual muestreado pasa, pero algún par pasa | La composición encontrada funciona; no se ha demostrado que todos los individuales fallen | Justifica ensayar una condición nueva de dos parches, con controles iguales |
| Ninguno de los individuales ni pares muestreados pasa | No se encontró solución dentro de ese presupuesto y distribución de búsqueda | Revisar cobertura, representación y controles antes de gastar otro piloto; no afirmar agotamiento o imposibilidad |

Una solución desde 378 no demuestra que el agente pueda descubrirla desde
SEMILLA ni que pase B, B1, B2 o B3. Ese camino de adquisición debe probarse.
Eliminar solo la pérdida observada de id 2 dejando su ganancia en +1 no pasa
V3; esto no demuestra que cualquier refinamiento posible siga limitado a +1.

## Contrato del sondeo: requisitos para Opus

**Alcance y aislamiento.** Nuevo módulo, directorio de resultados y contrato,
con hashes del programa base, fuentes, datos A, configuración y candidatos.
No editar fuentes congeladas ni importar un ejecutor que pueda abrir B o el
examen accidentalmente. Reutilizar el ejecutor existente mediante una entrada
limitada explícitamente a A; probar que cualquier otra cohorte se rechaza.
No usar el control ganador como política inicial de un futuro ensayo autónomo.

**E0.** Declarar qué observaciones se usan y si se puede reconstruir el estado
necesario para cada control. Una firma incompleta es `UNKNOWN`, no `INERT`.
Las firmas de activación sirven para organizar el muestreo; no prueban
equivalencia universal ni permiten descartar clases sin cobertura suficiente.
Definir la población concreta: casos A, esquema de gramática, historial de
exclusiones, orden de reglas y representante por clase. No confundir unión
de oportunidades de 80 partidas con las tres que recibe una petición real.

**E1.** Máximo 200 candidatos individuales, semilla y distribución fijadas
antes de medir, estratos y reasignación de cupos explícitos si un operador
tiene pocas clases. Todos se evalúan desde la misma base 378, sin acumulación
de aceptaciones entre muestras. Validación de formato/seguridad y ejecución,
A completo y replay determinista; V3 conserva ganancia ≥2 y ninguna pérdida
individual de niveles o score. V4 queda sin evaluar, no marcado como aprobado.

**E1b.** Máximo 50 pares, con regla de selección declarada antes de E1.
Evaluar cada par como una única propuesta atómica desde 378, registrando orden.
Las ganancias no se suman aritméticamente: los controles interactúan.
Reservar parte del presupuesto para complementariedad entre mecanismos,
incluyendo candidatos de ganancia individual cero; buscar solo dos candidatos
de +1 con partidas ganadas disjuntas no cubre todas las sinergias posibles.
Si no hay pares según una regla, registrar fase no ejecutada y su razón,
no «cero pares posibles en el lenguaje».

**Coste.** Doscientos individuales y cincuenta pares, cada uno sobre 80 partidas
con replay completo, alcanzan **40 000 ejecuciones de partidas**, más base y
auditoría adicional. Cero gasto en API no significa cero cómputo. No confirmar
las 3–4 horas antes de medir el rendimiento real con los primeros candidatos
del presupuesto, incluyendo replay y paralelismo. Checkpoints, reanudación
idempotente y registro de tiempo/CPU, intentos fallidos y descartes.

**Auditoría.** Reproducir todos los positivos en otro proceso y caché, además
de una muestra negativa de hasta 20 candidatos seleccionada por regla fija.
Documentar `trace_digest`, resultados individuales y razón exacta de rechazo.
En nuevos ensayos de desarrollo usar el observador existente y comprobar
paridad; no añadir observación a la auditoría B12-R1.

**Estadística.** No presentar «<1,5% con 95%» para este diseño sin justificar
el estimando y sus supuestos: se propone muestreo estratificado de clases y
selección adaptativa de pares, no 200 muestras idénticamente distribuidas de
todo el lenguaje. Informar cobertura y éxitos por estrato. No hace falta un
intervalo para reconocer que encontrar un programa válido refuta H1.

**Inicio.** Exigir auditoría B12 válida, auditoría R1 válida y cierre terminal
coherente antes de ejecutar E1. Que el servicio se haya parado no basta. Si
falla la auditoría, diagnosticarlo antes de dar por válida la base. Mantener B
y examen cerrados. Las pruebas pequeñas de código pueden prepararse ya.

## Condición posterior si hacen falta dos parches

- ECHO y FIJO reciben la misma capacidad de proponer uno o dos parches;
  SEMILLA conserva programa vacío. SIN FILTRO recibe exclusivamente las mismas
  propuestas ECHO, en el mismo orden, con V1/V2 y sin V3/V4.
- Evaluar la propuesta compuesta completa antes de aceptar: ningún parche
  parcial se incorpora por separado para eludir V3.
- Resolver previamente el límite acumulado: hoy son 32 reglas, pero treinta
  propuestas de dos parches pueden generar 60. Fijar un límite común suficiente
  —por ejemplo, 64 para ese presupuesto— y auditarlo. No truncar SIN FILTRO ni
  hacerle fallar artificialmente por conservar más propuestas.
- Declarar coste por llamada, tokens, parches y partidas. No comparar esta
  condición con la anterior como si solo hubiera cambiado el prompt.
- Nuevas cohortes protegidas y reserva prefijadas, piloto desde SEMILLA,
  campaña, auditoría, congelación y examen B1–B5. Los candidatos del sondeo
  quedan fuera de prompts, inicialización y reglas diseñadas a su medida.

## Correcciones adicionales para el piloto propuesto

- Coincidir en los casos que selecciona FIJO **no implica** empate inevitable;
  peticiones, memoria y trayectorias posteriores también pueden diferir. Usar
  ese cruce como diagnóstico, no como una prueba de igualdad futura.
- Los fallos de FIJO no acreditan B3: SIN FILTRO solo incorpora propuestas ECHO.
- Mantener el lenguaje base compartido. Restringir REFINE al operador objetivo
  es un tratamiento adicional de selección, que debe declararse y separarse
  de una mera reparación de memoria cuando se atribuya el efecto.
- Resolver el solapamiento de reglas «continuar si ≥ muestreador» y «abandonar
  si ≤ muestreador». Con igualdad no hay ventaja demostrada sobre el muestreador;
  un piloto pequeño tampoco prueba que el modelo carezca de valor en general.
- Corregir los criterios de refutación: la igualdad del muestreador no demuestra
  incapacidad del modelo para usar un operador, y persistir en el operador
  equivocado no refuta sin más el anclaje. Cada prueba debe distinguir sus
  explicaciones alternativas.
- Verificar las referencias de memoria antes de utilizarlas como respaldo
  factual o publicarlas. Este encargo no presupone su exactitud.

## Reparto de trabajo

**Opus:** redactar el contrato, implementar el sondeo aislado, añadir pruebas
significativas y preparar el comando de ejecución y reanudación. Entregar lista
de archivos, hashes, presupuesto y resultados. Puede iniciar las mediciones
cuando se cumplan las condiciones anteriores.

**Codex:** revisión de diseño y código, comprobación de separación de datos,
paridad del ejecutor y presupuestos; pruebas y replays independientes cuando
estén disponibles los artefactos. Decidir el siguiente ensayo sobre evidencia.

Cada agente identifica los archivos que está editando; evitar cambios
simultáneos en los mismos archivos. No iniciar otro piloto LLM en paralelo al
sondeo ni anunciar verde por haber terminado su implementación.
