import { mkdir, readFile } from 'node:fs/promises';
import { dirname, join, relative, resolve, sep, isAbsolute } from 'node:path';
import { fileURLToPath } from 'node:url';
import sharp from 'sharp';
import { getSharePreviewPath, isLocalPublicImage } from '../src/lib/share-preview-path.mjs';

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const publicDirectory = join(projectRoot, 'public');
const catalogPath = join(projectRoot, 'src', 'data', 'productos.json');
const catalog = JSON.parse(await readFile(catalogPath, 'utf8'));
const entries = [];

for (const [collectionKey, items] of Object.entries(catalog)) {
  if (['listasPersonalizadas', 'ordenColecciones', 'guiasVisuales'].includes(collectionKey) || !Array.isArray(items)) continue;
  for (const item of items) {
    if (!item || typeof item.id !== 'number' || typeof item.nombre !== 'string') continue;
    entries.push({
      type: 'original',
      collectionKey,
      itemId: item.uid || String(item.id),
      media: item.galeria,
    });
  }
}

for (const list of catalog.listasPersonalizadas ?? []) {
  for (const row of list.filas ?? []) {
    entries.push({
      type: 'lista',
      collectionKey: list.clave,
      itemId: row.uid || String(row.id),
      media: row.galeria,
    });
  }
}

let generatedCount = 0;

for (const entry of entries) {
  const image = entry.media?.find((item) => item.tipo === 'imagen' || !item.tipo);
  if (!image || !isLocalPublicImage(image.src)) continue;

  const imageUrl = new URL(image.src, 'https://local.invalid');
  const inputPath = resolve(publicDirectory, `.${decodeURIComponent(imageUrl.pathname)}`);
  const relativeInputPath = relative(publicDirectory, inputPath);
  if (relativeInputPath.startsWith(`..${sep}`) || relativeInputPath === '..' || isAbsolute(relativeInputPath)) {
    throw new Error(`La imagen para compartir debe estar dentro de public/: ${image.src}`);
  }

  const outputPath = join(projectRoot, 'public', getSharePreviewPath(entry.type, entry.collectionKey, entry.itemId).replaceAll('/', sep).replace(/^\\/, ''));
  await mkdir(dirname(outputPath), { recursive: true });

  try {
    await sharp(inputPath)
      .rotate()
      .resize(1200, 630, {
        fit: 'contain',
        background: { r: 255, g: 255, b: 255, alpha: 1 },
      })
      .jpeg({ quality: 85 })
      .toFile(outputPath);
  } catch (error) {
    throw new Error(`No se pudo generar la vista previa para ${entry.type}/${entry.collectionKey}/${entry.itemId} desde ${image.src}`, { cause: error });
  }

  generatedCount += 1;
}

console.log(`Vistas previas de redes generadas: ${generatedCount}`);
