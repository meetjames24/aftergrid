# Aftergrid landing page

Static site. No build step.

## Deploy to Vercel
- Drag this folder into vercel.com/new (or `vercel --prod` inside it). Framework preset: "Other". No build command, output directory: `.`
- Add the domain getaftergrid.com in the project's Domains settings.

## Before you launch: set the Buy link
Open `index.html`, find `const CONFIG` near the bottom, paste your checkout link:

    buyUrl: "https://buy.stripe.com/xxxxxxxx",

Every "Buy now" button uses it. While it's empty, the buttons scroll to the pricing section.
(Stripe Payment Link at $19.99 → after-payment redirect to a page with the download links.)

## GitHub link
`githubUrl` in the same CONFIG. The repo must be **public** for visitors to open it.

## Free download on the page
`downloads/aftergrid-first-aid-diagrams.zip`: the 14 first-aid diagrams.
