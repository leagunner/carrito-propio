const body = `User-agent: *
Allow: /

Sitemap: https://catalogo-metalurgica-exhibe.web.app/sitemap.xml
`;

export const GET = () => new Response(body, {
  headers: {
    'Content-Type': 'text/plain; charset=utf-8',
  },
});
