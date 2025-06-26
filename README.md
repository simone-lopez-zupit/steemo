# 🚀 STEEMO – Story Estimation

**STEEMO** è un assistente intelligente per stimare automaticamente le user story presenti in Jira e confrontarle semanticamente con task simili già svolti. Utilizza OpenAI (GPT) e FAISS per garantire stime coerenti e motivate.


---

## 🎯 Cosa fa

- Stima una user story Jira
- Confronta semanticamente il contenuto con attività precedenti
- Restituisce una stima motivata + coerenza basata su task simili
- Supporta ricerca semantica FAISS

---
## env
copiare il file .env.example in .env (le due api sono contenute in last pass)

## 🐳 Avvio con Docker 
- docker build -t steemo-app .

- docker run -d -p 8000:80 --env-file .env --name steemo steemo-app

# Swagger 
Apri Swagger UI 👉 http://localhost:8000/docs

