# 🚀 STEEMO – Story Estimation

**STEEMO** è un assistente intelligente per stimare automaticamente le user story presenti in Jira e confrontarle semanticamente con task simili già svolti. Utilizza OpenAI (GPT) e FAISS per garantire stime coerenti e motivate, anche includendo immagini e PDF generati dalla descrizione della task.


---

## 🎯 Cosa fa

- Estima una user story Jira tramite GPT
- Analizza immagini e PDF associati alla story
- Confronta semanticamente il contenuto con attività precedenti
- Restituisce una stima motivata + coerenza basata su task simili
- Supporta immagini integrate, PDF dinamici, e ricerca semantica FAISS

---
## env
copiare il file .env.example in .env (le due api sono contenute in last pass)

## 🐳 Avvio con Docker 
- docker build -t steemo-app .

- docker run -d -p 8000:80 --env-file .env --name steemo steemo-app
