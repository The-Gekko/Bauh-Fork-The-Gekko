# ¿Cómo puedo contribuir?
Bueno, puedes...
* Reportar errores (bugs)
* Proponer mejoras
* Corregir errores
* Añadir nuevas traducciones o corregir las existentes

# Reportar errores
El mejor medio para reportar errores es siguiendo estas pautas básicas:

* Primero describe en el título del reporte de problemas (issue tracker) qué es lo que ha fallado.
* En el cuerpo, explica un resumen básico de lo que ocurre exactamente, detallando cómo llegaste al error paso a paso. Si incluyes la salida de algún script, asegúrate de ejecutar el script con la bandera de depuración detallada `-v`.
* Explica qué esperabas que ocurriera y qué ocurrió realmente.
* Opcionalmente, si eres programador, puedes intentar enviar un pull request tú mismo para solucionar el problema.

# Proponer mejoras
El camino a seguir aquí es preguntarte si la mejora sería útil para más de una sola persona; si es apta para un caso de uso común, ¡adelante!

* En cualquier pull request, explica detalladamente qué cambios realizaste.
* Explica por qué crees que estos cambios podrían ser útiles.
* Si corrige un error, asegúrate de enlazarlo con el reporte de error (issue) correspondiente.
* Sigue el estilo de código [PEP 8](https://www.python.org/dev/peps/pep-0008/) para mantener la coherencia del código.
* **Configuración del Entorno:** Utilizamos `pyproject.toml` (PEP 517/518). Asegúrate de tener Python >= 3.8 y realiza pruebas locales usando `pipx install -e .` o un entorno virtual dedicado antes de enviar tus cambios.

# Añadir una nueva traducción
* Para añadir una nueva traducción, tendrás que crear un archivo en cada uno de los directorios listados a continuación con el nombre correspondiente a las dos primeras letras del idioma en formato ISO (por ejemplo: para 'español' sería 'es', para 'inglés' sería 'en'):
- `bauh/view/resources/locale`
- `bauh/gems/appimage/resources/locale`
- `bauh/gems/arch/resources/locale`
- `bauh/gems/flatpak/resources/locale`
- `bauh/gems/snap/resources/locale`
- `bauh/gems/web/resources/locale`
- `bauh/gems/debian/resources/locale`
