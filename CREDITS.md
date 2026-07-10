# Créditos y Agradecimientos

**Bauh** fue originalmente conceptualizado y creado por **[Vinicius Moreira](https://github.com/vinifmor)** como una herramienta robusta para administrar aplicaciones en Linux. Agradecemos enormemente su excelente base y las contribuciones de los colaboradores del proyecto original.

## Modernización y Fork
Este repositorio en particular es un **Fork Modernizado**, altamente refactorizado, optimizado y mejorado por **thegekko**.

### Mejoras Clave en este Fork:
- **Arquitectura**: Rediseño completo de clases monolíticas (como `ManageWindow`) en Mixins de Python para una mejor escalabilidad y código más limpio.
- **Rendimiento**: Optimizaciones profundas que incluyen carga perezosa (lazy-loading), pausas de renderizado en la interfaz (`setUpdatesEnabled(False)`) y la eliminación de bucles ineficientes de espera activa (busy-waiting) de CPU.
- **Estética**: Introducción del hermoso **tema Aurora** para llevar la interfaz de usuario a los estándares modernos.
- **Sistema de Construcción**: Migración a un sistema de construcción moderno compatible con PEP-517/518 utilizando `pyproject.toml`.
- **Instalador Fácil**: Creación de un script `install.sh` simplificado, colorido y a prueba de errores que aprovecha `pipx`.

Si te gustan estas mejoras, ¡considera darle una estrella a este repositorio!
