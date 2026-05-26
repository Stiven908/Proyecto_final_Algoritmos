#!/usr/bin/env python3
"""
  Controles:
    TAB          Seleccionar siguiente sugerencia
    SHIFT+TAB    Seleccionar sugerencia anterior
    ENTER        Enviar mensaje / Confirmar sugerencia
    ESC          Cancela sugerencia
    CTRL+C       Sali
"""

import sys
import os
import time
import platform

# Importar módulos del proyecto
sys.path.insert(0, os.path.dirname(__file__))
from autocomplete import AutocompleteEngine, Color, bold_match
from vocabulary   import RPG_VOCABULARY, BLACKLIST_WORDS

# Detectar SO para lectura de teclado
IS_WINDOWS = platform.system() == "Windows"

if IS_WINDOWS:
    import msvcrt

def _read_key_windows():
    """Lee una tecla en Windows."""
    ch = msvcrt.getwch()
    if ch in ("\x00", "\xe0"):
        ch2 = msvcrt.getwch()
        return "WIN_" + ch2
    return ch


def read_key():
    if IS_WINDOWS:
        return _read_key_windows()
    return _read_key_windows()


#  UI de ayuda
def clear_screen():
    os.system("cls" if IS_WINDOWS else "clear")

def move_up(n: int):
    if n > 0:
        print(f"\033[{n}A", end="", flush=True)

def erase_line():
    print("\033[2K\r", end="", flush=True)

def erase_lines(n: int):
    for _ in range(n):
        erase_line()
        if _ < n - 1:
            move_up(1)

SEPARATOR = f"{Color.GRAY}{'─' * 60}{Color.RESET}"
SEPARATOR_THICK = f"{Color.BLUE}{'═' * 60}{Color.RESET}"

def print_header():
    print(f"{Color.BLUE}{Color.BOLD}")
    print("  ╔══════════════════════════════════════════════════════╗")
    print("  ║         CHAT RPG  ─  Sistema de Autocompletado       ║")
    print("  ╚══════════════════════════════════════════════════════╝")
    print(Color.RESET)

def print_info(engine: AutocompleteEngine):
    print(f"  {Color.GRAY}Vocabulario: {Color.CYAN}{engine.vocab_size}{Color.GRAY} palabras  │"
          f"  Árbol Rojinegro: O(log n)  │  Lista negra: {len(BLACKLIST_WORDS)} palabras{Color.RESET}")
    print(f"  {Color.GRAY}Tiempo de construcción del árbol: "
          f"{Color.YELLOW}{engine.build_time_ms:.2f} ms{Color.RESET}")
    print(SEPARATOR)
    print(f"  {Color.GRAY}TAB = siguiente sugerencia  │  SHIFT+TAB = anterior  │"
          f"  ESC = cancelar  │  CTRL+C = salir{Color.RESET}")
    print(SEPARATOR)

def print_chat_history(history: list[tuple[str, str]]):
    """Imprime el historial de chat."""
    if not history:
        print(f"  {Color.GRAY}(El historial de chat aparecerá aquí...){Color.RESET}")
        return
    for sender, msg in history[-8:]:   # mostrar últimos 8
        if sender == "tú":
            print(f"  {Color.GREEN}{Color.BOLD}[Tú]{Color.RESET}  {Color.WHITE}{msg}{Color.RESET}")
        else:
            name_col = Color.MAGENTA if sender != "Sistema" else Color.YELLOW
            print(f"  {name_col}{Color.BOLD}[{sender}]{Color.RESET}  {Color.GRAY}{msg}{Color.RESET}")

def print_suggestions(suggestions: list[str], prefix: str,
                      selected: int, elapsed_ms: float):
    """Dibuja el panel de sugerencias."""
    if not suggestions:
        print(f"\n  {Color.GRAY}(sin sugerencias){Color.RESET}")
        return

    print(f"\n  {Color.YELLOW}💡 Sugerencias{Color.GRAY} "
          f"[{elapsed_ms:.2f} ms]{Color.RESET}  "
          f"{Color.GRAY}(TAB para navegar){Color.RESET}")

    for i, word in enumerate(suggestions):
        highlighted = bold_match(word, prefix)
        if i == selected:
            marker = f"{Color.BLUE}{Color.BOLD}▶{Color.RESET}"
            bg     = f"{Color.BLUE}"
            print(f"  {marker} {bg}{Color.BOLD}{word.upper()}{Color.RESET}"
                  f"  {Color.GRAY}← seleccionada{Color.RESET}")
        else:
            num = f"{Color.GRAY}{i + 1}.{Color.RESET}"
            print(f"    {num} {highlighted}")


