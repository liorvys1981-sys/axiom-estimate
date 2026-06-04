# axiom-estimate
Axiom Estimate plataforma SaaS de estimación automotriz autónoma, basada en multi-agentes de IA y arquitectura orientada a eventos. El backend será con Python (FastAPI), preparado para la integración modular de agentes autónomos (Visión, Inferencia Mecánica,
Extracción de Labor y Suministro Autónomo). Incluir:
app/main.py con FastAPI básica y rutas de salud
app/agents/ con carpetas para cada agente y init.py app/api/ con ejemplo de endpoint principal de ingesta
tests/ con test básico
Dockerfile y docker-compose.yml para desarrollo requirements.txt con FastAPI, Uvicorn y paquetes básicos .github/workflows/ci.yml para flujo de Cl (test y lint)
README.md profesional (ya provisto)
Esta plataforma estará lista para ser extendida en agentes especializados, siguiendo una arquitectura escalable y modular, orientada a MVP por fases.

