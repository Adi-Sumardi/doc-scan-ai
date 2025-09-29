# 🚀 Hostinger Deployment Guide for docscan.adilabs.id

## Overview
This guide covers the complete deployment process for the Doc Scan AI application on Hostinger hosting with the domain `docscan.adilabs.id`.

## Prerequisites
- Hostinger hosting account with Python support
- Domain `docscan.adilabs.id` configured in Hostinger
- FTP/SFTP access or File Manager access
- MySQL database access

## Deployment Steps

### 1. Domain Configuration
1. Log into your Hostinger panel
2. Navigate to Domains → Manage
3. Add `docscan.adilabs.id` to your hosting account
4. Point the domain to your hosting directory

### 2. Database Setup
1. Create a new MySQL database in Hostinger panel
2. Note the database credentials:
   - Database name
   - Username
   - Password
   - Host (usually localhost)

### 3. File Upload
Upload the following files to your hosting account:

```
public_html/
├── index.html (from dist/)
├── assets/ (from dist/assets/)
├── .htaccess
├── api.php
├── backend/
│   ├── *.py files
│   ├── requirements.txt
│   └── .env
├── uploads/ (empty directory)
├── exports/ (empty directory)
└── logs/ (empty directory)
```

### 4. Environment Configuration
Update the `.env` file in the backend directory:

```env
# Production Database Configuration
DATABASE_URL=mysql://username:password@localhost/database_name

# Domain Configuration
FRONTEND_URL=https://docscan.adilabs.id
BACKEND_URL=https://docscan.adilabs.id/api.php

# File Storage
UPLOAD_FOLDER=/home/username/public_html/uploads
EXPORT_FOLDER=/home/username/public_html/exports

# Security
SECRET_KEY=your-production-secret-key-here
ENVIRONMENT=production

# OCR Configuration
DEFAULT_OCR_ENGINE=paddleocr
ENABLE_CLOUD_OCR=false

# Cache
REDIS_URL=redis://localhost:6379/0
ENABLE_REDIS_CACHE=false
```

### 5. Python Setup (if supported)
If your Hostinger plan supports Python:

```bash
# SSH into your hosting account
ssh username@your-server.hostinger.com

# Navigate to your domain directory
cd ~/public_html

# Create virtual environment
python3 -m venv doc_scan_env
source doc_scan_env/bin/activate

# Install dependencies
cd backend
pip install -r requirements.txt

# Run migrations (if needed)
python database.py
```

### 6. Alternative: PHP Proxy Method
If Python is not directly supported, use the PHP proxy approach:

1. The `api.php` file acts as a proxy to route API calls
2. Run the Python backend on a custom port
3. Configure the proxy to forward requests

### 7. SSL Certificate
1. In Hostinger panel, navigate to SSL
2. Enable SSL for `docscan.adilabs.id`
3. Force HTTPS redirects

### 8. Testing
1. Visit `https://docscan.adilabs.id`
2. Test file upload functionality
3. Verify OCR processing works
4. Check export functionality

## File Structure After Deployment

```
public_html/
├── index.html                 # React app entry point
├── assets/                    # CSS, JS, images
├── .htaccess                  # Apache configuration
├── api.php                    # PHP proxy (if needed)
├── backend/                   # Python backend
│   ├── main.py
│   ├── ai_processor.py
│   ├── requirements.txt
│   └── .env
├── uploads/                   # Uploaded documents
├── exports/                   # Generated exports
└── logs/                      # Application logs
```

## Troubleshooting

### Common Issues

1. **403 Forbidden Error**
   - Check directory permissions (755)
   - Verify .htaccess syntax

2. **API Not Working**
   - Check PHP proxy configuration
   - Verify Python backend is running
   - Check database connection

3. **File Upload Issues**
   - Verify upload directory permissions
   - Check PHP upload limits
   - Ensure sufficient disk space

4. **OCR Processing Errors**
   - Check Python dependencies
   - Verify OCR library installation
   - Check memory limits

### Performance Optimization

1. **Frontend Caching**
   - Configure .htaccess cache headers
   - Use CDN if available

2. **Backend Optimization**
   - Enable Redis cache if available
   - Optimize database queries
   - Use connection pooling

3. **File Management**
   - Set up cleanup cron jobs
   - Monitor disk usage
   - Implement file rotation

## Monitoring and Maintenance

### Log Files
- Application logs: `~/public_html/logs/`
- Access logs: Check Hostinger panel
- Error logs: Check Hostinger panel

### Regular Tasks
1. Monitor disk usage
2. Check application logs
3. Update dependencies periodically
4. Backup database regularly

### Cron Jobs (Optional)
```bash
# Cleanup old files (daily at 2 AM)
0 2 * * * /usr/bin/find ~/public_html/uploads -type f -mtime +7 -delete

# Backup database (weekly)
0 3 * * 0 mysqldump -u username -p database_name > ~/backups/docscan_$(date +\%Y\%m\%d).sql
```

## Support
For technical issues:
1. Check Hostinger documentation
2. Review application logs
3. Test API endpoints individually
4. Contact Hostinger support for hosting issues

## Security Considerations
1. Regular security updates
2. Strong database passwords
3. HTTPS enforcement
4. Input validation
5. File upload restrictions
6. Access logging

---

**Last Updated**: Production deployment ready
**Domain**: docscan.adilabs.id
**Version**: 1.0.0 Production