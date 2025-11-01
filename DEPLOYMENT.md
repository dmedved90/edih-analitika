# Deployment Guide

## Docker Deployment

```bash
# Build
docker build -t edih-analytics .

# Run
docker run -d -p 8501:8501 --env-file .env edih-analytics

# Or use docker-compose
docker-compose up -d
```

## Cloud Deployment

### Streamlit Cloud
1. Push to GitHub
2. Connect at share.streamlit.io
3. Add secrets in settings

### Heroku
```bash
heroku create edih-analytics
heroku config:set OPENAI_API_KEY=sk-...
git push heroku main
```

## Monitoring
```bash
# View logs
docker logs -f edih-analytics

# Check health
curl http://localhost:8501/_stcore/health
```
