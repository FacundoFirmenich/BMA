# Revalidación pública ATLAS/TBAuctions — 2026-08-10

Estado: `PARTNERSHIP_REQUIRED`; revisión remota, sólo lectura.

La documentación pública actual confirma que ATLAS es infraestructura de TBAuctions, que Troostwijk opera B2B en más de veinte países europeos y que el portal exige una cuenta ATLAS Developer para realizar solicitudes. También confirma la separación material: las subastas se ejecutan en plataformas externas y ATLAS expone tras el cierre datos de orden; una orden es un lote vendido y pagado. Las órdenes tienen estados documentados, incluidos `Cancelled` y `Completed`.

Esto respalda mantener ATLAS como candidato de eventos post-subasta europeos, pero no cierra ningún gate de BMA. La documentación establece alcance por compañía/comprador y acceso autenticado; no demuestra una vista de mercado completa, densidad diaria, histórico exportable, semántica de impuestos/comisiones/cantidad, ni licencia de entrenamiento y derivados. No se creó cuenta, no se contactó a TBAuctions, no se aceptaron términos y no se descargó RAW.

La siguiente acción discriminante autorizable sólo con consentimiento expreso es solicitar una cuenta o una muestra mínima remota y contrastarla contra los diez gates de `EU_INDUSTRIAL_DAILY_SOURCE_ACQUISITION_V0_7_0.json`. Hasta entonces, `source_access_verified`, `coverage_verified`, `training_authorized`, `industrial_validation` y `BIND_pilot_ready` continúan en `false`.

Fuentes consultadas: `https://apidocs.tbauctions.com/` y `https://apidocs.tbauctions.com/getting-started`.
