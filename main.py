#!/usr/bin/env python3
"""
Chat RPG — Sistema de Autocompletado
=====================================
Controles:
  TAB          Seleccionar siguiente sugerencia
  SHIFT+TAB    Seleccionar sugerencia anterior
  ENTER        Enviar mensaje / Confirmar sugerencia seleccionada
  ESC          Cancelar sugerencia activa
  BACKSPACE    Borrar último carácter
  CTRL+C       Salir
"""

import os
import sys
import time
import platform

sys.path.insert(0, os.path.dirname(__file__))

from autocomplete import AutocompleteEngine, Color, bold_match
from vocabulary   import RPG_VOCABULARY, BLACKLIST_WORDS

# ── Compatibilidad de teclado (Windows solamente) ─────────────────────────────

IS_WINDOWS = platform.system() == "Windows"

if IS_WINDOWS:
    import msvcrt

    def read_key() -> str:
        """Lee una tecla raw en Windows."""
        ch = msvcrt.getwch()
        if ch in ("\x00", "\xe0"):          # tecla especial de dos bytes
            return "WIN_" + msvcrt.getwch()
        return ch
else:
    def read_key() -> str:                  # type: ignore[misc]
        raise RuntimeError("Este programa solo está soportado en Windows.")


# ── Constantes de UI ──────────────────────────────────────────────────────────

SEP_THIN  = f"{Color.GRAY}{'─' * 60}{Color.RESET}"
SEP_THICK = f"{Color.BLUE}{'═' * 60}{Color.RESET}"

HISTORY_VISIBLE = 8   # cuántos mensajes recientes mostrar


# ── Estado del chat ───────────────────────────────────────────────────────────

class ChatState:
    """
    Contiene todo el estado mutable del chat en un único lugar.
    Ninguna función de UI debería modificar el estado directamente;
    debe pasar por los métodos de esta clase.
    """

    def __init__(self, engine: AutocompleteEngine):
        self.engine       = engine
        self.history:     list[tuple[str, str]] = []
        self.current_input = ""
        self.suggestions:  list[str] = []
        self.selected_idx: int       = -1
        self.elapsed_ms:   float     = 0.0
        self._npc_queue   = _build_npc_queue()
        self._npc_index   = 0

    # ── Mutaciones ────────────────────────────────────────────────────────────

    def append_char(self, ch: str) -> None:
        self.current_input += ch
        self.selected_idx   = -1
        self._refresh_suggestions()

    def delete_char(self) -> None:
        self.current_input  = self.current_input[:-1]
        self.selected_idx   = -1
        self._refresh_suggestions()

    def next_suggestion(self) -> None:
        if self.suggestions:
            self.selected_idx = (self.selected_idx + 1) % len(self.suggestions)

    def prev_suggestion(self) -> None:
        if self.suggestions:
            self.selected_idx = (self.selected_idx - 1) % len(self.suggestions)

    def accept_suggestion(self) -> None:
        """Acepta la sugerencia seleccionada como texto actual (sin enviar)."""
        if self.selected_idx >= 0 and self.suggestions:
            self.current_input = self.suggestions[self.selected_idx]
        self._clear_suggestions()

    def cancel_suggestion(self) -> None:
        self._clear_suggestions()

    def send_message(self) -> None:
        """Censura y envía el mensaje actual; añade respuesta de NPC."""
        text = self.current_input.strip()
        if not text:
            return
        clean = self.engine.censor_message(text)
        self.history.append(("tú", clean))

        npc_name, npc_reply = self._npc_queue[self._npc_index % len(self._npc_queue)]
        self.history.append((npc_name, npc_reply))
        self._npc_index += 1

        self.current_input = ""
        self._clear_suggestions()

    # ── Helpers privados ──────────────────────────────────────────────────────

    def _refresh_suggestions(self) -> None:
        self.suggestions, self.elapsed_ms = self.engine.suggest(self.current_input)
        self.selected_idx = 0 if self.suggestions else -1

    def _clear_suggestions(self) -> None:
        self.suggestions  = []
        self.selected_idx = -1


