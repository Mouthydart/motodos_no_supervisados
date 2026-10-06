# ===============================================================
# Modelo de aprendizaje NO supervisado - Transmilenio
# Objetivo: agrupar (clustering) las estaciones según su
# comportamiento, SIN usar ninguna variable objetivo.
# Ejecución:  python clustering_transmilenio.py
# Requisitos: pip install pandas numpy scikit-learn matplotlib
# ===============================================================

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # permite guardar gráficas sin abrir ventanas
import matplotlib.pyplot as plt

from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score

np.random.seed(42)
pd.set_option("display.width", 200)       # evita que las tablas se corten
pd.set_option("display.max_columns", None)

# ---------------------------------------------------------------
# 1. HECHOS DEL PROYECTO ORIGINAL (conexiones y tiempos)
# ---------------------------------------------------------------
Hechos = [
    ("Portal Norte", "Toberín", 4), ("Toberín", "Calle 146", 3),
    ("Calle 146", "Pepe Sierra", 4), ("Pepe Sierra", "Calle 100", 3),
    ("Calle 100", "Héroes", 5), ("Héroes", "Calle 72", 3),
    ("Calle 72", "Calle 45", 5), ("Calle 45", "Calle 26", 4),
    ("Calle 26", "Av. Jiménez", 4), ("Av. Jiménez", "Tercer Milenio", 3),
    ("Av. Jiménez", "De La Sabana", 3), ("De La Sabana", "Ricaurte", 4),
    ("Ricaurte", "Pradera", 5), ("Pradera", "Banderas", 6),
    ("Banderas", "Portal Américas", 5), ("Calle 26", "Centro Memoria", 3),
    ("Centro Memoria", "CAD", 4), ("CAD", "Av. Rojas", 6),
    ("Av. Rojas", "Portal El Dorado", 5), ("Ricaurte", "Paloquemao", 3),
    ("Paloquemao", "CAD", 5),
]

# ---------------------------------------------------------------
# 2. CONSTRUCCIÓN DEL DATASET (una fila por estación)
# Las variables de red salen de los Hechos. Las de demanda se
# SIMULAN, porque no hay datos públicos con este nivel de detalle.
# ---------------------------------------------------------------
def construir_dataset():
    vecinos = {}
    for a, b, t in Hechos:
        vecinos.setdefault(a, []).append(t)
        vecinos.setdefault(b, []).append(t)

    filas = []
    for estacion, tiempos in vecinos.items():
        conexiones = len(tiempos)
        es_portal = 1 if estacion.startswith("Portal") else 0
        es_transbordo = 1 if conexiones >= 3 else 0

        # Demanda simulada: portales y estaciones de transbordo mueven más gente
        if es_portal:
            base, pico = 38000, 0.45
        elif es_transbordo:
            base, pico = 30000, 0.38
        else:
            base, pico = 12000, 0.30
        afluencia = int(np.random.normal(base, base * 0.12))
        pct_pico = float(np.clip(np.random.normal(pico, 0.03), 0.1, 0.7))

        filas.append([estacion, conexiones, round(np.mean(tiempos), 2),
                      es_portal, afluencia, round(pct_pico, 3)])

    columnas = ["estacion", "conexiones", "tiempo_prom_vecinas",
                "es_portal", "afluencia_diaria", "pct_hora_pico"]
    return pd.DataFrame(filas, columns=columnas)


df = construir_dataset()
df.to_csv("dataset_estaciones.csv", index=False)

# ---------------------------------------------------------------
# 3. EXPLORACIÓN
# ---------------------------------------------------------------
print("=== Primeras filas ===")
print(df.head())
print("\n=== Estadísticas ===")
print(df.describe().round(2))
print("\nValores nulos:", df.isnull().sum().sum())

# ---------------------------------------------------------------
# 4. PREPROCESAMIENTO
# K-Means usa distancias, así que todas las variables deben tener
# la misma escala (si no, "afluencia" dominaría a las demás).
# Nota: NO hay variable objetivo; el nombre de la estación no se usa.
# ---------------------------------------------------------------
variables = ["conexiones", "tiempo_prom_vecinas", "es_portal",
             "afluencia_diaria", "pct_hora_pico"]
