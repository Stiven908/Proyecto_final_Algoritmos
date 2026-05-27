# Chat RPG — Sistema de Autocompletado

Proyecto final de Algoritmos. Chat de consola con autocompletado en tiempo real usando un **Árbol Rojinegro** y **búsqueda binaria**.

## Ejecución

```bash
python main.py
```

> Requiere **Python 3.10+** y **Windows** (la lectura de teclado raw usa `msvcrt`).

## Controles

| Tecla        | Acción                              |
|--------------|-------------------------------------|
| Cualquier letra | Escribe y activa sugerencias     |
| `TAB`        | Siguiente sugerencia                |
| `SHIFT+TAB`  | Sugerencia anterior                 |
| `ENTER`      | Aceptar sugerencia / Enviar mensaje |
| `ESC`        | Cancelar sugerencia activa          |
| `BACKSPACE`  | Borrar último carácter              |
| `CTRL+C`     | Salir                               |

## Estructura

```
├── main.py          # Bucle principal, UI y manejo de teclado
├── autocomplete.py  # Árbol Rojinegro, Lista Negra y AutocompleteEngine
└── vocabulary.py    # Vocabulario RPG y lista de palabras prohibidas
```

## Estructuras de datos

- **Árbol Rojinegro** (`RedBlackTree`): almacena el vocabulario ordenado. Búsqueda de prefijos en O(log n).
- **Lista Negra** (`Blacklist`): lista ordenada + `bisect` de la stdlib. Búsqueda en O(log n).
- **AutocompleteEngine**: integra ambas estructuras; filtra sugerencias antes de mostrarlas.
