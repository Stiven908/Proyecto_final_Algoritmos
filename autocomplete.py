"""
Sistema de Autocompletado para Chat RPG
Estructuras: Árbol Rojinegro y Búsqueda Binaria
"""

import re
import time
import bisect
from enum import Enum


# ── Colores ANSI ─────────────────────────────────────────────────────────────

class Color(str, Enum):
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    CYAN    = "\033[96m"
    MAGENTA = "\033[95m"
    BLUE    = "\033[94m"
    GRAY    = "\033[90m"
    WHITE   = "\033[97m"

    def __str__(self) -> str:
        return self.value


def bold_match(word: str, prefix: str) -> str:
    """Resalta en cian+negrilla las letras que coinciden con el prefijo."""
    n = len(prefix)
    matched = word[:n]
    rest    = word[n:]
    return f"{Color.CYAN}{Color.BOLD}{matched}{Color.RESET}{Color.GRAY}{rest}{Color.RESET}"


# ── Árbol Rojinegro ───────────────────────────────────────────────────────────

_RED   = True
_BLACK = False


class _RBNode:
    """Nodo interno del Árbol Rojinegro."""

    __slots__ = ("key", "color", "left", "right", "parent")

    def __init__(self, key: str, color: bool = _RED):
        self.key    = key
        self.color  = color
        self.left:   "_RBNode | None" = None
        self.right:  "_RBNode | None" = None
        self.parent: "_RBNode | None" = None


class RedBlackTree:
    """
    Árbol Rojinegro autobalanceado para búsqueda de prefijos en O(log n).

    Uso:
        tree = RedBlackTree()
        tree.insert("espada")
        resultados = tree.search_prefix("esp")   # ["espada", ...]
    """

    def __init__(self):
        # Centinela NIL: hoja negra compartida por todos los nodos
        self._nil = _RBNode("", _BLACK)
        self._nil.left  = self._nil
        self._nil.right = self._nil
        self._root = self._nil
        self._size = 0

    # ── Propiedades públicas ──────────────────────────────────────────────────

    @property
    def size(self) -> int:
        return self._size

    # ── Inserción ─────────────────────────────────────────────────────────────

    def insert(self, key: str) -> None:
        """Inserta una clave (normalizada a minúsculas). Ignora duplicados."""
        key = key.lower()

        node = _RBNode(key)
        node.left   = self._nil
        node.right  = self._nil
        node.parent = None

        parent:  "_RBNode | None" = None
        current: "_RBNode"        = self._root

        while current is not self._nil:
            parent = current
            if key < current.key:
                current = current.left
            elif key > current.key:
                current = current.right
            else:
                return  # duplicado — no insertar

        node.parent = parent
        if parent is None:
            self._root = node
        elif key < parent.key:
            parent.left = node
        else:
            parent.right = node

        self._size += 1
        self._fix_insert(node)

    def _fix_insert(self, z: _RBNode) -> None:
        while z.parent and z.parent.color == _RED:
            gp = z.parent.parent
            if z.parent is gp.left:
                uncle = gp.right
                if uncle.color == _RED:                  # Caso 1
                    z.parent.color = _BLACK
                    uncle.color    = _BLACK
                    gp.color       = _RED
                    z = gp
                else:
                    if z is z.parent.right:              # Caso 2
                        z = z.parent
                        self._rotate_left(z)
                    z.parent.color = _BLACK              # Caso 3
                    gp.color       = _RED
                    self._rotate_right(gp)
            else:
                uncle = gp.left
                if uncle.color == _RED:                  # Caso 1 (simétrico)
                    z.parent.color = _BLACK
                    uncle.color    = _BLACK
                    gp.color       = _RED
                    z = gp
                else:
                    if z is z.parent.left:               # Caso 2 (simétrico)
                        z = z.parent
                        self._rotate_right(z)
                    z.parent.color = _BLACK              # Caso 3 (simétrico)
                    gp.color       = _RED
                    self._rotate_left(gp)
        self._root.color = _BLACK

    # ── Rotaciones ────────────────────────────────────────────────────────────

    def _rotate_left(self, x: _RBNode) -> None:
        y = x.right
        x.right = y.left
        if y.left is not self._nil:
            y.left.parent = x
        y.parent = x.parent
        if x.parent is None:
            self._root = y
        elif x is x.parent.left:
            x.parent.left = y
        else:
            x.parent.right = y
        y.left   = x
        x.parent = y

    def _rotate_right(self, y: _RBNode) -> None:
        x = y.left
        y.left = x.right
        if x.right is not self._nil:
            x.right.parent = y
        x.parent = y.parent
        if y.parent is None:
            self._root = x
        elif y is y.parent.right:
            y.parent.right = x
        else:
            y.parent.left = x
        x.right  = y
        y.parent = x

    # ── Búsqueda por prefijo ──────────────────────────────────────────────────

    def search_prefix(self, prefix: str, max_results: int = 10) -> list[str]:
        """
        Devuelve hasta `max_results` palabras que empiezan con `prefix`,
        en orden alfabético (recorrido in-order).
        """
        prefix  = prefix.lower()
        results: list[str] = []
        self._collect_prefix(self._root, prefix, results, max_results)
        return results

    def _collect_prefix(
        self,
        node: _RBNode,
        prefix: str,
        results: list[str],
        max_results: int,
    ) -> None:
        if node is self._nil or len(results) >= max_results:
            return

        # Determinar si puede haber coincidencias en el subárbol izquierdo:
        # sí cuando la clave actual es mayor que el prefijo (alfabéticamente
        # puede haber claves menores que sí coincidan).
        if node.key > prefix:
            self._collect_prefix(node.left, prefix, results, max_results)

        if len(results) >= max_results:
            return

        # Evaluar el nodo actual
        if node.key.startswith(prefix):
            results.append(node.key)

        # Siempre explorar el subárbol derecho cuando la clave actual
        # empieza con el prefijo O es menor que él: puede haber más
        # coincidencias con prefijos más largos a la derecha.
        if node.key < prefix or node.key.startswith(prefix):
            self._collect_prefix(node.right, prefix, results, max_results)