X = StandardScaler().fit_transform(df[variables])

# ---------------------------------------------------------------
# 5. ELEGIR EL NÚMERO DE GRUPOS (k)
# Método del codo (inercia) y coeficiente de silueta
# ---------------------------------------------------------------
ks = range(2, 7)
inercias, siluetas = [], []
for k in ks:
    km = KMeans(n_clusters=k, n_init=10, random_state=42).fit(X)
    inercias.append(km.inertia_)
    siluetas.append(silhouette_score(X, km.labels_))

print("\n=== Selección de k ===")
for k, i, s in zip(ks, inercias, siluetas):
    print(f"k={k} | inercia={i:.2f} | silueta={s:.3f}")

# Con k=2 solo se separan los portales del resto (poco útil para operar).
# Por eso se elige el k con mejor silueta exigiendo al menos 3 grupos.
candidatos = [(s, k) for k, s in zip(ks, siluetas) if k >= 3]
mejor_k = max(candidatos)[1]
print(f"\nMejor k según silueta (k >= 3): {mejor_k}")

fig, ax = plt.subplots(1, 2, figsize=(10, 4))
ax[0].plot(list(ks), inercias, "o-")
ax[0].set_title("Método del codo")
ax[0].set_xlabel("k")
ax[0].set_ylabel("Inercia")
ax[1].plot(list(ks), siluetas, "o-", color="green")
ax[1].set_title("Coeficiente de silueta")
ax[1].set_xlabel("k")
ax[1].set_ylabel("Silueta")
plt.tight_layout()
plt.savefig("grafica_codo_silueta.png", dpi=120)
plt.close()

# ---------------------------------------------------------------
# 6. MODELO FINAL K-MEANS
# ---------------------------------------------------------------
modelo = KMeans(n_clusters=mejor_k, n_init=10, random_state=42)
df["grupo"] = modelo.fit_predict(X)
df.to_csv("estaciones_agrupadas.csv", index=False)

# ---------------------------------------------------------------
# 7. INTERPRETACIÓN: perfil de cada grupo y estaciones que contiene
# ---------------------------------------------------------------
print("\n=== Perfil promedio de cada grupo ===")
print(df.groupby("grupo")[variables].mean().round(2))

print("\n=== Estaciones por grupo ===")
for g in sorted(df["grupo"].unique()):
    print(f"Grupo {g}: {', '.join(df[df['grupo'] == g]['estacion'])}")

# ---------------------------------------------------------------
# 8. VISUALIZACIÓN CON PCA (reduce 5 variables a 2 dimensiones)
# ---------------------------------------------------------------
pca = PCA(n_components=2)
coords = pca.fit_transform(X)
print(f"\nVarianza explicada por PCA (2 comp.): "
      f"{pca.explained_variance_ratio_.sum():.1%}")

plt.figure(figsize=(8, 6))
plt.scatter(coords[:, 0], coords[:, 1], c=df["grupo"], cmap="viridis", s=90)
for i, nombre in enumerate(df["estacion"]):
    plt.annotate(nombre, (coords[i, 0], coords[i, 1]), fontsize=7,
                 xytext=(4, 4), textcoords="offset points")
plt.title("Grupos de estaciones de Transmilenio (K-Means + PCA)")
plt.xlabel("Componente principal 1")
plt.ylabel("Componente principal 2")
plt.tight_layout()
plt.savefig("grafica_grupos_pca.png", dpi=120)
plt.close()

# ---------------------------------------------------------------
# 9. CLASIFICAR UNA ESTACIÓN NUEVA (inferencia)
# ---------------------------------------------------------------
escalador = StandardScaler().fit(df[variables])
nueva = pd.DataFrame([{"conexiones": 3, "tiempo_prom_vecinas": 4.5,
                       "es_portal": 0, "afluencia_diaria": 28000,
                       "pct_hora_pico": 0.40}])
grupo_nuevo = modelo.predict(escalador.transform(nueva))[0]
print(f"\nEstación nueva (3 conexiones, 28000 pasajeros/día) -> Grupo {grupo_nuevo}")
