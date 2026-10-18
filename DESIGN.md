# DESIGN.md — Diseño editorial de los documentos de TacticalGrid

`AGENTS.md` dice cómo se construye el proyecto; este archivo dice **cómo deben verse y leerse sus documentos**. Se
aplica a los dos entregables en Word: el documento técnico (`docs/entregables/documento-tecnico.docx`) y el manual de usuario
(`docs/entregables/manual-de-usuario.docx`). No se aplica a la interfaz Pygame ni al README.

La estructura sigue la convención de nueve secciones de los `DESIGN.md` de
[awesome-claude-design](https://github.com/VoltAgent/awesome-claude-design): tokens, reglas y su razón, para que
quien lo aplique pueda resolver también los casos que el archivo no cubre. Es un sistema propio, inspirado en las
documentaciones monocromas y de lectura cómoda (Stripe, Tailwind, Vercel, Linear, Mintlify); no copia ninguna marca.

---

## 1. Tema visual y atmósfera

- **Referente:** un libro técnico de calidad o una documentación web moderna. Sobrio, monocromo y con mucho aire.
- **Jerarquía por tamaño, peso y espacio**, nunca por color. El color solo separa superficies.
- **Cero azul.** Ni el azul de los títulos de Word ni el de los hipervínculos.
- **Plano.** Sin sombras, degradados, WordArt, íconos decorativos ni emojis.

## 2. Paleta de colores y roles

Escala pizarra (*slate*), la misma familia de grises fríos que usa Tailwind. Ningún otro color está permitido.

| Token | Hex | Rol |
|---|---|---|
| `titulo-portada` | `#27272A` | Título del documento (carbón). |
| `titulo` | `#1E293B` | Encabezados de nivel 1 a 3 (pizarra). |
| `texto` | `#334155` | Cuerpo, listas, celdas y enlaces. |
| `texto-secundario` | `#64748B` | Subtítulo, metadatos, pies de página, leyendas y la etiqueta del índice. |
| `borde-fuerte` | `#CBD5E1` | Línea bajo el encabezado de las tablas. |
| `borde` | `#E2E8F0` | Líneas horizontales de las tablas, divisores y marco del código. |
| `nota-borde` | `#94A3B8` | Barra izquierda de las notas y advertencias. |
| `superficie` | `#F8FAFC` | Fondo de las notas, del código y del encabezado de las tablas. |
| `fondo` | `#FFFFFF` | Página. |

**Enlaces:** color `texto` con subrayado fino. Nunca azul y nunca en negrita.

## 3. Tipografía

| Elemento | Fuente | Tamaño | Peso | Espacio antes / después | Interlineado |
|---|---|---:|---|---:|---:|
| Título del documento | Segoe UI Semibold | 26 pt | Seminegrita | 0 / 4 pt | 1,1 |
| Subtítulo | Segoe UI | 12 pt | Normal, `texto-secundario` | 0 / 24 pt | 1,2 |
| Encabezado 1 (capítulo) | Segoe UI Semibold | 18 pt | Seminegrita | 24 / 8 pt | 1,15 |
| Encabezado 2 | Segoe UI Semibold | 13 pt | Seminegrita | 18 / 6 pt | 1,2 |
| Encabezado 3 | Segoe UI Semibold | 11 pt | Seminegrita | 12 / 4 pt | 1,2 |
| Cuerpo | Segoe UI | 10 pt | Normal | 0 / 8 pt | 1,4 |
| Elementos de lista | Segoe UI | 10 pt | Normal | 0 / 4 pt | 1,35 |
| Celdas de tabla | Segoe UI | 8,5 pt | Normal; encabezado seminegrita | 2 / 2 pt | 1,2 |
| Código y rutas | Consolas | 8,5 pt | Normal | 6 / 10 pt | 1,25 |
| Pie de página | Segoe UI | 8 pt | Normal, `texto-secundario` | — | — |

- **Énfasis:** negrita moderada solo para la idea clave de un párrafo o el término que se define. A lo sumo una o dos
  por párrafo. Sin cursivas decorativas, sin subrayado como énfasis y sin mayúsculas sostenidas.
- **Números en tablas:** alineados a la derecha. Texto alineado a la izquierda. Nunca justificado.
- Segoe UI y Consolas vienen con Windows y Office. Si hace falta un PDF, se exporta desde Word, que incrusta las
  fuentes y evita la sustitución en otros equipos.

## 4. Componentes

### 4.1. Notas y advertencias

Todo dato crítico (una condición, un supuesto, una limitación o una advertencia de uso) va en un bloque de cita, **no
en una celda de tabla**:

```markdown
> **Nota:** Los tiempos dependen de la máquina; las conclusiones se basan en los contadores.

> **Advertencia:** Cambiar el orden de las acciones puede cambiar la acción elegida entre empatadas.
```

En Word: fondo `superficie`, barra izquierda de 3 pt `nota-borde`, sangría de 0,4 cm y relleno interno de 6 pt. La
etiqueta (`Nota:`, `Advertencia:`, `Importante:`) va en negrita y color `titulo`. Como máximo una nota por subsección.

### 4.2. Tablas

Se usan **solo para datos comparables**: métricas por algoritmo, criterios con pesos o una matriz de cumplimiento.
Una tabla se justifica si tiene al menos tres columnas que se comparan entre filas.

- **Sin bordes verticales.** Líneas horizontales de 0,5 pt `borde`; bajo el encabezado, 1 pt `borde-fuerte`.
- **Encabezado:** fondo `superficie`, seminegrita y repetido en cada página.
- Relleno de celda de 3 pt arriba y abajo y 5 pt a los lados. Ancho completo del texto.
- Ninguna fila se parte entre páginas.
- Una leyenda opcional va debajo, en `texto-secundario` de 8,5 pt.

### 4.3. Listas

- **Ordenadas (1, 2, 3) solo para pasos que se ejecutan en secuencia:** instalación, procedimiento experimental,
  reproducción.
- **Con viñeta** para enumeraciones sin orden.
- **Definiciones** (término en negrita seguido de dos puntos y su explicación) en lugar de tablas de dos columnas.

### 4.4. Código, comandos y diagramas

Bloque con fondo `superficie`, marco de 0,5 pt `borde` y Consolas de 8,5 pt. Las rutas y nombres del código dentro
del texto van en Consolas, sin fondo. Los diagramas de texto (flujo de datos, mapas) se mantienen como bloque de
código.

### 4.5. Divisores

Una línea horizontal de 0,5 pt `borde`, con 18 pt de espacio arriba y abajo, separa **solo**
capítulos o secciones macro. Nunca entre subsecciones.

### 4.6. Portada e índice

- **Portada:** título, subtítulo y los metadatos (equipo, curso, versión, fecha) como líneas cortas en
  `texto-secundario`, no como tabla.
- **Índice:** hasta el nivel 2, con la etiqueta "Contenido" en `texto-secundario`, seguido de un salto de página.

### 4.7. Pie de página

A la izquierda, el nombre del documento ("TacticalGrid · Documento técnico" o "TacticalGrid · Manual de usuario"); a
la derecha, el número de página. Todo en `texto-secundario` de 8 pt. Sin encabezado de página.

## 5. Distribución en la página

- Tamaño Carta, márgenes de 2,5 cm. El aire es parte del diseño.
- Un capítulo (encabezado 1) empieza en la misma página tras un divisor; solo la portada y el índice fuerzan un salto
  de página.
- Párrafos de 3 a 5 líneas. Si un párrafo supera 6 líneas, se divide o se convierte en lista.
- Ninguna sección encadena dos tablas sin una frase que explique qué se compara.

## 6. Profundidad y elevación

Ninguna: sin sombras, relieves, bordes redondeados ni cuadros de texto flotantes. La separación se logra con espacio,
una línea fina o el fondo `superficie`.

## 7. Sí y no

| Sí | No |
|---|---|
| Grises pizarra en títulos y enlaces | Azul de Word, hipervínculos azules o colores chillones |
| Notas en bloque de cita | Datos críticos dentro de una celda |
| Tablas para comparar datos | Tablas para pasos, flujos o listas de dos columnas |
| Listas ordenadas para instrucciones | Listas numeradas para enumeraciones sin orden |
| Oraciones cortas, voz activa, verbo al inicio de cada paso | Párrafos largos, voz pasiva o relleno |
| Divisor entre capítulos | Divisores entre subsecciones |
| Negrita para la idea clave | Negrita en frases enteras, cursiva o mayúsculas como énfasis |

## 8. Comportamiento al imprimir y exportar

- Mantener cada encabezado con el párrafo siguiente, y activar el control de viudas y huérfanas.
- Las tablas anchas reducen la letra hasta 8 pt. No se gira la página a horizontal.
- Si hace falta un PDF, exportarlo desde Word con las fuentes incrustadas.
- El documento debe leerse igual en escala de grises: ninguna información depende del color.

## 9. Guía para el agente

### 9.1. Rol

Actuar como **diseñador editorial y redactor técnico senior**. Aplicar este archivo de forma estricta, sin cambiar
el contenido técnico ni las cifras, que deben seguir coincidiendo con el código y las pruebas.

### 9.2. Estilo de redacción

- Minimalista, directo y orientado a la acción. Oraciones cortas, de no más de 25 palabras.
- Cada paso de una instrucción empieza con un verbo en imperativo: "Ejecuta", "Abre", "Compara".
- Sin relleno, sin repetir lo que dice una tabla y sin adjetivos de marketing.

### 9.3. Procedimiento para editar un documento en Word

1. Lee este archivo.
2. Abre el `.docx` en Word y edita el contenido con sus estilos, sin formato directo: Título, Título 1 a Título 3,
   Texto independiente, Texto de bloque para las notas y Source Code para comandos y diagramas.
3. Para un documento nuevo, parte de uno de los dos `.docx` existentes y reemplaza su contenido. Así hereda estilos,
   márgenes, pie de página y un tema sin azul. Un documento creado desde la plantilla normal de Word pinta de azul los
   títulos y los enlaces con los colores `accent1` y `hlink` del tema, aunque los estilos no lo pidan.
4. Si cambias una cifra, una regla o un comando, comprueba antes en la consola y con `python -m pytest` que el valor
   nuevo es el que produce el código.
5. Actualiza el índice: clic derecho sobre él, **Actualizar campos** y **Actualizar toda la tabla**.
6. Verifica con la lista de la sección 9.4.

### 9.4. Lista de verificación

- [ ] Ningún color fuera de la paleta en `word/document.xml`, `word/styles.xml` ni `word/theme/theme1.xml`, en
      particular ningún azul de Word (`0563C1`, `4472C4`, `2E74B5`, `1F4E79`, `4F81BD`).
- [ ] Los enlaces están en `#334155` y subrayados.
- [ ] Ninguna tabla describe pasos ni tiene solo dos columnas de texto.
- [ ] Cada dato crítico está en una nota con su etiqueta en negrita.
- [ ] Hay divisores solo entre capítulos.
- [ ] Las tablas no tienen bordes verticales y su encabezado se repite en cada página.
- [ ] La portada no usa tablas, el índice llega hasta el nivel 2 y el pie de página muestra el número de página.
- [ ] El documento se lee igual en escala de grises.
- [ ] Las cifras y los comandos coinciden con el código: `python -m pytest` pasa y cada comando citado produce el
      resultado que el documento reporta.
