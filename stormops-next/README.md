# StormOps Next.js App

Next.js rewrite of StormOps dashboard with WWE-style theming.

## Setup

```bash
cd stormops-next
npm install
npm run dev
```

## Deploy

Deploy to Vercel, Railway, or any Node.js hosting:

```bash
npm run build
npm start
```

## Structure

- `src/app` - Next.js 14 App Router pages
- `src/components` - React components (Sidebar, Header)
- `src/data` - Demo data (routes, jobs, leads)
- `tailwind.config.js` - WWE-style theme (orange primary)
- `postcss.config.js` - Tailwind + Autoprefixer
