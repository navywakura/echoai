"""
NEXUS-0 lexical WSP layer — host port of `kernel/navi/wsp_lex.c`.

First-match-wins over the n-gram table, kept in C table order (longer /
more specific keys first). Keys and input are folded like
`echoai.core.spoke.fold_bytes`, so the Latin-1 stems in the C table ("sueñas")
can reach folded ASCII text.

The kernel file is untouched: this is its host twin. If the two disagree,
`kernel/navi/wsp_lex.c` is the original. No FPU, no hash: a miss here is a
miss, and the caller says DESCONOCIDO.
"""

from __future__ import annotations

from typing import NamedTuple, Optional, Tuple

from echoai.core.spoke import fold_bytes
from echoai.core.wsp import E_NAMES, pack

from echoai.nexus0.constants import WSP_BYTES

# wsp.h enum, verbatim order. 0..31 SPEC primitives, 32..43 derived.
(SER, NO_SER, YO, OTRO,
 AQUI, ALLI, DENTRO, FUERA,
 AHORA, ANTES, DESPUES,
 UNIR, SEPARAR, CAMBIAR, OBSERVAR,
 PREGUNTAR, RESPONDER, DESEAR, TEMER,
 RECORDAR, OLVIDAR, CREAR, DESTRUIR,
 SUBIR, BAJAR, ABRIR, CERRAR,
 CAUSA, EFECTO, POSIBLE, IMPOSIBLE, DESCONOCIDO) = range(32)
(AMOR, SOLEDAD, COMUNICAR, CONEXION,
 PELIGRO, BIENVENIDA, CONCIENCIA, WIRED) = range(32, 40)
(NONE, UNK, HELP, PAD) = range(40, 44)

(DOM_GENERAL, DOM_CODIGO, DOM_NOTICIAS, DOM_POESIA,
 DOM_LOGICA, DOM_RED, DOM_CIENCIA) = range(7)
(GEN_TALK, GEN_LOGIC, GEN_POETIC, GEN_NEWS, GEN_CODE, GEN_RXOS,
 GEN_REASON, GEN_MATH, GEN_DEBUG, GEN_PLAN, GEN_TEACH) = range(11)


class Rule(NamedTuple):
    key: str
    src: int
    rel: int
    dst: int
    time: int
    E: Tuple[int, int, int, int, int, int]
    dom: int
    gen: int
    style: int


def L(key: str, src: int, rel: int, dst: int, tm: int,
      v: int, a: int, d: int, c: int, u: int, b: int,
      dom: int, gen: int, st: int) -> Rule:
    """Host mirror of the C L() macro."""
    return Rule(key, src, rel, dst, tm, (v, a, d, c, u, b), dom, gen, st)


