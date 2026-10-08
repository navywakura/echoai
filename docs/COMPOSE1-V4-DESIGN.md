# COMPOSE-1 v4 — tamaño muestral prospectivo, agente v3 intacto

Este es un protocolo nuevo, previo a sus datos. No amplía ni cambia el resultado
de v2/v3. Ambos rojos quedan conservados; sus confirmaciones permanecieron sin
abrir. El algoritmo y ejecutor son **los archivos congelados de compose1_v3**.
No se cambian neuronas, modelo, sensores, físico, PX4, umbrales, métricas ni N
de los bancos anteriores. No se evalúan candidatos nuevos ni se modifica la
política en respuesta a las semillas de v4.

## Motivo medido

V3 B: 64 parejas alcanzables, todas completadas por completo y horizonte uno.
Hay 22 ventajas, 10 desventajas y 32 empates en movimientos; ahorro total 100,
IC 97,5 % de la media [0,46875; 2,6875]. El test de signos exacto produce
p=0,025051229866221547, que **no** cumple p<0,025. Redondearlo no lo vuelve verde.

El resultado aporta una estimación de tamaño de efecto para planificar otro
examen: probabilidad de pareja informativa 0,5; probabilidad condicional de
ventaja 22/32. Bajo esos supuestos, integrando sobre el número aleatorio de
parejas informativas, la potencia del test de signos es:

| Semillas por etapa | Parejas alcanzables previstas | Potencia estimada |
|---:|---:|---:|
| 128 | 64 | 49,80 % |
| 256 | 128 | 83,76 % |
| 512 | 256 | 98,92 % |

Se fija **512** antes de abrir v4. Es potencia estimada para ese contraste y
alternativa observada, no garantía de éxito, potencia conjunta de las dos
puertas ni conclusión poblacional. No se aumenta N si v4 falla. No hay parada
anticipada por significación ni selección de episodios favorables.

## Particiones y criterios

- B funcional: **202623101–202623612**, 512 semillas ×6 modos =3.072 misiones.
- C funcional: **202624101–202624612**, otras 3.072 misiones.
- Alternancia fija: estática, cambio de abertura, cerrado, reserva insuficiente.
- Familia de 48 geometrías con muestreo con reemplazo: 1.024 semillas nuevas
  no significan 1.024 plantas diferentes. El alcance es esa familia finita.
- Mismos modelos, habilidades y 8/32 candidatos; profundidad 4 frente a 1,
  controles Q, convencional y sin caducidad. Parámetros congelados, mapa vacío
  al nacer cada misión, percepción activa, ninguna fuga del plano.
- **Todos los criterios de v3 se conservan:** seguridad funcional, ventaja
  frente a Q, IC 97,5 % con límite inferior positivo y test exacto p<0,025 en
  éxito o ahorro entre parejas exitosas, sin pérdida agregada de éxito. B y C
  deben pasar por separado. El contraste de coste publica su denominador.

Se preservan las ocho geometrías SITL declaradas antes de v2 y nunca evaluadas
en aceptación: B =202619301, 202619303, 202619304, 202619305; C =202619403,
202619404, 202619407, 202619408. Condiciones estática/estática/dinámica/reserva,
cuatro modos cada una: **32 vuelos**, sin reintentos. Completo ≥5/6 metas
alcanzables y más llegadas que Q; evidencia y ejecución válidas en todos los
vuelos; aborto en origen sin movimientos en los casos de reserva insuficiente.

## Reutilización comprobable

V4 importa directamente misión, consumidor, ejecutor, juez y métricas de v3.
El nuevo código sólo organiza muestras y congela su protocolo. Reutiliza por
hash los diez vuelos A y los 13 controles v3, porque la implementación es
idéntica; no los cuenta como vuelos nuevos. Reconstruye la escuela física y
el rojo B de v3, comprueba los inventarios previos, repite regresión y aislamiento
antes de congelar. El certificado vuelve a comprobar los controles y sus
mutaciones; una auditoría posterior arranca en otro proceso.

La escuela mantiene las mismas 56 consecuencias de A, sin heredar mapa. El
modelo aprendido no cambia. Los casos de aceptación reciben sólo observaciones
públicas y una hipótesis de coordenada objetivo. Un único WSP puede mandar;
las predicciones publicadas son auditables y no escriben experiencias imaginadas.

## Alcance físico conservado

Se conserva [el contrato físico de v2](COMPOSE1-V2-DESIGN.md) y
[el algoritmo v3](COMPOSE1-V3-DESIGN.md): X500/PX4, salas extruidas, vuelo a
2,5 m, marcador verde proporcionado, cuatro vistas de profundidad de la misma
familia y LiDAR. Disco libre exigido 900 mm para cuerpo de 400 mm; llegada
independiente ≤1 m; caducidad 250 ms también antes de ejecutar. Energía
abstracta, no julios. Pose verdadera sólo en el juez, nunca como odometría del
agente. Sin hardware, manipulación, recarga eléctrica ni LLM. No cierra
PX4-1, POWER-1, SAFE-1 ni TRANSFER-3; CAUSE-1 sigue después de COMPOSE-1.
