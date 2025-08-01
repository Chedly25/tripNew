# 🎨 Adding Your Logo to the Travel Planner

Your website is now configured to display logos in two places:

## 1. Browser Tab/Favicon (Required)
Add these logo files to `src/static/`:

- **favicon.ico** (16x16, 32x32 format) - Main browser tab icon
- **logo-16.png** (16x16 PNG) - Small favicon
- **logo-32.png** (32x32 PNG) - Standard favicon  
- **logo-180.png** (180x180 PNG) - Apple touch icon

## 2. Website Header Logo (Optional)
Add this file to `src/static/`:

- **logo.png** (Recommended: 60px height, transparent background) - Main header logo

## 🛠️ How to Add Your Logos

### Option A: Use AI Logo Generators
1. **Canva**, **Figma**, or **Logo.com** to create a travel-themed logo
2. Export in PNG format with transparent background
3. Create different sizes as needed

### Option B: Use Font Awesome Icons (Current Fallback)
The site currently uses a map icon (`fa-map-marked-alt`) as fallback
- No files needed, works immediately
- Automatically styled with your site's colors

### Option C: Use Free Travel Icons
1. Download from **Icons8**, **Flaticon**, or **Freepik**
2. Search for: "travel", "map", "route", "compass", "road trip"
3. Download as PNG with transparent background

## 📁 File Structure
```
src/
├── static/
│   ├── favicon.ico         ← Browser tab icon (required)
│   ├── logo.png           ← Header logo (optional)
│   ├── logo-16.png        ← Small favicon
│   ├── logo-32.png        ← Standard favicon
│   └── logo-180.png       ← Apple touch icon
└── templates/
    ├── travel_planner_main.html
    └── travel_results_enhanced.html
```

## 🎨 Logo Recommendations

**Style**: Clean, modern, travel-themed  
**Colors**: Blue/purple gradient (matches your site theme)  
**Elements**: Maps, routes, compass, road, mountains, or planes  
**Format**: PNG with transparent background  
**Size**: 60px height for header, various sizes for favicons  

## 🚀 Deploy to Heroku

After adding your logo files:
```bash
git add src/static/
git commit -m "Add logo and branding assets"
git push heroku master
```

Your logo will appear in:
- ✅ Browser tabs (favicon)
- ✅ Bookmarks
- ✅ Website header (if logo.png provided)
- ✅ Mobile home screen icons

## 🔧 Testing

Visit your site and check:
1. Browser tab shows your favicon
2. Header shows your logo (or falls back to icon)
3. Mobile devices show proper touch icons