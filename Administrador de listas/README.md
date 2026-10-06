# Administrador de listas

Aplicación de escritorio para editar el catálogo Astro de Metalúrgica Exhibe.

## Optimización de imágenes

Al importar una imagen, el programa la convierte automáticamente a WebP con calidad 82 y limita su lado mayor a 1600 píxeles. La versión optimizada se guarda en `public/images` y es la ruta que se escribe en el JSON.

El archivo original se conserva en `Administrador de listas/originales` por seguridad. Los GIF animados no se convierten automáticamente; deben importarse como JPG o PNG si se desea optimizarlos.

## Ejecutar

Desde esta carpeta:

```powershell
python -m pip install -r requirements.txt
python app.py
```

Al iniciar, el programa carga automáticamente `src/data/productos.json` a partir de la ubicación del propio administrador, aunque la raíz del proyecto cambie entre computadoras. El botón `Elegir lista JSON` permite seleccionar manualmente otro archivo cuando sea necesario. El programa calcula automáticamente la raíz del proyecto para ubicar las imágenes y los backups.

La barra lateral permite editar el título de una lista personalizada sin cambiar su clave interna, crear listas nuevas y eliminar listas con confirmación.

Cuando una lista tiene muchas columnas, la grilla de filas dispone de una barra de desplazamiento horizontal.

## Funciones actuales

- Editar campos de productos existentes.
- Crear, duplicar y eliminar productos o filas.
- Crear listas personalizadas desde un editor integrado, sin ventanas consecutivas.
- Generar automáticamente la clave técnica de cada lista a partir del título.
- Agregar y quitar columnas y filas desde la misma pantalla.
- Editar el texto de cada celda.
- Agregar varias imágenes a la vez por producto o fila, copiándolas a `public/images`.
- Administrar imágenes explicativas de la colección seleccionada, tanto original como personalizada.
- Agregar imágenes y videos de YouTube, reordenarlos y quitar elementos desde el botón de la colección.
- Editar el texto descriptivo accesible de cada imagen o video explicativo desde el elemento seleccionado.
- Guardar las guías en el bloque opcional `guiasVisuales` de `productos.json`, separadas de las galerías de productos y filas.
- Optimizar las guías a WebP en `public/images/explicaciones/<clave-lista>/`.
- Reordenar la galería con los botones `Subir` y `Bajar`; el orden se conserva en el JSON.
- Reordenar todas las colecciones, originales y personalizadas, con los botones `Subir` y `Bajar`.
- Agregar enlaces de YouTube a productos y filas.
- Validar la estructura antes de guardar.
- Crear un backup fechado antes de cada guardado.
- Guardar el JSON mediante un archivo temporal.

## Crear ejecutable portable

Con Python instalado:

```powershell
python -m pip install pyinstaller
pyinstaller --noconsole --onedir --name AdministradorListas app.py
```

El ejecutable queda dentro de `dist/AdministradorListas/`.

## Formato de listas personalizadas

El programa agrega una colección `listasPersonalizadas` al JSON cuando se crea la primera lista. Cada fila tiene sus valores en `celdas` y su galería independiente:

```json
{
  "clave": "servicios",
  "titulo": "Servicios",
  "columnas": [
    { "clave": "columna-1", "nombre": "Servicio" }
  ],
  "filas": [
    {
      "id": 1,
      "celdas": { "columna-1": "Corte" },
      "galeria": []
    }
  ]
}
```

Las imágenes no se eliminan automáticamente del disco cuando se quitan de una galería.

Las guías explicativas aceptan imágenes existentes con `src` y `alt`, o videos de YouTube con `tipo`, `src` y `alt`. Los videos se reproducen dentro de la guía web mediante un reproductor embebido.

El orden de las colecciones se guarda en `ordenColecciones`. Las categorías originales usan su clave, por ejemplo `jaulas`, y las listas personalizadas usan `lista:clave-de-la-lista`.
