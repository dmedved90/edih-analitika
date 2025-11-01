# EDIH ADRIA Analytics Dashboard

Enhanced production-ready analytics dashboard for EDIH ADRIA services with improved security, performance, and maintainability.

## 🧠 EDIH Analitika

**EDIH-Analitika** je Streamlit aplikacija razvijena za analizu i izvještavanje
u okviru projekata Europskih Digitalnih Inovacijskih Hubova (EDIH).
Aplikacija omogućuje:
- automatsku obradu DMA PDF izvještaja,
- AI OCR ekstrakciju i sažimanje (GPT-4o-mini),
- interaktivne grafove i tablične preglede,
- keširanje i generiranje agregiranih analiza.


## 🚀 Pokretanje aplikacije

### 1️⃣ Kloniraj repo
```bash
git clone https://github.com/<tvoj_username>/EDIH-Analitika.git
cd EDIH-Analitika
```

### 2. Create virtual environment

```bash
python3 -m venv venv
source venv/bin/activate  # na Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
# Copy example env file
cp .env.example .env

ili kreiraj

 .streamlit/secrets.toml

[deepseek]
api_key = "sk-XXXX..."


# Edit .env and add your API keys
nano .env  # or use your preferred editor
```

Required environment variables:
- `OPENAI_API_KEY`: Your OpenAI API key
- `DEEPSEEK_API_KEY`: Your DeepSeek API key
- `APP_FOLDER_WINDOWS`: Path to data folder (Windows)
- `APP_FOLDER_LINUX`: Path to data folder (Linux/Mac)

### 5. Prepare data directory structure

```
EDIH/
├── Data/
│   ├── EDIH_uploaded_services_102025.xlsx
│   ├── export-sme-102025.xlsx
│   ├── export-pso-102025.xlsx
│   ├── my-smes-dma-results-102025.xlsx
│   ├── my-psos-dma-results-102025.xlsx
│   ├── evidencija-zahtjeva-062025.xlsx
│   └── updated_edih_list_with_columns_022025.xlsx
├── DMA/
│   ├── SME/
│   │   └── JSON/
│   └── PSO/
│       └── JSON/
└── Slike/
    ├── Edih-Adria-svijetli.ico
    ├── SyntAgent-lila.png
    └── Edih Adria znak+logotip.jpg
```

## 🚀 Running the Application

### Development

```bash
streamlit run app.py
```

### Production

```bash
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
```

## 📁 Project Structure

```
.
├── EDIH-Analitika.py     # Main application
├── requirements.txt      # Python dependencies
├── .env.example          # Environment variables template
├── .gitignore            # Git ignore rules
└── README.md             # This file
```

## 🔒 Security Features

1. **No Hardcoded Secrets**: All API keys and sensitive data in environment variables
2. **Input Validation**: Configuration validation on startup
3. **Error Handling**: Comprehensive error handling with logging
4. **Secure Defaults**: Safe defaults for all configuration options

## 📊 Performance Optimizations

1. **Data Caching**: Streamlit cache for data loading (1-hour TTL)
2. **Lazy Loading**: Data loaded only when needed
3. **Efficient Queries**: Optimized pandas operations
4. **Resource Caching**: AI clients initialized once and cached

## 📝 Logging

Logs are written to:
- Console: INFO level and above
- File: All levels (configurable in `.env`)

Default log location: `logs/edih_app.log`

### Log Levels

- `DEBUG`: Detailed information for debugging
- `INFO`: General informational messages
- `WARNING`: Warning messages
- `ERROR`: Error messages

Configure in `.env`:
```
LOG_LEVEL=INFO
LOG_FILE=logs/edih_app.log
```

## 🧪 Testing

```bash
# Run with verbose logging
LOG_LEVEL=DEBUG streamlit run app.py
```

## 📦 Deployment

### Docker (Recommended)

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "EDIH-Analitika.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### Cloud Platforms

#### Streamlit Cloud
1. Push to GitHub
2. Connect to Streamlit Cloud
3. Add secrets in dashboard settings

#### Heroku
```bash
heroku create edih-analytics
heroku config:set OPENAI_API_KEY=your_key_here
git push heroku main
```

## 🔧 Configuration Options

All configuration in `config.py`:

- `TARGET_REVENUE`: Revenue target (default: 2,645,000)
- `TARGET_CUSTOMERS_DMA`: DMA customers target (default: 120)
- `TARGET_CUSTOMERS_BOOTCAMP`: Bootcamp target (default: 85)
- `CACHE_TTL`: Cache time-to-live in seconds (default: 3600)

## 🐛 Troubleshooting

### Common Issues

**1. Import errors**
```bash
# Ensure virtual environment is activated
pip install -r requirements.txt
```

**2. Tesseract not found**
```bash
# Install Tesseract OCR
sudo apt install tesseract-ocr -y
```

**3. Data files not found**
- Check `APP_FOLDER` path in `.env`
- Verify file structure matches expected layout

**4. API errors**
- Verify API keys in `.env`
- Check API key validity and quotas

## 📈 Monitoring

View logs:
```bash
tail -f logs/edih_app.log
```

## 🤝 Contributing

1. Create feature branch
2. Make changes
3. Test thoroughly
4. Submit pull request

## 📄 License

[Add your license here]

## 👥 Authors

- UNIRI - University of Rijeka
- Syntagent - UNIRI spin-off

## 📞 Support

For issues and questions:
- Email: support@edihadria.eu
- GitHub Issues: [repository]/issues

## 🔄 Version History

- **v5.0** (2025-10-29): Production-ready version with security and performance enhancements
- **v4.0** (2025-03-20): Previous version

## ⚠️ Important Notes

1. **Never commit `.env` file** - contains sensitive API keys
2. **Keep data files separate** - excluded from git by default
3. **Monitor logs regularly** - check for errors and warnings
4. **Update dependencies** - regularly check for security updates

## 🎯 Roadmap

- [ ] Database integration (MariaDB)
- [ ] Real-time data updates
- [ ] Advanced caching strategies
- [ ] User authentication
- [ ] API endpoints for external access
- [ ] Automated testing suite
- [ ] Performance monitoring dashboard
