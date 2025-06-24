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

## 🧩 Requisiti

| Componente      | Descrizione                                               |
|------------------|-----------------------------------------------------------|
| Python           | 3.11                                                      |
| wkhtmltopdf      | Programma esterno per convertire HTML in PDF              |
| OpenAI API Key   | Necessaria per generare embedding e prompt                |
| Jira API Token   | Accesso al tuo workspace Jira cloud                       |

---
## Installare wkhtmltopdf (obbligatorio)
wkhtmltopdf è un programma esterno che converte HTML in PDF. È richiesto per far funzionare STEEMO correttamente.

👉 Windows
Vai su: https://wkhtmltopdf.org/downloads.html

Scarica Windows 64-bit (MSVC)

Installa lasciando il percorso predefinito

Nel file .env, imposta il path così:

WKHTML_PATH=C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe

## Embeddings
scaricare embeddings per database vettoriale https://drive.google.com/file/d/1tQhXguzVyvwrlQz6ysLBkApFc7j7KiG_/view?usp=sharing e inserire il file nella cartella data come in esempio

## 🚀 Step 6 – Avviare l’applicazione
uvicorn app.main:app --reload