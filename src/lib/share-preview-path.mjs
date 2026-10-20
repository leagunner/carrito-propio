import { createHash } from 'node:crypto';

export const getSharePreviewPath = (type, collectionKey, itemId) => {
  const key = `${type}/${collectionKey}/${itemId}`;
  const filename = createHash('sha256').update(key).digest('hex');
  return `/images/share-previews/${filename}.jpg`;
};

export const isLocalPublicImage = (src) => (
  typeof src === 'string'
  && src.startsWith('/')
  && !src.startsWith('//')
);