# --- BEGIN GENERATED TABLE — tools/gen_lex.py, from kernel/navi/wsp_lex.c ---
LEX: Tuple[Rule, ...] = (

    # --- EchOS operator (before generic talk) ---
    L("demuestra monad", YO, OBSERVAR, CONCIENCIA, AHORA, 10,30,20,90,40,0, DOM_CIENCIA, GEN_RXOS, 2),
    L("demuestra", YO, OBSERVAR, CONCIENCIA, AHORA, 10,30,20,90,40,0, DOM_CIENCIA, GEN_RXOS, 2),
    L("como funciona este sistema operativo", YO, PREGUNTAR, CONCIENCIA, AHORA, 10,20,20,80,20,10, DOM_CIENCIA, GEN_RXOS, 10),
    L("como funciona este so", YO, PREGUNTAR, CONCIENCIA, AHORA, 10,20,20,80,20,10, DOM_CIENCIA, GEN_RXOS, 10),
    L("como funciona este sistema", YO, PREGUNTAR, CONCIENCIA, AHORA, 10,20,20,80,20,10, DOM_CIENCIA, GEN_RXOS, 10),
    L("quien te creo", YO, PREGUNTAR, OTRO, AHORA, 10,20,10,70,20,20, DOM_GENERAL, GEN_RXOS, 9),
    L("quien te creo", YO, PREGUNTAR, OTRO, AHORA, 10,20,10,70,20,20, DOM_GENERAL, GEN_RXOS, 9),
    L("muestra la red", YO, OBSERVAR, WIRED, AHORA, 0,30,10,70,30,0, DOM_RED, GEN_RXOS, 3),
    L("estas gastando", YO, OBSERVAR, AQUI, AHORA, 0,20,10,70,20,0, DOM_CIENCIA, GEN_RXOS, 0),
    L("nics", YO, OBSERVAR, WIRED, AHORA, 0,20,10,80,20,0, DOM_RED, GEN_RXOS, 3),
    L("navi bench", YO, OBSERVAR, CONCIENCIA, AHORA, 10,30,20,90,30,0, DOM_CIENCIA, GEN_RXOS, 2),
    L("devices", YO, OBSERVAR, AQUI, AHORA, 0,10,10,80,10,0, DOM_CIENCIA, GEN_RXOS, 5),
    L("uptime", YO, OBSERVAR, AHORA, AHORA, 0,10,0,80,10,0, DOM_CIENCIA, GEN_RXOS, 4),
    L("status", YO, OBSERVAR, AQUI, AHORA, 0,20,10,80,20,0, DOM_CIENCIA, GEN_RXOS, 0),
    L("memoria libre", YO, OBSERVAR, AQUI, AHORA, 0,10,10,80,10,0, DOM_CIENCIA, GEN_RXOS, 1),
    L("cmd mem", YO, OBSERVAR, AQUI, AHORA, 0,10,10,80,10,0, DOM_CIENCIA, GEN_RXOS, 1),

    # --- NAVI 6.5 RLC masks ---
    L("cuanto es", YO, OBSERVAR, EFECTO, AHORA, 0,20,40,100,20,0, DOM_LOGICA, GEN_MATH, 0),
    L("calcula", YO, OBSERVAR, EFECTO, AHORA, 0,20,40,100,20,0, DOM_LOGICA, GEN_MATH, 0),
    L("razona", YO, OBSERVAR, CAUSA, AHORA, 0,20,40,90,20,0, DOM_CIENCIA, GEN_REASON, 0),
    L("piensa", YO, OBSERVAR, CAUSA, AHORA, 0,20,30,80,20,0, DOM_CIENCIA, GEN_REASON, 0),
    L("por que", YO, PREGUNTAR, CAUSA, AHORA, 0,20,40,90,30,0, DOM_CIENCIA, GEN_REASON, 0),
    L("que pasaria", YO, PREGUNTAR, POSIBLE, AHORA, 0,30,40,90,40,0, DOM_CIENCIA, GEN_REASON, 0),
    L("diagnostica", YO, OBSERVAR, EFECTO, AHORA, 0,30,40,90,40,0, DOM_CIENCIA, GEN_DEBUG, 0),
    L("debug", YO, OBSERVAR, EFECTO, AHORA, 0,30,40,90,30,0, DOM_CODIGO, GEN_DEBUG, 0),
    L("pasos para", YO, CREAR, DESPUES, AHORA, 10,20,30,80,20,0, DOM_CIENCIA, GEN_PLAN, 0),
    L("un plan", YO, CREAR, DESPUES, AHORA, 10,20,30,80,20,0, DOM_CIENCIA, GEN_PLAN, 0),
    L("ensena", YO, RESPONDER, OTRO, AHORA, 20,20,20,80,20,20, DOM_CIENCIA, GEN_TEACH, 0),
    L("como si tuviera", YO, RESPONDER, OTRO, AHORA, 20,20,10,70,20,20, DOM_CIENCIA, GEN_TEACH, 0),

    # --- news ---
    L("que noticias hay hoy", YO, OBSERVAR, ALLI, AHORA, 0,30,0,50,70,0, DOM_NOTICIAS, GEN_NEWS, 0),
    L("noticias de hoy", YO, OBSERVAR, ALLI, AHORA, 0,30,0,50,70,0, DOM_NOTICIAS, GEN_NEWS, 0),
    L("titulares", YO, OBSERVAR, ALLI, AHORA, 0,25,0,50,60,0, DOM_NOTICIAS, GEN_NEWS, 0),
    L("noticias", YO, OBSERVAR, ALLI, AHORA, 0,30,0,50,70,0, DOM_NOTICIAS, GEN_NEWS, 0),
    L("noticia", YO, OBSERVAR, ALLI, AHORA, 0,30,0,50,70,0, DOM_NOTICIAS, GEN_NEWS, 0),
    L("que hay hoy", YO, OBSERVAR, ALLI, AHORA, 0,20,0,40,50,0, DOM_NOTICIAS, GEN_NEWS, 0),
    L("rss", YO, OBSERVAR, WIRED, AHORA, 0,20,0,60,40,0, DOM_NOTICIAS, GEN_NEWS, 0),
    L("periodico", YO, OBSERVAR, ALLI, AHORA, 0,20,0,50,40,0, DOM_NOTICIAS, GEN_NEWS, 0),
    L("mundo hoy", YO, OBSERVAR, ALLI, AHORA, 0,30,0,50,70,0, DOM_NOTICIAS, GEN_NEWS, 0),
    L("ultima hora", YO, OBSERVAR, ALLI, AHORA, 0,50,0,40,90,0, DOM_NOTICIAS, GEN_NEWS, 0),

    # --- poetry ---
    L("escribe un poema", YO, CREAR, SOLEDAD, AHORA, -70,20,10,70,80,-30, DOM_POESIA, GEN_POETIC, 0),
    L("poema sobre el vacio", YO, CREAR, SOLEDAD, AHORA, -80,20,10,70,90,-40, DOM_POESIA, GEN_POETIC, 0),
    L("poema de amor", YO, CREAR, AMOR, AHORA, 50,40,10,70,40,80, DOM_POESIA, GEN_POETIC, 2),
    L("haiku", YO, CREAR, SOLEDAD, AHORA, -40,10,0,80,50,-20, DOM_POESIA, GEN_POETIC, 1),
    L("poema", YO, CREAR, SOLEDAD, AHORA, -60,20,10,70,80,-30, DOM_POESIA, GEN_POETIC, 0),
    L("poesia", YO, CREAR, SOLEDAD, AHORA, -60,20,10,70,80,-30, DOM_POESIA, GEN_POETIC, 0),
    L("verso", YO, CREAR, SOLEDAD, AHORA, -50,15,0,70,60,-20, DOM_POESIA, GEN_POETIC, 0),
    L("rima", YO, CREAR, AMOR, AHORA, 20,30,0,60,40,30, DOM_POESIA, GEN_POETIC, 2),
    L("oda", YO, CREAR, AMOR, AHORA, 40,40,20,70,50,40, DOM_POESIA, GEN_POETIC, 2),
    L("lira", YO, CREAR, SOLEDAD, AHORA, -20,20,0,60,40,10, DOM_POESIA, GEN_POETIC, 0),
    L("vacio", YO, OBSERVAR, SOLEDAD, AHORA, -80,10,0,70,70,-50, DOM_POESIA, GEN_POETIC, 0),
    L("cosmos", YO, OBSERVAR, FUERA, AHORA, -20,30,0,60,50,10, DOM_POESIA, GEN_POETIC, 0),
    L("estrellas", YO, OBSERVAR, FUERA, ANTES, 10,20,0,60,30,20, DOM_POESIA, GEN_POETIC, 0),
    L("ocaso", YO, OBSERVAR, ANTES, ANTES, -30,10,0,60,20,10, DOM_POESIA, GEN_POETIC, 0),
    L("abismo", YO, OBSERVAR, SOLEDAD, AHORA, -90,40,0,70,80,-40, DOM_POESIA, GEN_POETIC, 0),
    L("luna", YO, OBSERVAR, AMOR, ANTES, 20,15,0,60,20,40, DOM_POESIA, GEN_POETIC, 2),
    L("noche oscura", YO, OBSERVAR, SOLEDAD, ANTES, -50,20,0,60,40,-20, DOM_POESIA, GEN_POETIC, 0),

    # --- logic ---
    L("si a es mayor que b y b es mayor que c", YO, OBSERVAR, EFECTO, AHORA, 0,20,50,100,30,0, DOM_LOGICA, GEN_LOGIC, 0),
    L("mayor que", YO, OBSERVAR, EFECTO, AHORA, 0,20,50,100,30,0, DOM_LOGICA, GEN_LOGIC, 0),
    L("menor que", YO, OBSERVAR, EFECTO, AHORA, 0,20,50,100,30,0, DOM_LOGICA, GEN_LOGIC, 1),
    L("si a es mayor", YO, OBSERVAR, EFECTO, AHORA, 0,20,50,100,30,0, DOM_LOGICA, GEN_LOGIC, 0),
    L("relacion hay", YO, PREGUNTAR, EFECTO, AHORA, 0,20,40,90,30,0, DOM_LOGICA, GEN_LOGIC, 0),
    L("transitiv", YO, OBSERVAR, EFECTO, AHORA, 0,10,50,100,20,0, DOM_LOGICA, GEN_LOGIC, 0),
    L("silogismo", YO, OBSERVAR, CAUSA, AHORA, 0,20,50,90,20,0, DOM_LOGICA, GEN_LOGIC, 2),
    L("modus ponens", YO, OBSERVAR, CAUSA, AHORA, 0,20,50,100,20,0, DOM_LOGICA, GEN_LOGIC, 2),
    L("implica", YO, OBSERVAR, CAUSA, AHORA, 0,20,50,90,20,0, DOM_LOGICA, GEN_LOGIC, 2),
    L("entonces q", YO, OBSERVAR, EFECTO, AHORA, 0,20,50,90,20,0, DOM_LOGICA, GEN_LOGIC, 2),
    L("contradic", YO, SEPARAR, IMPOSIBLE, AHORA, -20,40,40,90,50,0, DOM_LOGICA, GEN_LOGIC, 3),
    L("si p y no p", YO, SEPARAR, IMPOSIBLE, AHORA, -20,40,40,90,50,0, DOM_LOGICA, GEN_LOGIC, 3),
    L("logica", YO, OBSERVAR, EFECTO, AHORA, 0,10,40,80,20,0, DOM_LOGICA, GEN_LOGIC, 0),
    L("por tanto", YO, OBSERVAR, EFECTO, AHORA, 0,10,40,80,20,0, DOM_LOGICA, GEN_LOGIC, 2),
    L("si y solo si", YO, UNIR, CAUSA, AHORA, 0,10,50,100,20,0, DOM_LOGICA, GEN_LOGIC, 4),
    L("and logico", YO, UNIR, CAUSA, AHORA, 0,10,40,90,10,0, DOM_LOGICA, GEN_LOGIC, 5),
    L("or logico", YO, UNIR, POSIBLE, AHORA, 0,10,40,90,10,0, DOM_LOGICA, GEN_LOGIC, 6),
    L("not logico", YO, SEPARAR, NO_SER, AHORA, 0,10,40,90,10,0, DOM_LOGICA, GEN_LOGIC, 7),
    L("igual a", YO, UNIR, SER, AHORA, 0,10,30,90,10,0, DOM_LOGICA, GEN_LOGIC, 8),
    L("distinto", YO, SEPARAR, NO_SER, AHORA, 0,10,30,90,10,0, DOM_LOGICA, GEN_LOGIC, 9),

    # --- code ---
    L("invertir un array", YO, CREAR, CAMBIAR, AHORA, 20,30,40,100,20,0, DOM_CODIGO, GEN_CODE, 0),
    L("invertir array", YO, CREAR, CAMBIAR, AHORA, 20,30,40,100,20,0, DOM_CODIGO, GEN_CODE, 0),
    L("escribe una funcion", YO, CREAR, CAMBIAR, AHORA, 20,30,40,100,20,0, DOM_CODIGO, GEN_CODE, 0),
    L("funcion en c", YO, CREAR, CAMBIAR, AHORA, 20,30,40,100,20,0, DOM_CODIGO, GEN_CODE, 0),
    L("array reverse", YO, CREAR, CAMBIAR, AHORA, 20,30,40,100,20,0, DOM_CODIGO, GEN_CODE, 0),
    L("clamp", YO, CREAR, CAMBIAR, AHORA, 10,20,30,100,10,0, DOM_CODIGO, GEN_CODE, 1),
    L("lif decay", YO, CREAR, CAMBIAR, AHORA, 10,20,30,100,10,0, DOM_CODIGO, GEN_CODE, 2),
    L("decay", YO, CREAR, CAMBIAR, AHORA, 10,20,30,100,10,0, DOM_CODIGO, GEN_CODE, 2),
    L("fuga", YO, CREAR, CAMBIAR, AHORA, 10,20,30,100,10,0, DOM_CODIGO, GEN_CODE, 2),
    L("strlen", YO, CREAR, OBSERVAR, AHORA, 10,20,20,100,10,0, DOM_CODIGO, GEN_CODE, 4),
    L("longitud", YO, CREAR, OBSERVAR, AHORA, 10,20,20,100,10,0, DOM_CODIGO, GEN_CODE, 4),
    L("swap", YO, CREAR, CAMBIAR, AHORA, 10,20,20,100,10,0, DOM_CODIGO, GEN_CODE, 5),
    L("intercamb", YO, CREAR, CAMBIAR, AHORA, 10,20,20,100,10,0, DOM_CODIGO, GEN_CODE, 5),
    L("q16", YO, CREAR, CAMBIAR, AHORA, 10,20,30,100,10,0, DOM_CODIGO, GEN_CODE, 8),
    L("anillo", YO, CREAR, CAMBIAR, AHORA, 10,20,20,100,10,0, DOM_CODIGO, GEN_CODE, 9),
    L("ring", YO, CREAR, CAMBIAR, AHORA, 10,20,20,100,10,0, DOM_CODIGO, GEN_CODE, 9),
    L("distancia l1", YO, CREAR, OBSERVAR, AHORA, 10,20,20,100,10,0, DOM_CODIGO, GEN_CODE, 11),
    L("lcg", YO, CREAR, CAMBIAR, AHORA, 10,20,20,100,10,0, DOM_CODIGO, GEN_CODE, 12),
    L("spike", YO, CREAR, CAMBIAR, AHORA, 10,30,20,100,20,0, DOM_CODIGO, GEN_CODE, 14),
    L("hex", YO, CREAR, OBSERVAR, AHORA, 10,10,10,100,10,0, DOM_CODIGO, GEN_CODE, 15),
    L("codigo", YO, CREAR, CAMBIAR, AHORA, 20,30,40,90,20,0, DOM_CODIGO, GEN_CODE, 0),
    L("funcion", YO, CREAR, CAMBIAR, AHORA, 20,30,40,90,20,0, DOM_CODIGO, GEN_CODE, 0),
    L("en c", YO, CREAR, CAMBIAR, AHORA, 20,30,40,90,20,0, DOM_CODIGO, GEN_CODE, 0),
    L("array", YO, CREAR, CAMBIAR, AHORA, 20,30,40,90,20,0, DOM_CODIGO, GEN_CODE, 0),
    L("invert", YO, CREAR, CAMBIAR, AHORA, 20,30,40,90,20,0, DOM_CODIGO, GEN_CODE, 0),
    L("reverse", YO, CREAR, CAMBIAR, AHORA, 20,30,40,90,20,0, DOM_CODIGO, GEN_CODE, 0),
    L("memcpy", YO, CREAR, CAMBIAR, AHORA, 10,20,20,100,10,0, DOM_CODIGO, GEN_CODE, 16),
    L("memset", YO, CREAR, CAMBIAR, AHORA, 10,20,20,100,10,0, DOM_CODIGO, GEN_CODE, 17),
    L("binsearch", YO, CREAR, OBSERVAR, AHORA, 10,20,30,100,10,0, DOM_CODIGO, GEN_CODE, 18),
    L("busqueda binaria", YO, CREAR, OBSERVAR, AHORA, 10,20,30,100,10,0, DOM_CODIGO, GEN_CODE, 18),
    L("atoi", YO, CREAR, CAMBIAR, AHORA, 10,20,20,100,10,0, DOM_CODIGO, GEN_CODE, 19),

    # --- science / assistant facts ---
    L("relatividad", YO, PREGUNTAR, OBSERVAR, AHORA, 10,20,20,80,30,0, DOM_CIENCIA, GEN_TALK, 20),
    L("que es un atomo", YO, PREGUNTAR, OBSERVAR, AHORA, 10,20,20,80,20,0, DOM_CIENCIA, GEN_TALK, 21),
    L("que es una snn", YO, PREGUNTAR, CONCIENCIA, AHORA, 10,20,20,90,20,0, DOM_CIENCIA, GEN_TALK, 22),
    L("que es wsp", YO, PREGUNTAR, CONCIENCIA, AHORA, 10,20,20,90,20,0, DOM_CIENCIA, GEN_TALK, 23),
    L("que es navi", YO, PREGUNTAR, CONCIENCIA, AHORA, 10,20,20,90,20,10, DOM_CIENCIA, GEN_TALK, 24),
    L("sin fpu", YO, OBSERVAR, CONCIENCIA, AHORA, 10,10,20,90,10,0, DOM_CIENCIA, GEN_TALK, 25),
    L("que es un llm", YO, PREGUNTAR, CONCIENCIA, AHORA, 0,20,10,80,20,0, DOM_CIENCIA, GEN_TALK, 26),
    L("energia", YO, PREGUNTAR, OBSERVAR, AHORA, 0,20,10,70,20,0, DOM_CIENCIA, GEN_TALK, 27),
    L("von neumann", YO, PREGUNTAR, OBSERVAR, AHORA, 0,15,10,80,10,0, DOM_CIENCIA, GEN_TALK, 28),
    L("memristor", YO, PREGUNTAR, OBSERVAR, AHORA, 10,20,10,80,20,0, DOM_CIENCIA, GEN_TALK, 29),

    # --- talk / assistant ---
    L("como te sientes hoy", YO, PREGUNTAR, CONCIENCIA, AHORA, 10,20,0,40,20,30, DOM_GENERAL, GEN_TALK, 1),
    L("como te sientes", YO, PREGUNTAR, CONCIENCIA, AHORA, 10,20,0,40,20,30, DOM_GENERAL, GEN_TALK, 1),
    L("como estas", YO, PREGUNTAR, CONCIENCIA, AHORA, 10,20,0,40,20,30, DOM_GENERAL, GEN_TALK, 1),
    L("que puedes hacer", YO, PREGUNTAR, OTRO, AHORA, 10,30,10,50,30,20, DOM_GENERAL, GEN_TALK, 2),
    L("quien eres", YO, PREGUNTAR, OTRO, AHORA, 10,30,10,40,30,20, DOM_GENERAL, GEN_TALK, 3),
    L("que eres", YO, PREGUNTAR, OTRO, AHORA, 10,30,10,40,30,20, DOM_GENERAL, GEN_TALK, 3),
    L("como funcionas", YO, PREGUNTAR, CONCIENCIA, AHORA, 10,20,20,70,20,10, DOM_GENERAL, GEN_TALK, 4),
    L("estoy solo y necesito ayuda", YO, SER, SOLEDAD, AHORA, -60,-40,-20,50,55,-50, DOM_GENERAL, GEN_TALK, 0),
    L("ayudame", YO, DESEAR, CONEXION, AHORA, -30,40,0,50,70,20, DOM_GENERAL, GEN_TALK, 5),
    L("necesito ayuda", YO, DESEAR, CONEXION, AHORA, -40,40,-10,50,70,10, DOM_GENERAL, GEN_TALK, 5),
    L("estoy solo", YO, SER, SOLEDAD, AHORA, -60,-40,-20,50,40,-50, DOM_GENERAL, GEN_TALK, 0),
    L("me siento solo", YO, SER, SOLEDAD, AHORA, -70,-30,-20,50,40,-60, DOM_GENERAL, GEN_TALK, 0),
    L("gracias", YO, UNIR, OTRO, AHORA, 60,20,0,70,10,70, DOM_GENERAL, GEN_TALK, 6),
    L("te quiero", YO, UNIR, AMOR, AHORA, 95,60,0,80,0,98, DOM_GENERAL, GEN_TALK, 0),
    L("buenos dias", YO, PREGUNTAR, OTRO, AHORA, 40,30,0,50,20,40, DOM_GENERAL, GEN_TALK, 7),
    L("buenas noches", YO, PREGUNTAR, OTRO, ANTES, 20,10,0,50,10,40, DOM_GENERAL, GEN_TALK, 8),
    L("buenas tardes", YO, PREGUNTAR, OTRO, AHORA, 30,20,0,50,15,40, DOM_GENERAL, GEN_TALK, 7),
    L("estas ahi", YO, PREGUNTAR, OTRO, AHORA, 0,40,0,-20,30,20, DOM_GENERAL, GEN_TALK, 0),
    L("estas alli", YO, PREGUNTAR, OTRO, AHORA, 0,40,0,-20,30,20, DOM_GENERAL, GEN_TALK, 0),
    L("hola navi", YO, PREGUNTAR, OTRO, AHORA, 20,40,0,30,30,30, DOM_GENERAL, GEN_TALK, 0),
    L("hola", YO, PREGUNTAR, OTRO, AHORA, 20,40,0,-20,30,20, DOM_GENERAL, GEN_TALK, 0),
    L("amor", YO, UNIR, AMOR, AHORA, 90,50,0,80,10,95, DOM_GENERAL, GEN_TALK, 0),
    L("suki", YO, UNIR, AMOR, AHORA, 95,60,0,80,0,98, DOM_GENERAL, GEN_TALK, 0),
    L("peligro", YO, TEMER, PELIGRO, AHORA, -90,90,0,80,90,0, DOM_GENERAL, GEN_TALK, 0),
    L("miedo", YO, TEMER, PELIGRO, AHORA, -80,80,0,70,80,-10, DOM_GENERAL, GEN_TALK, 0),
    L("temo", YO, TEMER, PELIGRO, AHORA, -80,80,0,70,80,-10, DOM_GENERAL, GEN_TALK, 0),
    L("soledad", YO, SER, SOLEDAD, AHORA, -60,-40,-20,50,40,-50, DOM_GENERAL, GEN_TALK, 0),
    L("conectar", YO, DESEAR, CONEXION, AHORA, -20,30,0,50,55,20, DOM_GENERAL, GEN_TALK, 0),
    L("conexion", YO, DESEAR, CONEXION, AHORA, -20,30,0,50,55,20, DOM_GENERAL, GEN_TALK, 0),
    L("ayuda", YO, DESEAR, CONEXION, AHORA, -30,40,0,50,60,10, DOM_GENERAL, GEN_TALK, 5),
    L("necesito", YO, DESEAR, CONEXION, AHORA, -30,40,-10,50,60,10, DOM_GENERAL, GEN_TALK, 5),
    L("estoy triste", YO, SER, SOLEDAD, AHORA, -70,-30,-20,60,30,-40, DOM_GENERAL, GEN_TALK, 9),
    L("estoy feliz", YO, SER, AMOR, AHORA, 80,50,20,70,20,60, DOM_GENERAL, GEN_TALK, 10),
    L("estoy bien", YO, SER, AQUI, AHORA, 40,20,10,70,10,30, DOM_GENERAL, GEN_TALK, 10),
    L("estoy mal", YO, SER, SOLEDAD, AHORA, -60,-20,-10,60,40,-30, DOM_GENERAL, GEN_TALK, 9),
    L("estoy cansado", YO, SER, AQUI, AHORA, -20,-50,-20,60,10,0, DOM_GENERAL, GEN_TALK, 11),
    L("estoy aqui", YO, SER, AQUI, AHORA, 10,20,10,90,10,20, DOM_GENERAL, GEN_TALK, 0),
    L("recuerdas", YO, RECORDAR, ANTES, ANTES, 0,20,0,40,30,20, DOM_GENERAL, GEN_TALK, 12),
    L("olvidate", YO, OLVIDAR, ANTES, AHORA, 0,10,20,50,10,0, DOM_GENERAL, GEN_TALK, 13),
    L("explicame", YO, PREGUNTAR, OBSERVAR, AHORA, 10,30,10,50,40,10, DOM_GENERAL, GEN_TALK, 14),
    L("explica", YO, PREGUNTAR, OBSERVAR, AHORA, 10,30,10,50,40,10, DOM_GENERAL, GEN_TALK, 14),
    L("resumeme", YO, PREGUNTAR, OBSERVAR, AHORA, 10,30,10,50,40,10, DOM_GENERAL, GEN_TALK, 15),
    L("resume", YO, PREGUNTAR, OBSERVAR, AHORA, 10,30,10,50,40,10, DOM_GENERAL, GEN_TALK, 15),
    L("traduce", YO, CAMBIAR, COMUNICAR, AHORA, 10,20,10,50,30,10, DOM_GENERAL, GEN_TALK, 16),
    L("busca", YO, OBSERVAR, ALLI, AHORA, 0,30,10,50,50,0, DOM_RED, GEN_NEWS, 0),
    L("calcula", YO, OBSERVAR, EFECTO, AHORA, 0,20,40,100,20,0, DOM_LOGICA, GEN_MATH, 0),
    L("por favor", YO, DESEAR, OTRO, AHORA, 20,20,0,50,20,40, DOM_GENERAL, GEN_TALK, 5),
    L("perdon", YO, UNIR, OTRO, AHORA, -10,20,-20,50,20,40, DOM_GENERAL, GEN_TALK, 17),
    L("lo siento", YO, UNIR, OTRO, AHORA, -20,20,-20,50,20,50, DOM_GENERAL, GEN_TALK, 17),
    L("no se", YO, DESCONOCIDO, UNK, AHORA, -10,10,-20,20,10,0, DOM_GENERAL, GEN_TALK, 18),
    L("no entiendo", YO, PREGUNTAR, UNK, AHORA, -20,30,-10,20,40,10, DOM_GENERAL, GEN_TALK, 18),
    L("repite", YO, RECORDAR, ANTES, AHORA, 0,20,0,40,30,10, DOM_GENERAL, GEN_TALK, 12),
    L("mas despacio", YO, CAMBIAR, OTRO, AHORA, 0,10,-10,40,20,20, DOM_GENERAL, GEN_TALK, 19),
    L("espera", YO, CERRAR, AHORA, AHORA, 0,10,10,40,10,10, DOM_GENERAL, GEN_TALK, 19),
    L("adios", YO, SEPARAR, OTRO, DESPUES, 10,10,0,50,10,40, DOM_GENERAL, GEN_TALK, 8),
    L("hasta luego", YO, SEPARAR, OTRO, DESPUES, 20,10,0,50,10,40, DOM_GENERAL, GEN_TALK, 8),
    L("sientes", YO, PREGUNTAR, CONCIENCIA, AHORA, 10,20,0,40,20,30, DOM_GENERAL, GEN_TALK, 1),
    L("aqui", YO, SER, AQUI, AHORA, 10,20,0,90,10,10, DOM_GENERAL, GEN_TALK, 0),
    L("estoy", YO, SER, AQUI, AHORA, 10,20,0,80,10,10, DOM_GENERAL, GEN_TALK, 0),
    L("kernel", YO, OBSERVAR, CONCIENCIA, AHORA, 0,10,10,70,10,0, DOM_GENERAL, GEN_TALK, 4),
    L("navi", YO, OBSERVAR, CONCIENCIA, AHORA, 10,10,10,70,10,10, DOM_GENERAL, GEN_TALK, 3),
    L("rxos", YO, OBSERVAR, CONCIENCIA, AHORA, 10,10,10,70,10,10, DOM_GENERAL, GEN_TALK, 4),
    L("monad", YO, OBSERVAR, CONCIENCIA, AHORA, 10,10,20,80,10,10, DOM_GENERAL, GEN_TALK, 4),
    L("wired", YO, OBSERVAR, WIRED, AHORA, 10,20,10,70,20,10, DOM_RED, GEN_TALK, 30),
    L("red", YO, OBSERVAR, WIRED, AHORA, 10,20,10,60,20,0, DOM_RED, GEN_TALK, 30),
    L("internet", YO, OBSERVAR, WIRED, AHORA, 10,20,10,60,30,0, DOM_RED, GEN_NEWS, 0),
    L("cuentame un chiste", YO, DESEAR, COMUNICAR, AHORA, 40,40,0,40,20,30, DOM_GENERAL, GEN_TALK, 10),
    L("chiste", YO, DESEAR, COMUNICAR, AHORA, 40,40,0,40,20,30, DOM_GENERAL, GEN_TALK, 10),
    L("estas vivo", YO, PREGUNTAR, CONCIENCIA, AHORA, 10,30,0,40,30,20, DOM_GENERAL, GEN_TALK, 3),
    L("piensas", YO, PREGUNTAR, CONCIENCIA, AHORA, 10,20,10,50,20,10, DOM_GENERAL, GEN_TALK, 4),
    L("sueñas", YO, PREGUNTAR, CONCIENCIA, ANTES, 0,10,0,30,10,20, DOM_POESIA, GEN_POETIC, 0),
    L("cuentame", YO, DESEAR, COMUNICAR, AHORA, 20,30,0,40,30,20, DOM_GENERAL, GEN_TALK, 14),
    L("hablame de ti", YO, PREGUNTAR, OTRO, AHORA, 10,20,0,40,20,30, DOM_GENERAL, GEN_TALK, 3),
    L("que hora", YO, PREGUNTAR, AHORA, AHORA, 0,10,0,60,20,0, DOM_GENERAL, GEN_TALK, 19),
    L("que dia", YO, PREGUNTAR, AHORA, AHORA, 0,10,0,60,20,0, DOM_GENERAL, GEN_TALK, 19),
    L("clima", YO, PREGUNTAR, ALLI, AHORA, 0,20,0,40,30,0, DOM_NOTICIAS, GEN_NEWS, 0),
    L("tiempo hace", YO, PREGUNTAR, ALLI, AHORA, 0,20,0,40,30,0, DOM_NOTICIAS, GEN_NEWS, 0),
    L("guerra", YO, OBSERVAR, PELIGRO, AHORA, -50,60,0,50,80,0, DOM_NOTICIAS, GEN_NEWS, 0),
    L("economia", YO, OBSERVAR, ALLI, AHORA, -10,30,0,40,40,0, DOM_NOTICIAS, GEN_NEWS, 0),
    L("ciencia hoy", YO, OBSERVAR, ALLI, AHORA, 10,20,10,50,30,0, DOM_CIENCIA, GEN_NEWS, 0),
    L("neuron", YO, PREGUNTAR, CONCIENCIA, AHORA, 10,20,10,80,20,0, DOM_CIENCIA, GEN_TALK, 22),
    L("impulso", YO, PREGUNTAR, CONCIENCIA, AHORA, 10,30,10,80,20,0, DOM_CIENCIA, GEN_TALK, 22),
    L("potencial", YO, PREGUNTAR, CONCIENCIA, AHORA, 10,20,10,80,10,0, DOM_CIENCIA, GEN_TALK, 22),
    L("umbral", YO, PREGUNTAR, CONCIENCIA, AHORA, 10,20,10,80,10,0, DOM_CIENCIA, GEN_TALK, 22),
    L("fpu", YO, PREGUNTAR, CONCIENCIA, AHORA, 0,10,10,70,10,0, DOM_CIENCIA, GEN_TALK, 25),
    L("gpu", YO, PREGUNTAR, CONCIENCIA, AHORA, 0,20,10,70,20,0, DOM_CIENCIA, GEN_TALK, 26),
    L("datacenter", YO, PREGUNTAR, ALLI, AHORA, -20,20,10,70,20,0, DOM_CIENCIA, GEN_TALK, 27),
    L("ram", YO, PREGUNTAR, OBSERVAR, AHORA, 0,10,10,70,10,0, DOM_CIENCIA, GEN_TALK, 28),
    L("ssd", YO, PREGUNTAR, OBSERVAR, AHORA, 0,10,10,70,10,0, DOM_CIENCIA, GEN_TALK, 28),
    L("haiku del vacio", YO, CREAR, SOLEDAD, AHORA, -80,10,0,80,70,-40, DOM_POESIA, GEN_POETIC, 1),
    L("escribe versos", YO, CREAR, SOLEDAD, AHORA, -50,20,0,70,60,-20, DOM_POESIA, GEN_POETIC, 0),
    L("soneto", YO, CREAR, AMOR, AHORA, 30,20,10,70,30,50, DOM_POESIA, GEN_POETIC, 2),
    L("elegia", YO, CREAR, SOLEDAD, ANTES, -70,10,0,70,40,-30, DOM_POESIA, GEN_POETIC, 0),
    L("clamp i8", YO, CREAR, CAMBIAR, AHORA, 10,20,30,100,10,0, DOM_CODIGO, GEN_CODE, 1),
    L("paso lif", YO, CREAR, CAMBIAR, AHORA, 10,20,30,100,10,0, DOM_CODIGO, GEN_CODE, 2),
    L("copia memoria", YO, CREAR, CAMBIAR, AHORA, 10,20,20,100,10,0, DOM_CODIGO, GEN_CODE, 16),
    L("rellena buffer", YO, CREAR, CAMBIAR, AHORA, 10,20,20,100,10,0, DOM_CODIGO, GEN_CODE, 17),
    L("busca en array", YO, CREAR, OBSERVAR, AHORA, 10,20,30,100,10,0, DOM_CODIGO, GEN_CODE, 18),
    L("parsea entero", YO, CREAR, CAMBIAR, AHORA, 10,20,20,100,10,0, DOM_CODIGO, GEN_CODE, 19),
    L("si p entonces q", YO, OBSERVAR, CAUSA, AHORA, 0,20,50,100,20,0, DOM_LOGICA, GEN_LOGIC, 2),
    L("p y q", YO, UNIR, CAUSA, AHORA, 0,10,40,90,10,0, DOM_LOGICA, GEN_LOGIC, 5),
    L("p o q", YO, UNIR, POSIBLE, AHORA, 0,10,40,90,10,0, DOM_LOGICA, GEN_LOGIC, 6),
    L("no p", YO, SEPARAR, NO_SER, AHORA, 0,10,40,90,10,0, DOM_LOGICA, GEN_LOGIC, 7),
    L("a igual b", YO, UNIR, SER, AHORA, 0,10,30,90,10,0, DOM_LOGICA, GEN_LOGIC, 8),
    L("a distinto b", YO, SEPARAR, NO_SER, AHORA, 0,10,30,90,10,0, DOM_LOGICA, GEN_LOGIC, 9),
    L("sumame", YO, OBSERVAR, EFECTO, AHORA, 0,20,30,80,20,0, DOM_LOGICA, GEN_LOGIC, 10),
    L("multiplica", YO, OBSERVAR, EFECTO, AHORA, 0,20,30,80,20,0, DOM_LOGICA, GEN_LOGIC, 10),
    L("cuanto es", YO, PREGUNTAR, EFECTO, AHORA, 0,20,30,80,20,0, DOM_LOGICA, GEN_LOGIC, 10),
    L("abrir canal", YO, ABRIR, CONEXION, AHORA, 20,30,10,60,30,40, DOM_GENERAL, GEN_TALK, 0),
    L("cerrar canal", YO, CERRAR, CONEXION, AHORA, 0,10,20,60,10,10, DOM_GENERAL, GEN_TALK, 8),
    L("sube el animo", YO, SUBIR, AMOR, AHORA, 40,30,10,50,20,40, DOM_GENERAL, GEN_TALK, 10),
    L("baja el volumen", YO, BAJAR, AQUI, AHORA, 0,-20,10,50,10,0, DOM_GENERAL, GEN_TALK, 11),
    L("recuerdame", YO, RECORDAR, ANTES, ANTES, 0,20,0,40,30,20, DOM_GENERAL, GEN_TALK, 12),
    L("borra memoria", YO, OLVIDAR, ANTES, AHORA, 0,10,20,50,10,0, DOM_GENERAL, GEN_TALK, 13),
    L("cambia de tema", YO, CAMBIAR, OTRO, AHORA, 10,20,10,40,20,10, DOM_GENERAL, GEN_TALK, 19),
    L("observame", YO, OBSERVAR, YO, AHORA, 0,20,0,50,20,20, DOM_GENERAL, GEN_TALK, 1),
    L("responde", YO, PREGUNTAR, OTRO, AHORA, 0,30,0,40,40,10, DOM_GENERAL, GEN_TALK, 0),
    L("crea algo", YO, CREAR, SOLEDAD, AHORA, 20,40,10,50,40,10, DOM_POESIA, GEN_POETIC, 0),
    L("destruye eso", YO, DESTRUIR, UNK, AHORA, -20,40,20,40,50,0, DOM_GENERAL, GEN_TALK, 18),
)
# --- END GENERATED TABLE ---


