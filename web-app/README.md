# LuxeSmile Web App - Browser-Based YOLO Detection

## 🌐 Quick Start

### Local Development
```bash
python -m http.server 8000
# Open http://localhost:8000
```

### Deploy to GitHub Pages
```bash
# Create gh-pages branch
git checkout --orphan gh-pages
git rm -rf .
cp -r web-app/* .
git add .
git commit -m "Deploy web app"
git push origin gh-pages
```

Then enable GitHub Pages in repository settings (Settings → Pages → Deploy from branch → gh-pages).

### Deploy to Netlify
```bash
npm install -g netlify-cli
cd web-app
netlify deploy
```

## 🎨 Features

✅ Real-time camera feed  
✅ YOLO object detection  
✅ FPS counter  
✅ Confidence threshold slider  
✅ Tracking toggle  
✅ Frame capture & download  
✅ Responsive design  
✅ Mobile-friendly  

## 🔧 Integration

### Add Your YOLO Model

Replace the simulated detections in `app.js`:

```javascript
async runDetection() {
    // Load your YOLO model
    const session = await ort.InferenceSession.create('your-model.onnx');
    
    // Preprocess image
    const imageData = this.canvas.getImageData(0, 0, this.canvas.width, this.canvas.height);
    
    // Run inference
    const results = await session.run({'images': imageData});
    
    // Parse results
    return results;
}
```

## 📱 Browser Support

| Browser | Support | Notes |
|---------|---------|-------|
| Chrome | ✅ | Full support |
| Firefox | ✅ | Full support |
| Safari | ✅ | May need HTTPS for camera |
| Edge | ✅ | Full support |
| Mobile Safari | ⚠️ | Limited camera access |

## 🔐 Security

- Camera access requires HTTPS (except localhost)
- No data sent to external servers
- All processing happens locally in browser
- Model runs on user device only

## ⚡ Performance Tips

1. **Reduce input resolution** → Faster inference
2. **Lower confidence threshold** → More detections
3. **Disable tracking** → Slightly faster
4. **Use GPU acceleration** → Install WebGL backend

## 🐛 Troubleshooting

**Camera not showing:**
- Check browser permissions
- Ensure HTTPS (except localhost)
- Check console for errors

**Slow inference:**
- Reduce resolution
- Optimize model (quantization)
- Enable GPU backend

**Model won't load:**
- Check file path
- Verify CORS headers
- Check browser console
