# AhorroScan · matriz de monetización multicanal

Actualizada 2026-09-23. Documento de trabajo, no implica que un programa concreto esté aprobado para AhorroScan.

## Canales y prioridad de fuentes

| Canal | Familias | Fuentes iniciales | Redes a investigar |
|---|---|---|---|
| Tech | tecnología | Amazon, AliExpress | Awin, TradeTracker, Webgains |
| Hogar | hogar | Amazon, AliExpress, AWIN | TradeTracker, Webgains |
| Moda | moda | Amazon, AliExpress | Awin, Webgains, TradeTracker |
| Belleza | belleza | Amazon, AliExpress | Awin, Webgains, TradeTracker |
| Familia | bebé/juguetes | Amazon, AliExpress | Awin, Webgains, TradeTracker |
| Deporte | fitness/outdoor | Amazon, AliExpress | Awin, Webgains, TradeTracker |
| Mascotas | mascotas | Amazon, AliExpress | Awin, Webgains, TradeTracker |
| Automóvil | motor/movilidad | Amazon, AliExpress | Awin, Webgains, TradeTracker |
| Bricolaje | herramientas/jardín | Amazon, AliExpress | Awin, Webgains, TradeTracker |
| Viajes | equipaje/viajes | no depender solo de retail | Awin, TradeTracker, Webgains |

## Redes verificadas para la expansión

### Awin
Awin comunica actualmente más de 30.000 marcas y cubre sectores como retail, moda, belleza, tecnología y viajes. Su página española para partners indica acceso a marcas y herramientas de tracking; la aceptación de cada programa depende de sus criterios. Entre las marcas mostradas por Awin figuran AliExpress, Booking.com, Decathlon, Dyson, Nike, Samsung, Sephora, Sixt, TUI y otras. Revisar programa por programa antes de automatizar publicaciones.

### TradeTracker
TradeTracker España dispone de red de afiliación para publishers, acceso a múltiples anunciantes y herramientas/API para automatización, feeds y cupones. La disponibilidad y condiciones deben comprobarse dentro de cada campaña.

### Webgains
Webgains España comunica más de 1.800 anunciantes, 250.000 afiliados y presencia en más de 150 países. Declara sectores especialmente relevantes para nuestra expansión: moda y joyería, salud y belleza, viajes y hoteles, hogar y jardín, electrónica y gadgets, motor, alimentación y deporte/ocio.

## Regla de ingeniería
Las fuentes y redes no se codifican dentro de cada canal. Se deben registrar como proveedores reutilizables:

`merchant/network -> familia -> categorías -> feed/API -> tracking -> reglas editoriales -> canal(es)`

Así un mismo anunciante puede alimentar varios canales sin duplicar integraciones.