def _build_npc_queue() -> list[tuple[str, str]]:
    """Devuelve la lista de respuestas NPC en orden fijo."""
    return [
        ("NPC Guerrero",   "¡Por el reino! Buen movimiento."),
        ("NPC Archimago",  "Fascinante elección, joven aventurero."),
        ("NPC Arquera",    "Mi arco está listo. ¿Y el tuyo?"),
        ("NPC Enano",      "¡Por las barbas de mi padre! ¡Vamos!"),
        ("NPC Paladín",    "Debo ser valiente..."),
        ("NPC Explorador", "Interesante... muy interesante."),
        ("NPC Oráculo",    "Tu destino ya está escrito..."),
    ]


# ── Renderizado ───────────────────────────────────────────────────────────────

class Renderer:
    """
    Responsable exclusivamente de pintar la UI en consola.
    """

    def __init__(self):
        self._last_lines = 0   # líneas pintadas en el ciclo anterior

    # ── Pantalla completa (solo al inicio) ────────────────────────────────────

    @staticmethod
    def clear_screen() -> None:
        os.system("cls" if IS_WINDOWS else "clear")

    @staticmethod
    def print_header() -> None:
        print(f"{Color.BLUE}{Color.BOLD}")
        print("  ╔══════════════════════════════════════════════════════╗")
        print("  ║         CHAT RPG  ─  Sistema de Autocompletado       ║")
        print("  ╚══════════════════════════════════════════════════════╝")
        print(Color.RESET)

    @staticmethod
    def print_info(engine: AutocompleteEngine) -> None:
        print(
            f"  {Color.GRAY}Vocabulario: {Color.CYAN}{engine.vocab_size}{Color.GRAY} palabras  │"
            f"  Árbol Rojinegro: O(log n)  │  Lista negra: {len(BLACKLIST_WORDS)} palabras{Color.RESET}"
        )
        print(
            f"  {Color.GRAY}Tiempo de construcción del árbol: "
            f"{Color.YELLOW}{engine.build_time_ms:.2f} ms{Color.RESET}"
        )
        print(SEP_THIN)
        print(
            f"  {Color.GRAY}TAB = siguiente  │  SHIFT+TAB = anterior  │"
            f"  ESC = cancelar  │  CTRL+C = salir{Color.RESET}"
        )
        print(SEP_THIN)

    # ── Redibujado incremental ────────────────────────────────────────────────

    def redraw(self, state: ChatState) -> None:
        """Borra las líneas del ciclo anterior y pinta el estado actual."""
        self._erase_previous()

        lines = 0

        # Historial
        print(SEP_THIN);  lines += 1
        chat_lines = self._print_history(state.history)
        lines += chat_lines
        print(SEP_THIN);  lines += 1

        # Sugerencias
        lines += self._print_suggestions(state)

        # Línea de entrada
        print()
        lines += 1
        self._print_prompt(state)
        lines += 1

        self._last_lines = lines

    # ── Secciones privadas ────────────────────────────────────────────────────

    def _print_history(self, history: list[tuple[str, str]]) -> int:
        recent = history[-HISTORY_VISIBLE:]
        if not recent:
            print(f"  {Color.GRAY}(El historial de chat aparecerá aquí...){Color.RESET}")
            return 1
        for sender, msg in recent:
            if sender == "tú":
                print(f"  {Color.GREEN}{Color.BOLD}[Tú]{Color.RESET}  {Color.WHITE}{msg}{Color.RESET}")
            elif sender == "Sistema":
                print(f"  {Color.YELLOW}{Color.BOLD}[Sistema]{Color.RESET}  {Color.GRAY}{msg}{Color.RESET}")
            else:
                print(f"  {Color.MAGENTA}{Color.BOLD}[{sender}]{Color.RESET}  {Color.GRAY}{msg}{Color.RESET}")
        return max(len(recent), 1)

    def _print_suggestions(self, state: ChatState) -> int:
        if not state.suggestions:
            print(f"\n  {Color.GRAY}(escribe para ver sugerencias){Color.RESET}")
            return 2

        print(
            f"\n  {Color.YELLOW}💡 Sugerencias{Color.GRAY} "
            f"[{state.elapsed_ms:.2f} ms]{Color.RESET}  "
            f"{Color.GRAY}(TAB para navegar){Color.RESET}"
        )
        for i, word in enumerate(state.suggestions):
            if i == state.selected_idx:
                print(
                    f"  {Color.BLUE}{Color.BOLD}▶{Color.RESET} "
                    f"{Color.BLUE}{Color.BOLD}{word.upper()}{Color.RESET}"
                    f"  {Color.GRAY}← seleccionada{Color.RESET}"
                )
            else:
                print(f"    {Color.GRAY}{i + 1}.{Color.RESET} {bold_match(word, state.current_input)}")
        return len(state.suggestions) + 2

    @staticmethod
    def _print_prompt(state: ChatState) -> None:
        if state.selected_idx >= 0 and state.suggestions:
            selected = state.suggestions[state.selected_idx]
            display  = (
                f"{Color.CYAN}{Color.BOLD}{selected}{Color.RESET}"
                f"{Color.GRAY} [TAB=siguiente · ENTER=aceptar · ESC=cancelar]{Color.RESET}"
            )
        else:
            display = f"{Color.WHITE}{state.current_input}{Color.RESET}█"
        print(f"  {Color.GREEN}{Color.BOLD}Tú ›{Color.RESET}  {display}", end="", flush=True)

    # ── Utilidades de cursor ──────────────────────────────────────────────────

    def _erase_previous(self) -> None:
        if self._last_lines <= 0:
            return
        # Sube N líneas y luego borra todo desde el cursor hacia abajo.
        # \033[{n}A  → subir n líneas
        # \033[J     → borrar desde cursor hasta fin de pantalla
        print(f"\033[{self._last_lines}A\033[J", end="", flush=True)


