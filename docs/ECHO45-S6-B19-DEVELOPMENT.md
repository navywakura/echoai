# S6-B19 — diagnóstico del coste de reiniciar una intervención

5 de octubre de 2026. Desarrollo privado, posterior al rechazo válido de B18.
S6 permanece abierto. No se cambia ningún criterio de aceptación ni fuente
congelada de B18. Este documento no autoriza abrir el examen final.

La condición B18 obtiene 383 frente a 378 en A. En su bloque B gana tres
niveles, pero pierde score en v3/28027 y v3/28039. B18 queda cerrado con ese
resultado. Sus 40 casos B están consumidos: cualquier diagnóstico posterior
sobre ellos se etiqueta desarrollo retrospectivo, jamás confirmación ciega.

La inspección del código muestra que HOLD es una inhibición de teclas de
reinicio, no una espera inactiva. En H4, otra pulsación reemplaza la copia que
reproduce el camino. `pending_effect` registra `_tried_at`, que se borra ante
un incremento de `events`; ese incremento no certifica que el proceso haya
terminado. HOLD 0/1 elimina prácticamente la inhibición. Es una hipótesis
causal de las pérdidas; todavía falta aislarla mediante intervenciones.

Primera prueba declarada antes de ejecutar: conservar la guarda B18 y variar
únicamente HOLD entre 1, 2, 4, 8, 12, 16, 20, 24, 32 y 40, incluyendo la base
sin parche adicional. Cribado diagnóstico: A18, A42, A51, A53, A59, A68, A76,
A77 y los casos consumidos v3/28026, 28027, 28031, 28039. Son 132 ejecuciones
máximas, cuatro procesos, Python 3.12.13, 2000 decisiones por caso, cero LLM.
Se conservan resultados completos y diarios observables; no se escribe en
los artefactos originales. Se comparan niveles, score, decisiones, reinicios
y primera divergencia. Los datos de entorno privado solo pueden usarse para
explicar el mecanismo, nunca como entrada al actor o al selector.

Este cribado puede refutar que acortar menos HOLD resuelva la conservación.
No equivale a un piloto autónomo. Cualquier candidato posterior debe pasar
todo A y el desarrollo ampliado, replay exacto, auditoría independiente y un
bloque protegido nuevo congelado antes de medir. Una pérdida individual de
nivel o score sigue rechazándolo. No se garantiza una solución en esta
gramática ni se atribuye una reparación humana al LLM.