# ── Lista Negra ───────────────────────────────────────────────────────────────

class Blacklist:
    """
    Lista negra de palabras prohibidas con búsqueda binaria en O(log n).

    Uso:
        bl = Blacklist(["malo", "feo"])
        bl.contains("malo")          # True
        bl.filter(["hola", "malo"])  # ["hola"]
        bl.censor_text("hola malo")  # "hola ####"
    """

    def __init__(self, words: list[str]):
        # bisect requiere lista ordenada
        self._words: list[str] = sorted(w.lower() for w in words)

    def contains(self, word: str) -> bool:
        """Búsqueda binaria: True si la palabra está en la lista negra."""
        target = word.lower()
        idx    = bisect.bisect_left(self._words, target)
        return idx < len(self._words) and self._words[idx] == target

    def filter(self, words: list[str]) -> list[str]:
        """Devuelve la lista sin las palabras prohibidas."""
        return [w for w in words if not self.contains(w)]

    def censor_text(self, text: str) -> str:
        """
        Reemplaza cada palabra prohibida por una cadena de '#'
        del mismo largo que el token original (incluyendo signos).
        """
        tokens = text.split()
        result = []
        for token in tokens:
            clean = re.sub(r"[^a-zA-ZáéíóúÁÉÍÓÚñÑ]", "", token).lower()
            result.append("#" * len(token) if self.contains(clean) else token)
        return " ".join(result)

    def __len__(self) -> int:
        return len(self._words)


# ── Motor de Autocompletado ───────────────────────────────────────────────────

class AutocompleteEngine:
    """
    Integra el Árbol Rojinegro y la Lista Negra en un único motor.

    Uso:
        engine = AutocompleteEngine(vocabulario, palabras_prohibidas)
        sugerencias, ms = engine.suggest("esp")
        mensaje_limpio  = engine.censor_message("texto con malas palabras")
    """

    def __init__(self, vocabulary: list[str], blacklist_words: list[str]):
        self.blacklist = Blacklist(blacklist_words)
        self.tree      = RedBlackTree()

        t0 = time.perf_counter()
        for word in vocabulary:
            self.tree.insert(word)
        self._build_time = time.perf_counter() - t0

    # ── API pública ───────────────────────────────────────────────────────────

    def suggest(self, prefix: str, max_results: int = 8) -> tuple[list[str], float]:
        """
        Devuelve (sugerencias_filtradas, tiempo_en_ms).
        Las sugerencias están en orden alfabético y no contienen
        palabras de la lista negra.
        """
        if not prefix.strip():
            return [], 0.0

        t0       = time.perf_counter()
        raw      = self.tree.search_prefix(prefix, max_results * 2)
        filtered = self.blacklist.filter(raw)[:max_results]
        elapsed  = (time.perf_counter() - t0) * 1000
        return filtered, elapsed

    def censor_message(self, text: str) -> str:
        return self.blacklist.censor_text(text)

    # ── Propiedades informativas ──────────────────────────────────────────────

    @property
    def vocab_size(self) -> int:
        return self.tree.size

    @property
    def build_time_ms(self) -> float:
        return self._build_time * 1000
