# 📘 EDIH Analitika

**EDIH Analitika** je Streamlit aplikacija za interaktivnu analizu i vizualizaciju podataka prikupljenih kroz aktivnosti **EDIH ADRIA** centra.

Aplikacija omogućuje:
- automatsko učitavanje najnovijih Excel i PDF datoteka iz `data/` direktorija,  
- pregled i usporedbu pruženih usluga SME i PSO korisnicima,  
- analizu napretka kroz DMA procjene (T0, T1, T2),  
- prikaz AI sažetaka PDF izvještaja.

---

## ⚙️ Instalacija i pokretanje

### Preduvjeti
- Python 3.10+
- Virtualno okruženje (`venv`)
- Instalirani paketi iz `requirements.txt`

### Instalacija

```bash
cd EDIH
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
### Pokretanje

```bash

streamlit run EDIH-Analitika.py
```
Aplikacija će se otvoriti na: http://localhost:8501

## 🎯 Roadmap

- [ ] Database integration (MariaDB)
- [ ] Real-time data updates
- [ ] Advanced caching strategies
- [ ] User authentication
- [ ] API endpoints for external access
- [ ] Automated testing suite
- [ ] Performance monitoring dashboard