# ── Bucle principal ───────────────────────────────────────────────────────────

# Teclas especiales reconocidas
_KEY_TAB        = "\t"
_KEY_ENTER      = {"\r", "\n"}
_KEY_ESC        = "\x1b"
_KEY_CTRL_C     = "\x03"
_KEY_CTRL_D     = "\x04"
_KEY_BACKSPACE  = {"\x7f", "\x08", "WIN_\x08"}
_KEY_SHIFT_TAB  = {"\x1b[Z", "ESC_[Z", "WIN_\x0f"}


def run_chat(engine: AutocompleteEngine) -> None:
    state    = ChatState(engine)
    renderer = Renderer()

    # Mensajes iniciales del sistema
    state.history.extend([
        ("Sistema",      "¡Bienvenido al chat del reino! Escribe para comenzar."),
        ("NPC Guerrero", "¡Saludos, aventurero! ¿Listo para la batalla?"),
        ("NPC Oráculo",  "Un mago nunca llega tarde... empieza a escribir."),
    ])

    Renderer.clear_screen()
    Renderer.print_header()
    Renderer.print_info(engine)
    print()

    while True:
        renderer.redraw(state)
        key = read_key()

        if key == _KEY_TAB:
            state.next_suggestion()

        elif key in _KEY_SHIFT_TAB:
            state.prev_suggestion()

        elif key in _KEY_ENTER:
            if state.selected_idx >= 0 and state.suggestions:
                state.accept_suggestion()
            else:
                state.send_message()

        elif key == _KEY_ESC:
            state.cancel_suggestion()

        elif key in (_KEY_CTRL_C, _KEY_CTRL_D):
            print(f"\n\n  {Color.YELLOW}¡Hasta la próxima, aventurero!{Color.RESET}\n")
            sys.exit(0)

        elif key in _KEY_BACKSPACE:
            state.delete_char()

        elif len(key) == 1 and key.isprintable():
            state.append_char(key)

        # Teclas de flecha y otras secuencias especiales → ignorar
        # (no hace falta una rama explícita; el while continúa)


# ── Punto de entrada ──────────────────────────────────────────────────────────

def main() -> None:
    print(f"\n{Color.CYAN}Cargando vocabulario RPG...{Color.RESET}")
    engine = AutocompleteEngine(RPG_VOCABULARY, BLACKLIST_WORDS)
    print(
        f"{Color.GREEN}✔ Árbol Rojinegro construido con "
        f"{engine.vocab_size} palabras en {engine.build_time_ms:.2f} ms{Color.RESET}"
    )
    time.sleep(0.8)
    run_chat(engine)


if __name__ == "__main__":
    main()