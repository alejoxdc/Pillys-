# Backup Automático SCP

## 🎯 Descripción
Módulo de Odoo 17 que permite realizar backups automáticos de la base de datos cada 8 horas y enviarlos directamente a un servidor remoto utilizando protocolo SCP, **sin usar espacio en disco local**.

## ✨ Características Principales

- ⏰ **Backup automático cada 8 horas** (configurable)
- 🚀 **Envío directo por SCP** sin usar espacio local
- 🔐 **Autenticación SSH automática** con sshpass  
- 📊 **Interfaz web completa** con vistas Kanban, Lista y Formulario
- 📈 **Estadísticas detalladas** de backups realizados
- 🎮 **Backup manual** cuando sea necesario
- 🔄 **Estados configurables** (Activo/Inactivo/Borrador)

## 🛠️ Instalación

### 1. Instalar dependencias del sistema
```bash
sudo apt-get update
sudo apt-get install sshpass curl
```

### 2. Instalar el módulo
1. Copiar la carpeta `backup_auto_scp` en tu directorio de addons
2. Actualizar lista de aplicaciones en Odoo
3. Instalar el módulo "Backup Automático SCP"

## ⚙️ Configuración

### 1. Crear nueva configuración
- Ir a **Backup SCP > Configuraciones Backup**
- Hacer clic en **Crear**
- Completar los datos del servidor SSH:
  - **Servidor SSH**: Dirección IP del servidor remoto
  - **Usuario SSH**: Usuario con permisos de escritura
  - **Password SSH**: Contraseña del usuario
  - **Ruta en Servidor**: Directorio donde guardar los backups

### 2. Activar backup automático
- Abrir la configuración creada
- Hacer clic en **🟢 Activar Backup**
- El módulo comenzará a hacer backups cada 8 horas automáticamente

## 🎮 Uso

### Backup Manual
- Abrir cualquier configuración
- Hacer clic en **📤 Backup Manual**
- El backup se ejecutará inmediatamente

### Monitorear Backups
- Ver **estadísticas** en tiempo real
- **Próximo backup programado**
- **Resultado del último backup**
- **Tamaño de archivos** generados

## 🔧 Configuración Técnica

### Servidor de destino por defecto
```
Host: 5.78.131.185
Usuario: root  
Password: xApgsicXgqmX
Ruta: /home/a.fecol.digital/odoo17/backups/
```

### Cron automático
El módulo instala un cron que se ejecuta **cada 8 horas** y busca configuraciones activas para procesar automáticamente.

## 🛡️ Seguridad

- ✅ **Autenticación SSH automática** sin prompts interactivos
- ✅ **Creación automática** de directorios remotos
- ✅ **Validación de conexión** antes del envío
- ✅ **Logs detallados** para troubleshooting
- ✅ **No almacena archivos localmente** (ahorro de espacio)

## 📝 Archivos generados

Los backups se guardan con el formato:
```
backup_[database]_YYYY-MM-DD_HH-MM-SS.zip
```

Ejemplo:
```
backup_prueba13_2024-01-15_14-30-25.zip
```

## 🐛 Troubleshooting

### Error de conexión SSH
- Verificar conectividad: `ping [servidor]`
- Probar SSH manualmente: `ssh user@servidor`
- Verificar sshpass: `which sshpass`

### Error de espacio
- El módulo **NO usa espacio local**
- Verificar espacio en servidor remoto
- Verificar permisos de escritura en directorio destino

### Error de permisos
- Verificar usuario SSH tenga permisos de escritura
- Verificar directorio destino existe o puede crearse

## 📞 Soporte

Para soporte técnico, revisar los logs de Odoo en modo desarrollo o contactar al administrador del sistema.

---
**Desarrollado para Odoo 17.0** | **Versión 1.0.0**