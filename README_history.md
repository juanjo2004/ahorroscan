# Modo histórico V2

Este parche activa el histórico de precios de forma conservadora.

- 0-2 muestras previas: el histórico no modifica el Deal Score.
- 3-6 muestras: empieza a aportar, con confianza 0.50.
- 7-13 muestras: confianza 0.75.
- 14+ muestras: confianza 1.00.
- Se comparan el precio actual contra la media de 30 días y contra el mínimo previo.
- El snapshot del día actual se sigue excluyendo del histórico, evitando que un precio se compare consigo mismo.
- No conecta Telegram ni altera V1.
