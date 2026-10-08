# FLIGHT-1S v5 — GNSS: precisión declarada de posición y velocidad

Prerregistro anterior a cualquier vuelo v5. Una única configuración nueva;
sin barrido de ganancias ni repetición hasta acertar. La cadena v4 quedó
cerrada roja: interrumpida en 44/64 vuelos A, sin negativos, con su fallo de
recuperación conservado (`lab/echo3_flight1s_v4_report.json`). No autorizó banco.

## Causa que se prueba

En v4, `perturbed-eddc87870377f61b-r5` entró en radio 200 mm entre 4.399 y
6.726 s (2.327 s), salió hasta unos 263 mm y reentró a 8.503 s. El final de
124.563 mm no demuestra permanencia. No se extiende su ventana ni se modifica
su resultado. El nominal r8 de ese mundo alcanzó 256.294 mm; esto último es
diagnóstico v2, no el fallo de v4.

La fuente congelada PX4 demuestra otra incoherencia además de `eph`:

```
SensorGpsSim.cpp:
  posición angular += generate_wgn() * 0.2 / radio_tierra
  velocidad += noiseGauss3f(0.06, 0.077, 0.158)
  eph = 0.9; s_variance_m_s = 0.4
SensorGpsSim.hpp:
  noiseGauss3f(stdx,stdy,stdz): Gaussianas multiplicadas por esos std
SensorGps.msg:
  s_variance_m_s: speed accuracy estimate (metres/sec)
EKF/gps_control.cpp:
  vel_var = square(max(sacc, gps_vel_noise))
  varianza vertical = vel_var * square(1.5)
```

Hipótesis: declarar conservadoramente la precisión disponible de velocidad
permitirá aprovecharla para limitar deriva; corregir sólo posición, como
`gpsfix_7n`, dejó sin corregir ese canal. No se afirma que sea la única causa
ni que vaya a pasar. La conversión angular de longitud hace que los 0.2 m
sean una cota conservadora horizontal, no sigma idéntica en ambos ejes.

## Intervención fija

Nueva imagen derivada de stock, etiqueta `v1.15.4-gpsaccuracy`:

- `eph`: 0.9 → 0.2 m.
- `s_variance_m_s`: 0.4 → 0.158 m/s, máximo de las tres sigmas inyectadas.
- Ruido inyectado, timestamps, frecuencia, `epv`, modelo, sensores y masas
  intactos. No se introduce una nueva ayuda de posición ni groundtruth al EKF.
- PX4: GPS_DELAY=0; GPS_P_NOISE=0.2; GPS_V_NOISE=0.158; P=3, D=0.4, I=0.
  El suelo del filtro no puede volver a ocultar la precisión declarada.
- NOAID_NOISE vuelve al stock. Dosis: 7 N / 600 ms.

El binario es distinto: se publican imagen por ID, parche de dos líneas,
hashes de fuente antes/después, comprobación de ruido intacto y SHA del
binario compilado. El commit de base por sí solo no identifica esta variante.

## Banco y aceptación

Se hereda íntegramente el contrato de aceptación v4: radio 200 mm, permanencia
3 s, ventana 10 s, desafío perturbado >250 mm, impulso 500–1500 ppk, envolvente
1000 mm, mismos controles, seguridad, repetición y contraste por mundo.
Sigue sin certificar precisión nominal máxima ≤250 mm en cada vuelo.

A: 64 vuelos nuevos + 4 controles negativos; sólo un A verde auditado abre
los 48 vuelos de doce mundos rehearsal + 3 mutantes físicos. Orden 20260923
y 20260924. Dos contenedores; no reintentos; se ejecuta cada denominador
completo aunque haya fallo. Un candidato, una cadena; no seleccionar corridas.
El compilado se realiza después de terminar v4 para no cargar su host durante
los vuelos. Nuevos locks antes de A; código, parámetros y criterios congelados.

V1–v4 permanecen intactos. Las versiones usan namespaces hermanos para no
cambiar inventarios históricos. La aritmética física, el contraste v4 y los
componentes de SIM-3 se importan. El coordinador se versiona porque los hashes
anteriores prohíben editarlo. Ningún cambio en Q/T/CAM/WSP ni en kernel.

Un resultado verde significaría estabilidad SITL bajo esta configuración
corregida; no autonomía echoAI, hardware real ni una demostración sim-to-real.
