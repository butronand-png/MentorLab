# MentorMatch · EPIC Lab
### Setup & Deploy en 5 minutos

---

## 📁 Estructura de archivos

```
mentormatch/
├── app.py               ← app principal
├── mentors.json         ← base de datos de mentores
├── system_prompt.txt    ← cerebro del chatbot
├── requirements.txt     ← dependencias
└── .streamlit/
    └── secrets.toml     ← API key (NO subir a GitHub)
```

---

## 🖥️ Correr en local

### 1. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 2. Crear archivo de secrets
Crea la carpeta `.streamlit` y dentro el archivo `secrets.toml`:
```toml
ANTHROPIC_API_KEY = "sk-ant-..."
```

### 3. Correr la app
```bash
streamlit run app.py
```
Abre tu navegador en: http://localhost:8501

---

## 🌐 Deploy en Streamlit Cloud (link público)

1. Sube todos los archivos a un repo de GitHub
   (IMPORTANTE: agrega `.streamlit/secrets.toml` al `.gitignore`)

2. Ve a https://share.streamlit.io
   - Conecta tu cuenta de GitHub
   - Selecciona el repo y el archivo `app.py`
   - Haz clic en **Deploy**

3. Agrega tu API key en Streamlit Cloud:
   - Settings → Secrets
   - Pega: `ANTHROPIC_API_KEY = "sk-ant-..."`

4. ¡Listo! Tendrás un link público para compartir y para el video.

---

## 🎥 Caso de prueba para el video

Usa este perfil para demostrar el chatbot en vivo:

**Turno 1:**
> "Estamos construyendo una app de pagos B2B para PyMEs en México.
> Estamos en etapa Seed, ya tenemos 15 clientes pagando."

**Turno 2:**
> "Nuestro mayor reto es escalar las ventas — tenemos buen producto
> pero el equipo comercial es débil. El objetivo es triplicar clientes
> en 6 meses."

**Turno 3:**
> "Prefiero un mentor muy hands-on que revise métricas conmigo.
> Puedo 2-3 sesiones al mes."

**Resultado esperado:** Ana Martínez como 🥇 (ventas B2B + fintech + seed)

---

## 🤖 AI usado en este proyecto

| Herramienta | Uso |
|-------------|-----|
| Claude (Anthropic) | Motor de matching y razonamiento |
| Claude API | Integración backend del chatbot |
| Streamlit | Framework de la web app |
| Claude (chat) | Diseño del sistema, prompts y código |
