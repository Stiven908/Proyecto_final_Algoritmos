"""
 Sistema de Autocompletado para Chat RPG
 Estructura: Árbol Rojinegro y Búsqueda Binaria
"""

import time
import sys
import os
import re

# COLORES ANSI para consola
class Color:
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
    BG_DARK = "\033[40m"

def bold_match(word: str, prefix: str) -> str:
    """
    Resalta en negrilla+color las letras que coinciden con el prefijo.
    El resto de la palabra se muestra en gris.
    """
    n = len(prefix)
    matched  = word[:n]
    rest     = word[n:]
    return f"{Color.CYAN}{Color.BOLD}{matched}{Color.RESET}{Color.GRAY}{rest}{Color.RESET}"


# ÁRBOL ROJINEGRO
RED   = True
BLACK = False

class RBNode:
    """Nodo del Árbol Rojinegro."""
    __slots__ = ("key", "color", "left", "right", "parent")

    def __init__(self, key: str, color: bool = RED):
        self.key    = key
        self.color  = color
        self.left   = None
        self.right  = None
        self.parent = None


class RedBlackTree:
    """
    Árbol Rojinegro autobalanceado.
    """

    def __init__(self):
        # Centinela NIL (hoja negra)
        self.NIL = RBNode("", BLACK)
        self.NIL.left  = self.NIL
        self.NIL.right = self.NIL
        self.root = self.NIL
        self._size = 0

    # Rotaciones
    def _rotate_left(self, x: RBNode):
        y = x.right
        x.right = y.left
        if y.left is not self.NIL:
            y.left.parent = x
        y.parent = x.parent
        if x.parent is None:
            self.root = y
        elif x is x.parent.left:
            x.parent.left = y
        else:
            x.parent.right = y
        y.left   = x
        x.parent = y

    def _rotate_right(self, y: RBNode):
        x = y.left
        y.left = x.right
        if x.right is not self.NIL:
            x.right.parent = y
        x.parent = y.parent
        if y.parent is None:
            self.root = x
        elif y is y.parent.right:
            y.parent.right = x
        else:
            y.parent.left = x
        x.right  = y
        y.parent = x

    # Inserción
    def insert(self, key: str):
        """Inserta una clave."""
        key = key.lower()
        node = RBNode(key)
        node.left   = self.NIL
        node.right  = self.NIL
        node.parent = None

        parent = None
        current = self.root

        while current is not self.NIL:
            parent = current
            if key < current.key:
                current = current.left
            elif key > current.key:
                current = current.right
            else:
                return  # duplicado, no insertar

        node.parent = parent
        if parent is None:
            self.root = node
        elif key < parent.key:
            parent.left = node
        else:
            parent.right = node

        self._size += 1
        self._fix_insert(node)

    def _fix_insert(self, z: RBNode):
        while z.parent and z.parent.color == RED:
            if z.parent is z.parent.parent.left:
                y = z.parent.parent.right
                if y.color == RED:
                    z.parent.color         = BLACK
                    y.color                = BLACK
                    z.parent.parent.color  = RED
                    z = z.parent.parent
                else:
                    if z is z.parent.right:
                        z = z.parent
                        self._rotate_left(z)
                    z.parent.color        = BLACK
                    z.parent.parent.color = RED
                    self._rotate_right(z.parent.parent)
            else:
                y = z.parent.parent.left
                if y.color == RED:
                    z.parent.color        = BLACK
                    y.color               = BLACK
                    z.parent.parent.color = RED
                    z = z.parent.parent
                else:
                    if z is z.parent.left:
                        z = z.parent
                        self._rotate_right(z)
                    z.parent.color        = BLACK
                    z.parent.parent.color = RED
                    self._rotate_left(z.parent.parent)
        self.root.color = BLACK

    # Búsqueda por prefijo
    def search_prefix(self, prefix: str, max_results: int = 10) -> list[str]:
        """
        Devuelve hasta `max_results` palabras que empiezan con `prefix`.
        Orden: alfabético (in-order).
        """
        prefix = prefix.lower()
        results: list[str] = []
        self._search_prefix_helper(self.root, prefix, results, max_results)
        return results

    def _search_prefix_helper(self, node: RBNode, prefix: str, results: list, max_results: int):
        if node is self.NIL or len(results) >= max_results:
            return
        if node.key > prefix:
            # Puede haber coincidencias en el subárbol izquierdo
            self._search_prefix_helper(node.left, prefix, results, max_results)
        if len(results) >= max_results:
            return
        if node.key.startswith(prefix):
            results.append(node.key)
        if node.key <= prefix or node.key.startswith(prefix):
            self._search_prefix_helper(node.right, prefix, results, max_results)

    @property
    def size(self) -> int:
        return self._size


# LISTA NEGRA (búsqueda binaria)
class Blacklist:
    """
    Lista negra de palabras ofensivas.
    Búsqueda binaria: O(log n)
    """

    def __init__(self, words: list[str]):
        self._words = sorted(w.lower() for w in words)

    def contains(self, word: str) -> bool:
        """Búsqueda binaria."""
        target = word.lower()
        lo, hi = 0, len(self._words) - 1
        while lo <= hi:
            mid = (lo + hi) // 2
            if self._words[mid] == target:
                return True
            elif self._words[mid] < target:
                lo = mid + 1
            else:
                hi = mid - 1
        return False

    def filter(self, words: list[str]) -> list[str]:
        return [w for w in words if not self.contains(w)]
    
    def censor_text(self, text: str) -> str:
        """
        Reemplaza palabras prohibidas por #.
        """

        words = text.split()

        censored = []

        for word in words:

            # limpiar signos para comparar
            clean = re.sub(r'[^a-zA-ZáéíóúÁÉÍÓÚñÑ]', '', word).lower()

            if self.contains(clean):
                censored.append("#" * len(word))
            else:
                censored.append(word)

        return " ".join(censored)


# MOTOR DE AUTOCOMPLETADO
class AutocompleteEngine:

    """
    Todavia no funciona muy bien y no se porque
    Motor principal que integra el Árbol Rojinegro y la Lista Negra.
    """

    def __init__(self, vocabulary: list[str], blacklist_words: list[str]):
        self.tree      = RedBlackTree()
        self.blacklist = Blacklist(blacklist_words)

        t0 = time.perf_counter()
        for word in vocabulary:
            self.tree.insert(word)
        self._build_time = time.perf_counter() - t0
    def censor_message(self, text: str) -> str:
        return self.blacklist.censor_text(text)
    
    def suggest(self, prefix: str, max_results: int = 8) -> tuple[list[str], float]:
        """
        Devuelve sugerencias filtradas y el tiempo de búsqueda en ms.
        """
        if not prefix:
            return [], 0.0

        t0 = time.perf_counter()
        raw      = self.tree.search_prefix(prefix, max_results * 2)
        filtered = self.blacklist.filter(raw)[:max_results]
        elapsed  = (time.perf_counter() - t0) * 1000
        return filtered, elapsed

    @property
    def vocab_size(self) -> int:
        return self.tree.size

    @property
    def build_time_ms(self) -> float:
        return self._build_time * 1000
