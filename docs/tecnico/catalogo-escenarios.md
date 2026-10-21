# Catálogo y clasificación de escenarios

El catálogo se comprobó el 20 de octubre de 2026 cargando cada JSON con `cargar_escenario`. La carga valida dimensiones,
terrenos, costos, posiciones, unidades, turno y coherencia del recurso; los escenarios pequeños se conservan para
propiedades concretas y no se rechazan como entradas externas.

| Archivo | Clasificación | Tamaño | Unidades A/B | Uso |
|---|---|---:|---:|---|
| `arquitectura_basica.json` | Principal de desarrollo | 20 × 20 | 3 / 3 | Escenario base de arquitectura y desarrollo |
| `campo_20x20.json` | Principal de desarrollo y búsqueda | 20 × 20 | 3 / 3 | Caso grande, comparación BFS/DFS, Beam y adversarial |
| `ejemplo_enunciado.json` | Ejemplo compacto de interoperabilidad | 4 × 4 | 2 / 2 | Reproduce el ejemplo pequeño del enunciado; no se presenta como JSON externo del profesor |
| `ruta_corta_vs_economica.json` | Experimento mínimo | 5 × 9 | 3 / 3 | Diferencia longitud BFS de costo UCS |
| `obstaculo_rodeo.json` | Experimento mínimo | 8 × 7 | 3 / 3 | Rodeo de barrera y comparación Manhattan/HTO |
| `recurso_en_transporte.json` | Experimento mínimo de partida/adversarial | 6 × 8 | 3 / 3 | Portador inicial, alfa-beta, turnos y efecto del orden/profundidad |
| `estado_compuesto_libre.json` | Experimento adversarial | 5 × 5 | 3 / 3 | Recurso libre y estados compuestos |
| `estado_compuesto_portador.json` | Experimento adversarial | 5 × 5 | 3 / 3 | Mismas posiciones, portador asignado |
| `decision_adversarial.json` | Experimento adversarial | 3 × 6 | 3 / 3 | Riesgo de tomar el recurso y respuesta del rival |
| `caso_06_estado_compuesto_libre_20x20.json` | Variante académica | 20 × 20 | 3 / 3 | Estado compuesto con recurso libre; topología original 5 × 5 aislada por muros |
| `caso_06_estado_compuesto_portador_20x20.json` | Variante académica | 20 × 20 | 3 / 3 | Mismas posiciones que la variante libre; A1 lleva el recurso |
| `caso_07_decision_adversarial_20x20.json` | Variante académica | 20 × 20 | 3 / 3 | Profundidades 1–4; región 3 × 6 y muros exteriores |
| `caso_08_minimax_alfa_beta_20x20.json` | Variante académica | 20 × 20 | 3 / 3 | Equivalencia Minimax/alfa-beta y poda; región 6 × 8 y muros exteriores |
| `caso_10_profundidad_20x20.json` | Variante académica | 20 × 20 | 3 / 3 | Mismo estado base del caso 8, con foco en profundidad 1–4 |
| `prueba_gui_partida.json` | Fixture de validación manual de GUI | 5 × 5 | 3 / 3 | Recogida, turno de B, transporte, victoria, historial y replay; no es escenario principal de desarrollo |

Los dos escenarios principales satisfacen simultáneamente el mínimo de 20 × 20 y tres unidades por bando. Los casos
didácticos pequeños se conservan y se complementan con variantes 20 × 20. Estas mantienen la región transitable
original y rodean la extensión con muros; las pruebas comparan resultados y contadores para demostrar que la
topología y el comportamiento buscado se conservan. El fixture GUI sigue siendo deliberadamente compacto para que
un equipo pueda probar entrega y victoria en cinco jugadas sin alterar las reglas.

Todos los archivos de la tabla cargaron sin errores. La validez sintáctica del formato no certifica por sí sola cada
propiedad; los resultados 20 × 20 y sus hashes se conservan aparte en `docs/experimentos/resultados-casos-minimos.json`.
