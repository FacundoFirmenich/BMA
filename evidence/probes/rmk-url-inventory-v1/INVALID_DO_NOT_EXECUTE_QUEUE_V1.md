# INVALID_DO_NOT_EXECUTE — ordered queue V1

`rmk_ordered_payload_queue_with_head.csv` no debe ejecutarse. Contiene 83 filas
para 63 URLs porque conserva múltiples páginas de descubrimiento como filas de
adquisición. Ejecutarla podría abrir el mismo payload más de una vez y duplicar
evidencia. Se preserva como intento fallido. La sucesora válida es V3.
