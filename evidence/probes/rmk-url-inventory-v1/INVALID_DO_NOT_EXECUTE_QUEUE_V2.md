# INVALID_DO_NOT_EXECUTE — ordered queue V2

`rmk_ordered_payload_queue_v2.csv` no debe ejecutarse. Deduplicó correctamente
63 URLs, pero una indexación escalar de PowerShell truncó todas las fechas al
primer carácter (`2`), reduciendo falsamente los pares a uno. Se preserva como
evidencia adversa. La sucesora válida es V3.
