# Decisiones funcionales confirmadas

Registro de aclaraciones del responsable del proyecto. Estas decisiones complementan el plan maestro sin marcar requisitos como terminados antes de verificarlos.

## 19 de octubre de 2026

### Planes SaaS y administración

- Los precios, límites, capacidades, presentación visual y demás datos comerciales de los tres planes se administrarán desde backend; no quedarán codificados únicamente en las interfaces.
- El administrador maestro podrá configurar las plantillas globales y los planes de cualquier empresa.
- El administrador del tenant contará con una vista administrativa diferente a la del cliente y podrá configurar precio, contenido y presentación de sus planes únicamente dentro de su propia empresa. Los cambios de un tenant nunca afectarán a otra empresa ni a las plantillas globales.
- El tercer plan continuará siendo configurable. Su nombre, precio y capacidades iniciales no se considerarán definidos hasta crear o editar su configuración administrativa.

### Reservas y recogida

- Una reserva puede registrarse a cualquier hora del día.
- El cliente debe elegir la fecha y hora en que pasará a recoger la prenda.
- La recogida solo puede programarse dentro del horario de atención configurado por el tenant para la sucursal elegida.
- La fecha de recogida no puede superar tres días desde el registro de la reserva.
- Para conservar compatibilidad con clientes anteriores, si un cliente API antiguo omite la hora se usa temporalmente la hora de apertura; las interfaces nuevas sí exigen selección explícita.

### Git y despliegue

- Se autorizan commits en los tres repositorios después de ejecutar las verificaciones correspondientes.
- Los mensajes serán breves, descriptivos y naturales.
- Esta autorización no incluye `push` ni despliegue automático; estos requieren instrucción explícita porque modifican los entornos publicados.
