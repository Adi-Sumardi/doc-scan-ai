# Doc Scan AI - Production Ready

A professional document scanning and OCR processing application with AI-powered text extraction for Indonesian tax documents.

## 🚀 Features

- **Multi-Document Support**: Faktur Pajak, PPh 21, PPh 23, Rekening Koran, Invoice
- **Raw OCR Text Display**: Pure scan results without structured parsing
- **Export Functionality**: Excel and PDF exports with complete OCR data
- **Real-time Processing**: WebSocket-based real-time document processing
- **Modern UI**: React TypeScript frontend with Tailwind CSS

## 📋 System Requirements

### Backend
- Python 3.10+
- FastAPI
- OpenCV, EasyOCR, RapidOCR
- SQLAlchemy, Redis (optional)

### Frontend
- Node.js 18+
- React 18
- TypeScript
- Vite

## 🛠 Production Deployment

### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv doc_scan_env
source doc_scan_env/bin/activate  # Linux/Mac
# doc_scan_env\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your production settings

# Run production server
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 2. Frontend Setup

```bash
# Install dependencies
npm install

# Build for production
npm run build

# Preview production build
npm run preview

# Or serve with a static server
npx serve -s dist -l 3000
```

### 3. Environment Variables

Create `.env` file in backend directory:

```env
# Database
DATABASE_URL=sqlite:///./app.db

# Redis (optional)
REDIS_URL=redis://localhost:6379

# Security
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256

# File Upload
MAX_FILE_SIZE=10485760  # 10MB
UPLOAD_DIR=./uploads
EXPORT_DIR=./exports

# OCR Settings
OCR_CONFIDENCE_THRESHOLD=0.6
MAX_PROCESSING_TIME=300  # 5 minutes
```

### 4. Production Checklist

- [ ] Set secure `SECRET_KEY` in environment
- [ ] Configure proper database (PostgreSQL recommended)
- [ ] Set up Redis for caching (optional)
- [ ] Configure reverse proxy (Nginx)
- [ ] Set up SSL/TLS certificates
- [ ] Configure log rotation
- [ ] Set up monitoring and health checks
- [ ] Configure backup strategy for uploads

## 🐳 Docker Deployment

### Using Docker Compose

```yaml
version: '3.8'
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/docscanner
    volumes:
      - ./backend/uploads:/app/uploads
      - ./backend/exports:/app/exports
    depends_on:
      - db

  frontend:
    build: .
    ports:
      - "3000:3000"
    depends_on:
      - backend

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=docscanner
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

### Run with Docker

```bash
# Build and start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## 🔧 Production Configuration

### Nginx Configuration

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Frontend
    location / {
        root /path/to/dist;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket support
    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

### Systemd Service (Linux)

Create `/etc/systemd/system/docscanner-backend.service`:

```ini
[Unit]
Description=Doc Scanner Backend
After=network.target

[Service]
Type=exec
User=www-data
WorkingDirectory=/path/to/backend
Environment=PATH=/path/to/backend/doc_scan_env/bin
ExecStart=/path/to/backend/doc_scan_env/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable docscanner-backend
sudo systemctl start docscanner-backend
```

## 📊 Monitoring

### Health Check Endpoints

- `GET /health` - Basic health check
- `GET /metrics` - Application metrics (if implemented)

### Log Monitoring

Logs are written to:
- Backend: `backend/logs/app.log`
- Access logs: Configure through uvicorn/gunicorn

## 🔐 Security Considerations

1. **Environment Variables**: Never commit `.env` files
2. **File Upload Security**: Validate file types and sizes
3. **CORS**: Configure proper CORS settings for production
4. **Rate Limiting**: Implement rate limiting for API endpoints
5. **Input Validation**: Sanitize all user inputs
6. **HTTPS**: Always use HTTPS in production

## 📝 API Documentation

Once deployed, API documentation is available at:
- Swagger UI: `http://your-domain/docs`
- ReDoc: `http://your-domain/redoc`

## 🚨 Troubleshooting

### Common Issues

1. **OCR Libraries**: Ensure all OCR dependencies are installed
2. **File Permissions**: Check write permissions for uploads/exports
3. **Memory Usage**: Monitor memory usage during OCR processing
4. **Database Connections**: Configure proper connection pooling

### Performance Optimization

- Use Redis for caching
- Configure proper worker processes
- Implement file cleanup strategies
- Monitor and optimize OCR processing times

## 📞 Support

For production support and issues:
- Check logs first
- Verify environment configuration
- Monitor system resources
- Check database connectivity

---

**Production Ready** ✅ | **Scalable** ⚡ | **Secure** 🔒