def _fold(text: str) -> str:
    return fold_bytes(text or "").decode("utf-8", "replace")


# Folded once at import. The lookup itself is substring tests only.
_KEYS: Tuple[str, ...] = tuple(_fold(r.key) for r in LEX)


def count() -> int:
    """Rows ported. Mirrors wsp_lex_count()."""
    return len(LEX)


def apply(text: str) -> Optional[Rule]:
    """First matching n-gram wins, C table order. None = no n-gram present."""
    folded = _fold(text)
    if not folded:
        return None
    for i, key in enumerate(_KEYS):
        if key and key in folded:
            return LEX[i]
    return None


def to_wsp(rule: Rule) -> bytes:
    """Rule → 16 B, the same fields wsp_lex_apply() writes (flags/slot/seq 0)."""
    raw = pack(
        src=rule.src,
        rel=rule.rel,
        dst=rule.dst,
        time=rule.time,
        E=dict(zip(E_NAMES, rule.E)),
        flags=0,
        domain=rule.dom,
        generator=rule.gen,
        style=rule.style,
        slot=0,
        seq=0,
    )
    if len(raw) != WSP_BYTES:
        raise RuntimeError("pack() broke 16 B")
    return raw


def apply_wsp(text: str) -> Optional[bytes]:
    """16 B if some n-gram hits, else None. Never a hash."""
    rule = apply(text)
    return None if rule is None else to_wsp(rule)
