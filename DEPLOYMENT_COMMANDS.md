# 🚀 Quick Deployment Commands

## On LOCAL Machine (Development)

```bash
# 1. Commit and push changes
git add .
git commit -m "Prepare for production deployment"
git push origin master
```

## On VPS Server (Production)

### Fresh Installation (New Server)

```bash
# 1. Connect to VPS
ssh root@docscan.adilabs.id

# 2. Download deployment script
wget https://raw.githubusercontent.com/Adi-Sumardi/doc-scan-ai/master/deploy_to_vps.sh
chmod +x deploy_to_vps.sh

# 3. Run deployment
sudo ./deploy_to_vps.sh
```

### Clean Reinstall (Existing Server)

```bash
# 1. Stop services
sudo systemctl stop docscan-backend
sudo systemctl stop nginx

# 2. Backup data (if needed)
sudo tar -czf /tmp/docscan_backup_$(date +%Y%m%d).tar.gz \
    /var/www/docscan/uploads \
    /var/www/docscan/exports

# 3. Remove old installation
sudo rm -rf /var/www/docscan
sudo userdel -r docScan 2>/dev/null || true
sudo mysql -e "DROP DATABASE IF EXISTS docscan_db;"
sudo mysql -e "DROP USER IF EXISTS 'docuser'@'localhost';"

# 4. Run fresh deployment
cd ~
wget https://raw.githubusercontent.com/Adi-Sumardi/doc-scan-ai/master/deploy_to_vps.sh
chmod +x deploy_to_vps.sh
sudo ./deploy_to_vps.sh
```

### Upload Google Cloud Credentials

```bash
# From local machine
scp backend/config/automation-ai-pajak-c560daf6c6d1.json \
    docScan@docscan.adilabs.id:/var/www/docscan/backend/config/

# On server, verify
sudo su - docScan
ls -l /var/www/docscan/backend/config/
```

### Create Admin User

```bash
# On server
sudo su - docScan
cd /var/www/docscan/backend
source ../venv/bin/activate
python fresh_start.py
```

## Verify Deployment

```bash
# Check backend status
sudo systemctl status docscan-backend

# Check backend logs
sudo journalctl -u docscan-backend -n 50

# Check Nginx status
sudo systemctl status nginx

# Test API
curl https://docscan.adilabs.id/api/health

# Test login
curl -X POST https://docscan.adilabs.id/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

## Maintenance Commands

```bash
# Restart backend
sudo systemctl restart docscan-backend

# Reload Nginx
sudo systemctl reload nginx

# View real-time logs
sudo journalctl -u docscan-backend -f

# Update application
sudo su - docScan
cd /var/www/docscan
git pull
source venv/bin/activate
pip install -r backend/requirements.txt
exit
sudo systemctl restart docscan-backend

# Update frontend
cd /var/www/docscan
npm install
npm run build
sudo cp -r dist/* /var/www/docscan/dist/
sudo systemctl reload nginx
```

## Troubleshooting

```bash
# Check which port is using 8000
sudo lsof -i :8000

# Kill process on port 8000
sudo kill -9 $(sudo lsof -t -i:8000)

# Check MySQL connection
mysql -u docuser -p docscan_db

# Check file permissions
ls -la /var/www/docscan/

# Fix permissions
sudo chown -R docScan:docScan /var/www/docscan/
sudo chmod -R 755 /var/www/docscan/
sudo chmod 600 /var/www/docscan/backend/.env
```
