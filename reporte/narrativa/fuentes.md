### Interpretación: qué se puede y qué no se puede afirmar sobre las fuentes

El centroide ponderado ubica las cuatro estimaciones en el **norte de Itagüí**, alrededor de la Avenida
Carrera 42 *(fuente: `artefactos/indicadores/fuentes_estimadas.csv`; nombre de la vía según Nominatim de
OpenStreetMap)*. Pero la misma cuenta no significa lo mismo en los cuatro canales, porque en esta banda
**no transmite el mismo tipo de equipo**:

| Canal | Atribución en Colombia | Quién transmite |
|---|---|---|
| A (840-845 MHz) | IMT, 824-849 MHz (banda celular de 850 MHz) | Teléfonos celulares (enlace de subida) |
| B (845-850 MHz) | IMT, hasta 849 MHz | Teléfonos celulares (enlace de subida) |
| C (850-855 MHz) | Trunking, 851-869 MHz | Estaciones base fijas |
| D (855-860 MHz) | Trunking, 851-869 MHz | Estaciones base fijas |

*(fuentes: Resolución ANE 648 de 2023, bandas IMT; Resolución ANE 105 de 2020, plan de trunking
806-824 / 851-869 MHz, donde la estación base transmite en `Fm + 45 MHz`)*

**Canal C: fuente fija localizada (conclusión más sólida).** La potencia del canal alcanza su máximo en las
capturas 024 y 025 (+3,9 y +0,5 dBm) y cae con la distancia: 023 marca −6,3 dBm, 026 −20,7 dBm y 027
−28,9 dBm *(fuente: `artefactos/indicadores/potencia_canal_captura.csv`)*. Ese patrón corresponde a un
transmisor fijo cercano. La fuente más probable es **una estación base de trunking a unos 500 m de las
capturas 024-025, en el norte de Itagüí**. En esa zona están, como referencia, la planta de concentrado
Agro Colanta (a 91 m de la captura 024), el Centro Comercial Itagüí (a 560 m) y la estación Itagüí del
Metro (a 630 m), todos según OpenStreetMap. Esta ubicación es más precisa que la del centroide (±2,3 km).

**Canal D: no se puede señalar un lugar.** Sus máximos están repartidos en las capturas 045, 031, 034 y
028. Eso es compatible con varias estaciones base, o con una sola de cobertura amplia.

**Canales A y B: no tienen una fuente única.** Lo que se midió en estos canales son teléfonos transmitiendo
hacia sus estaciones base. Los picos del canal B, entre −2 y −5 dBm, aparecen dispersos en las capturas
020, 024, 028, 031 y 045. Para A y B el centroide indica, a lo sumo, una **zona de alto tráfico móvil**
(Metro, centros comerciales, vías principales), **no un emisor que se pueda ubicar**.

**Lo que no se puede afirmar:**

- **Qué antena exacta es.** OpenStreetMap solo registra 3 antenas de telecomunicaciones en el sur del
  valle, y ninguna está dentro de los círculos de incertidumbre; la más cercana está a unos 3,8 km. Para
  identificar el transmisor del canal C hace falta el registro de estaciones licenciadas de la ANE.
- **Si la planta industrial contribuye.** La captura 024 tiene además el piso de ruido 21,8 dB por encima
  de la mediana. Eso es compatible con ruido industrial de banda ancha de la planta cercana, pero también
  con el efecto de la portadora del canal C, que en ese punto es la más fuerte del estudio. Con estos datos
  las dos explicaciones no se pueden separar, y la evidencia del canal C favorece la del transmisor.

*Las ubicaciones y nombres de lugares provienen de OpenStreetMap (Overpass y Nominatim, licencia ODbL),
consultados el 26 de septiembre de 2026. No forman parte del pipeline, que funciona sin conexión.*