#  BUCLE PRINCIPAL DEL CHAT
def run_chat(engine: AutocompleteEngine):
    history: list[tuple[str, str]] = [
        ("Sistema", "¡Bienvenido al chat del reino! Escribe para comenzar."),
        ("NPC1", "¡Saludos, aventurero! ¿Listo para la batalla?"),
        ("NPC2", "Un mago nunca llega tarde... empieza a escribir."),
    ]

    # NPC que responden al azar
    npcs = [
        ("NPC1",  "¡Por el reino! Buen movimiento."),
        ("NPC3",  "Fascinante elección, joven aventurero."),
        ("NPC3",  "Mi arco está listo. ¿Y el tuyo?"),
        ("NPC4",    "¡Por las barbas de mi padre! ¡Vamos!"),
        ("NPC5",    "Debo ser valiente..."),
        ("NPC6",  "Interesante... muy interesante."),
        ("NPC7",   "Tu destino ya está escrito..."),
    ]
    npc_idx = 0

    current_input = ""
    suggestions:  list[str] = []
    selected_idx: int = -1
    elapsed_ms:   float = 0.0
    last_lines:   int = 0       #líneas que necesitamos borrar en el redibujado

    def redraw():
        nonlocal last_lines

        # Borrar lo que se dibujó antes
        if last_lines > 0:
            move_up(last_lines)
            for _ in range(last_lines):
                erase_line()
                print()
            move_up(last_lines)

        lines = 0

        # Historial
        print(SEPARATOR)
        lines += 1
        chat_lines = min(len(history), 8)
        print_chat_history(history)
        lines += max(chat_lines, 1)
        print(SEPARATOR)
        lines += 1

        # Sugerencias
        if suggestions:
            print_suggestions(suggestions, current_input, selected_idx, elapsed_ms)
            lines += len(suggestions) + 2
        else:
            print(f"\n  {Color.GRAY}(escribe para ver sugerencias){Color.RESET}")
            lines += 2

        # Prompt de escritura
        print()
        lines += 1
        prefix_display = ""
        if selected_idx >= 0 and suggestions:
            selected_word = suggestions[selected_idx]
            prefix_display = (
                f"{Color.CYAN}{Color.BOLD}{selected_word}{Color.RESET}"
                f"{Color.GRAY} [TAB=siguiente · ENTER=aceptar · ESC=cancelar]{Color.RESET}"
            )
        else:
            prefix_display = f"{Color.WHITE}{current_input}{Color.RESET}█"

        print(f"  {Color.GREEN}{Color.BOLD}Tú ›{Color.RESET}  {prefix_display}",
              end="", flush=True)
        lines += 1

        last_lines = lines

    def send_message(text: str):
        nonlocal npc_idx
        history.append(("tú", text))
        npc, reply = npcs[npc_idx % len(npcs)]
        history.append((npc, reply))
        npc_idx += 1


    # Bucle de entrada
    clear_screen()
    print_header()
    print_info(engine)
    print()

    while True:
        redraw()
        key = read_key()

        #TAB: siguiente sugerencia
        if key == "\t":
            if suggestions:
                selected_idx = (selected_idx + 1) % len(suggestions)

        #  SHIFT+TAB
        elif key in ("\x1b[Z", "ESC_[Z", "WIN_\x0f"):
            if suggestions:
                selected_idx = (selected_idx - 1) % len(suggestions)

        # ENTER: enviar
        elif key in ("\r", "\n"):
            if selected_idx >= 0 and suggestions:
                # Autocompletar con la palabra seleccionada
                current_input = suggestions[selected_idx]
                selected_idx  = -1
                suggestions   = []
            elif current_input.strip():
                 # Censura el mensaje

                clean_message = engine.censor_message(current_input.strip())
                # Enviar mensaje

                send_message(clean_message)
                current_input = ""
                selected_idx  = -1
                suggestions   = []

        # ESC: cancelar selección
        elif key == "\x1b":
            selected_idx = -1
            suggestions  = []

        #CTRL+C / CTRL+D: salir
        elif key in ("\x03", "\x04"):
            print(f"\n\n  {Color.YELLOW}Chao manito, todo bien!{Color.RESET}\n")
            sys.exit(0)

        # BACKSPACE
        elif key in ("\x7f", "\x08", "WIN_\x08"):
            current_input = current_input[:-1]
            selected_idx  = -1
            suggestions, elapsed_ms = engine.suggest(current_input)
            if suggestions:
                selected_idx = 0

        # Caracteres normales
        elif len(key) == 1 and key.isprintable():
            current_input += key
            selected_idx = -1

            suggestions, elapsed_ms = engine.suggest(current_input)
            if suggestions:
                selected_idx = 0
            else:
                selected_idx = -1

        #  Teclas de flecha (ignorar)
        elif key.startswith("ESC_[") or key.startswith("WIN_"):
            pass


#  PUNTO DE ENTRADA
def main():
    print(f"\n{Color.CYAN}Cargando vocabulario RPG...{Color.RESET}")
    engine = AutocompleteEngine(RPG_VOCABULARY, BLACKLIST_WORDS)
    print(f"{Color.GREEN} Árbol Rojinegro construido con "
          f"{engine.vocab_size} palabras en {engine.build_time_ms:.2f} ms{Color.RESET}")
    time.sleep(0.8)
    run_chat(engine)


if __name__ == "__main__":
    main()
